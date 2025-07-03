import requests

# TODO Check file size. For now we will support only files smaller than 1MB due to the limited context window of the LLM
# This means we should be able to process files in memory
def download_file(file_url: str):
    response = requests.get(file_url)
    return response.text
    