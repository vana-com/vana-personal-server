import json
import logging
import time
from typing import Optional, List
import requests
from requests.exceptions import RequestException, Timeout

from .grant_models import GrantFile, validate_grant_file_structure

logger = logging.getLogger(__name__)


class NetworkError(Exception):
    """Error thrown when network operations fail"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


def retrieve_grant_file(grant_url: str, timeout: int = 10) -> GrantFile:
    """
    Retrieves a grant file from IPFS.

    Args:
        grant_url: The IPFS URL (e.g., "ipfs://QmHash...")
        timeout: Request timeout in seconds

    Returns:
        GrantFile object

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
                logger.debug(f"Trying gateway: {gateway_url}")
                response = requests.get(gateway_url, timeout=timeout)

                if response.status_code == 200:
                    try:
                        grant_data = response.json()

                        if validate_grant_file_structure(grant_data):
                            return GrantFile(
                                grantee=grant_data["grantee"],
                                operation=grant_data["operation"],
                                parameters=grant_data["parameters"],
                                expires=grant_data.get("expires"),
                            )
                        else:
                            logger.warning(
                                f"Invalid grant file structure from {gateway_url}"
                            )
                            continue

                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON from {gateway_url}: {e}")
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


def is_grant_expired(grant_file: GrantFile) -> bool:
    """
    Utility to check if a grant has expired

    Args:
        grant_file: The grant file to check

    Returns:
        True if the grant has expired, False otherwise
    """
    if not grant_file.expires:
        return False  # No expiration set

    current_time = int(time.time())
    return current_time > grant_file.expires


def get_grant_time_remaining(grant_file: GrantFile) -> Optional[int]:
    """
    Utility to get the time remaining before grant expires (in seconds)

    Args:
        grant_file: The grant file to check

    Returns:
        Seconds remaining before expiration, or None if no expiration set
    """
    if not grant_file.expires:
        return None  # No expiration set

    current_time = int(time.time())
    remaining = grant_file.expires - current_time
    return max(0, remaining)
