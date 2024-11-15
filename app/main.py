import json
from typing import Dict

from fastapi import FastAPI, HTTPException, Query, Request, status

from app import core
from common.helpers import get_version_from_pyproject, jsonify
from common.settings import Settings

app = FastAPI()
settings = Settings()


# Routes
@app.get("/dota2-gsi/version")
async def version() -> Dict[str, str]:
    res = jsonify(
        {
            "version": get_version_from_pyproject(),
            "api_name": settings.service_name
        }
    )
    return res

@app.get("/dota2-gsi/health")
async def health_check() -> Dict[str, str]:
    return jsonify({"status": "healthy"})

@app.post("/dota2-gsi/dota2-event")
async def reg_dota2_event(request: Request) -> core.RegEventStatus:
    try:
        event_data = await request.json()
        return await core.reg_dota2_event(event_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid JSON format")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred while processing the event")

@app.get("/dota2-gsi/live-match/stats")
async def live_match_stats(
    token: str = Query(
        default="",
        description="Provide your personal spectator's token",
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    ),
) -> core.Match:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is required and cannot be empty"
        )
    return await core.live_match_stat(token)
