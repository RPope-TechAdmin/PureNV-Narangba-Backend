import logging
import azure.functions as func
import pyodbc
import os
import json
import jwt
from jwt import PyJWKClient

# 🔐 Token validation
def validate_token(token):
    tenant_id = "655e497b-f0e8-44ed-98fb-77680dd02944"
    client_id = "162019e9-1091-4c41-8ab4-a5b00bdbf1fe"
    jwks_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    # Log unverified token (optional but helpful)
    unverified = jwt.decode(token, options={"verify_signature": False})
    logging.info(f"🪪 Unverified token: {json.dumps(unverified, indent=2)}")

    jwk_client = PyJWKClient(jwks_url)
    signing_key = jwk_client.get_signing_key_from_jwt(token)

    decoded = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=f"api://{client_id}",
        issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    )
    return decoded

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

    # Get and validate Bearer token
    auth_header = req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return func.HttpResponse(
            json.dumps({"error": "Missing or invalid Authorization header"}),
            status_code=401,
            mimetype="application/json"
        )

    token = auth_header.split(" ")[1]
    try:
        claims = validate_token(token)
        logging.info(f"✅ Token validated: {json.dumps(claims)}")
    except Exception as e:
        logging.exception("❌ Token validation failed")
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized", "details": str(e)}),
            status_code=401,
            mimetype="application/json"
        )

    # Parse body
    try:
        data = req.get_json()
        logging.info(f"📦 Parsed request body: {json.dumps(data)}")
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
