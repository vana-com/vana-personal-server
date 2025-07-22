/**
 * Edge Case Compatibility Tests
 * 
 * This test suite explores potential failure scenarios that might break compatibility
 * between TypeScript/JavaScript encryption and Python decryption.
 */

const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);
const crypto = require('crypto');
const fs = require('fs');

// Import platform adapters
const { BrowserPlatformAdapter } = require('../../vana-sdk/packages/vana-sdk/dist/platform.browser.js');

const EDGE_CASES = [
  // Binary data edge cases
  {
    name: 'Data with null bytes',
    data: 'Hello\x00World\x00Test',
    expectedFailure: true,
    reason: 'Null bytes may cause UTF-8 encoding/decoding issues'
  },
  {
    name: 'Pure binary data (non-UTF8)',
    data: String.fromCharCode(0xFF, 0xFE, 0xFD, 0xFC, 0xFB, 0x00, 0x01, 0x02),
    expectedFailure: true,
    reason: 'Invalid UTF-8 sequences may get corrupted during string conversion'
  },
  {
    name: 'Data with all possible byte values',
    data: Array.from({length: 256}, (_, i) => String.fromCharCode(i)).join(''),
    expectedFailure: true,
    reason: 'Not all byte values form valid UTF-8 when combined'
  },
  
  // UTF-8 edge cases
  {
    name: 'Invalid UTF-8 sequences',
    data: '\xC0\x80\xE0\x80\x80\xF0\x80\x80\x80', // Overlong encodings
    expectedFailure: true,
    reason: 'Invalid UTF-8 sequences may be handled differently across platforms'
  },
  {
    name: 'UTF-8 replacement characters',
    data: '\uFFFD\uFFFE\uFFFF',
    expectedFailure: false,
    reason: 'Valid Unicode replacement characters should work'
  },
  
  // Size edge cases  
  {
    name: 'Extremely large string (1MB)',
    data: 'A'.repeat(1024 * 1024),
    expectedFailure: false,
    reason: 'Large data should work but may cause memory issues'
  },
  {
    name: 'Maximum safe string length approach',
    data: 'B'.repeat(500000), // Much smaller than actual limit but still large
    expectedFailure: false,
    reason: 'Should work but test memory handling'
  },
  
  // Control character edge cases
  {
    name: 'ASCII control characters',
    data: '\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E\x0F',
    expectedFailure: false,
    reason: 'ASCII control chars should be valid UTF-8'
  },
  {
    name: 'DEL and high control chars',
    data: '\x7F\x80\x81\x82\x83\x84\x85\x86\x87',
    expectedFailure: true,
    reason: 'High control characters may not be valid UTF-8'
  }
];

const INVALID_KEY_CASES = [
  {
    name: 'Zero private key',
    privateKey: '0'.repeat(64), // All zeros
    publicKey: null, // Will be generated
    expectedFailure: true,
    reason: 'Private key cannot be zero on secp256k1'
  },
  {
    name: 'Maximum private key (curve order)',
    privateKey: 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141',
    publicKey: null,
    expectedFailure: true, 
    reason: 'Private key cannot be >= curve order'
  },
  {
    name: 'Invalid private key (too large)',
    privateKey: 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF',
    publicKey: null,
    expectedFailure: true,
    reason: 'Private key larger than curve order'
  },
  {
    name: 'Short private key',
    privateKey: '123456', // Too short
    publicKey: null,
    expectedFailure: true,
    reason: 'Private key must be 32 bytes (64 hex chars)'
  },
  {
    name: 'Invalid hex in private key',
    privateKey: '123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEFG', // G is invalid hex
    publicKey: null,
    expectedFailure: true,
    reason: 'Invalid hex character in private key'
  }
];

const MALFORMED_KEY_CASES = [
  {
    name: 'Invalid public key point',
    publicKey: '04' + 'FF'.repeat(64), // Invalid point on curve
    expectedFailure: true,
    reason: 'Public key point not on secp256k1 curve'
  },
  {
    name: 'Wrong length public key', 
    publicKey: '04' + '00'.repeat(32), // Too short
    expectedFailure: true,
    reason: 'Public key wrong length'
  },
  {
    name: 'Compressed key with wrong prefix',
    publicKey: '05' + '00'.repeat(32), // Invalid prefix
    expectedFailure: true,
    reason: 'Invalid compressed public key prefix'
  }
];

