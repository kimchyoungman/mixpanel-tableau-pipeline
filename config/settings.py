"""
Configuration settings for Mixpanel to Tableau pipeline.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
BASE_DIR = PROJECT_ROOT
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output"))
LOG_DIR = Path(os.getenv("LOG_DIR", PROJECT_ROOT / "logs"))
STATE_PATH = os.getenv("STATE_PATH", str(PROJECT_ROOT / "state.json"))

# Create directories if they don't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

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
