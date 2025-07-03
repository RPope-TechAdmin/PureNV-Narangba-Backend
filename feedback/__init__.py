import logging
import azure.functions as func
import os
import json
import pyodbc
from sqlalchemy import create_engine, text

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

    try:
        username = os.environ["SQL_USER"]
        password = os.environ["SQL_PASSWORD"]
        server = os.environ["SQL_SERVER"]
        db = os.environ["SQL_DB"]

        connection_string = (
            f"mssql+pyodbc://{username}:{password}@{server}:1433/{db}"
            "?driver=ODBC+Driver+18+for+SQL+Server"
            "&encrypt=yes"
            "&trustServerCertificate=no"
        )

        engine = create_engine(connection_string, connect_args={"autocommit": True})
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO Narangba.Feedback (Name, Feedback) VALUES (:name, :feedback)"),
                {"name": name, "feedback": feedback}
            )
        logging.info("✅ Feedback saved to SQL database")
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
