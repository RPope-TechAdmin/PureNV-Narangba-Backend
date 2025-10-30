import os
import smtplib
from email.message import EmailMessage

def send_email(recipient: str, subject: str, body: str) -> None:
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    if not sender or not password:
        raise EnvironmentError("Missing EMAIL_USER or EMAIL_PASS environment variables")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(sender, password)
        smtp.send_message(msg)
