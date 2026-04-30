import os
from pathlib import Path
from dotenv import load_dotenv

_project_dir = Path(__file__).resolve().parent
load_dotenv(_project_dir / ".env")

ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
VLM_MODEL_ID = os.getenv("VLM_MODEL_ID", "doubao-seed-2-0-pro-260215")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL_ID = os.getenv("OPENAI_MODEL_ID", "gpt-4o")

DEFAULT_VLM_BACKEND = os.getenv("DEFAULT_VLM_BACKEND", "volcengine")

SCREENSHOTS_DIR = os.path.join(_project_dir, "screenshots")
REPORTS_DIR = os.path.join(_project_dir, "reports")
