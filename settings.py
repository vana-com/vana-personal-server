"""
Application settings loaded from environment variables.
"""

import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    def __init__(self):
        self.REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
        if not self.REPLICATE_API_TOKEN:
            raise ValueError("REPLICATE_API_TOKEN is not set")
        
        self.WALLET_MNEMONIC = os.getenv("WALLET_MNEMONIC")
        if not self.WALLET_MNEMONIC:
            raise ValueError("WALLET_MNEMONIC is not set")

        self.MNEMONIC_LANGUAGE = os.getenv("MNEMONIC_LANGUAGE", "english")

settings = Settings()
