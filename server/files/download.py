import requests

class Download:
    def execute(self, file_url: str):
        response = requests.get(file_url)
        return response.text