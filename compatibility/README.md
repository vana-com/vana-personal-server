# Encryption/Decryption Compatibility Test Suite

This directory contains comprehensive compatibility tests between JavaScript/TypeScript encryption functions and Python decryption functions.

## 📁 Files Overview

### Test Scripts
- **`cross_platform_compatibility_test.js`** - Main test suite covering Browser + Node.js → Python compatibility
- **`edge_case_tests.js`** - Edge case tests exploring potential failure scenarios
- **`standalone_decrypt.py`** - Isolated Python decryption function for testing

### Test Results
- **`cross_platform_test_results.json`** - Detailed results from cross-platform tests (114 tests)
- **`edge_case_test_results.json`** - Results from edge case failure scenario tests

### Reports
- **`CROSS_PLATFORM_COMPATIBILITY_REPORT.md`** - Comprehensive analysis and findings

## 🚀 Running Tests

### Cross-Platform Compatibility Tests
Tests both Browser and Node.js encryption against Python decryption:
```bash
node cross_platform_compatibility_test.js
```
- **Coverage:** 114 tests (19 scenarios × 3 key pairs × 2 platforms)
- **Success Rate:** 100%
- **Platforms:** Browser JavaScript + Node.js + Python

### Edge Case Tests
Tests potential failure scenarios:
```bash
node edge_case_tests.js
```
- **Coverage:** 17 edge cases (binary data, invalid keys, malformed inputs)
- **Purpose:** Identify actual compatibility breaking conditions

## 📊 Test Results Summary

### ✅ **Full Compatibility Confirmed**
- **Browser → Python:** 57/57 tests passed (100%)
- **Node.js → Python:** 57/57 tests passed (100%)
- **Format Consistency:** ✅ IDENTICAL output formats

### 🎯 **Real Failure Cases Found**
- **Invalid private keys:** Zero, too large, wrong format
- **Malformed public keys:** Invalid curve points, wrong length
- **Cryptographic violations:** All fail with proper error messages

### 😮 **Surprising Robustness**
- **Binary data with null bytes:** ✅ Works perfectly
- **Invalid UTF-8 sequences:** ✅ Handled correctly  
- **Large data (1MB+):** ✅ No issues
- **Control characters:** ✅ All supported

## 🔧 Technical Details

### Encryption Functions Tested
- **Browser:** `vana-sdk/src/platform/browser.ts#encryptWithWalletPublicKey`
- **Node.js:** `vana-sdk/src/platform/node.ts#encryptWithWalletPublicKey` 
- **Python:** `vana-personal-server/utils/files/decrypt.py#decrypt_with_private_key`

### Cryptographic Implementation
- **Algorithm:** ECDH + AES-256-CBC + HMAC-SHA256
- **Curve:** secp256k1
- **Format:** `iv(16) + ephemPublicKey(65) + ciphertext + mac(32)`
- **Encoding:** Hex string output

## 🎯 Conclusions

1. **Production Ready:** All implementations are fully compatible
2. **Cross-Platform:** Browser, Node.js, and Python work seamlessly together
3. **Robust:** Handles edge cases including binary data and large payloads
4. **Secure:** Proper cryptographic validation and error handling

## 🔄 Re-running Tests

To re-run all tests after code changes:

```bash
# Cross-platform compatibility (main test)
node cross_platform_compatibility_test.js

# Edge cases and failure scenarios  
node edge_case_tests.js
```

Both test suites are self-contained and include their own Python environment setup.