import replicate
from dotenv import load_dotenv
from personal_server import PersonalServer
from llm import Llm

load_dotenv()


class Predictor:
    def setup(self):
        self.model_name = "deepseek-ai/deepseek-v3"

    def predict(
        self, replicate_auth_token: str, signature: str, request_json: str
    ) -> str:
        import web3
        llm = Llm(client=replicate.Client(api_token=replicate_auth_token))
        personal_server = PersonalServer(llm, web3=web3.Web3())
        output = personal_server.execute(request_json, signature)
        return output
