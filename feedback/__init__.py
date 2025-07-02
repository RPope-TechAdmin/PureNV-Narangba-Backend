import logging
import azure.functions as func
import pyodbc
import os
import json
import jwt
from jwt import PyJWKClient

# 🔌 SQL connection using SQL Authentication
def get_db_connection():
    connection_string = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={os.environ['SQL_SERVER']};"
        f"Database={os.environ['SQL_DB']};"
        f"UID={os.environ['SQL_USER']};"
        f"PWD={os.environ['SQL_PASSWORD']};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Authentication=SqlPassword;"
    )
    conn = pyodbc.connect(connection_string)
    return conn

# 📥 Main Azure Function trigger
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("🔁 Processing feedback submission")

    # Handle CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "https://victorious-pond-02e3be310.2.azurestaticapps.net",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",
                "Access-Control-Max-Age": "86400"
            }
        )

    # Parse body
    try:
        data = req.get_json()
        logging.info("📦 Parsed request body:\n%s", json.dumps(data))
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

    # Save to DB
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Narangba.Feedback (Name, Feedback) VALUES (?, ?)", (name, feedback))
        conn.commit()
        cursor.close()
        conn.close()
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
        mimetype="application/json"
    )