async function testDataEdgeCases() {
  console.log('🔍 Testing Data Edge Cases');
  console.log('===========================');
  
  const adapter = new BrowserPlatformAdapter();
  const keyPair = await adapter.crypto.generateKeyPair();
  
  const results = [];
  
  for (const testCase of EDGE_CASES) {
    console.log(`Testing: ${testCase.name}`);
    
    try {
      // Attempt encryption
      const encryptedData = await adapter.crypto.encryptWithWalletPublicKey(
        testCase.data,
        keyPair.publicKey
      );
      
      // Attempt Python decryption
      const testDataPath = `/tmp/edge_test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}.json`;
      const testDataPayload = {
        encrypted_data: encryptedData,
        private_key: keyPair.privateKey,
        original_data: testCase.data
      };
      
      fs.writeFileSync(testDataPath, JSON.stringify(testDataPayload));
      
      const { stdout, stderr } = await execAsync(`source /tmp/test_env/bin/activate && python3 /Users/maciejwitowski/Documents/vana/vana-personal-server/compatibility/standalone_decrypt.py ${testDataPath}`);
      
      fs.unlinkSync(testDataPath);
      
      if (stderr) {
        throw new Error(`Python error: ${stderr}`);
      }
      
      const result = JSON.parse(stdout.trim());
      const success = result.success;
      const actuallyFailed = !success;
      
      results.push({
        name: testCase.name,
        expectedFailure: testCase.expectedFailure,
        actuallyFailed,
        correctPrediction: testCase.expectedFailure === actuallyFailed,
        reason: testCase.reason,
        error: result.error,
        dataLength: testCase.data.length
      });
      
      const status = success ? '✅' : '❌';
      const prediction = testCase.expectedFailure === actuallyFailed ? '🎯' : '😮';
      console.log(`  ${status} ${prediction} ${testCase.name} - ${success ? 'PASSED' : 'FAILED'}`);
      
      if (!success) {
        console.log(`    Error: ${result.error}`);
      }
      
    } catch (error) {
      const actuallyFailed = true;
      results.push({
        name: testCase.name,
        expectedFailure: testCase.expectedFailure,
        actuallyFailed,
        correctPrediction: testCase.expectedFailure === actuallyFailed,
        reason: testCase.reason,
        error: error.message,
        dataLength: testCase.data.length
      });
      
      const prediction = testCase.expectedFailure === actuallyFailed ? '🎯' : '😮';
      console.log(`  ❌ ${prediction} ${testCase.name} - FAILED (Exception)`);
      console.log(`    Error: ${error.message}`);
    }
  }
  
  return results;
}

async function testInvalidKeys() {
  console.log('\n🔍 Testing Invalid Key Cases');
  console.log('==============================');
  
  const adapter = new BrowserPlatformAdapter();
  const results = [];
  
  for (const testCase of INVALID_KEY_CASES) {
    console.log(`Testing: ${testCase.name}`);
    
    try {
      // For invalid private keys, we can't generate the public key normally
      // We'll try to use the invalid private key directly and see what happens
      
      const testData = "Test data for invalid key";
      
      // Generate a valid public key for encryption
      const validKeyPair = await adapter.crypto.generateKeyPair();
      
      // Encrypt with valid key
      const encryptedData = await adapter.crypto.encryptWithWalletPublicKey(
        testData,
        validKeyPair.publicKey
      );
      
      // Try to decrypt with invalid private key via Python
      const testDataPath = `/tmp/key_test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}.json`;
      const testDataPayload = {
        encrypted_data: encryptedData,
        private_key: testCase.privateKey, // Invalid private key
        original_data: testData
      };
      
      fs.writeFileSync(testDataPath, JSON.stringify(testDataPayload));
      
      const { stdout, stderr } = await execAsync(`source /tmp/test_env/bin/activate && python3 /Users/maciejwitowski/Documents/vana/vana-personal-server/compatibility/standalone_decrypt.py ${testDataPath}`);
      
      fs.unlinkSync(testDataPath);
      
      if (stderr) {
        throw new Error(`Python error: ${stderr}`);
      }
      
      const result = JSON.parse(stdout.trim());
      const success = result.success;
      const actuallyFailed = !success;
      
      results.push({
        name: testCase.name,
        expectedFailure: testCase.expectedFailure,
        actuallyFailed,
        correctPrediction: testCase.expectedFailure === actuallyFailed,
        reason: testCase.reason,
        error: result.error
      });
      
      const status = success ? '✅' : '❌';
      const prediction = testCase.expectedFailure === actuallyFailed ? '🎯' : '😮';
      console.log(`  ${status} ${prediction} ${testCase.name} - ${success ? 'PASSED' : 'FAILED'}`);
      
      if (!success) {
        console.log(`    Error: ${result.error}`);
      }
      
    } catch (error) {
      const actuallyFailed = true;
      results.push({
        name: testCase.name,
        expectedFailure: testCase.expectedFailure,
        actuallyFailed,
        correctPrediction: testCase.expectedFailure === actuallyFailed,
        reason: testCase.reason,
        error: error.message
      });
      
      const prediction = testCase.expectedFailure === actuallyFailed ? '🎯' : '😮';
      console.log(`  ❌ ${prediction} ${testCase.name} - FAILED (Exception)`);
      console.log(`    Error: ${error.message}`);
    }
  }
  
  return results;
}

