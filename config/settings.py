"""
Configuration settings for Mixpanel to Tableau pipeline.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load the project-local environment file explicitly. This keeps source and
# installed CLI behavior consistent regardless of where the package lives.
load_dotenv(Path.cwd() / ".env")

# Runtime paths. Defaults are relative to the directory where the CLI is run so
# an installed wheel never attempts to write inside site-packages.
BASE_DIR = Path.cwd()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output")).expanduser()
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs")).expanduser()
STATE_PATH = os.getenv("STATE_PATH", str(BASE_DIR / "state.json"))

# Mixpanel settings
MIXPANEL_API_SECRET = os.getenv("MIXPANEL_API_SECRET")
MIXPANEL_PROJECT_ID = os.getenv("MIXPANEL_PROJECT_ID")
MIXPANEL_EXPORT_URL = "https://data.mixpanel.com/api/2.0/export"
MIXPANEL_TIMEZONE = os.getenv("MIXPANEL_TIMEZONE", "UTC")

# Hyper settings
DEFAULT_SCHEMA_NAME = "Extract"
DEFAULT_TABLE_NAME = "events"

# Tableau Publishing settings
TABLEAU_PROJECT_NAME = os.getenv("TABLEAU_PROJECT_NAME", "Default")
TABLEAU_DATASOURCE_NAME = os.getenv("TABLEAU_DATASOURCE_NAME", "mixpanel_hyper")
