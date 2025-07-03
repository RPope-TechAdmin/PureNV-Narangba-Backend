import logging
import azure.functions as func
import os
import json
import jwt
from jwt import PyJWKClient
import sys

print(jwt.__version__)
logging.info("📂 Site packages: %s", os.listdir('/home/site/wwwroot/.python_packages/lib/site-packages'))
logging.info("📦 Python path: %s", sys.path)
logging.info("🎯 FULL CLAIMS:\n%s", json.dumps(claims, indent=2))

cors_headers={
                "Access-Control-Allow-Origin": "https://victorious-pond-02e3be310.2.azurestaticapps.net",
                "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",
                "Access-Control-Max-Age": "86400"
            }

# 🔐 Token validation
def validate_token(token):
    tenant_id = "655e497b-f0e8-44ed-98fb-77680dd02944"
    client_id = "87cbd10b-1303-4056-a899-27bd61691211"
    audience = f"api://{client_id}"
    jwks_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    # Log unverified token
    unverified = jwt.decode(token, options={"verify_signature": False})
    logging.info("🔍 Unverified token contents:\n%s", json.dumps(unverified, indent=2))
    logging.info("🎯 Token Audience (aud): %s", unverified.get("aud"))

    # Load signing key and decode with verification
    jwk_client = PyJWKClient(jwks_url)
    signing_key = jwk_client.get_signing_key_from_jwt(token)

    logging.info("🔐 Validating token with audience: api://%s", client_id)
    logging.info(f"Token claims: {json.dumps(claims)}")
    logging.info(f"Token scopes: {claims.get('scp')}")

    decoded = jwt.decode(
    token,
    signing_key.key,
    algorithms=["RS256"],
    audience=audience,
    issuer=f"https://sts.windows.net/{tenant_id}/"
)
    return decoded

# 🔌 SQLAlchemy + pytds connection
def get_db_engine():
    username = os.environ["SQL_USER"]
    password = os.environ["SQL_PASSWORD"]
    server = os.environ["SQL_SERVER"]
    db = os.environ["SQL_DB"]

    engine = create_engine(
        f"mssql+pytds://{username}:{password}@{server}/{db}",
        connect_args={"autocommit": True}
    )
    return engine

# 📥 Azure Function trigger
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("🔁 Processing feedback submission")

    # CORS
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=204,
            headers=cors_headers
        )

    # Token check
    auth_header = req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return func.HttpResponse(
            json.dumps({"error": "Missing or invalid Authorization header"}),
            status_code=401,
            mimetype="application/json"
        )

    token = auth_header.split(" ")[1]
    try:
        logging.info("🚨 Starting token validation")
        claims = validate_token(token)
        logging.info("✅ Token validated:\n%s", json.dumps(claims, indent=2))
    except Exception as e:
        logging.exception("❌ Token validation failed")
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized", "details": str(e)}),
            status_code=401,
            mimetype="application/json"
        )

    # Parse JSON
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

    # Save feedback
    try:
        engine = get_db_engine()
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
        mimetype="application/json"
    )