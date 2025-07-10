#!/usr/bin/env python3
"""
Simple test to verify ECIES decryption works with provided inputs.
"""

import sys
import os

# Add the files directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'files'))

from decrypt import decrypt_with_wallet_private_key, fetch_and_decrypt_ipfs_content


def test_decrypt_key():
    """Test ECIES decryption with provided inputs."""
    private_key = "a1f47b0e9506e0303c6cc532a48e8bfbbceb20350011a010a9a47ed1a8ebdb46"
    encrypted_key = "72567c6e698c8d680e3088f3eed9dda404de8c79e0b19afc6b7d4beacfb2cede9bf899e4c870e6cc5a6707e0622d26d917814422bba4e1051e8776abc55a6aba27f9277eb8f5ebf32c0cf47624e8c91d574a756eeb578c8f6cab9c2258fbdd3b692294fb9434ce90adb03a56275a8c2f07e520b619962ee1312e8e2b7a5557893fa2c43b131f0195c68f88deb775ceffb2cbb1791ff64203aecd05b19796c28505b56ce976d47d29a458059ef7c5e23482b221b7abe103c456652a18e3c5d8f09e5e80218fd5ccfef2e75f652632662e23fe27879542003fc318a448770acb1e1f9c6bdb335c7bc3d53f73ce27fd835257b1c4b91cb75916ed07b8bf0c3dd3d5ea"
    
    try:
        decrypted_key = decrypt_with_wallet_private_key(encrypted_key, private_key)
        print(f"✅ Key decryption successful!")
        print(f"Decrypted key: {decrypted_key}")
        return decrypted_key
    except Exception as e:
        print(f"❌ Key decryption failed: {e}")
        return None


def test_full_decryption():
    """Test complete flow: decrypt key -> decrypt IPFS content."""
    private_key = "a1f47b0e9506e0303c6cc532a48e8bfbbceb20350011a010a9a47ed1a8ebdb46"
    encrypted_key = "72567c6e698c8d680e3088f3eed9dda404de8c79e0b19afc6b7d4beacfb2cede9bf899e4c870e6cc5a6707e0622d26d917814422bba4e1051e8776abc55a6aba27f9277eb8f5ebf32c0cf47624e8c91d574a756eeb578c8f6cab9c2258fbdd3b692294fb9434ce90adb03a56275a8c2f07e520b619962ee1312e8e2b7a5557893fa2c43b131f0195c68f88deb775ceffb2cbb1791ff64203aecd05b19796c28505b56ce976d47d29a458059ef7c5e23482b221b7abe103c456652a18e3c5d8f09e5e80218fd5ccfef2e75f652632662e23fe27879542003fc318a448770acb1e1f9c6bdb335c7bc3d53f73ce27fd835257b1c4b91cb75916ed07b8bf0c3dd3d5ea"
    ipfs_url = "ipfs://QmdXMUxRxKuxikKHcuPP2K62MUR98KQAePe8tYVemkotHD"
    
    try:
        decrypted_content = fetch_and_decrypt_ipfs_content(ipfs_url, private_key, encrypted_key)
        print(f"✅ Full decryption successful!")
        print(f"Decrypted content length: {len(decrypted_content)} bytes")
        
        # Try to decode as text if possible
        try:
            text_content = decrypted_content.decode('utf-8')
            print(f"Content as text: {text_content[:200]}...")
        except UnicodeDecodeError:
            print(f"Content is binary data: {decrypted_content[:50].hex()}...")
            
        return True
    except Exception as e:
        print(f"❌ Full decryption failed: {e}")
        return False


if __name__ == "__main__":
    print("🔓 Testing key decryption...")
    key_success = test_decrypt_key()
    
    if key_success:
        print("\n🔓 Testing full decryption flow...")
        full_success = test_full_decryption()
        sys.exit(0 if full_success else 1)
    else:
        sys.exit(1)