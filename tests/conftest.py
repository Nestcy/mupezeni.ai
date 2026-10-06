import sys
from pathlib import Path

# Add repo root and apps/api to sys.path for test discovery
root_dir = Path(__file__).resolve().parent.parent
api_dir = root_dir / "apps" / "api"

for d in (root_dir, api_dir):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
