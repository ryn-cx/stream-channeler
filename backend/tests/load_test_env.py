# TODO: Validate
import os

from app.constants import BACKEND_FOLDER

env_file = BACKEND_FOLDER / ".env.test"
if not env_file.exists():
    msg = f"Test environment file not found at {env_file}"
    raise FileNotFoundError(msg)

for line in env_file.read_text().strip().splitlines():
    # TODO: This works but is clunky.
    if "=" in line and not line.startswith("#"):
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
