from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load the .env file
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8'
    )

    google_project_id: str = ""
    google_project_number: str = ""
    service_name: str = ""
    pubsub_topic_name: str = ""
    steam_api_keys_secret_name: str = ""
    firestore_database_name: str = ""
    live_matches_collection_name: str = "live-matches"
    gsi_events_collection_name: str = "gsi-events"
    github_actions_ci_cd: bool = False
