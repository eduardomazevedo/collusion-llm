import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configuration variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WRDS_USERNAME = os.getenv('WRDS_USERNAME')
WRDS_PASSWORD = os.getenv('WRDS_PASSWORD')