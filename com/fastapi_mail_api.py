# fastapi_mail_api.py
import os, requests
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

TENANT_ID     = os.environ["AZURE_TENANT_ID"]
CLIENT_ID     = os.environ["AZURE_CLIENT_ID"]       # your server app reg
CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
TOKEN_URL     = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_SCOPE   = "https://graph.microsoft.com/.default"

def obo_exchange(user_access_token: str) -> str:
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "requested_token_use": "on_behalf_of",
        "scope": GRAPH_SCOPE,
        "assertion": user_access_token,
    }
    r = requests.post(TOKEN_URL, data=data, timeout=20)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"OBO failed: {r.text}")
    return r.json()["access_token"]

def get_user_access_token(req: Request) -> str:
    # Ensure oauth2-proxy is set with: --pass-access-token --pass-authorization-header --set-xauthrequest
    auth = req.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1]
    xauth = req.headers.get("x-auth-request-access-token")
    if xauth:
        return xauth
    raise HTTPException(status_code=401, detail="No user access token from OAuth2 Proxy.")

@app.post("/api/send-mail")
async def send_mail(req: Request, body: dict):
    user_token  = get_user_access_token(req)
    graph_token = obo_exchange(user_token)

    payload = {
        "message": {
            "subject": body.get("subject", "No subject"),
            "body": {"contentType": "HTML", "content": body.get("html", "")},
            "toRecipients": [{"emailAddress": {"address": addr}} for addr in body.get("to", [])],
            "ccRecipients": [{"emailAddress": {"address": addr}} for addr in body.get("cc", [])],
        },
        "saveToSentItems": True,
    }

    r = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={"Authorization": f"Bearer {graph_token}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    if r.status_code not in (202, 200, 201, 204):
        raise HTTPException(status_code=502, detail=f"Graph sendMail failed: {r.text}")
    return {"status": "sent"}


@app.get("/debug/headers")
async def debug_headers(request: Request):
    return dict(request.headers)