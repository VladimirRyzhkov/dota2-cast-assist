import argparse
import json
import os
from typing import Tuple

import apache_beam as beam
from apache_beam.options.pipeline_options import GoogleCloudOptions, PipelineOptions, StandardOptions, WorkerOptions
from apache_beam.transforms import GroupByKey, window
from libs.firestore import LiveMatches


class DownloadLiveMatches(beam.DoFn):
    """
    A DoFn that downloads live matches from Steam
    """
    def __init__(self, project_id: str, collection_name: str, *args, **kwargs):
        # At the moment Beam does not support calls of super() (BEAM-6158)
        #super(DownloadLiveMatches, self).__init__(*args, **kwargs)
        beam.DoFn.__init__(self, *args, **kwargs)

        self.project_id = project_id
        self.collection_name = collection_name

    def process(self, _element, *args, **kwargs):
        from common.steam_api import SteamAPIConnection

        steam_api = SteamAPIConnection.get_instance()
        live_matches = steam_api.get_live_matches()
        yield live_matches


class Parse(beam.DoFn):
    """
    A DoFn class for parsing and validating messages

    Extracts essential attributes from nested structures of an incoming message
    """
    def process(self, message: bytes, **kwargs):
        import json

        import chardet
        from libs.firestore import GsiEvent

        def convert_to_int(val, default: int = 0) -> Tuple[bool, int]:
            try:
                int_value = int(val)
                res = True
            except (ValueError, TypeError):
                int_value = default
                res = False

            return res, int_value

        try:
            encoding = chardet.detect(message)["encoding"]
            match_data = message.decode(encoding)
            event_data = json.loads(match_data)
        except (ValueError, TypeError):
            event_data = {}
            match_data = ""

        gsi_event = GsiEvent(match_data=match_data)

        # Pull main nested attributes to the top
        gsi_event.token = event_data.get("auth", {}).get("token", "")

        _, gsi_event.timestamp = convert_to_int(
            val=event_data.get("provider", {}).get("timestamp", "0"),
            default=0
        )

        _, gsi_event.match_id = convert_to_int(
            val=event_data.get("map", {}).get("matchid", "0"),
            default=0
        )

        _, gsi_event.game_time = convert_to_int(
            val=event_data.get("map", {}).get("game_time", "0"),
            default=0
        )

        _, clock_time = convert_to_int(
            val=event_data.get("map", {}).get("clock_time", "0"),
            default=0
        )

        gsi_event.clock_time = max(0, clock_time)

        player_data = event_data.get("player", {})

        if gsi_event.match_id > 0 and gsi_event.token and player_data.keys():
            yield gsi_event.match_id, gsi_event


class EnrichWrite(beam.DoFn):
    """
    DoFn that extracts the latest events for every token, enriches with the
    live team names and saves in the Firestore
    """

    def __init__(
        self,
        project_id: str,
        gsi_events_collection_name: str,
        live_matches_collection_name: str,
        database_name: str,
        *args,
        **kwargs
    ):
        # At the moment Beam does not support calls of super() (BEAM-6158)
        #super(EnrichWrite, self).__init__(*args, **kwargs)
        beam.DoFn.__init__(self, *args, **kwargs)
        self.project_id = project_id
        self.gsi_events_collection_name = gsi_events_collection_name
        self.live_matches_collection_name = live_matches_collection_name
        self.database_name = database_name


    def process(
        self,
        match_events,
        **kwargs
    ):
        from libs.firestore import FirestoreDb, GsiEvent, LiveMatchInfo

        fs_client = FirestoreDb(
            project_id=self.project_id,
            database_name=self.database_name
        )

        def update_team_names(gsi_event: GsiEvent):
            # Live Matches are stored in only one document with id == "0"
            live_matches: LiveMatches = fs_client.query_document(
                document_id="0",
                collection_name=self.live_matches_collection_name
            )

            # Filter only needed live match data
            flt = filter(lambda lm: lm.match_id == gsi_event.match_id, live_matches.matches)
            live_match: LiveMatchInfo = next(flt, None)

            if not live_match:
                return

            gsi_match_dict = json.loads(gsi_event.match_data)
            player_data = gsi_match_dict.get("player", {})

            team_radiant_data = player_data.get("team2", {})
            team_dire_data = player_data.get("team3", {})

            for p in team_radiant_data.values():
                p["team_name"] = live_match.radiant_team_name

            for p in team_dire_data.values():
                p["team_name"] = live_match.dire_team_name

            gsi_event.match_data = json.dumps(gsi_match_dict)

        match_id, gsi_events = match_events

        # One single token means one particular spectator
        all_tokens= set(e.token for e in gsi_events)

        for token in all_tokens:
            # Find the latest event
            max_clock_time = -1
            latest_event = None

            for e in gsi_events:
                if e.token == token and e.clock_time >= 0:
                    clock_time = e.clock_time
                    if clock_time > max_clock_time:
                        max_clock_time = clock_time
                        latest_event = e

            if not latest_event:
                continue

            update_team_names(gsi_event=latest_event)

            # We are going to write a DB event. We need to write the latest
            # matches checking by all timestamp metrics
            write_to_db = True

            # Retrieving the last stored event from the Firestore for the token
            prev_gsi_event = fs_client.query_document(
                document_id=token,
                collection_name=self.gsi_events_collection_name
            )

            if prev_gsi_event:
                if (
                    prev_gsi_event.game_time > latest_event.game_time and
                    prev_gsi_event.match_id == latest_event.match_id
                ):
                    write_to_db = False

                if prev_gsi_event.timestamp > latest_event.timestamp:
                    write_to_db = False

            if not write_to_db:
                continue

            fs_client.save_documents(
                docs=[latest_event, ],
                collection_name=self.gsi_events_collection_name
            )

            yield True


