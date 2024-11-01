from typing import Sequence, Tuple
from urllib.parse import urlparse

import toml
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def get_base_url(url):
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def jsonify(context):
    return JSONResponse(
        content=jsonable_encoder(context)
    )


def divide_chunks(collection: Sequence, n: int):
    for i in range(0, len(collection), n):
        yield collection[i: i + n]


def get_version_from_pyproject() -> str:
    try:
        pyproject_path = "/app/pyproject.toml"
        with open(pyproject_path, "r") as f:
            pyproject_data = toml.load(f)
        return pyproject_data["tool"]["poetry"]["version"]
    except (FileNotFoundError, KeyError):
        return "Unknown"


def convert_to_int(val, default: int = 0) -> Tuple[bool, int]:
    try:
        int_value = int(val)
        res = True
    except (ValueError, TypeError):
        int_value = default
        res = False

    return res, int_value
