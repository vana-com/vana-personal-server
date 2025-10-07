import logging
import time
import re
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO
import requests
from requests.exceptions import RequestException, Timeout, HTTPError
from urllib.parse import urlparse, parse_qs

from utils.ipfs import (
    is_ipfs_url,
    convert_ipfs_url_with_fallbacks,
    extract_ipfs_hash,
    IPFSError,
    IPFSTimeoutError,
    IPFSNotFoundError,
    IPFSRateLimitError,
    DEFAULT_TIMEOUT,
    DEFAULT_RETRY_DELAY,
    MAX_RETRY_DELAY
)
from domain.exceptions import FileAccessError, ValidationError

logger = logging.getLogger(__name__)

# File size limits
MAX_FILE_SIZE = 1024 * 1024 * 5  # 5MB
DEFAULT_CHUNK_SIZE = 8192    # 8KB chunks for streaming

# URL type enumeration
URL_TYPE_IPFS = "ipfs"
URL_TYPE_GOOGLE_DRIVE = "google_drive"
URL_TYPE_HTTP = "http"
URL_TYPE_HTTPS = "https"

# Google Drive patterns
GOOGLE_DRIVE_VIEW_PATTERN = r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/view'
GOOGLE_DRIVE_OPEN_PATTERN = r'https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)'
GOOGLE_DRIVE_DOWNLOAD_TEMPLATE = "https://drive.google.com/file/d/{file_id}/download"
GOOGLE_DRIVE_EXPORT_TEMPLATE = "https://drive.google.com/uc?export=download&id={file_id}"


def detect_url_type(url: str) -> str:
    """
    Detect the type of URL for appropriate download handling.
    
    Args:
        url: The URL to analyze
        
    Returns:
        URL type constant (URL_TYPE_IPFS, URL_TYPE_GOOGLE_DRIVE, etc.)
    """
    if is_ipfs_url(url):
        return URL_TYPE_IPFS
    
    if is_google_drive_url(url):
        return URL_TYPE_GOOGLE_DRIVE
    
    parsed = urlparse(url)
    if parsed.scheme == 'https':
        return URL_TYPE_HTTPS
    elif parsed.scheme == 'http':
        return URL_TYPE_HTTP
    
    return URL_TYPE_HTTP  # Default fallback


def is_google_drive_url(url: str) -> bool:
    """
    Check if a URL is a Google Drive URL.
    
    Args:
        url: The URL to check
        
    Returns:
        True if the URL is a Google Drive URL
    """
    return ('drive.google.com' in url or 'docs.google.com' in url)


def extract_google_drive_file_id(url: str) -> Optional[str]:
    """
    Extract Google Drive file ID from various URL formats.
    
    Args:
        url: The Google Drive URL
        
    Returns:
        The file ID or None if not found
        
    Examples:
        >>> extract_google_drive_file_id("https://drive.google.com/file/d/1Mb2JjYVwQVj-a8W3Uf8u8uZcwKCC4Ytk/view")
        '1Mb2JjYVwQVj-a8W3Uf8u8uZcwKCC4Ytk'
        >>> extract_google_drive_file_id("https://drive.google.com/open?id=1Mb2JjYVwQVj-a8W3Uf8u8uZcwKCC4Ytk")
        '1Mb2JjYVwQVj-a8W3Uf8u8uZcwKCC4Ytk'
    """
    # Try the /file/d/ pattern first
    match = re.search(GOOGLE_DRIVE_VIEW_PATTERN, url)
    if match:
        return match.group(1)
    
    # Try the open?id= pattern
    match = re.search(GOOGLE_DRIVE_OPEN_PATTERN, url)
    if match:
        return match.group(1)
    
    # Try to extract from URL parameters
    parsed = urlparse(url)
    if parsed.query:
        params = parse_qs(parsed.query)
        if 'id' in params:
            return params['id'][0]
    
    return None


