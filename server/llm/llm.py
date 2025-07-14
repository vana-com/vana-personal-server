import replicate

class Llm:
    def __init__(self, client: replicate.Client):
        self.client = client
        self.model_name = "deepseek-ai/deepseek-v3"

    def run(self, prompt: str):
        result = self.client.run(self.model_name, input={"prompt": prompt})
        return "\n".join(result)