import logging
import azure.functions as func
import os
import json
import time
import pymssql
import smtplib
from email.message import EmailMessage

cors_headers = {
    "Access-Control-Allow-Origin": "https://victorious-pond-02e3be310.2.azurestaticapps.net",
    "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
    "Access-Control-Allow-Headers": "Content-Type, Accept",
    "Access-Control-Max-Age": "86400"
}

def send_email(recipient: str, subject: str, body: str) -> None:
    sender = os.getenv("EMAIL_USER")
    eml_pass = os.getenv("EMAIL_PASS")

    if not sender or not eml_pass:
        raise EnvironmentError("Missing EMAIL_USER or EMAIL_PASS environment variables")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(sender, eml_pass)
        smtp.send_message(msg)

def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=cors_headers)

    try:
        data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON"}),
            status_code=400,
            mimetype="application/json"
        )

    name = data.get("name")
    feedback = data.get("feedback")

    if not name or not feedback:
        return func.HttpResponse(
            json.dumps({"error": "Both 'name' and 'feedback' are required."}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        sql_user = os.getenv("SQL_USER")
        sql_password = os.getenv("SQL_PASSWORD")
        sql_server = os.getenv("SQL_SERVER")
        sql_db = os.getenv("SQL_DB")

        table = "[Narangba].[Feedback]"
        columns = "[Name], [Feedback]"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with pymssql.connect(sql_server, sql_user, sql_password, sql_db) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            f"INSERT INTO {table} ({columns}) VALUES (%s, %s);",
                            (name, feedback)
                        )
                    conn.commit()
                break
            except pymssql.OperationalError as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Retrying DB connection in 5 seconds... Attempt {attempt + 1}")
                    time.sleep(5)
                else:
                    raise

        recipient = "rpope@purenv.au"
        subject = "New Feedback for Narangba Dashboard!"
        body = (
            "Hey,\n\n"
            "Congratulations! Someone has uploaded feedback into the Narangba Dashboard.\n"
            "You should go check it out!"
        )
        send_email(recipient, subject, body)

    except Exception as e:
        logging.exception("❌ Server error")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

    return func.HttpResponse(
        json.dumps({"code": 200, "message": "Feedback submitted successfully."}),
        status_code=200,
        mimetype="application/json",
        headers=cors_headers
    )
