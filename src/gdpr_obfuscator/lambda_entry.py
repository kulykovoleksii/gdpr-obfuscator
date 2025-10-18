import os
import json
import logging
from typing import Any, Dict, Optional
import boto3

from . import s3_adapter

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def get_secret_string(secret_name: Optional[str]) -> Optional[str]:
    if not secret_name:
        return None
    client = boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=secret_name)
    return resp.get("SecretString")


def safe_parse_payload(event: Any) -> Dict[str, Any]:
    """Return dict payload. Accept dict or JSON string."""
    if isinstance(event, str):
        try:
            return json.loads(event)
        except json.JSONDecodeError:
            raise ValueError("Event is string but not valid JSON")
    if isinstance(event, dict):
        return event
    raise ValueError("Unsupported event type")


def lambda_handler(event: Any, context: Any) -> Dict[str, Any]:
    """
    Lambda entrypoint.
    - event can be dict (from EventBridge / Step Functions) or string.
    - Example event:
      {
        "s3_uri": "s3://bucket/input.csv",
        "fields": ["email","phone"],
        "primary_key": "id",
        "target_s3_uri": "s3://bucket/output.obf.csv"   # optional
      }
    """
    logger.info("Lambda invoked")
    # load secret if secret name provided
    secret_name = os.getenv("OBFUSCATOR_SECRET_NAME")
    try:
        secret = get_secret_string(secret_name) if secret_name else None
        if secret:
            os.environ["OBFUSCATOR_KEY"] = secret
    except Exception:
        logger.exception(
            "Failed to load secret from Secrets Manager; continuing if env var set"
        )

    try:
        payload = safe_parse_payload(event)
    except ValueError as e:
        logger.error("Invalid event payload: %s", e)
        return {"status": "error", "message": str(e)}

    # required fields
    s3_uri = payload.get("s3_uri")
    fields = payload.get("fields")
    if not s3_uri or not fields:
        msg = "Missing required 's3_uri' or 'fields' in payload"
        logger.error(msg)
        return {"status": "error", "message": msg}

    pk = payload.get("primary_key", "id")
    target = payload.get("target_s3_uri")  # optional

    # choose path: do process+upload if target given; otherwise just process and return length
    try:
        if target:
            logger.info("Processing and uploading: %s -> %s", s3_uri, target)
            # in tests you can pass a stub s3_client via payload or env, here we use real boto3 client
            s3_adapter.process_and_upload(
                source_s3_uri=s3_uri,
                target_s3_uri=target,
                sensitive_fields=fields,
                primary_key_field=pk,
            )
            return {"status": "ok", "uploaded": True, "target": target}
        else:
            logger.info(
                "Processing and returning bytes for %s (no upload)", s3_uri
            )
            # use process_s3_csv_to_bytes which returns bytes
            result_bytes = s3_adapter.process_s3_csv_to_bytes(
                s3_uri, sensitive_fields=fields, primary_key_field=pk
            )
            return {"status": "ok", "uploaded": False, "length": len(result_bytes)}
    except Exception:
        logger.exception("Processing failed for %s", s3_uri)
        return {"status": "error", "message": "processing failed"}
    