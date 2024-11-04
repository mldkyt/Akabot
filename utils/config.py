import logging
import os


def get_key(key: str, default: str = ""):
    key = key.upper()
    value = os.getenv(key)
    if not value:
        logging.warning("Using default %s for %s", default, key)

        if len(default.strip()) == 0:
            raise ValueError("The default for the value %s is by default None. This value is required" % key)

        return default

    return value
