import os
from pathlib import Path
from dotenv import load_dotenv

_adsflow_dir = Path(__file__).resolve().parent
load_dotenv(_adsflow_dir / ".env")

ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
SEEDANCE_MODEL_ID = os.getenv("SEEDANCE_MODEL_ID", "doubao-seedance-2-0-260128")
SEEDANCE_FAST_MODEL_ID = os.getenv("SEEDANCE_FAST_MODEL_ID", "doubao-seedance-2-0-fast-260128")
VLM_MODEL_ID = os.getenv("VLM_MODEL_ID", "doubao-seed-2-0-pro-260215")
SEEDREAM_MODEL_ID = os.getenv("SEEDREAM_MODEL_ID", "doubao-seedream-5-0-260128")

SEEDANCE_MAX_DURATION = 15
SLICE_DURATION = 15
POLL_INTERVAL = 10
POLL_TIMEOUT = 600

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
