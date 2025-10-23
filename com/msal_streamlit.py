import os, requests, streamlit as st

TENANT_ID     = os.environ["AZURE_TENANT_ID"]
CLIENT_ID     = os.environ["AZURE_CLIENT_ID"]
CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
TOKEN_URL     = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

def get_app_token() -> str:
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default",
    }
    r = requests.post(TOKEN_URL, data=data, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]

st.header("Service Mail Sender (App-only)")

user_upn = st.text_input("Send as mailbox (UPN or shared mailbox)")
to       = st.text_input("To (comma-separated)")
subject  = st.text_input("Subject")
html     = st.text_area("HTML Body", height=220)

if st.button("Send"):
    try:
        token = get_app_token()
        payload = {
            "message": {
                "subject": subject or "No subject",
                "body": {"contentType": "HTML", "content": html or ""},
                "toRecipients": [{"emailAddress": {"address": a.strip()}} for a in to.split(",") if a.strip()],
            },
            "saveToSentItems": True,
        }
        r = requests.post(
            f"https://graph.microsoft.com/v1.0/users/{user_upn}/sendMail",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload, timeout=20
        )
        r.raise_for_status()
        st.success("Email sent ✅")
    except Exception as e:
        st.error(f"Failed: {e}")


'''

{
  "to": ["john.doe@t-mobile.com", "jane.doe@t-mobile.com"],
  "cc": ["manager@t-mobile.com"],
  "subject": "Test Email from FastAPI",
  "html": "<h3>Hello Team,</h3><p>This is an automated email sent via <b>FastAPI + Outlook Graph API</b>.</p><br><p>Regards,<br>Nitin</p>"
}




-----------------

provider = "azure"
pass_access_token = true
pass_authorization_header = true
set_xauthrequest = true
pass_user_headers = true
pass_host_header = true

# Optional: pass ID token if you also want user info
pass_id_token = true
'''