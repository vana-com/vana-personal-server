"""
Application settings loaded from environment variables.
"""

import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "dummy")
    REPLICATE_API_BASE_URL: str = os.getenv(
        "REPLICATE_API_BASE_URL", "https://api.replicate.com/v1"
    )

    SERVER_MODEL_VERSION: str = os.getenv(
        "SERVER_MODEL_VERSION",
        "vana-com/personal-server:6dae0fead4017557a2e6bd020643359ac1769228a9cfe3bd2365eeeb9711610e",
    )

    WALLET_MNEMONIC: str = os.getenv("WALLET_MNEMONIC")
    MNEMONIC_LANGUAGE: str = os.getenv("MNEMONIC_LANGUAGE", "english")

settings = Settings()
