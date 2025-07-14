import replicate
from dotenv import load_dotenv
from server import Server
from llm import Llm
import traceback
import sys
import os
from cog import Secret
from onchain.chain import MOKSHA, get_chain

load_dotenv()


class Predictor:
    def setup(self):
        self.model_name = "deepseek-ai/deepseek-v3"

    def predict(
        self, 
        replicate_api_token: Secret, # Apparently must be added in order to forward the request to replicate.Client (for LLM)
        signature: str, 
        request_json: str, 
        chain_id: int = MOKSHA.chain_id, 
    ) -> str:
        try:
            chain = get_chain(chain_id)
            llm = Llm(client=replicate.Client(api_token=replicate_api_token.get_secret_value()))
            server = Server(llm, chain)
            
            output = server.execute(request_json, signature)
            
            if output is None:
                return "Error: No output generated"
            
            return output
        except Exception as e:
            error_msg = f"Error in predict: {str(e)}\n{traceback.format_exc()}"
            print(error_msg, file=sys.stderr)
            return f"Error: {str(e)}"
