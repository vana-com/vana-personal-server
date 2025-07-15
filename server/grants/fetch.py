import json
import logging
from typing import Any, Optional
import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)


class NetworkError(Exception):
    """Error thrown when network operations fail"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


def fetch_raw_grant_file(grant_url: str, timeout: int = 10) -> Any:
    """
    Retrieves a grant file from IPFS.

    Args:
        grant_url: The IPFS URL (e.g., "ipfs://QmHash...")
        timeout: Request timeout in seconds

    Returns:
        Raw grant file data

    Raises:
        NetworkError: When all gateways fail to retrieve the file
        ValueError: When the retrieved data is not a valid grant file
    """
    try:
        # Extract IPFS hash from URL
        ipfs_hash = (
            grant_url.replace("ipfs://", "")
            if grant_url.startswith("ipfs://")
            else grant_url
        )

        # Try multiple IPFS gateways
        gateways = [
            f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}",
            f"https://ipfs.io/ipfs/{ipfs_hash}",
            f"https://dweb.link/ipfs/{ipfs_hash}",
        ]

        for gateway_url in gateways:
            try:
                logger.info(f"Trying gateway: {gateway_url}")
                response = requests.get(gateway_url, timeout=timeout)

                if response.status_code == 200:
                    try:
                        return response.json()
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON from {gateway_url}: {e}")
                        continue
                else:
                    logger.warning(f"Failed to retrieve grant file from {gateway_url}")
                    continue

            except (RequestException, Timeout) as e:
                logger.warning(f"Gateway {gateway_url} failed: {e}")
                continue

        raise NetworkError(
            f"Failed to retrieve grant file from any IPFS gateway: {grant_url}"
        )

    except Exception as e:
        if isinstance(e, NetworkError):
            raise
        raise NetworkError(f"Error retrieving grant file: {str(e)}", e)

