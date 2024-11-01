import json
from collections import deque
from typing import Any, Dict, List, Tuple

import requests

from common.helpers import convert_to_int
from common.secret_keys import get_secret_value
from common.settings import Settings
from events_processor.libs.firestore import LiveMatches, LiveMatchInfo

settings = Settings()

keys: List[str] = []


class ApiKeys:
    def __init__(self):
        self.keys_rotator = ApiKeys.launch_keys_rotator()
        self.current_key = next(iter(self.keys_rotator), "")

    @staticmethod
    def launch_keys_rotator() -> deque:
        global keys # noqa: PLW0603
        if not keys:
            keys_dump, err_msg = get_secret_value(
                name=settings.steam_api_keys_secret_name,
                settings=settings
            )

            keys = []

            if keys_dump:
                try:
                    keys = json.loads(keys_dump)
                except (ValueError, TypeError) as ex:
                    print(f"Failed getting Steam API keys from the secret manager: {ex}")
            else:
                print(f"Failed getting Steam API keys from the secret manager: {err_msg}")


        return deque([key.strip() for key in keys if key.strip()])

    def get_next_key(self) -> str:
        self.current_key = self.keys_rotator[0] if len(self.keys_rotator) > 0 else ""
        self.keys_rotator.rotate(-1)  # Rotate left
        return self.current_key


class SteamApi:
    def __init__(self, request_timeout: int = 1):
        self.api_keys = ApiKeys()
        self.request_timeout = request_timeout

    def send_request(self, url) -> Tuple[Dict[str, Any], str]:
        api_key = self.api_keys.get_next_key()
        url += f"{'&' if '?' in url else '?'}key={api_key}"

        try:
            response = requests.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            return response.json(), ""
        except requests.RequestException as e:
            return {}, str(e)

    def get_live_matches(self) -> LiveMatches:
        url = 'https://api.steampowered.com/IDOTA2Match_570/GetLiveLeagueGames/V001/?format=json'
        data, error_msg = self.send_request(url)

        if error_msg:
            print(f"Steam API get_live_matches request error: {error_msg}")

        live_matches = LiveMatches()
        for game in data.get("result", {}).get("games", []):
            match_id = convert_to_int(game.get("match_id"), 0)[1]
            if match_id > 0:
                live_matches.matches.append(
                    LiveMatchInfo(
                        match_id=match_id,
                        radiant_team_name=game.get("radiant_team", {}).get(
                            "team_name", ""),
                        dire_team_name=game.get("dire_team", {}).get(
                            "team_name", "")
                    )
                )
        return live_matches


class SteamAPIConnection:
    _instance = None

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = SteamApi()
        return cls._instance
