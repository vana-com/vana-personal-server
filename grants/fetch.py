import logging
from typing import Any, Optional
from utils.ipfs import (
    fetch_json_with_fallbacks, 
    IPFSError, 
    IPFSTimeoutError, 
    IPFSNotFoundError, 
    IPFSRateLimitError
)
from domain.exceptions import FileAccessError

logger = logging.getLogger(__name__)


class NetworkError(Exception):
    """Error thrown when network operations fail"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


def fetch_raw_grant_file(grant_url: str, timeout: int = 10) -> Any:
    """
    Retrieves a grant file from IPFS using robust gateway fallbacks.

    Args:
        grant_url: The IPFS URL (e.g., "ipfs://QmHash...")
        timeout: Request timeout in seconds per gateway

    Returns:
        Raw grant file data (parsed JSON)

    Raises:
        FileAccessError: When all gateways fail to retrieve the file
        ValueError: When the retrieved data is not a valid grant file
    """
    try:
        logger.info(f"Fetching grant file from: {grant_url}")
        
        # Use the robust IPFS fetching with fallbacks
        grant_data = fetch_json_with_fallbacks(
            url=grant_url,
            timeout=timeout,
            retry_delay=1,  # 1 second base delay between retries
            headers={
                'User-Agent': 'Vana-Personal-Server/1.0',
                'Accept': 'application/json'
            }
        )
        
        # Validate that we got some data
        if not grant_data:
            raise ValueError(f"Empty grant file retrieved from {grant_url}")
        
        logger.info(f"Successfully retrieved grant file from {grant_url}")
        return grant_data

    except IPFSNotFoundError as e:
        logger.error(f"Grant file not found: {str(e)}")
        raise FileAccessError(f"Grant file not found at {grant_url}: {str(e)}")
    
    except IPFSTimeoutError as e:
        logger.error(f"Timeout retrieving grant file: {str(e)}")
        raise FileAccessError(f"Timeout retrieving grant file from {grant_url}: {str(e)}")
    
    except IPFSRateLimitError as e:
        logger.error(f"Rate limited retrieving grant file: {str(e)}")
        raise FileAccessError(f"Rate limited retrieving grant file from {grant_url}: {str(e)}")
    
    except IPFSError as e:
        logger.error(f"IPFS error retrieving grant file: {str(e)}")
        raise FileAccessError(f"IPFS error retrieving grant file from {grant_url}: {str(e)}")
    
    except ValueError as e:
        logger.error(f"Invalid grant file data: {str(e)}")
        raise ValueError(f"Invalid grant file data from {grant_url}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error retrieving grant file: {str(e)}")
        raise FileAccessError(f"Unexpected error retrieving grant file from {grant_url}: {str(e)}")

