"""
State Manager for tracking pipeline progress.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from google.cloud import storage
    HAS_GCP = True
except ImportError:
    HAS_GCP = False

from config.settings import STATE_PATH

logger = logging.getLogger(__name__)


class StateManager:
    """Manages the state of the ETL pipeline to ensure safe incremental updates."""

    def __init__(self, key: str = "default"):
        """
        Initialize StateManager.

        Args:
            key: Unique key for the state (allows multiple independent pipelines).
        """
        self.key = key
        self.state_path = STATE_PATH
        self.is_gcs = self.state_path.startswith("gs://")

        if self.is_gcs and not HAS_GCP:
            raise ImportError("google-cloud-storage is required for GCS state persistence.")

        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load state from file or GCS."""
        if self.is_gcs:
            return self._load_from_gcs()

        path = Path(self.state_path)
        if not path.exists():
            return {}
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Corrupt state file at {self.state_path}, starting fresh.")
            return {}

    def _load_from_gcs(self) -> dict:
        """Load state from Google Cloud Storage."""
        try:
            bucket_name, blob_name = self._parse_gcs_path(self.state_path)
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            if not blob.exists():
                return {}

            content = blob.download_as_text()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading state from GCS: {e}")
            return {}

    def _save_state(self):
        """Save state to file or GCS."""
        if self.is_gcs:
            self._save_to_gcs()
        else:
            path = Path(self.state_path)
            with open(path, 'w') as f:
                json.dump(self.state, f, indent=2)

    def _save_to_gcs(self):
        """Save state to Google Cloud Storage."""
        try:
            bucket_name, blob_name = self._parse_gcs_path(self.state_path)
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            blob.upload_from_string(
                json.dumps(self.state, indent=2),
                content_type='application/json'
            )
            logger.info(f"State saved to GCS: {self.state_path}")
        except Exception as e:
            logger.error(f"Error saving state to GCS: {e}")

    def _parse_gcs_path(self, path: str) -> tuple[str, str]:
        """Parse gs://bucket/path into (bucket, path)."""
        parts = path[5:].split("/", 1)
        if len(parts) < 2:
            raise ValueError(f"Invalid GCS path: {path}")
        return parts[0], parts[1]

    def get_last_processed_date(self) -> Optional[str]:
        """Get the last processed date (YYYY-MM-DD) for the current key."""
        return self.state.get(self.key, {}).get("last_processed_date")

    def get_next_start_date(self) -> Optional[str]:
        """
        Calculate the next start date based on the last processed date.
        Returns: next_start_date (str) or None if no history.
        """
        last_date = self.get_last_processed_date()
        if not last_date:
            return None

        dt = datetime.strptime(last_date, "%Y-%m-%d")
        next_dt = dt + timedelta(days=1)
        return next_dt.strftime("%Y-%m-%d")

    def update_state(self, last_processed_date: str):
        """
        Update the state with the last processed date.
        """
        if self.key not in self.state:
            self.state[self.key] = {}

        self.state[self.key]["last_processed_date"] = last_processed_date
        self.state[self.key]["updated_at"] = datetime.now().isoformat()

        self._save_state()
        logger.info(f"State updated: {self.key} -> {last_processed_date}")
