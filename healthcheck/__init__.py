import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({ "status": "ok", "message": "Function App is running ✅" }),
        mimetype="application/json",
        status_code=200
    )