def run(**kwargs):
    default_job_name = "dota2-cast-assist"

    parser = argparse.ArgumentParser(description=f"Job: {default_job_name}")

    parser.add_argument(
        "--google_application_credentials_path",
        type=str,
        required=True,
        help="Absolute path to the Google Cloud Service Account Credentials JSON key file")

    # General parameters
    parser.add_argument(
        "--project_id",
        type=str,
        required=True,
        help="GCP project where Dataflow job should be launched")

    parser.add_argument(
        "--gcs_working_folder",
        type=str,
        required=True,
        help="File path to the working folder of Dataflow job. Format: <bucket>/<folder>"
    )

    parser.add_argument(
        "--pubsub_subscription",
        type=str,
        required=True,
        help="PubSub subscription name from where to read events"
    )

    parser.add_argument(
        "--firestore_database_name",
        type=str,
        required=True,
        help="Firestore Database name to readn and write processed events"
    )

    parser.add_argument(
        "--job_name",
        type=str,
        default=default_job_name,
        help="Dataflow job name"
    )

    parser.add_argument(
        "--region",
        type=str,
        default="us-central1",
        help="GCP region for the Dataflow job"
    )

    parser.add_argument(
        "--vpc_network",
        type=str,
        default="default",
        help="GCP VPC network name in the job's region"
    )

    parser.add_argument(
        "--vpc_subnetwork",
        type=str,
        default="default",
        help="GCP subnetwork path"
    )

    parser.add_argument(
        "--max_workers",
        type=int,
        default=3,
        help="Maximum number of workers in Dataflow job"
    )

    parser.add_argument(
        "--machine_type",
        type=str,
        default="e2-medium",
        help="Machine type of a worker"
    )

    parser.add_argument(
        "--refresh_rate_secs",
        type=int,
        default=3,
        help="Refresh rate of the stats in seconds"
    )

    args, pipeline_args = parser.parse_known_args()
    project_id = args.project_id

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = args.google_application_credentials_path

    pubsub_subscription_name = f"projects/{project_id}/subscriptions/{args.pubsub_subscription}"
    firestore_database_name = args.firestore_database_name

    collection_gsi_event = "gsi-events"
    collection_live_matches = "live-matches"

    assert args.refresh_rate_secs > 0
    refresh_rate = args.refresh_rate_secs

    options = PipelineOptions(
        [
            "--setup_file=./setup.py",
        ]
    )

    standard_options = options.view_as(StandardOptions)
    standard_options.runner =  "DataflowRunner"
    standard_options.streaming = True

    google_cloud_options = options.view_as(GoogleCloudOptions)
    google_cloud_options.project = project_id
    google_cloud_options.job_name = args.job_name
    google_cloud_options.region = args.region
    google_cloud_options.staging_location = f"gs://{args.gcs_working_folder}/binaries"
    google_cloud_options.temp_location = f"gs://{args.gcs_working_folder}/tmp"

    worker_options = options.view_as(WorkerOptions)
    worker_options.num_workers = 1
    worker_options.max_num_workers = args.max_workers
    worker_options.machine_type = args.machine_type
    worker_options.autoscaling_algorithm = "THROUGHPUT_BASED"

    with beam.Pipeline(options=options) as p:
        events = (
            p
            | "Read" >> beam.io.ReadFromPubSub(
                            subscription=pubsub_subscription_name
                        ).with_input_types(str)
        )

        events_window = (
            events
            | "E: Window" >> beam.WindowInto(
                                window.FixedWindows(refresh_rate)
                             )
        )

        # Extracting events from messages
        pure_events = (
            events_window
            | "E: Parse" >> beam.ParDo(Parse())
        )

        # Enriching matches with team names and writing to DB
        (
                pure_events
                | "E: Aggregate" >> GroupByKey()
                | "E: Enrich & Write" >> beam.ParDo(
                                            EnrichWrite(
                                                project_id=project_id,
                                                gsi_events_collection_name=collection_gsi_event,
                                                live_matches_collection_name=collection_live_matches,
                                                database_name=firestore_database_name
                                            )
                                         )
        )

if __name__ == "__main__":
    run()
