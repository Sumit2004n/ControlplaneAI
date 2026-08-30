import os
import sys
from pathlib import Path

# Use an isolated test database and force demo mode before the app is imported.
BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DB = BACKEND_DIR / "test_controlplane.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["DEMO_MODE"] = "true"

sys.path.insert(0, str(BACKEND_DIR))
