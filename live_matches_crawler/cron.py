import logging
import subprocess
import time

from common.logging_config import setup_logging
from common.settings import Settings

settings = Settings()

if __name__ == '__main__':
    setup_logging()
    logger = logging.getLogger(settings.service_name)

    if settings.github_actions_ci_cd:
        logger.info("[CI/CD] Live Matches Crawler is skipped \U0001F44C")
        exit(0)

    logger.info("[done] Live Matches Crawler is started \U0001F680")

    while True:
        try:
            subprocess.call(
                "poetry run python /live_matches_crawler/crawler.py",
                shell=True
            )
        except Exception as ex:
            logger.error(f"Live Matches Crawler's cron exception: {repr(ex)}")
            logger.warning("Live Matches Crawler's cron next attempt is in 3 seconds...")

            time.sleep(3)

    exit(1)
