#!/usr/bin/env python3
"""
Local test script for key derivation server
"""

import os
import json
from dotenv import load_dotenv
from identity_server import IdentityServer
from bip_utils import Bip39MnemonicGenerator, Bip39Languages

# Load environment variables
load_dotenv()


def test_key_derivation():
    """Test key derivation with sample addresses"""
    print("🔑 Testing Key Derivation Server Locally")
    print("=" * 50)

    # Create a new mnemonic
    mnemonic = (
        Bip39MnemonicGenerator(Bip39Languages.ENGLISH).FromWordsNumber(12).ToStr()
    )
    print(f"🔑 New mnemonic: {mnemonic}")
    os.environ["VANA_MNEMONIC"] = mnemonic
    print(f"🔑 VANA_MNEMONIC: {os.getenv('VANA_MNEMONIC')}")

    try:
        # Create key derivation server
        key_server = IdentityServer()
        print("✅ Key derivation server initialized")

        # Test addresses
        test_addresses = [
            "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4",
            "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            "0x1234567890123456789012345678901234567890",
        ]

        results = []

        for i, user_address in enumerate(test_addresses, 1):
            print(f"\n🧪 Test {i}: Deriving keys for {user_address}")
            print("-" * 40)

            try:
                derived_address = key_server.derive_user_server_address(user_address)
                results.append(
                    {"user_address": user_address, "derived_address": derived_address}
                )

                print("✅ Address derived successfully:")
                print(f"   User Address: {user_address}")
                print(f"   Derived Address: {derived_address}")

            except Exception as e:
                print(f"❌ Failed to derive keys: {e}")
                continue

        # Test deterministic behavior
        print(f"\n🔄 Testing deterministic behavior...")
        print("-" * 40)

        test_address = "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"
        deterministic_results = []

        for i in range(3):
            result = key_server.derive_user_server_address(test_address)
            deterministic_results.append(result)
            print(f"   Call {i + 1}: Address {result}")

        # Verify all results are identical
        if all(r == deterministic_results[0] for r in deterministic_results):
            print("✅ Deterministic behavior confirmed - all results identical")
        else:
            print("❌ Non-deterministic behavior detected!")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_key_derivation()

    if success:
        print("\n🎉 Key derivation test completed successfully!")
    else:
        print("\n❌ Key derivation test failed!")