def convert_google_drive_url_to_download(url: str) -> List[str]:
    """
    Convert Google Drive URLs to direct download URLs with fallbacks.
    
    Args:
        url: The Google Drive URL
        
    Returns:
        List of download URLs to try (with fallbacks)
        
    Raises:
        GoogleDriveError: If file ID cannot be extracted
    """
    file_id = extract_google_drive_file_id(url)
    if not file_id:
        raise GoogleDriveError(f"Could not extract file ID from Google Drive URL: {url}")
    
    # Return multiple download URL formats as fallbacks
    return [
        GOOGLE_DRIVE_DOWNLOAD_TEMPLATE.format(file_id=file_id),
        GOOGLE_DRIVE_EXPORT_TEMPLATE.format(file_id=file_id)
    ]


def download_from_google_drive(
    url: str,
    max_size: int = MAX_FILE_SIZE,
    timeout: int = DEFAULT_TIMEOUT,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    headers: Optional[Dict[str, str]] = None
) -> bytes:
    """
    Download a file from Google Drive with robust error handling.
    
    Args:
        url: The Google Drive URL
        max_size: Maximum file size in bytes
        timeout: Timeout per request in seconds
        retry_delay: Base delay between retries in seconds
        headers: Optional headers to include in requests
        
    Returns:
        File content as bytes
        
    Raises:
        GoogleDriveError: When download fails
        FileTooLargeError: When file exceeds size limit
    """
    try:
        download_urls = convert_google_drive_url_to_download(url)
    except GoogleDriveError as e:
        logger.error(f"Google Drive URL conversion failed: {str(e)}")
        raise
    
    logger.info(f"Downloading from Google Drive: {url}")
    logger.debug(f"Trying {len(download_urls)} Google Drive download URLs")
    
    # Prepare headers with user agent
    request_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }
    if headers:
        request_headers.update(headers)
    
    last_error: Optional[Exception] = None
    
    for i, download_url in enumerate(download_urls):
        try:
            logger.debug(f"Attempting Google Drive download {i+1}/{len(download_urls)}: {download_url}")
            
            # Create a session to handle redirects and cookies
            session = requests.Session()
            session.headers.update(request_headers)
            
            # Start the request with streaming
            response = session.get(download_url, timeout=timeout, stream=True, allow_redirects=True)
            
            # Google Drive may return HTML with a virus warning for large files
            # Check if we got HTML instead of the file
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                # Try to extract direct download link from the HTML
                if response.text and 'virus scan warning' in response.text.lower():
                    # Look for the confirm download link
                    confirm_match = re.search(r'confirm=([^&]+)', response.text)
                    if confirm_match:
                        confirm_code = confirm_match.group(1)
                        confirm_url = f"{download_url}&confirm={confirm_code}"
                        logger.debug(f"Using virus scan confirmation URL: {confirm_url}")
                        response = session.get(confirm_url, timeout=timeout, stream=True)
            
            # Check status code
            if not response.ok:
                if response.status_code == 404:
                    last_error = GoogleDriveError(f"File not found at {download_url}")
                    logger.warning(f"File not found at: {download_url}")
                    continue
                elif response.status_code == 403:
                    last_error = GoogleDriveError(f"Access denied at {download_url}")
                    logger.warning(f"Access denied at: {download_url}")
                    continue
                elif response.status_code == 429:
                    last_error = GoogleDriveError(f"Rate limited at {download_url}")
                    logger.warning(f"Rate limited at: {download_url}")
                    continue
                else:
                    last_error = GoogleDriveError(f"HTTP {response.status_code} at {download_url}")
                    logger.warning(f"HTTP {response.status_code} at: {download_url}")
                    continue
            
            # Check content length if available
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    if size > max_size:
                        last_error = FileTooLargeError(
                            f"File size ({size} bytes) exceeds limit ({max_size} bytes) at {download_url}"
                        )
                        logger.warning(f"File too large ({size} bytes) at: {download_url}")
                        continue
                except ValueError:
                    logger.debug(f"Invalid content-length header at: {download_url}")
            
            # Download file in chunks
            content = BytesIO()
            downloaded_size = 0
            
            try:
                for chunk in response.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
                    if chunk:  # Filter out keep-alive chunks
                        chunk_size = len(chunk)
                        if downloaded_size + chunk_size > max_size:
                            raise FileTooLargeError(
                                f"File size exceeds limit ({max_size} bytes) during download from {download_url}"
                            )
                        
                        content.write(chunk)
                        downloaded_size += chunk_size
                
                file_content = content.getvalue()
                logger.info(f"Successfully downloaded {downloaded_size} bytes from Google Drive: {download_url}")
                return file_content
                
            finally:
                content.close()
                response.close()
                session.close()
        
        except Timeout as e:
            last_error = GoogleDriveError(f"Timeout downloading from {download_url}")
            logger.warning(f"Timeout downloading from: {download_url}")
        except RequestException as e:
            last_error = GoogleDriveError(f"Request error downloading from {download_url}: {str(e)}")
            logger.warning(f"Request error downloading from {download_url}: {str(e)}")
        except FileTooLargeError as e:
            last_error = e
            logger.warning(str(e))
        except Exception as e:
            last_error = GoogleDriveError(f"Unexpected error downloading from {download_url}: {str(e)}")
            logger.warning(f"Unexpected error downloading from {download_url}: {str(e)}")
        
        # Add delay between retries (except for last attempt)
        if i < len(download_urls) - 1:
            delay = min(retry_delay * (2 ** i), MAX_RETRY_DELAY)
            logger.debug(f"Waiting {delay}s before trying next Google Drive URL")
            time.sleep(delay)
    
    # All Google Drive URLs failed
    error_msg = f"All Google Drive download URLs failed for {url}"
    if last_error:
        error_msg += f". Last error: {str(last_error)}"
    
    if isinstance(last_error, FileTooLargeError):
        raise last_error
    else:
        raise GoogleDriveError(error_msg)


