import logging
import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("✅ Echo test triggered")
    return func.HttpResponse(
        json.dumps({
            "message": "Echo is working",
            "method": req.method,
            "headers": dict(req.headers)
        }),
        mimetype="application/json",
        status_code=200
    )
