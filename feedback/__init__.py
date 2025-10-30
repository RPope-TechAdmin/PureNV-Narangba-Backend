import logging
import azure.functions as func
import os
import json
import time
import pymssql
from send_email import send_email

logging.info("📦 Deployed site packages: %s", os.listdir('/home/site/wwwroot/.python_packages/lib/site-packages'))

cors_headers = {
    "Access-Control-Allow-Origin": "https://victorious-pond-02e3be310.2.azurestaticapps.net",
    "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
    "Access-Control-Allow-Headers": "Content-Type, Accept",
    "Access-Control-Max-Age": "86400"
}

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

    logging.info(f"INSERT INTO Narangba.Feedback (Name, Feedback) VALUES ('{name}', '{feedback}')")

    try:
        username = os.environ["SQL_USER"]
        password = os.environ["SQL_PASSWORD"]
        server = os.environ["SQL_SERVER"]
        db = os.environ["SQL_DB"]
        table="[Narangba].[Feedback]"
        variables="[Name], [Feedback]"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with pymssql.connect(server, username, password, db) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(f"INSERT INTO {table} ({variables}) VALUES ('{name}', '{feedback}');")
                    conn.commit()
                break
            except pymssql.OperationalError as e:
                if attempt < max_retries - 1:
                        logging.warning(f"Retrying DB connection in 5 seconds... Attempt {attempt + 1}")
                        time.sleep(5)
                else:
                    raise

        logging.info("✅ Feedback saved to SQL database")
        try:
            recipient=os.env["FEEDBACK_RECIPIENT"]
            subject="New Feedback for Narangba Dashboard!"
            body=("Hey," \
            "" \
            "Congratulations! Someone has uploaded some feedback into the Narangba Dashboard. You should go check it out!"
            )

            send_email(recipient, subject, body)
            
        except Exception as e:
            logging.exception(f"❌ Error sending email: {e}")

    except Exception as e:
        logging.exception("❌ Database error")
        return func.HttpResponse(
            json.dumps({"error": "Server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

    return func.HttpResponse(
        json.dumps({"code": 200, "message": "Feedback submitted successfully."}),
        status_code=200,
        mimetype="application/json",
        headers=cors_headers
    )
