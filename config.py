# Paths = Data type specific
# MAke sure that a fodler name with following data type exists inside 
#   data/, generated_tasks/ and output/ folders.
#
#### Select any one data type by uncommenting the line below

import os
from dotenv import load_dotenv

# Load .env from project root (load_dotenv looks for a .env file)
load_dotenv()

# DATA_TYPE available options: "temp_humidity", "air_quality", "soil", "weather"
DATA_TYPE = "air_quality"  # change only this line to switch data type
OLLAMA_SERVER_URL = os.getenv("OLLAMA_SERVER_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3:8b")

if not OLLAMA_SERVER_URL:
    raise RuntimeError("OLLAMA_SERVER_URL not found. Add it to your .env or set the environment variable.")

if not DATA_TYPE:
    raise RuntimeError("DATA_TYPE is not set. Please set it in config.py.")