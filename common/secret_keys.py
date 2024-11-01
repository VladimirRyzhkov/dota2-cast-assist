from typing import Optional, Tuple

from google.cloud import secretmanager

from common.settings import Settings


def get_secret_value(name: str, settings: Settings = Settings()) -> Tuple[Optional[str], str]:
    err_msg = ""
    client = secretmanager.SecretManagerServiceClient()
    request = {
        "name": f"projects/{settings.google_project_number}/secrets/{name}/versions/latest"
    }

    try:
        resp = client.access_secret_version(request)
        value = resp.payload.data.decode("UTF-8")
    except Exception as ex:
        value = None
        err_msg = f"Failed pulling secret '{name}' value from Google Secret Manager: {ex}"

    return value, err_msg
