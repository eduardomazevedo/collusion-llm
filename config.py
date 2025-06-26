import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configuration variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WRDS_USERNAME = os.getenv('WRDS_USERNAME')
WRDS_PASSWORD = os.getenv('WRDS_PASSWORD')

# LLM
OPENAI_MODEL = "gpt-4o-mini"

# Root folder
ROOT = os.getenv('ROOT')

# Paths
DATABASE_PATH = os.path.join(ROOT, "data/queries.sqlite")
PROMPTS_PATH = os.path.join(ROOT, "assets/prompts.json")
TRANSCRIPT_DETAIL_PATH = os.path.join(ROOT, "data/transcript-detail.feather")
ACL_SCORES_PATH = os.path.join(ROOT, "data/raw/acl_scores.csv")
JOE_SCORES_PATH = os.path.join(ROOT, "data/raw/joe_scores.csv")
HUMAN_RATINGS_PATH = os.path.join(ROOT, "data/human-ratings.csv")
OUTPUT_DIR = os.path.join(ROOT, "output")
DATA_DIR = os.path.join(ROOT, "data")

# rclone
RCLONE_REMOTE = "collusion-llm"
RCLONE_REMOTE_DATABASE_PATH = "data/queries.sqlite"


def ensure_running_from_root():
    """Ensures the script runs from the ROOT directory."""
    if os.getcwd() != ROOT:
        os.chdir(ROOT)
        sys.path.insert(0, ROOT)  # Ensure imports work properly

# Run this automatically whenever config is imported
ensure_running_from_root()
