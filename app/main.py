from typing import Dict

from fastapi import FastAPI, Query, Request

from app import core
from common.helpers import get_version_from_pyproject, jsonify
from common.settings import Settings

app = FastAPI()
settings = Settings()


# Routes
@app.get("/version")
async def version() -> Dict[str, str]:
    res = jsonify(
        {
            "version": get_version_from_pyproject(),
            "api_name": settings.service_name
        }
    )
    return res

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return jsonify({"status": "healthy"})

@app.post("/dota2-event")
async def reg_dota2_event(request: Request) -> core.RegEventStatus:
    event_data = await request.json()
    return await core.reg_dota2_event(event_data)

@app.get("/live-match/stats")
async def live_match_stats(
    token: str = Query(
        default="",
        description="Provide your personal spectator's token",
    ),
) -> core.Match:
    return await core.live_match_stat(token)
