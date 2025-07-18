import requests

MAX_FILE_SIZE = 1024 * 1024  # 1MB


def download_file(file_url: str):
    if file_url.startswith("ipfs://"):
        fetch_url = file_url.replace("ipfs://", "https://ipfs.io/ipfs/")
    else:
        fetch_url = file_url

    response = requests.get(fetch_url, stream=True)

    # Check content length if available
    content_length = response.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise ValueError(f"File size ({int(content_length)} bytes) exceeds 1MB limit")

    # If no content-length header, check size after downloading
    content = response.content
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(f"File size ({len(content)} bytes) exceeds 1MB limit")

    return content
