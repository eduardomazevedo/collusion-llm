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
OPENAI_MODEL = "gpt-4.1-mini"
PROVIDER = "openai"
MAX_TOKENS = 10000
TEMPERATURE = 1.0

# Root folder
ROOT = os.getenv('ROOT')

# Paths
DATA_DIR = os.path.join(ROOT, "data")
DATABASE_PATH = os.path.join(DATA_DIR, "datasets", "queries.sqlite")
PROMPTS_PATH = os.path.join(ROOT, "assets", "prompts.json")
TRANSCRIPT_DETAIL_PATH = os.path.join(DATA_DIR, "datasets", "transcript_detail.feather")
ACL_SCORES_PATH = os.path.join(DATA_DIR, "raw", "human_ratings", "acl_scores.csv")
JOE_SCORES_PATH = os.path.join(DATA_DIR, "raw", "human_ratings", "joe_scores.csv")
HUMAN_RATINGS_PATH = os.path.join(DATA_DIR, "datasets", "human_ratings.csv")
COMPANIES_TRANSCRIPTS_PATH = os.path.join(DATA_DIR, "intermediaries", "companies_transcripts.csv")
OUTPUTS_DIR = os.path.join(DATA_DIR, "outputs")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

BENCHMARKING_PATH = os.path.join(DATA_DIR, "benchmarking", "comprehensive_metrics.csv")

# Thresholds
JOE_SCORE_THRESHOLD = 50  # Lowered from 75 to capture more of Joe's conservative ratings (5 transcripts vs 1)
LLM_SCORE_THRESHOLD = 75
ANALYSIS_SCORE_THRESHOLD = 75

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