async function testMalformedPublicKeys() {
  console.log('\n🔍 Testing Malformed Public Key Cases');
  console.log('======================================');
  
  const adapter = new BrowserPlatformAdapter();
  const results = [];
  
  for (const testCase of MALFORMED_KEY_CASES) {
    console.log(`Testing: ${testCase.name}`);
    
    try {
      const testData = "Test data for malformed key";
      
      // Try to encrypt with malformed public key
      const encryptedData = await adapter.crypto.encryptWithWalletPublicKey(
        testData,
        testCase.publicKey
      );
      
      // If encryption succeeded, it shouldn't have
      const success = true;
      const actuallyFailed = false;
      
      results.push({
        name: testCase.name,
        expectedFailure: testCase.expectedFailure,
        actuallyFailed,
        correctPrediction: testCase.expectedFailure === actuallyFailed,
        reason: testCase.reason,
        error: null
      });
      
      const prediction = testCase.expectedFailure === actuallyFailed ? '🎯' : '😮';
      console.log(`  ✅ ${prediction} ${testCase.name} - UNEXPECTEDLY PASSED`);
      
    } catch (error) {
      const actuallyFailed = true;
      results.push({
        name: testCase.name,
        expectedFailure: testCase.expectedFailure,
        actuallyFailed,
        correctPrediction: testCase.expectedFailure === actuallyFailed,
        reason: testCase.reason,
        error: error.message
      });
      
      const prediction = testCase.expectedFailure === actuallyFailed ? '🎯' : '😮';
      console.log(`  ❌ ${prediction} ${testCase.name} - FAILED as expected`);
      console.log(`    Error: ${error.message}`);
    }
  }
  
  return results;
}

async function runEdgeCaseTests() {
  console.log('🚨 Edge Case Compatibility Test Suite');
  console.log('=====================================');
  console.log('This test explores potential failure scenarios\n');
  
  const dataResults = await testDataEdgeCases();
  const keyResults = await testInvalidKeys();
  const malformedKeyResults = await testMalformedPublicKeys();
  
  const allResults = [...dataResults, ...keyResults, ...malformedKeyResults];
  
  console.log('\n📊 EDGE CASE TEST SUMMARY');
  console.log('==========================');
  
  const totalTests = allResults.length;
  const correctPredictions = allResults.filter(r => r.correctPrediction).length;
  const unexpectedPasses = allResults.filter(r => r.expectedFailure && !r.actuallyFailed).length;
  const unexpectedFailures = allResults.filter(r => !r.expectedFailure && r.actuallyFailed).length;
  
  console.log(`Total edge case tests: ${totalTests}`);
  console.log(`Correct predictions: ${correctPredictions}/${totalTests} (${(correctPredictions/totalTests*100).toFixed(1)}%)`);
  console.log(`Unexpected passes: ${unexpectedPasses}`);
  console.log(`Unexpected failures: ${unexpectedFailures}`);
  
  if (unexpectedPasses > 0) {
    console.log('\n😮 UNEXPECTED PASSES (cases we thought would fail but didn\'t):');
    allResults.filter(r => r.expectedFailure && !r.actuallyFailed).forEach(r => {
      console.log(`  - ${r.name}: ${r.reason}`);
    });
  }
  
  if (unexpectedFailures > 0) {
    console.log('\n😮 UNEXPECTED FAILURES (cases we thought would pass but didn\'t):');
    allResults.filter(r => !r.expectedFailure && r.actuallyFailed).forEach(r => {
      console.log(`  - ${r.name}: ${r.error}`);
      console.log(`    Expected reason: ${r.reason}`);
    });
  }
  
  console.log('\n🎯 CORRECTLY PREDICTED FAILURES:');
  allResults.filter(r => r.expectedFailure && r.actuallyFailed).forEach(r => {
    console.log(`  - ${r.name}: ${r.reason}`);
    console.log(`    Actual error: ${r.error}`);
  });
  
  // Save detailed results
  const reportPath = `/Users/maciejwitowski/Documents/vana/vana-personal-server/compatibility/edge_case_test_results.json`;
  fs.writeFileSync(reportPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    summary: {
      totalTests,
      correctPredictions,
      unexpectedPasses,
      unexpectedFailures
    },
    results: allResults
  }, null, 2));
  
  console.log(`\n📄 Detailed results saved to: ${reportPath}`);
  
  return {
    totalTests,
    correctPredictions,
    unexpectedPasses,
    unexpectedFailures,
    results: allResults
  };
}

if (require.main === module) {
  runEdgeCaseTests()
    .then(summary => {
      console.log('\n🎉 Edge case test suite completed!');
      
      if (summary.unexpectedFailures > 0) {
        console.log('\n⚠️  Found unexpected compatibility issues!');
        process.exit(1);
      } else {
        console.log('\n✅ No unexpected compatibility issues found');
        process.exit(0);
      }
    })
    .catch(error => {
      console.error('💥 Edge case test suite failed:', error);
      process.exit(1);
    });
}

module.exports = { runEdgeCaseTests };