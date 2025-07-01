import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from eth_account.messages import encode_defunct
from server.entities import PersonalServerRequest
from dotenv import load_dotenv
from server.personal_server import PersonalServer
from server.llm import Llm

load_dotenv()

MOCK_REQUEST = PersonalServerRequest(
    user_address=os.getenv("USER_ADDRESS"),
    file_ids=[12],
    operation="llm_inference",
    parameters={"prompt": "Summarise the content of: {{data}}"},
)

def __main__():
    web3 = Web3()

    # Prepare test data
    request = MOCK_REQUEST

    # Create a message hash for signing
    # TODO: In prod, the request will be sign by the JS library so double check for potential incompatibility
    message = json.dumps(request.__dict__, sort_keys=True)
    message_hash = encode_defunct(text=message)

    app_address = os.getenv("TEST_APP_ADDRESS")
    signature = web3.eth.account.sign_message(message_hash, private_key=os.getenv("TEST_APP_PRIVATE_KEY"))
    print(f"App {app_address} signed the message")

    # Dummy llm which returns "Processed prompt: <prompt>" when executed
    dummy_llm = Llm(client=None)
    dummy_llm.run = lambda prompt: "Processed prompt: " + prompt

    personal_server = PersonalServer(llm=dummy_llm, web3=web3)
    output = personal_server.execute(message, signature.signature)
    print(f"Output: {output}")


if __name__ == "__main__":
    __main__()

