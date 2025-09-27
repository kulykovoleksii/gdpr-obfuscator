import json
from typing import Any, Dict

from . import s3_adapter


def process_request(json_payload: str) -> Dict[str, Any]:
    """
    Accept JSON payload with keys:
      - s3_uri: str (s3://bucket/key)
      - fields: list[str]
      - primary_key: str (optional, default 'id')

    Returns dict with 'bytes' and 'length'.
    """
    data = json.loads(json_payload)
    s3_uri = data["s3_uri"]
    fields = data["fields"]
    pk = data.get("primary_key", "id")

    result_bytes = s3_adapter.process_s3_csv_to_bytes(s3_uri, fields, pk)

    return {"bytes": result_bytes, "length": len(result_bytes)}
