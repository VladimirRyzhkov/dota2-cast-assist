import json
import time
from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel

from common.helpers import convert_to_int
from common.pubsub import PubSub
from common.settings import Settings
from events_processor.libs.firestore import FirestoreDb

settings = Settings()

TEAM_KEYS = {"team2": "radiant", "team3": "dire"}

# TODO: check event_data.get("timestamp", 0) is UTC

# See Player's the full list of features here https://snyk.io/advisor/npm-package/dotagsi
FEATURES = [
    "activity",
    "assists",
    "camps_stacked",
    "consumable_gold_spent",
    "deaths",
    "denies",
    "gold",
    "gold_from_creep_kills",
    "gold_from_hero_kills",
    "gold_from_income",
    "gold_from_shared",
    "gold_lost_to_death",
    "gold_reliable",
    "gold_spent_on_buybacks",
    "gold_unreliable",
    "gpm",
    "hero_damage",
    "hero_healing",
    "item_gold_spent",
    "kill_streak",
    "kills",
    "last_hits",
    "net_worth",
    "runes_activated",
    "support_gold_spent",
    "tower_damage",
    "wards_destroyed",
    "wards_placed",
    "wards_purchased",
    "xpm",
]


class Player(BaseModel):
    player_name: str = ""
    # Actions per minute (such as moving units, issuing commands, or using abilities)
    apm: int = 0
    # Player"s slot in the event
    slot: int = 0
    # Player"s side: radiant or dire
    side: str = ""
    # Player's team name
    team_name: str = ""
    # Player's Steam ID is the full identifier. Steam uses it universally across all platforms
    steam_id: int = 0
    # Player's Account ID is a shorter version for Dota 2 platform
    account_id: int = 0
    # Key-Value feature
    features: Dict[str, str] = {}
    # Items
    items: Dict[int, str] = {}
    # Hero name
    hero_name: str = ""
    # Hero level from 1 to 30
    hero_level: int = 0

    def __init__(
        self,
        clock_time: int,
        slot: int,
        team_name: str,
        player_data: Dict,
        items_data: Dict,
        hero_data: Dict,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        # Retrieve mandatory attributes of a player

        # APM
        _, commands_issued = convert_to_int(
            player_data.get("commands_issued", "0"),
            0
        )

        if clock_time > 0:
            self.apm = 60 * int(commands_issued / clock_time)

        # Steam and Account IDs
        _, self.steam_id = convert_to_int(
            player_data.get("steamid", "0"),
            0
        )
        if self.steam_id > 0:
            self.account_id = self.steam_id - 76561197960265728

        # The rest attributes
        self.player_name = player_data.get("name", "")
        self.slot = slot
        self.side = team_name
        self.team_name = player_data.get("team_name", "")

        # Retrieve non-mandatory features of a player
        for f in FEATURES:
            f_val = player_data.get(f) or ""
            self.features[f] = str(f_val)

        # Retrieve Items
        for s in range(10):
            slot_data = items_data.get(f"slot{s}")

            item_name = ""
            if isinstance(slot_data, dict):
                item_name = slot_data.get("name", "")

            self.items[s] = item_name

        # Retrieve Hero info
        self.hero_name= hero_data.get("name", "")
        _, self.hero_level = convert_to_int(hero_data.get("level", "0"), 0)


class Match(BaseModel):
    # model_config = ConfigDict(arbitrary_types_allowed=True)

    match_id: int = -1
    clock_time: str = "..."
    win_team: str = ""
    players: dict[str, Player] = {}
    # How old is the provided match information is (in seconds). -1 means the
    # age is unknown
    event_age_seconds: int = -1
    message: str = "We have not got any incoming events for your token yet"


class RegEventStatus(BaseModel):
    registered: bool = False
    reg_id: str = ""


async def live_match_stat(token: str) -> Match:
    match_data = Match()

    gsi_event = FirestoreDb( # type: ignore[attr-defined]
        project_id=settings.google_project_id,
        database_name=settings.firestore_database_name,
    ).query_document(
        document_id=token,
        collection_name=settings.gsi_events_collection_name
    )

    try:
        event_match_data = json.loads(gsi_event.match_data)
    except ValueError:
        event_match_data = {}

    if not event_match_data.keys():
        match_data.message = (
            "Try again a bit later, we are almost ready to provide the stats for you"
        )
        return match_data

    timestamp = gsi_event.timestamp

    if timestamp > 0:
        utc = datetime.now(timezone.utc).timestamp()
        # TODO: check if timestamp is UTC
        match_data.event_age_seconds = int(utc) - timestamp

    clock_time = 0
    # Ok, now we retrieve all the stats from the different sections of the event
    map_data = event_match_data.get("map")

    if isinstance(map_data, dict):
        _, match_data.match_id = convert_to_int(map_data.get("matchid"), 0)
        _, clock_time = convert_to_int(map_data.get("clock_time"),0)
        match_data.win_team = map_data.get("win_team", "")

    player = event_match_data.get("player")
    items = event_match_data.get("items")
    hero = event_match_data.get("hero")

    if isinstance(player, dict):
        for team_key, team_name in TEAM_KEYS.items():
            player_data = player.get(team_key)
            items_data = items.get(team_key, {}) if isinstance(items, dict) else {}
            hero_data = hero.get(team_key, {}) if isinstance(hero, dict) else {}

            if isinstance(player_data, dict):
                # each event has 20 random slots for both teams cumulatively to
                # store a player information
                for slot in range(20):
                    player_name = f"player{slot}"
                    player_n = player_data.get(player_name)
                    player_n_items = items_data.get(player_name) or {}
                    player_n_hero = hero_data.get(player_name) or {}

                    if isinstance(player_n, dict):
                        match_data.players[player_name] = Player(
                            clock_time=clock_time,
                            slot=slot,
                            team_name=team_name,
                            player_data=player_n,
                            items_data=player_n_items,
                            hero_data=player_n_hero,
                        )

    mask = "%H:%M:%S" if clock_time >= 3600 else "%M:%S" # noqa: PLR2004
    match_data.clock_time = time.strftime(mask, time.gmtime(clock_time))
    match_data.message = ""

    return match_data


async def reg_dota2_event(event_data: Dict[str, Any]) -> RegEventStatus:
    cleaned_data = json.dumps(event_data, ensure_ascii=True)

    # It's a singleton, so it's okay to call it an immense number of times
    pub_sub = PubSub(
        project_id=settings.google_project_id,
        topic_name=settings.pubsub_topic_name
    )

    message_id = await pub_sub.publish_messages( # type: ignore[attr-defined]
        message=cleaned_data,
    )

    return RegEventStatus(
        registered=bool(message_id),
        reg_id=message_id
    )
