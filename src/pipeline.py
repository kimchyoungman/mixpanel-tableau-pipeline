"""
Main pipeline orchestration for Mixpanel to Tableau Hyper ETL.
"""
import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from config.settings import OUTPUT_DIR
from src.data_transformer import DataTransformer
from src.hyper_writer import HyperWriter
from src.mixpanel_client import MixpanelClient

logger = logging.getLogger(__name__)


class Pipeline:
    """ETL pipeline: Mixpanel → Transform → Hyper file."""

    def __init__(
        self,
        api_secret: str | None = None,
        project_id: str | None = None
    ):
        """
        Initialize pipeline.

        Args:
            api_secret: Mixpanel API secret. Defaults to env variable.
            project_id: Mixpanel project ID. Defaults to env variable.
        """
        self.mixpanel_client = MixpanelClient(api_secret, project_id)
        self.transformer = DataTransformer()

    def run(
        self,
        from_date: str,
        to_date: str,
        output_path: str | None = None,
        event_names: list | None = None,
        filters: list[str] | None = None,
        target_columns: list[str] | None = None,
        schema_name: str = "Extract",
        table_name: str = "events"
    ) -> str:
        """
        Run the full ETL pipeline.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            output_path: Path for output .hyper file.
            event_names: Optional list of event names to filter.
            filters: Optional list of property filters in 'key=value' format.
            target_columns: Optional list of specific columns to include.
            schema_name: Hyper schema name (default: 'Extract').
            table_name: Hyper table name (default: 'events').

        Returns:
            Path to the generated .hyper file.
        """
        # Generate default output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = OUTPUT_DIR / f"mixpanel_events_{from_date}_{to_date}_{timestamp}.hyper"
        else:
            output_path = Path(output_path)

        logger.info(f"Starting pipeline: {from_date} to {to_date}")
        logger.info(f"Output: {output_path}")

        # Step 1: Extract from Mixpanel
        logger.info("Step 1/3: Extracting events from Mixpanel...")
        raw_events_gen = self.mixpanel_client.export_events(from_date, to_date, event_names)
        raw_events = list(raw_events_gen)

        if not raw_events:
            logger.warning("No events found for the specified date range")
            self._write_empty_extract(
                output_path,
                target_columns=target_columns,
                schema_name=schema_name,
                table_name=table_name,
            )
            return str(output_path)

        # Deduplication based on $insert_id
        initial_count = len(raw_events)
        unique_events = {}
        for event in raw_events:
            # Fallback to string representation of event if $insert_id is missing
            iid = event.get("properties", {}).get("$insert_id") or hash(json.dumps(event, sort_keys=True))
            if iid not in unique_events:
                unique_events[iid] = event

        raw_events = list(unique_events.values())
        if len(raw_events) < initial_count:
            logger.info(f"Deduplicated: {initial_count} -> {len(raw_events)} events")
        else:
            logger.info(f"Extracted {len(raw_events)} events (no duplicates found)")

        # Step 2: Transform
        logger.info("Step 2/3: Transforming events...")
        flattened_events = [self.transformer.flatten_event(e) for e in raw_events]

        # Apply property filters
        if filters:
            flattened_events = self.transformer.filter_events(flattened_events, filters)
            if not flattened_events:
                logger.warning("No events match the filter criteria")
                self._write_empty_extract(
                    output_path,
                    target_columns=target_columns,
                    schema_name=schema_name,
                    table_name=table_name,
                )
                return str(output_path)

        # Infer schema from sample (considering target_columns)
        sample_size = min(1000, len(flattened_events))
        schema = self.transformer.infer_schema(
            flattened_events[:sample_size],
            target_columns=target_columns
        )

        # Prepare rows
        rows = self.transformer.prepare_rows(flattened_events, schema)
        logger.info(f"Prepared {len(rows)} rows with {len(schema)} columns")

        # Step 3: Load to Hyper
        logger.info("Step 3/3: Writing to Hyper file...")
        with HyperWriter(str(output_path)) as writer:
            table_def = writer.create_table(schema, schema_name, table_name)
            writer.write_rows_chunked(table_def, rows, chunk_size=10000)

        logger.info(f"Pipeline complete! Output: {output_path}")
        return str(output_path)

    def _write_empty_extract(
        self,
        output_path: Path,
        target_columns: list[str] | None = None,
        schema_name: str = "Extract",
        table_name: str = "events",
    ) -> None:
        """Create a valid empty Hyper extract instead of returning a missing file."""
        schema = self.transformer.infer_schema([], target_columns=target_columns)
        with HyperWriter(str(output_path)) as writer:
            writer.create_table(schema, schema_name, table_name)
        logger.info(f"Created empty Hyper extract: {output_path}")

    def run_chunked(
        self,
        from_date: str,
        to_date: str,
        output_path: str | None = None,
        event_names: list | None = None,
        filters: list[str] | None = None,
        target_columns: list[str] | None = None,
        chunk_days: int | None = None,
        chunk_months: int | None = None,
        on_chunk_end: Callable[[str], None] | None = None
    ) -> str:
        """
        Run pipeline with chunked date processing for large date ranges.
        Iterative writing to Hyper file per chunk to save memory.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            output_path: Path for output .hyper file.
            event_names: Optional list of event names to filter.
            filters: Optional list of property filters in 'key=value' format.
            target_columns: Optional list of specific columns to include.
            chunk_days: Number of days per chunk.
            chunk_months: Number of months per chunk.

        Returns:
            Path to the generated .hyper file.
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = OUTPUT_DIR / f"mixpanel_events_{from_date}_{to_date}_{timestamp}.hyper"
        else:
            output_path = Path(output_path)

        logger.info(f"Starting memory-efficient iterative pipeline: {from_date} to {to_date}")

        total_raw = 0
        total_unique = 0
        table_created = False
        schema = None
        table_def = None

        # Initialize HyperWriter context
        with HyperWriter(str(output_path)) as writer:
            # Pre-parse filters if provided
            parsed_filters = self.transformer._parse_filters(filters) if filters else None

            # Extract and transform in chunks
            for chunk_end_date, chunk_generator in self.mixpanel_client.export_events_chunked(
                from_date, to_date, event_names, chunk_days, chunk_months
            ):
                chunk_raw_count = 0
                chunk_unique_count = 0
                chunk_ids = set()
                batch_events = []
                batch_size = 10000

                for event in chunk_generator:
                    chunk_raw_count += 1

                    # 1. Deduplicate using ID set (much lighter than full objects)
                    iid = event.get("properties", {}).get("$insert_id") or hash(json.dumps(event, sort_keys=True))
                    if iid in chunk_ids:
                        continue

                    chunk_ids.add(iid)
                    chunk_unique_count += 1
                    total_unique += 1

                    # 2. Transform (Flatten)
                    flattened = self.transformer.flatten_event(event)

                    # Apply property filters
                    if parsed_filters and not self.transformer._matches_filters(flattened, parsed_filters):
                        continue

                    batch_events.append(flattened)

                    # 3. Process batch if full
                    if len(batch_events) >= batch_size:
                        if not table_created:
                            schema = self.transformer.infer_schema(
                                batch_events[:1000],
                                target_columns=target_columns
                            )
                            table_def = writer.create_table(schema)
                            table_created = True

                        chunk_rows = self.transformer.prepare_rows(batch_events, schema)
                        writer.write_rows(table_def, chunk_rows)
                        batch_events = []

                # 4. Finalize remaining events in chunk
                if batch_events:
                    if not table_created:
                        schema = self.transformer.infer_schema(
                            batch_events[:1000],
                            target_columns=target_columns
                        )
                        table_def = writer.create_table(schema)
                        table_created = True

                    chunk_rows = self.transformer.prepare_rows(batch_events, schema)
                    writer.write_rows(table_def, chunk_rows)

                total_raw += chunk_raw_count
                logger.info(f"Chunk processed: Raw={chunk_raw_count}, Unique={chunk_unique_count}, Total Unique So Far={total_unique}")

                # Update state if callback provided
                if on_chunk_end:
                    on_chunk_end(chunk_end_date)

                # Clear chunk-specific memory
                chunk_ids.clear()
                del chunk_ids

            if not table_created:
                schema = self.transformer.infer_schema([], target_columns=target_columns)
                writer.create_table(schema)
                logger.info("Created an empty Extract.events table because no events were returned")

        logger.info(f"Pipeline complete! Total Raw={total_raw}, Total Unique={total_unique}")
        logger.info(f"Output: {output_path}")
        return str(output_path)
