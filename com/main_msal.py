# app/main.py
from fastapi import FastAPI, Request, HTTPException
import msal, os, requests

app = FastAPI()

TENANT_ID = os.environ["AZURE_TENANT_ID"]
CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]

def _get_user_access_token(req: Request) -> str:
    auth = req.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1]
    xauth = req.headers.get("x-auth-request-access-token")
    if xauth:
        return xauth
    raise HTTPException(status_code=401, detail="No user access token from OAuth2 Proxy")

def _obo_graph_token(user_access_token: str) -> str:
    cca = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY,
    )
    result = cca.acquire_token_on_behalf_of(user_access_token, scopes=SCOPES)
    if "access_token" not in result:
        raise HTTPException(status_code=502, detail=f"OBO failed: {result}")
    return result["access_token"]

@app.post("/api/send-mail")
async def send_mail(req: Request, body: dict):
    user_token = _get_user_access_token(req)
    graph_token = _obo_graph_token(user_token)

    payload = {
        "message": {
            "subject": body.get("subject", "No subject"),
            "body": {"contentType": "HTML", "content": body.get("html", "")},
            "toRecipients": [{"emailAddress": {"address": a}} for a in body.get("to", [])],
        },
        "saveToSentItems": True,
    }
    r = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={"Authorization": f"Bearer {graph_token}", "Content-Type": "application/json"},
        json=payload, timeout=20
    )
    if r.status_code not in (200, 201, 202, 204):
        raise HTTPException(status_code=502, detail=r.text)
    return {"status": "sent"}
