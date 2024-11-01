import os
import sys

import requests


def check_api_health() -> bool:
    api_port = os.getenv('PORT')
    url = f"http://localhost:{api_port}/health"
    try:
        response = requests.get(url)
        response.raise_for_status()
        print("[ok] API is currently running and healthy.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[error] API health check failed with error: {repr(e)}")
        return False


def main():
    if not check_api_health():
        sys.exit(1)


if __name__ == "__main__":
    main()
