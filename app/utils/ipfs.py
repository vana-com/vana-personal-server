"""
IPFS utilities for robust data fetching with gateway fallbacks.

Provides centralized functions for handling IPFS URLs, converting them to gateway URLs,
and fetching content with automatic fallback and retry logic.
"""

import asyncio
import logging
import re
import time
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlparse
import requests
from requests.exceptions import RequestException, Timeout, HTTPError

logger = logging.getLogger(__name__)

# Default IPFS gateway URL
DEFAULT_IPFS_GATEWAY = "https://dweb.link/ipfs/"

# Alternative IPFS gateways ordered by reliability and rate limits
IPFS_GATEWAYS = [
    "https://dweb.link/ipfs/",                    # Interplanetary Shipyard - highly reliable
    "https://ipfs.io/ipfs/",                      # IPFS Foundation - reliable
    "https://cloudflare-ipfs.com/ipfs/",          # Cloudflare - good performance
    "https://gateway.pinata.cloud/ipfs/",         # Pinata - backup option (has rate limits)
    "https://ipfs.filebase.io/ipfs/",            # Filebase - emerging reliable option
    "https://nftstorage.link/ipfs/",             # NFT.Storage - additional reliability
    "https://w3s.link/ipfs/",                    # Web3.Storage - backup option
]

# Default timeout settings
DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_RETRY_DELAY = 1  # base delay between retries
MAX_RETRY_DELAY = 8  # maximum delay between retries


class IPFSError(Exception):
    """Base exception for IPFS-related errors."""
    pass


class IPFSTimeoutError(IPFSError):
    """Raised when IPFS requests timeout."""
    pass


class IPFSNotFoundError(IPFSError):
    """Raised when IPFS content is not found."""
    pass


class IPFSRateLimitError(IPFSError):
    """Raised when IPFS gateway rate limits are exceeded."""
    pass


def is_ipfs_url(url: str) -> bool:
    """
    Check if a URL is an IPFS URL (starts with ipfs://).
    
    Args:
        url: The URL to check
        
    Returns:
        True if the URL is an IPFS URL
    """
    return url.startswith("ipfs://")