class FileTooLargeError(FileAccessError):
    """Raised when downloaded file exceeds size limit."""
    pass


class GoogleDriveError(FileAccessError):
    """Raised when Google Drive download fails."""
    pass


class UnsupportedURLError(FileAccessError):
    """Raised when URL type is not supported."""
    pass


def download_from_http(
    url: str,
    max_size: int = MAX_FILE_SIZE,
    timeout: int = DEFAULT_TIMEOUT,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    headers: Optional[Dict[str, str]] = None
) -> bytes:
    """
    Download a file from HTTP/HTTPS with robust error handling.
    
    Args:
        url: The HTTP/HTTPS URL
        max_size: Maximum file size in bytes
        timeout: Timeout per request in seconds
        retry_delay: Base delay between retries in seconds
        headers: Optional headers to include in requests
        
    Returns:
        File content as bytes
        
    Raises:
        FileAccessError: When download fails
        FileTooLargeError: When file exceeds size limit
    """
    logger.info(f"Downloading from HTTP/HTTPS: {url}")
    
    # Prepare headers
    request_headers = {
        'User-Agent': 'Vana-Personal-Server/1.0',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
    }
    if headers:
        request_headers.update(headers)
    
    try:
        # Start the request with streaming
        response = requests.get(url, timeout=timeout, headers=request_headers, stream=True)
        
        # Check status code
        if not response.ok:
            if response.status_code == 404:
                raise FileAccessError(f"File not found at {url}")
            elif response.status_code == 403:
                raise FileAccessError(f"Access denied at {url}")
            elif response.status_code == 429:
                raise FileAccessError(f"Rate limited at {url}")
            else:
                raise FileAccessError(f"HTTP {response.status_code} at {url}")
        
        # Check content length if available
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > max_size:
                    raise FileTooLargeError(
                        f"File size ({size} bytes) exceeds limit ({max_size} bytes) at {url}"
                    )
            except ValueError:
                logger.debug(f"Invalid content-length header at: {url}")
        
        # Download file in chunks
        content = BytesIO()
        downloaded_size = 0
        
        try:
            for chunk in response.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
                if chunk:  # Filter out keep-alive chunks
                    chunk_size = len(chunk)
                    if downloaded_size + chunk_size > max_size:
                        raise FileTooLargeError(
                            f"File size exceeds limit ({max_size} bytes) during download from {url}"
                        )
                    
                    content.write(chunk)
                    downloaded_size += chunk_size
            
            file_content = content.getvalue()
            logger.info(f"Successfully downloaded {downloaded_size} bytes from: {url}")
            return file_content
            
        finally:
            content.close()
            response.close()
    
    except Timeout as e:
        raise FileAccessError(f"Timeout downloading from {url}")
    except RequestException as e:
        raise FileAccessError(f"Request error downloading from {url}: {str(e)}")
    except FileTooLargeError as e:
        raise e
    except Exception as e:
        raise FileAccessError(f"Unexpected error downloading from {url}: {str(e)}")


