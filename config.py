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
PROVIDER = "openai"
MAX_TOKENS = 1000
TEMPERATURE = 1.0

# Root folder
ROOT = os.getenv('ROOT')

# Paths
DATABASE_PATH = os.path.join(ROOT, "data", "datasets", "queries.sqlite")
PROMPTS_PATH = os.path.join(ROOT, "assets", "prompts.json")
TRANSCRIPT_DETAIL_PATH = os.path.join(ROOT, "data", "datasets", "transcript_detail.feather")
ACL_SCORES_PATH = os.path.join(ROOT, "data", "raw", "human_ratings", "acl_scores.csv")
JOE_SCORES_PATH = os.path.join(ROOT, "data", "raw", "human_ratings", "joe_scores.csv")
HUMAN_RATINGS_PATH = os.path.join(ROOT, "data", "datasets", "human_ratings.csv")
COMPANIES_TRANSCRIPTS_PATH = os.path.join(ROOT, "data", "intermediaries", "companies_transcripts.csv")
OUTPUTS_DIR = os.path.join(ROOT, "data", "outputs")
DATA_DIR = os.path.join(ROOT, "data")
BENCHMARKING_PATH = os.path.join(DATA_DIR, "benchmarking", "comprehensive_metrics.csv")

# Thresholds
JOE_SCORE_THRESHOLD = 75
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
