"""Settings de test : données isolées dans un dossier temporaire, Huey synchrone."""

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="mue-tests-")
os.environ["MUE_DATA_DIR"] = os.path.join(_tmp, "data")
os.environ["MUE_LOG_DIR"] = os.path.join(_tmp, "logs")
os.environ["MUE_HUEY_IMMEDIATE"] = "1"

from .settings import *  # noqa: E402,F403