def download_from_ipfs(
    file_url: str,
    max_size: int = MAX_FILE_SIZE,
    timeout: int = DEFAULT_TIMEOUT,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    max_retries: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None
) -> bytes:
    """
    Download a file from IPFS with robust gateway fallbacks.
    
    Args:
        file_url: The IPFS URL to download from
        max_size: Maximum file size in bytes
        timeout: Timeout per request in seconds
        retry_delay: Base delay between retries in seconds
        max_retries: Maximum number of retries (defaults to number of IPFS gateways)
        headers: Optional headers to include in requests
        
    Returns:
        File content as bytes
        
    Raises:
        FileAccessError: When download fails
        FileTooLargeError: When file exceeds size limit
    """
    download_urls = convert_ipfs_url_with_fallbacks(file_url)
    ipfs_hash = extract_ipfs_hash(file_url)
    logger.info(f"Downloading from IPFS: {file_url}")
    logger.debug(f"IPFS file detected, hash: {ipfs_hash}, trying {len(download_urls)} gateways")
    
    if max_retries is None:
        max_retries = len(download_urls)
    
    # Prepare headers
    request_headers = {
        'User-Agent': 'Vana-Personal-Server/1.0',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
    }
    if headers:
        request_headers.update(headers)
    
    last_error: Optional[Exception] = None
    
    for i, download_url in enumerate(download_urls):
        try:
            logger.debug(f"Attempting IPFS download {i+1}/{len(download_urls)}: {download_url}")
            
            # Start the request with streaming
            response = requests.get(
                download_url,
                timeout=timeout,
                headers=request_headers,
                stream=True
            )
            
            # Check status code
            if not response.ok:
                if response.status_code == 404:
                    last_error = IPFSNotFoundError(f"File not found at {download_url}")
                    logger.warning(f"File not found at: {download_url}")
                    continue
                elif response.status_code == 429:
                    last_error = IPFSRateLimitError(f"Rate limited at {download_url}")
                    logger.warning(f"Rate limited at: {download_url}")
                    continue
                else:
                    last_error = FileAccessError(f"HTTP {response.status_code} at {download_url}")
                    logger.warning(f"HTTP {response.status_code} at: {download_url}")
                    continue
            
            # Check content length if available
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    if size > max_size:
                        last_error = FileTooLargeError(
                            f"File size ({size} bytes) exceeds limit ({max_size} bytes) at {download_url}"
                        )
                        logger.warning(f"File too large ({size} bytes) at: {download_url}")
                        continue
                except ValueError:
                    logger.debug(f"Invalid content-length header at: {download_url}")
            
            # Download file in chunks to control memory usage and size
            content = BytesIO()
            downloaded_size = 0
            
            try:
                for chunk in response.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
                    if chunk:  # Filter out keep-alive chunks
                        chunk_size = len(chunk)
                        if downloaded_size + chunk_size > max_size:
                            raise FileTooLargeError(
                                f"File size exceeds limit ({max_size} bytes) during download from {download_url}"
                            )
                        
                        content.write(chunk)
                        downloaded_size += chunk_size
                
                file_content = content.getvalue()
                logger.info(f"Successfully downloaded {downloaded_size} bytes from IPFS: {download_url}")
                return file_content
                
            finally:
                content.close()
                response.close()
        
        except Timeout as e:
            last_error = IPFSTimeoutError(f"Timeout downloading from {download_url}")
            logger.warning(f"Timeout downloading from: {download_url}")
        except RequestException as e:
            last_error = FileAccessError(f"Request error downloading from {download_url}: {str(e)}")
            logger.warning(f"Request error downloading from {download_url}: {str(e)}")
        except FileTooLargeError as e:
            # Re-raise size errors immediately for this URL, but try other URLs
            last_error = e
            logger.warning(str(e))
        except Exception as e:
            last_error = FileAccessError(f"Unexpected error downloading from {download_url}: {str(e)}")
            logger.warning(f"Unexpected error downloading from {download_url}: {str(e)}")
        
        # Add exponential backoff between retries (except for last attempt)
        if i < len(download_urls) - 1:
            delay = min(retry_delay * (2 ** i), MAX_RETRY_DELAY)
            logger.debug(f"Waiting {delay}s before trying next URL")
            time.sleep(delay)
    
    # All IPFS gateways failed
    error_msg = f"All IPFS gateways failed for file {file_url}"
    if last_error:
        error_msg += f". Last error: {str(last_error)}"
    
    # Raise appropriate exception based on last error type
    if isinstance(last_error, IPFSTimeoutError):
        raise FileAccessError(f"Timeout downloading file: {error_msg}")
    elif isinstance(last_error, IPFSNotFoundError):
        raise FileAccessError(f"File not found: {error_msg}")
    elif isinstance(last_error, IPFSRateLimitError):
        raise FileAccessError(f"Rate limited downloading file: {error_msg}")
    elif isinstance(last_error, FileTooLargeError):
        raise last_error  # Re-raise size errors as-is
    else:
        raise FileAccessError(f"Download failed: {error_msg}")