def extract_ipfs_hash(url: str) -> Optional[str]:
    """
    Extract IPFS hash from various URL formats.
    
    Args:
        url: The URL to extract hash from
        
    Returns:
        The IPFS hash or None if not found
        
    Examples:
        >>> extract_ipfs_hash("ipfs://QmHash123")
        'QmHash123'
        >>> extract_ipfs_hash("https://gateway.pinata.cloud/ipfs/QmHash123")
        'QmHash123'
        >>> extract_ipfs_hash("QmHash123456789012345678901234567890123456")
        'QmHash123456789012345678901234567890123456'
    """
    # Handle various IPFS URL formats
    patterns = [
        r'ipfs/([a-zA-Z0-9]+)',                   # https://gateway.pinata.cloud/ipfs/HASH
        r'^ipfs://([a-zA-Z0-9]+)$',              # ipfs://HASH
        r'^([a-zA-Z0-9]{46,})$',                 # Just the hash (46+ chars for IPFS hashes)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def convert_ipfs_url(url: str, gateway: str = DEFAULT_IPFS_GATEWAY) -> str:
    """
    Convert an IPFS URL to an HTTP gateway URL.
    
    Args:
        url: The IPFS URL to convert (e.g., "ipfs://QmHash...")
        gateway: Optional gateway URL (defaults to DEFAULT_IPFS_GATEWAY)
        
    Returns:
        The HTTP gateway URL or original URL if not an IPFS URL
        
    Examples:
        >>> convert_ipfs_url("ipfs://QmHash123")
        'https://dweb.link/ipfs/QmHash123'
        >>> convert_ipfs_url("ipfs://QmHash123", "https://gateway.pinata.cloud/ipfs/")
        'https://gateway.pinata.cloud/ipfs/QmHash123'
    """
    hash_value = extract_ipfs_hash(url)
    if hash_value:
        return f"{gateway}{hash_value}"
    return url


def get_gateway_urls(hash_value: str) -> List[str]:
    """
    Get multiple gateway URLs for an IPFS hash (useful for fallback).
    
    Args:
        hash_value: The IPFS hash
        
    Returns:
        Array of gateway URLs
    """
    return [f"{gateway}{hash_value}" for gateway in IPFS_GATEWAYS]


def convert_ipfs_url_with_fallbacks(url: str) -> List[str]:
    """
    Convert an IPFS URL to multiple gateway URLs for fallback.
    
    Args:
        url: The IPFS URL
        
    Returns:
        Array of gateway URLs or original URL if not IPFS
    """
    hash_value = extract_ipfs_hash(url)
    if hash_value:
        return get_gateway_urls(hash_value)
    return [url]


def fetch_with_fallbacks(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    max_retries: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None
) -> requests.Response:
    """
    Fetch content from IPFS with automatic gateway fallbacks.
    
    Args:
        url: The IPFS URL to fetch
        timeout: Timeout per request in seconds
        retry_delay: Base delay between retries in seconds
        max_retries: Maximum number of retries per gateway (defaults to len(IPFS_GATEWAYS))
        headers: Optional headers to include in requests
        
    Returns:
        Response object from successful request
        
    Raises:
        IPFSError: If all gateways fail
        IPFSTimeoutError: If requests timeout
        IPFSNotFoundError: If content is not found
        IPFSRateLimitError: If rate limits are exceeded
    """
    hash_value = extract_ipfs_hash(url)
    if not hash_value:
        # Not an IPFS URL, fetch directly
        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            return response
        except Timeout as e:
            raise IPFSTimeoutError(f"Timeout fetching {url}: {str(e)}")
        except HTTPError as e:
            if e.response.status_code == 404:
                raise IPFSNotFoundError(f"Content not found at {url}")
            elif e.response.status_code == 429:
                raise IPFSRateLimitError(f"Rate limited at {url}")
            raise IPFSError(f"HTTP error fetching {url}: {str(e)}")
        except RequestException as e:
            raise IPFSError(f"Error fetching {url}: {str(e)}")
    
    gateway_urls = get_gateway_urls(hash_value)
    if max_retries is None:
        max_retries = len(gateway_urls)
    
    last_error: Optional[Exception] = None
    request_headers = headers or {}
    
    for i, gateway_url in enumerate(gateway_urls):
        try:
            logger.debug(f"Attempting to fetch from gateway {i+1}/{len(gateway_urls)}: {gateway_url}")
            
            response = requests.get(
                gateway_url,
                timeout=timeout,
                headers=request_headers
            )
            
            # If response is ok, return it
            if response.ok:
                logger.info(f"Successfully fetched from gateway: {gateway_url}")
                return response
            
            # Handle specific HTTP errors
            if response.status_code == 404:
                last_error = IPFSNotFoundError(f"Content not found at {gateway_url}")
                logger.warning(f"Content not found at gateway: {gateway_url}")
                continue
            
            # If rate limited (429), try next gateway immediately
            if response.status_code == 429:
                last_error = IPFSRateLimitError(f"Rate limited at gateway: {gateway_url}")
                logger.warning(f"Rate limited at gateway: {gateway_url}")
                continue
            
            # For other HTTP errors, still try next gateway
            last_error = IPFSError(f"Gateway error {response.status_code}: {gateway_url}")
            logger.warning(f"Gateway error {response.status_code}: {gateway_url}")
            
        except Timeout as e:
            last_error = IPFSTimeoutError(f"Timeout at gateway: {gateway_url}")
            logger.warning(f"Timeout at gateway: {gateway_url}")
        except RequestException as e:
            last_error = IPFSError(f"Request error at gateway {gateway_url}: {str(e)}")
            logger.warning(f"Request error at gateway {gateway_url}: {str(e)}")
        
        # Add exponential backoff between retries (except for last attempt)
        if i < len(gateway_urls) - 1:
            delay = min(retry_delay * (2 ** i), MAX_RETRY_DELAY)
            logger.debug(f"Waiting {delay}s before trying next gateway")
            time.sleep(delay)
    
    # All gateways failed
    error_msg = f"All IPFS gateways failed for hash {hash_value}"
    if last_error:
        error_msg += f". Last error: {str(last_error)}"
    
    if isinstance(last_error, IPFSTimeoutError):
        raise IPFSTimeoutError(error_msg)
    elif isinstance(last_error, IPFSNotFoundError):
        raise IPFSNotFoundError(error_msg)
    elif isinstance(last_error, IPFSRateLimitError):
        raise IPFSRateLimitError(error_msg)
    else:
        raise IPFSError(error_msg)


def fetch_json_with_fallbacks(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    max_retries: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Fetch JSON content from IPFS with automatic gateway fallbacks.
    
    Args:
        url: The IPFS URL to fetch
        timeout: Timeout per request in seconds
        retry_delay: Base delay between retries in seconds
        max_retries: Maximum number of retries per gateway
        headers: Optional headers to include in requests
        
    Returns:
        Parsed JSON data
        
    Raises:
        IPFSError: If all gateways fail or JSON parsing fails
    """
    response = fetch_with_fallbacks(
        url=url,
        timeout=timeout,
        retry_delay=retry_delay,
        max_retries=max_retries,
        headers=headers
    )
    
    try:
        return response.json()
    except ValueError as e:
        raise IPFSError(f"Invalid JSON content from {url}: {str(e)}")


def test_gateway_availability(timeout: int = 5) -> Dict[str, bool]:
    """
    Test availability of all IPFS gateways.
    
    Args:
        timeout: Timeout per gateway test in seconds
        
    Returns:
        Dictionary mapping gateway URLs to availability status
    """
    # Use a well-known IPFS hash for testing
    test_hash = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"  # "hello world"
    gateway_status = {}
    
    for gateway in IPFS_GATEWAYS:
        test_url = f"{gateway}{test_hash}"
        try:
            response = requests.get(test_url, timeout=timeout)
            gateway_status[gateway] = response.ok
            logger.debug(f"Gateway {gateway}: {'✓' if response.ok else '✗'}")
        except Exception as e:
            gateway_status[gateway] = False
            logger.debug(f"Gateway {gateway}: ✗ ({str(e)})")
    
    return gateway_status