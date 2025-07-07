import requests

# TODO Check file size. For now we will support only files smaller than 1MB due to the limited context window of the LLM
# This means we should be able to process files in memory
def download_file(file_url: str):
    # Convert IPFS URL to HTTP gateway URL if needed
    if file_url.startswith("ipfs://"):
        fetch_url = file_url.replace("ipfs://", "https://ipfs.io/ipfs/")
    else:
        fetch_url = file_url
    response = requests.get(fetch_url)
    return response.content
    