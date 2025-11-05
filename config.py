
# Paths = Data type specific
# MAke sure that a fodler name with following data type exists inside 
#   data/, generated_tasks/ and output/ folders.
#
#### Select any one data type by uncommenting the line below

import os
from dotenv import load_dotenv

# Load .env from project root (load_dotenv looks for a .env file)
load_dotenv()

# DATA_TYPE and other config
DATA_TYPE = os.getenv("DATA_TYPE", "temp_humidity")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found. Add it to your .env or set the environment variable.")

NO_OF_TASKS = 1
parallel_execution = False
parallel_execution_limit = 2  # Max number of parallel tasks if parallel_execution is True, DEFAULT value is 1
