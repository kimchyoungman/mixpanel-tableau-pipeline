"""
Mixpanel API client for exporting raw event data.
"""
import json
import logging
from typing import Generator, Optional
from datetime import datetime

import requests

from config.settings import MIXPANEL_API_SECRET, MIXPANEL_PROJECT_ID, MIXPANEL_EXPORT_URL

logger = logging.getLogger(__name__)


class MixpanelClient:
    """Client for Mixpanel Raw Data Export API."""

    def __init__(self, api_secret: Optional[str] = None, project_id: Optional[str] = None):
        """
        Initialize Mixpanel client.

        Args:
            api_secret: Mixpanel API secret. Defaults to env variable.
            project_id: Mixpanel project ID. Defaults to env variable.
        """
        self.api_secret = api_secret or MIXPANEL_API_SECRET
        self.project_id = project_id or MIXPANEL_PROJECT_ID

        if not self.api_secret:
            raise ValueError("Mixpanel API secret is required. Set MIXPANEL_API_SECRET env variable.")
        if not self.project_id:
            raise ValueError("Mixpanel Project ID is required. Set MIXPANEL_PROJECT_ID env variable.")

    def export_events(
        self,
        from_date: str,
        to_date: str,
        event_names: Optional[list] = None
    ) -> Generator[dict, None, None]:
        """
        Export events from Mixpanel for a given date range as a generator.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            event_names: Optional list of event names to filter.

        Yields:
            Event dictionaries.
        """
        return self._stream_export(from_date, to_date, event_names)

    def _stream_export(
        self,
        from_date: str,
        to_date: str,
        event_names: Optional[list] = None
    ) -> Generator[dict, None, None]:
        """
        Stream export events from Mixpanel API with retry logic.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            event_names: Optional list of event names to filter.

        Yields:
            Event dictionaries.
        """
        import time
        max_retries = 3
        retry_delay = 5

        params = {
            "from_date": from_date,
            "to_date": to_date,
        }

        if event_names:
            params["event"] = json.dumps(event_names)

        logger.info(f"Fetching events from {from_date} to {to_date}")

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    MIXPANEL_EXPORT_URL,
                    params=params,
                    auth=(self.api_secret, ""),
                    headers={"Accept": "application/json"},
                    stream=True,
                    timeout=300
                )
                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        try:
                            event = json.loads(line.decode("utf-8"))
                            yield event
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse event line: {e}")
                            continue

                # If we get here and finished the loop, we are done
                return

            except (requests.exceptions.RequestException, ConnectionResetError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Mixpanel API request failed after {max_retries} attempts")
                    raise

    def export_events_chunked(
        self,
        from_date: str,
        to_date: str,
        event_names: Optional[list] = None,
        chunk_days: Optional[int] = None,
        chunk_months: Optional[int] = None
    ) -> Generator[list, None, None]:
        """
        Export events in day-based or month-based chunks to handle large date ranges.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            event_names: Optional list of event names to filter.
            chunk_days: Number of days per chunk.
            chunk_months: Number of months per chunk. If provided, overrides chunk_days.

        Yields:
            Lists of event dictionaries for each chunk.
        """
        from datetime import timedelta

        start = datetime.strptime(from_date, "%Y-%m-%d")
        end = datetime.strptime(to_date, "%Y-%m-%d")

        # Default to 7 days if neither is provided
        if chunk_days is None and chunk_months is None:
            chunk_days = 7

        current_start = start
        while current_start <= end:
            if chunk_months:
                # Calculate the end of the month-based chunk
                month = current_start.month - 1 + chunk_months
                year = current_start.year + month // 12
                next_month = month % 12 + 1

                # First day of the month after the chunk
                next_period_start = datetime(year, next_month, 1)
                current_end = min(next_period_start - timedelta(days=1), end)
            else:
                # Day-based chunking
                current_end = min(current_start + timedelta(days=chunk_days - 1), end)

            chunk_from = current_start.strftime("%Y-%m-%d")
            chunk_to = current_end.strftime("%Y-%m-%d")

            logger.info(f"Processing chunk: {chunk_from} to {chunk_to}")

            # Yield (end_date, generator) for this chunk
            yield chunk_to, self.export_events(chunk_from, chunk_to, event_names)

            # Add delay to avoid API rate limits
            import time
            time.sleep(2)

            current_start = current_end + timedelta(days=1)
