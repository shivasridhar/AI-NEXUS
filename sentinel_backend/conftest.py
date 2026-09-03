import sys
import os
from dotenv import load_dotenv

# Ensure sentinel_backend/ is always the first path entry so that
# `import app.*` resolves to sentinel_backend/app/ in all cases.
_backend_root = os.path.dirname(os.path.abspath(__file__))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

# Load the backend .env file so settings (like SECRET_KEY) are populated
_env_path = os.path.join(_backend_root, '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path)
