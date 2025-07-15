#!/usr/bin/env python3
"""
Client to test the personal server deployed on r8.im
"""

import os
import json
import replicate
from dotenv import load_dotenv
from eth_account.messages import encode_defunct
from web3 import Web3

# Load environment variables
load_dotenv()


def test_personal_server():
    """Test the personal server with the same data as test_personal_server.py"""
    print("Testing personal server on r8.im...")

    # Check if API token is set
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        print("❌ REPLICATE_API_TOKEN not found in environment")
        return False

    print(f"🔑 API Token found: {api_token[:10]}...")

    # Test data from test_personal_server.py
    request_json = '{"user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4", "file_ids": [999], "operation": "llm_inference", "parameters": {"prompt": "Analyze personality: {{data}}"}}'

    web3 = Web3()
    message_hash = encode_defunct(text=request_json)

    # Use the same test private key as in test_personal_server.py
    application_private_key = (
        "bce540d49a5a7f3982f20937b2c4b9d2010dc4ba6f8a9c77ea1221366f062ab7"
    )

    try:
        # Sign the message
        signature = web3.eth.account.sign_message(
            message_hash, private_key=application_private_key
        )
        signature_hex = signature.signature.hex()
        print(f"✅ Message signed successfully. Signature: {signature_hex}")

        # Call the deployed model
        print("🚀 Calling personal server on r8.im...")
        print(f"📤 Request JSON: {request_json}")
        print(f"📤 Signature: {signature_hex}")

        try:
            output = replicate.run(
                "vana-com/personal-server:1ef2dbffd550699b73b1a4d43ec9407e129333bdb59cdb701caefa6c03a42155",
                input={
                    "replicate_api_token": api_token,
                    "signature": signature_hex,
                    "request_json": request_json,
                },
            )

            print(f"📥 Raw output type: {type(output)}")
            print(f"📥 Raw output: {output}")

            if output is None:
                print("❌ No response received from model")
                return False
            elif isinstance(output, str):
                print(f"✅ Response received: {output}")
                return True
            elif hasattr(output, "__iter__") and not isinstance(output, str):
                response = "".join(str(chunk) for chunk in output)
                print(f"✅ Response received: {response}")
                return True
            else:
                print(f"✅ Response received: {str(output)}")
                return True

        except Exception as replicate_error:
            print(f"❌ Replicate API error: {replicate_error}")
            print(f"❌ Error type: {type(replicate_error)}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"❌ Error type: {type(e)}")
        return False


def main():
    """Main function to test the personal server"""
    print("🤖 Testing Personal Server on r8.im")
    print("=" * 50)

    success = test_personal_server()

    if success:
        print("\n🎉 Personal server test completed successfully!")
    else:
        print("\n❌ Personal server test failed!")


if __name__ == "__main__":
    main()
