import requests

# TODO Check file size. For now we will support only files smaller than 1MB due to the limited context window of the LLM
def download_file(file_url: str):
    response = requests.get(file_url)
    return response.text
    