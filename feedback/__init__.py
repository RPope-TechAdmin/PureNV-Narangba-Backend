import logging
import azure.functions as func
import os
import json
import requests
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

cors_headers = {
    "Access-Control-Allow-Origin": "https://victorious-pond-02e3be310.2.azurestaticapps.net",
    "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
    "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",
    "Access-Control-Max-Age": "86400"
}

# Decode JWT parts
def decode_part(part):
    padded = part + '=' * (-len(part) % 4)  # pad base64 string
    return json.loads(base64.urlsafe_b64decode(padded).decode())

# Fetch and cache Microsoft identity public keys
def get_public_keys(tenant_id):
    openid_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    res = requests.get(openid_url)
    res.raise_for_status()
    return {key["kid"]: key for key in res.json()["keys"]}

# Validate signature using cryptography
def verify_signature(header, payload, signature, public_key_jwk):
    # Reconstruct the signed data
    signed_data = f"{header}.{payload}".encode()

    # Get the modulus and exponent
    n = int.from_bytes(base64.urlsafe_b64decode(public_key_jwk["n"] + "=="), byteorder="big")
    e = int.from_bytes(base64.urlsafe_b64decode(public_key_jwk["e"] + "=="), byteorder="big")

    public_numbers = serialization.rsa.RSAPublicNumbers(e, n)
    pub_key = public_numbers.public_key(default_backend())

    try:
        pub_key.verify(
            base64.urlsafe_b64decode(signature + "=="),
            signed_data,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False

def validate_token(token):
    tenant_id = "655e497b-f0e8-44ed-98fb-77680dd02944"
    client_id = "87cbd10b-1303-4056-a899-27bd61691211"
    audience = f"api://{client_id}"

    header_b64, payload_b64, signature_b64 = token.split('.')

    header = decode_part(header_b64)
    payload = decode_part(payload_b64)

    keys = get_public_keys(tenant_id)
    kid = header.get("kid")

    if kid not in keys:
        raise Exception("Key ID not found in public keys")

    valid = verify_signature(header_b64, payload_b64, signature_b64, keys[kid])
    if not valid:
        raise Exception("Invalid token signature")

    if payload["aud"] != audience:
        raise Exception("Invalid audience")

    return payload

# Main function trigger
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("🔁 Processing feedback submission")

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=cors_headers)

    auth_header = req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return func.HttpResponse(
            json.dumps({"error": "Missing or invalid Authorization header"}),
            status_code=401,
            mimetype="application/json"
        )

    token = auth_header.split(" ")[1]
    try:
        logging.info("🚨 Validating token manually")
        claims = validate_token(token)
        logging.info("✅ Token claims:\n%s", json.dumps(claims, indent=2))
    except Exception as e:
        logging.exception("❌ Token validation failed")
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized", "details": str(e)}),
            status_code=401,
            mimetype="application/json"
        )

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

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(
            f"mssql+pytds://{os.environ['SQL_USER']}:{os.environ['SQL_PASSWORD']}@{os.environ['SQL_SERVER']}/{os.environ['SQL_DB']}",
            connect_args={"autocommit": True}
        )
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