def download_file(
    file_url: str,
    max_size: int = MAX_FILE_SIZE,
    timeout: int = DEFAULT_TIMEOUT,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    max_retries: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None
) -> bytes:
    """
    Download a file with robust error handling for multiple source types.
    
    Supports IPFS URLs, Google Drive URLs, and regular HTTP/HTTPS URLs.
    Each source type has specialized handling for optimal reliability.
    
    Args:
        file_url: The URL to download from (supports IPFS, Google Drive, HTTP/HTTPS)
        max_size: Maximum file size in bytes (default: 1MB)
        timeout: Timeout per request in seconds
        retry_delay: Base delay between retries in seconds
        max_retries: Maximum number of retries (varies by source type)
        headers: Optional headers to include in requests
        
    Returns:
        File content as bytes
        
    Raises:
        FileAccessError: When download fails
        FileTooLargeError: When file exceeds size limit
        ValidationError: When inputs are invalid
        GoogleDriveError: When Google Drive-specific issues occur
        UnsupportedURLError: When URL type is not supported
    """
    if not file_url:
        raise ValidationError("File URL cannot be empty", "file_url")
    
    if max_size <= 0:
        raise ValidationError("Max size must be positive", "max_size")
    
    # Detect URL type and route to appropriate handler
    url_type = detect_url_type(file_url)
    logger.info(f"Downloading file from {url_type.upper()}: {file_url}")
    
    try:
        if url_type == URL_TYPE_IPFS:
            return download_from_ipfs(
                file_url=file_url,
                max_size=max_size,
                timeout=timeout,
                retry_delay=retry_delay,
                max_retries=max_retries,
                headers=headers
            )
        
        elif url_type == URL_TYPE_GOOGLE_DRIVE:
            return download_from_google_drive(
                url=file_url,
                max_size=max_size,
                timeout=timeout,
                retry_delay=retry_delay,
                headers=headers
            )
        
        elif url_type in [URL_TYPE_HTTP, URL_TYPE_HTTPS]:
            return download_from_http(
                url=file_url,
                max_size=max_size,
                timeout=timeout,
                retry_delay=retry_delay,
                headers=headers
            )
        
        else:
            raise UnsupportedURLError(f"Unsupported URL type: {url_type} for URL: {file_url}")
    
    except (FileAccessError, FileTooLargeError, ValidationError, GoogleDriveError, UnsupportedURLError):
        # Re-raise domain exceptions as-is
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise FileAccessError(f"Unexpected error downloading from {file_url}: {str(e)}")


def download_file_simple(file_url: str, max_size: int = MAX_FILE_SIZE) -> bytes:
    """
    Simple wrapper for download_file with default settings.
    
    Args:
        file_url: The URL to download from (supports IPFS, Google Drive, HTTP/HTTPS)
        max_size: Maximum file size in bytes
        
    Returns:
        File content as bytes
    """
    return download_file(file_url=file_url, max_size=max_size)
