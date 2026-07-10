#!/usr/bin/env python3
"""
Main entry point for Mixpanel to Tableau Hyper pipeline.

Usage:
    python main.py --from-date 2024-01-01 --to-date 2024-01-31
    python main.py --from-date 2024-01-01 --to-date 2024-01-31 --output ./output/events.hyper
    python main.py --from-date 2024-01-01 --to-date 2024-01-31 --events "Page View" "Button Click"
    python main.py --from-date 2024-01-01 --to-date 2024-01-31 --filter "application=myapp" --filter "mp_country_code=KR"
"""
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta

import pytz

from config.settings import (
    LOG_DIR,
    MIXPANEL_API_SECRET,
    MIXPANEL_PROJECT_ID,
    MIXPANEL_TIMEZONE,
    OUTPUT_DIR,
    STATE_PATH,
    TABLEAU_DATASOURCE_NAME,
    TABLEAU_PROJECT_NAME,
)
from src.pipeline import Pipeline
from src.state_manager import StateManager


def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    log_level = logging.DEBUG if verbose else logging.INFO
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)

    # File handler
    log_file = LOG_DIR / "pipeline.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    # Clear existing handlers to avoid duplicates if re-setup
    if root_logger.handlers:
        root_logger.handlers = []
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def _is_missing(value: str | None) -> bool:
    """Return True for empty or obvious placeholder config values."""
    if value is None:
        return True
    stripped = value.strip()
    return not stripped or stripped.startswith("your_")


