import os
import tempfile

# Must be set before the app is imported, because config reads the environment at import time.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["COMMITTEE_CODE"] = "test-code"
