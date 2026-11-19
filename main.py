import os
import sys

root_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.join(root_dir, "api")
backend_dir = os.path.join(root_dir, "backend")

for p in [api_dir, backend_dir, root_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from api.app.main import app

handler = app
