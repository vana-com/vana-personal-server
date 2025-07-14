#!/usr/bin/env python3
"""
Test script to verify the grant integration works correctly
"""

import json
import sys
import os
import time

# Add the server directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grants.grant_models import GrantFile, GrantValidationOptions
from grants.grant_validation import validate_grant, validate_grant_schema
from grants.grant_files import validate_grant_file_structure


def test_grant_validation():
    """Test grant validation functionality"""
    print("Testing grant validation...")
    
    # Use a future expiration date (1 year from now)
    future_expires = int(time.time()) + 365 * 24 * 60 * 60
    
    # Test valid grant data
    valid_grant_data = {
        "grantee": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        "operation": "llm_inference",
        "parameters": {
            "prompt": "Analyze this data: {{data}}",
            "model": "gpt-4",
            "maxTokens": 2000,
            "temperature": 0.7
        },
        "expires": future_expires
    }
    
    # Test structure validation
    assert validate_grant_file_structure(valid_grant_data), "Structure validation should pass"
    print("✓ Structure validation passed")
    
    # Test schema validation
    assert validate_grant_schema(valid_grant_data), "Schema validation should pass"
    print("✓ Schema validation passed")
    
    # Test full validation
    try:
        grant_file = validate_grant(valid_grant_data, GrantValidationOptions(
            grantee="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            operation="llm_inference"
        ))
        assert isinstance(grant_file, GrantFile), "Should return GrantFile"
        print("✓ Full validation passed")
        
        # Test grantee mismatch
        try:
            validate_grant(valid_grant_data, GrantValidationOptions(
                grantee="0x1234567890123456789012345678901234567890",
                operation="llm_inference"
            ))
            assert False, "Should have raised GranteeMismatchError"
        except Exception as e:
            assert "grantee" in str(e).lower() or "permission denied" in str(e).lower()
            print("✓ Grantee mismatch detection works")
        
        # Test operation mismatch
        try:
            validate_grant(valid_grant_data, GrantValidationOptions(
                grantee="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                operation="data_analysis"
            ))
            assert False, "Should have raised OperationNotAllowedError"
        except Exception as e:
            assert "operation" in str(e).lower() or "permission denied" in str(e).lower()
            print("✓ Operation mismatch detection works")
            
    except Exception as e:
        print(f"✗ Full validation failed: {e}")
        return False
    
    return True


def test_invalid_grant_data():
    """Test validation with invalid grant data"""
    print("\nTesting invalid grant data...")
    
    # Test missing required fields
    invalid_grant = {
        "grantee": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        # Missing operation and parameters
    }
    
    assert not validate_grant_file_structure(invalid_grant), "Should fail structure validation"
    print("✓ Invalid structure detection works")
    
    # Test invalid grantee address
    invalid_address_grant = {
        "grantee": "invalid_address",
        "operation": "llm_inference",
        "parameters": {}
    }
    
    assert not validate_grant_file_structure(invalid_address_grant), "Should fail address validation"
    print("✓ Invalid address detection works")
    
    return True


def test_grant_file_creation():
    """Test GrantFile creation and properties"""
    print("\nTesting GrantFile creation...")
    
    future_expires = int(time.time()) + 365 * 24 * 60 * 60
    
    grant_file = GrantFile(
        grantee="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        operation="llm_inference",
        parameters={"model": "gpt-4"},
        expires=future_expires
    )
    
    assert grant_file.grantee == "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    assert grant_file.operation == "llm_inference"
    assert grant_file.parameters["model"] == "gpt-4"
    assert grant_file.expires == future_expires
    
    print("✓ GrantFile creation works")
    return True


def main():
    """Run all tests"""
    print("Testing grant integration...")
    
    tests = [
        test_grant_validation,
        test_invalid_grant_data,
        test_grant_file_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"✗ {test.__name__} failed")
        except Exception as e:
            print(f"✗ {test.__name__} failed with exception: {e}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Grant integration is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 