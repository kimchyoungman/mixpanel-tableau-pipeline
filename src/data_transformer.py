"""
Data transformer for converting Mixpanel events to Hyper-compatible format.
"""
import json
import logging
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass

import pytz

from config.settings import MIXPANEL_TIMEZONE

logger = logging.getLogger(__name__)


@dataclass
class ColumnDef:
    """Column definition for Hyper table."""
    name: str
    python_type: type
    nullable: bool = True


class DataTransformer:
    """Transform Mixpanel event data for Tableau Hyper format."""

    # Standard Mixpanel properties to always include
    STANDARD_COLUMNS = [
        ColumnDef("event_name", str),
        ColumnDef("distinct_id", str),
        ColumnDef("event_time", datetime),
        ColumnDef("insert_id", str, nullable=True),
    ]

    def __init__(self, max_properties: int = 100):
        """
        Initialize transformer.

        Args:
            max_properties: Maximum number of custom properties to include.
        """
        self.max_properties = max_properties

    def flatten_event(self, event: dict) -> dict:
        """
        Flatten a Mixpanel event into a single-level dictionary.

        Args:
            event: Raw Mixpanel event with nested properties.

        Returns:
            Flattened dictionary with all properties at top level.
        """
        properties = event.get("properties", {})

        flattened = {
            "event_name": event.get("event", ""),
            "distinct_id": properties.get("distinct_id", ""),
            "event_time": self.convert_timestamp(properties.get("time")),
            "insert_id": properties.get("$insert_id"),
        }

        # Add custom properties (excluding standard Mixpanel properties)
        exclude_keys = {"distinct_id", "time", "$insert_id"}

        for key, value in properties.items():
            if key not in exclude_keys:
                # Clean key name for Hyper compatibility
                clean_key = self._clean_column_name(key)
                flattened[clean_key] = self._serialize_value(value)

        return flattened

    def _parse_filters(self, filters: list[str]) -> list[tuple[str, str]]:
        """Parse filter strings into cleaned key-value pairs."""
        parsed = []
        for f in filters:
            if "=" not in f:
                logger.warning(f"Invalid filter format '{f}', expected 'key=value'")
                continue
            key, value = f.split("=", 1)
            clean_key = self._clean_column_name(key)
            parsed.append((clean_key, value))
        return parsed

    def _matches_filters(self, event: dict, parsed_filters: list[tuple[str, str]]) -> bool:
        """Check if a single event matches all parsed filters."""
        for key, value in parsed_filters:
            event_value = event.get(key)
            if event_value is None or str(event_value) != value:
                return False
        return True

    def filter_events(
        self,
        events: list[dict],
        filters: Optional[list[str]] = None
    ) -> list[dict]:
        """
        Filter events based on property conditions.
        """
        if not filters:
            return events

        parsed_filters = self._parse_filters(filters)
        if not parsed_filters:
            return events

        logger.info(f"Applying {len(parsed_filters)} filter(s)")
        filtered = [e for e in events if self._matches_filters(e, parsed_filters)]

        logger.info(f"Filtered {len(events)} -> {len(filtered)} events")
        return filtered

    def convert_timestamp(self, unix_ts: Optional[int]) -> Optional[datetime]:
        """
        Convert Unix timestamp to datetime.

        Args:
            unix_ts: Unix timestamp in seconds.

        Returns:
            datetime object or None if timestamp is invalid.
        """
        if unix_ts is None:
            return None
        try:
            timezone = pytz.timezone(MIXPANEL_TIMEZONE)
            dt = datetime.fromtimestamp(unix_ts, tz=timezone)
            return dt.replace(tzinfo=None)
        except Exception as e:
            logger.warning(f"Invalid timestamp {unix_ts}: {e}")
            return None

    def infer_schema(
        self,
        events: list,
        target_columns: Optional[list[str]] = None
    ) -> list[ColumnDef]:
        """
        Infer schema from a sample of events.

        Args:
            events: List of flattened event dictionaries.
            target_columns: Optional list of columns to include.
                           If provided, only these columns (plus standard ones)
                           will be included.

        Returns:
            List of ColumnDef objects representing the schema.
        """
        if not events:
            return list(self.STANDARD_COLUMNS)

        # Collect all unique column names
        column_names = set()
        for event in events:
            for key in event.keys():
                column_names.add(key)

        # Build schema with standard columns first
        schema = list(self.STANDARD_COLUMNS)
        standard_names = {col.name for col in self.STANDARD_COLUMNS}

        # Determine allowed columns if target_columns is provided
        allowed_columns = None
        if target_columns:
            # Clean target columns to match how event keys are cleaned
            allowed_columns = {self._clean_column_name(col) for col in target_columns}
            logger.info(f"Filtering for specific columns: {allowed_columns}")

        # Add discovered columns
        custom_count = 0
        for name in sorted(column_names):
            if name in standard_names:
                continue

            # Filter if target_columns provided
            if allowed_columns and name not in allowed_columns:
                continue

            # If no filter, respect max_properties limit
            if not allowed_columns and custom_count >= self.max_properties:
                continue

            schema.append(ColumnDef(name, str, nullable=True))
            custom_count += 1

        logger.info(f"Inferred schema with {len(schema)} columns")
        return schema

    def prepare_rows(self, events: list, schema: list[ColumnDef]) -> list[tuple]:
        """
        Prepare event data as rows matching the schema.

        Args:
            events: List of flattened event dictionaries.
            schema: List of ColumnDef objects.

        Returns:
            List of tuples ready for Hyper insertion.
        """
        column_names = [col.name for col in schema]
        rows = []

        for event in events:
            row = []
            for name in column_names:
                value = event.get(name)
                row.append(value)
            rows.append(tuple(row))

        return rows

    def _clean_column_name(self, name: str) -> str:
        """Clean column name for Hyper compatibility."""
        if not name:
            return "unnamed_property"

        # Remove $ prefix from Mixpanel special properties
        if name.startswith("$"):
            name = "mp_" + name[1:]

        # Replace invalid characters
        name = name.replace(" ", "_").replace("-", "_").replace(".", "_")

        # Ensure it starts with a letter or underscore
        if name and not (name[0].isalpha() or name[0] == "_"):
            name = "_" + name

        # Final safety check
        cleaned = name.lower()
        return cleaned if cleaned else "unnamed_property"

    def _serialize_value(self, value: Any) -> Any:
        """Serialize all values to string for consistent typing.

        Mixpanel data can have inconsistent types for the same property
        across different events (e.g., username as int or string).
        Converting everything to string avoids type conflicts.
        """
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def _infer_type(self, value: Any) -> type:
        """Infer Python type from a value."""
        if isinstance(value, bool):
            return bool
        elif isinstance(value, int):
            return int
        elif isinstance(value, float):
            return float
        elif isinstance(value, datetime):
            return datetime
        else:
            return str
