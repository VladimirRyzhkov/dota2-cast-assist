import time

from common.settings import Settings
from common.steam_api import SteamAPIConnection
from events_processor.libs.firestore import FirestoreDb

settings = Settings()


def main():
    while True:
        steam_api = SteamAPIConnection.get_instance()
        live_matches = steam_api.get_live_matches()

        fs_client = FirestoreDb(
            project_id=settings.google_project_id,
            database_name=settings.firestore_database_name
        )

        fs_client.save_documents(
            docs=[live_matches, ],
            collection_name=settings.live_matches_collection_name
        )

        # There is no need to collect live matches information more frequently
        time.sleep(5)


if __name__ == '__main__':
    main()
    exit(1)