def check_config(validate_tableau: bool = False) -> int:
    """Validate local configuration without calling external APIs."""
    checks: list[tuple[bool, str]] = []

    checks.append((not _is_missing(MIXPANEL_API_SECRET), "MIXPANEL_API_SECRET is set"))
    checks.append((not _is_missing(MIXPANEL_PROJECT_ID), "MIXPANEL_PROJECT_ID is set"))

    try:
        pytz.timezone(MIXPANEL_TIMEZONE)
        checks.append((True, f"MIXPANEL_TIMEZONE is valid: {MIXPANEL_TIMEZONE}"))
    except Exception:
        checks.append((False, f"MIXPANEL_TIMEZONE is invalid: {MIXPANEL_TIMEZONE}"))

    for name, path in (("OUTPUT_DIR", OUTPUT_DIR), ("LOG_DIR", LOG_DIR)):
        try:
            path.mkdir(parents=True, exist_ok=True)
            checks.append((path.is_dir(), f"{name} is ready: {path}"))
        except OSError as e:
            checks.append((False, f"{name} is not writable: {path} ({e})"))

    if STATE_PATH.startswith("gs://"):
        checks.append((STATE_PATH.count("/") >= 3, f"STATE_PATH is a GCS path: {STATE_PATH}"))
    else:
        state_parent = Path(STATE_PATH).expanduser().parent
        try:
            state_parent.mkdir(parents=True, exist_ok=True)
            checks.append((state_parent.is_dir(), f"STATE_PATH parent is ready: {state_parent}"))
        except OSError as e:
            checks.append((False, f"STATE_PATH parent is not writable: {state_parent} ({e})"))

    if validate_tableau:
        import os
        tableau_vars = [
            "TABLEAU_SERVER_URL",
            "TABLEAU_SITE_ID",
            "TABLEAU_TOKEN_NAME",
            "TABLEAU_TOKEN_VALUE",
        ]
        for name in tableau_vars:
            checks.append((not _is_missing(os.getenv(name)), f"{name} is set"))

    for passed, message in checks:
        marker = "OK" if passed else "MISSING"
        print(f"[{marker}] {message}")

    failed = [message for passed, message in checks if not passed]
    if failed:
        print("\nConfiguration is incomplete. Update .env or your environment variables.")
        return 1

    print("\nConfiguration looks ready.")
    return 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Export Mixpanel events to Tableau Hyper file.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Date selection group
    date_group = parser.add_mutually_exclusive_group(required=True)

    date_group.add_argument(
        "--auto-incremental",
        action="store_true",
        help="Automatically determine start date from state file and run to yesterday"
    )

    date_group.add_argument(
        "--from-date",
        help="Start date in YYYY-MM-DD format"
    )

    date_group.add_argument(
        "--yesterday",
        action="store_true",
        help="Use yesterday's date for start and end date (for daily automation)"
    )

    date_group.add_argument(
        "--check-config",
        action="store_true",
        help="Validate local configuration without exporting data"
    )

    parser.add_argument(
        "--to-date",
        help="End date in YYYY-MM-DD format (Required if --from-date is used)"
    )

    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: auto-generated in ./output/)"
    )

    parser.add_argument(
        "--events", "-e",
        nargs="*",
        help="Specific event names to export (default: all events)"
    )

    parser.add_argument(
        "--columns", "-c",
        nargs="*",
        help="Specific columns to include (default: all discovered columns). Standard columns are always included."
    )

    parser.add_argument(
        "--column-file",
        help="Path to a text file containing column names (one per line) to include."
    )

    parser.add_argument(
        "--chunked",
        action="store_true",
        help="Use chunked processing for large date ranges"
    )

    parser.add_argument(
        "--filter", "-f",
        action="append",
        dest="filters",
        help="Property filter in 'key=value' format. Can be used multiple times."
    )

    parser.add_argument(
        "--chunk-days",
        type=int,
        help="Days per chunk when using chunked mode (default: 7 if no chunk-months set)"
    )

    parser.add_argument(
        "--chunk-months",
        type=int,
        help="Months per chunk when using chunked mode"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    # Publishing arguments
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish the generated file to Tableau Cloud"
    )

    parser.add_argument(
        "--project-name",
        default=TABLEAU_PROJECT_NAME,
        help=f"Tableau Cloud Project Name to publish to (default: {TABLEAU_PROJECT_NAME})"
    )

    parser.add_argument(
        "--datasource-name",
        default=TABLEAU_DATASOURCE_NAME,
        help=f"Name of the datasource on Tableau Cloud (default: {TABLEAU_DATASOURCE_NAME})"
    )

    parser.add_argument(
        "--tableau-overwrite",
        action="store_true",
        help="Overwrite the datasource if it exists (instead of appending)"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    if args.check_config:
        sys.exit(check_config(validate_tableau=args.publish))

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Handle column file
    columns = args.columns or []
    if args.column_file:
        col_path = Path(args.column_file)
        if col_path.exists():
            with open(col_path) as f:
                # Read lines, strip whitespace, and filter empty lines/comments
                file_cols = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                columns.extend(file_cols)
            logger.info(f"Loaded {len(file_cols)} columns from {args.column_file}")
        else:
            logger.error(f"Column file not found: {args.column_file}")
            sys.exit(1)

    # Remove duplicates while preserving order
    columns = list(dict.fromkeys(columns))

    # Initialize state manager for progress tracking
    state_manager = StateManager()

    # Determine dates
    try:
        tz = pytz.timezone(MIXPANEL_TIMEZONE)
        now_in_tz = datetime.now(tz)
        yesterday_in_tz = (now_in_tz - timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"Invalid timezone {MIXPANEL_TIMEZONE}, falling back to local time: {e}")
        yesterday_in_tz = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    if args.auto_incremental:
        next_start = state_manager.get_next_start_date()

        if not next_start:
            logger.warning("No state found. Defaulting to yesterday for first run.")
            from_date = yesterday_in_tz
        else:
            from_date = next_start

        to_date = yesterday_in_tz

        # Verify from_date <= to_date
        if from_date > to_date:
            logger.info(f"Up to date. Next start ({from_date}) is after yesterday ({to_date}). Nothing to do.")
            sys.exit(0)

        logger.info(f"Auto-Incremental: Running from {from_date} to {to_date}")

    elif args.yesterday:
        from_date = yesterday_in_tz
        to_date = yesterday_in_tz
        logger.info(f"Running for Yesterday: {yesterday_in_tz}")
    else:
        if not args.to_date:
            logger.error("--to-date is required when using --from-date")
            sys.exit(1)
        from_date = args.from_date
        to_date = args.to_date

    try:
        pipeline = Pipeline()

        if args.chunked:
            output_path = pipeline.run_chunked(
                from_date=from_date,
                to_date=to_date,
                output_path=args.output,
                event_names=args.events,
                filters=args.filters,
                target_columns=columns,
                chunk_days=args.chunk_days,
                chunk_months=args.chunk_months,
                on_chunk_end=state_manager.update_state
            )
        else:
            output_path = pipeline.run(
                from_date=from_date,
                to_date=to_date,
                output_path=args.output,
                event_names=args.events,
                filters=args.filters,
                target_columns=columns
            )

        print(f"\n✅ Success! Hyper file created: {output_path}")

        # Publish to Tableau if requested
        if args.publish:
            # Keep Tableau publishing optional for users who only generate
            # local Hyper extracts.
            from src.tableau_publisher import TableauPublisher

            print("\n🚀 Publishing to Tableau Cloud...")
            publisher = TableauPublisher()
            publisher.publish(
                file_path=output_path,
                project_name=args.project_name,
                datasource_name=args.datasource_name,
                mode="Overwrite" if args.tableau_overwrite else "Append"
            )
            print("✨ Published successfully!")

            # Update state only after successful publish
            if args.auto_incremental:
                state_manager.update_state(to_date)

        else:
            print("   Open this file in Tableau Prep to use the data.")

            # If not publishing but auto-incremental, still update state?
            # Usually better to update state only if the full process (including publish) succeeds if publish is intended.
            # But if the user just wants to generate files, we should update state.
            if args.auto_incremental:
                 state_manager.update_state(to_date)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
