# streamlit_app.py
import streamlit as st, requests, json

st.title("Send Email")

to = st.tags_input("To", suggestions=[]) if hasattr(st, "tags_input") else st.text_input("To (comma-separated)")
cc = st.text_input("CC (comma-separated)")
subject = st.text_input("Subject")
html = st.text_area("HTML Body", height=240)

if st.button("Send"):
    payload = {
        "to": [x.strip() for x in (to if isinstance(to, list) else to.split(",")) if x.strip()],
        "cc": [x.strip() for x in cc.split(",") if x.strip()],
        "subject": subject,
        "html": html,
    }
    try:
        r = requests.post("http://mail-api:8000/api/send-mail", json=payload, timeout=30)
        r.raise_for_status()
        st.success("Email sent ✅")
    except Exception as e:
        st.error(f"Failed to send: {e}")
