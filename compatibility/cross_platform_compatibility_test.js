/**
 * Cross-Platform Compatibility Test Suite
 * 
 * This test validates that data encrypted using BOTH:
 * - browser.ts encryptWithWalletPublicKey function 
 * - node.ts encryptWithWalletPublicKey function
 * can be successfully decrypted using the Python decrypt_with_private_key function.
 * 
 * This ensures complete cross-platform compatibility across Browser, Node.js, and Python environments.
 */

const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);
const crypto = require('crypto');
const fs = require('fs');

// Import both SDK platform adapters
let BrowserPlatformAdapter, NodePlatformAdapter;

// Test cases configuration (same as before but now testing both platforms)
const TEST_CASES = [
  // Basic string tests
  { name: 'Simple ASCII string', data: 'Hello, World!' },
  { name: 'Empty string', data: '' },
  { name: 'Single character', data: 'A' },
  
  // Unicode and special characters
  { name: 'Unicode characters', data: 'Hello 🌍 世界 🚀' },
  { name: 'Special characters', data: '!@#$%^&*()_+-={}[]|\\:";\'<>?,./' },
  { name: 'Newlines and tabs', data: 'Line 1\nLine 2\t\tTabbed' },
  
  // Different data sizes
  { name: 'Small data (10 bytes)', data: 'a'.repeat(10) },
  { name: 'Medium data (1KB)', data: 'b'.repeat(1024) },
  { name: 'Large data (10KB)', data: 'c'.repeat(10240) },
  { name: 'Very large data (50KB)', data: 'd'.repeat(51200) }, // Reduced from 100KB for faster testing
  
  // JSON data structures
  { name: 'Simple JSON', data: JSON.stringify({ name: 'test', value: 123 }) },
  { name: 'Complex JSON', data: JSON.stringify({ 
    user: { name: 'John', age: 30 }, 
    items: [1, 2, 3], 
    metadata: { created: '2024-01-01', tags: ['test', 'compatibility'] }
  }) },
  
  // Binary-like data (as strings)
  { name: 'Base64 encoded data', data: Buffer.from('This is binary data').toString('base64') },
  { name: 'Hex encoded data', data: Buffer.from('Binary content here').toString('hex') },
  
  // Edge cases
  { name: 'Only spaces', data: '   ' },
  { name: 'Only newlines', data: '\n\n\n' },
  { name: 'Mixed whitespace', data: ' \t\n\r ' },
  
  // Real-world-like data
  { name: 'Email format', data: 'user@example.com' },
  { name: 'URL format', data: 'https://example.com/path?param=value' },
];

// Test platforms configuration (adapters initialized in initializePlatforms())
const PLATFORMS = [
  { name: 'Browser', adapter: null },  // Initialized in initializePlatforms()
  { name: 'Node.js', adapter: null }   // Initialized in initializePlatforms()
];

// Store key pairs for testing
const KEY_PAIRS = [];

async function initializePlatforms() {
  try {
    // Import browser platform adapter
    const browserModule = require('../../vana-sdk/packages/vana-sdk/dist/platform.browser.js');
    BrowserPlatformAdapter = browserModule.BrowserPlatformAdapter;
    PLATFORMS[0].adapter = new BrowserPlatformAdapter();
    
    // Import node platform adapter  
    const nodeModule = require('../../vana-sdk/packages/vana-sdk/dist/platform.node.js');
    NodePlatformAdapter = nodeModule.NodePlatformAdapter;
    PLATFORMS[1].adapter = new NodePlatformAdapter();
    
    console.log('✅ Successfully initialized both Browser and Node.js platform adapters');
  } catch (error) {
    throw new Error(`Failed to initialize platform adapters: ${error.message}`);
  }
}

async function generateTestKeyPairs() {
  // Generate key pairs using the browser adapter (both should generate compatible keys)
  const browserAdapter = PLATFORMS[0].adapter;
  
  for (let i = 0; i < 3; i++) { // Reduced from 5 to 3 for faster testing
    const keyPair = await browserAdapter.crypto.generateKeyPair();
    KEY_PAIRS.push({
      name: `KeyPair ${i + 1}`,
      ...keyPair
    });
  }
  
  console.log(`✅ Generated ${KEY_PAIRS.length} test key pairs`);
}

async function testEncryptionDecryption(testCase, keyPair, platform) {
  try {
    const adapter = platform.adapter;
    
    // Step 1: Encrypt with the specified platform's function
    const encryptedData = await adapter.crypto.encryptWithWalletPublicKey(
      testCase.data, 
      keyPair.publicKey
    );
    
    // Step 2: Create temporary files for Python script
    const testDataPath = `/tmp/test_data_${Date.now()}_${Math.random().toString(36).substr(2, 9)}.json`;
    const testData = {
      encrypted_data: encryptedData,
      private_key: keyPair.privateKey,
      original_data: testCase.data,
      platform: platform.name
    };
    
    fs.writeFileSync(testDataPath, JSON.stringify(testData));
    
    // Step 3: Call standalone Python decryption function
    const { stdout, stderr } = await execAsync(`source /tmp/test_env/bin/activate && python3 /Users/maciejwitowski/Documents/vana/vana-personal-server/compatibility/standalone_decrypt.py ${testDataPath}`);
    
    // Clean up temporary files
    fs.unlinkSync(testDataPath);
    
    if (stderr) {
      throw new Error(`Python error: ${stderr}`);
    }
    
    const result = JSON.parse(stdout.trim());
    
    return {
      testCase: testCase.name,
      keyPair: keyPair.name,
      platform: platform.name,
      success: result.success,
      originalLength: result.original_length,
      decryptedLength: result.decrypted_length,
      matches: result.matches,
      error: result.error,
      encryptedLength: encryptedData.length
    };
    
  } catch (error) {
    return {
      testCase: testCase.name,
      keyPair: keyPair.name,
      platform: platform.name,
      success: false,
      error: error.message,
      originalLength: testCase.data.length,
      decryptedLength: 0,
      matches: false,
      encryptedLength: 0
    };
  }
}

async function runCrossPlatformTests() {
  console.log('🚀 Starting Cross-Platform Compatibility Test Suite');
  console.log('====================================================');
  
  // Initialize platform adapters
  console.log('🔄 Initializing platform adapters...');
  await initializePlatforms();
  
  // Generate test key pairs
  console.log('🔄 Generating test key pairs...');
  await generateTestKeyPairs();
  
  console.log('🔄 Running cross-platform compatibility tests...');
  console.log(`   Test cases: ${TEST_CASES.length}`);
  console.log(`   Key pairs: ${KEY_PAIRS.length}`);
  console.log(`   Platforms: ${PLATFORMS.length}`);
  console.log(`   Total tests: ${TEST_CASES.length * KEY_PAIRS.length * PLATFORMS.length}`);
  
  const results = [];
  let totalTests = 0;
  let passedTests = 0;
  const platformStats = {};
  
  // Initialize platform statistics
  PLATFORMS.forEach(platform => {
    platformStats[platform.name] = { passed: 0, total: 0 };
  });
  
  // Run each test case with each key pair on each platform
  for (const testCase of TEST_CASES) {
    for (const keyPair of KEY_PAIRS) {
      for (const platform of PLATFORMS) {
        console.log(`Testing: ${testCase.name} with ${keyPair.name} on ${platform.name}`);
        
        const result = await testEncryptionDecryption(testCase, keyPair, platform);
        results.push(result);
        
        totalTests++;
        platformStats[platform.name].total++;
        
        if (result.success) {
          passedTests++;
          platformStats[platform.name].passed++;
        } else {
          console.log(`❌ FAILED: ${result.testCase} with ${result.keyPair} on ${result.platform}: ${result.error}`);
        }
      }
    }
  }
  
  // Generate comprehensive report
  console.log('\n📊 CROSS-PLATFORM TEST RESULTS SUMMARY');
  console.log('========================================');
  console.log(`Total tests: ${totalTests}`);
  console.log(`Passed: ${passedTests}`);
  console.log(`Failed: ${totalTests - passedTests}`);
  console.log(`Overall success rate: ${((passedTests / totalTests) * 100).toFixed(2)}%`);
  
  // Platform-specific statistics
  console.log('\n📈 PLATFORM-SPECIFIC RESULTS:');
  PLATFORMS.forEach(platform => {
    const stats = platformStats[platform.name];
    const successRate = (stats.passed / stats.total * 100).toFixed(2);
    console.log(`${platform.name}: ${stats.passed}/${stats.total} (${successRate}%)`);
  });
  
  // Group failures by platform and error type
  const failures = results.filter(r => !r.success);
  if (failures.length > 0) {
    console.log('\n❌ FAILURES BY PLATFORM:');
    
    PLATFORMS.forEach(platform => {
      const platformFailures = failures.filter(f => f.platform === platform.name);
      if (platformFailures.length > 0) {
        console.log(`\n${platform.name}: ${platformFailures.length} failures`);
        
        // Group by error type
        const errorGroups = {};
        platformFailures.forEach(f => {
          const errorKey = f.error || 'Unknown error';
          if (!errorGroups[errorKey]) errorGroups[errorKey] = [];
          errorGroups[errorKey].push(f);
        });
        
        Object.entries(errorGroups).forEach(([error, cases]) => {
          console.log(`  "${error}": ${cases.length} cases`);
          cases.slice(0, 2).forEach(c => {
            console.log(`    - ${c.testCase} with ${c.keyPair}`);
          });
          if (cases.length > 2) {
            console.log(`    - ... and ${cases.length - 2} more`);
          }
        });
      }
    });
  }
  
  // Success analysis by platform
  const successes = results.filter(r => r.success);
  if (successes.length > 0) {
    console.log('\n✅ SUCCESS ANALYSIS BY PLATFORM:');
    
    PLATFORMS.forEach(platform => {
      const platformSuccesses = successes.filter(s => s.platform === platform.name);
      if (platformSuccesses.length > 0) {
        const avgOverhead = Math.round(platformSuccesses.reduce((sum, s) => sum + (s.encryptedLength - s.originalLength), 0) / platformSuccesses.length);
        console.log(`${platform.name}:`);
        console.log(`  - Success cases: ${platformSuccesses.length}`);
        console.log(`  - Data size range: ${Math.min(...platformSuccesses.map(s => s.originalLength))} - ${Math.max(...platformSuccesses.map(s => s.originalLength))} bytes`);
        console.log(`  - Average encryption overhead: ${avgOverhead} bytes`);
      }
    });
  }
  
  // Cross-platform consistency check
  console.log('\n🔄 CROSS-PLATFORM CONSISTENCY CHECK:');
  
  const testGroups = {};
  results.forEach(result => {
    const key = `${result.testCase}-${result.keyPair}`;
    if (!testGroups[key]) testGroups[key] = [];
    testGroups[key].push(result);
  });
  
  let consistentTests = 0;
  let inconsistentTests = 0;
  
  Object.entries(testGroups).forEach(([key, group]) => {
    const allSuccess = group.every(r => r.success);
    const allFailed = group.every(r => !r.success);
    
    if (allSuccess || allFailed) {
      consistentTests++;
    } else {
      inconsistentTests++;
      console.log(`⚠️  Inconsistent: ${key}`);
      group.forEach(r => {
        console.log(`    ${r.platform}: ${r.success ? '✅' : '❌'}`);
      });
    }
  });
  
  console.log(`Consistent across platforms: ${consistentTests} test combinations`);
  console.log(`Inconsistent across platforms: ${inconsistentTests} test combinations`);
  
  // Save detailed results to file
  const reportPath = `/Users/maciejwitowski/Documents/vana/vana-personal-server/compatibility/cross_platform_test_results.json`;
  const detailedReport = {
    timestamp: new Date().toISOString(),
    summary: {
      totalTests,
      passedTests,
      failedTests: totalTests - passedTests,
      overallSuccessRate: (passedTests / totalTests) * 100,
      platformStats,
      consistentTests,
      inconsistentTests
    },
    testConfiguration: {
      platforms: PLATFORMS.map(p => p.name),
      testCases: TEST_CASES.length,
      keyPairs: KEY_PAIRS.length
    },
    results
  };
  
  fs.writeFileSync(reportPath, JSON.stringify(detailedReport, null, 2));
  console.log(`\n📄 Detailed results saved to: ${reportPath}`);
  
  return detailedReport.summary;
}

// Cross-platform encryption format consistency test
async function testEncryptionFormatConsistency() {
  console.log('\n🔍 ENCRYPTION FORMAT CONSISTENCY TEST');
  console.log('=====================================');
  
  const testData = "Test consistency across platforms";
  const keyPair = KEY_PAIRS[0];
  
  // Encrypt the same data with both platforms
  const browserEncrypted = await PLATFORMS[0].adapter.crypto.encryptWithWalletPublicKey(testData, keyPair.publicKey);
  const nodeEncrypted = await PLATFORMS[1].adapter.crypto.encryptWithWalletPublicKey(testData, keyPair.publicKey);
  
  console.log(`Browser encrypted length: ${browserEncrypted.length}`);
  console.log(`Node.js encrypted length: ${nodeEncrypted.length}`);
  
  // Both should be decryptable by Python
  const testCases = [
    { platform: 'Browser', encrypted: browserEncrypted },
    { platform: 'Node.js', encrypted: nodeEncrypted }
  ];
  
  const results = [];
  
  for (const testCase of testCases) {
    const testDataPath = `/tmp/format_test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}.json`;
    const testDataPayload = {
      encrypted_data: testCase.encrypted,
      private_key: keyPair.privateKey,
      original_data: testData
    };
    
    fs.writeFileSync(testDataPath, JSON.stringify(testDataPayload));
    
    try {
      const { stdout, stderr } = await execAsync(`source /tmp/test_env/bin/activate && python3 /Users/maciejwitowski/Documents/vana/vana-personal-server/compatibility/standalone_decrypt.py ${testDataPath}`);
      
      if (stderr) {
        throw new Error(`Python error: ${stderr}`);
      }
      
      const result = JSON.parse(stdout.trim());
      results.push({
        platform: testCase.platform,
        success: result.success,
        error: result.error
      });
      
      console.log(`${testCase.platform} → Python decryption: ${result.success ? '✅' : '❌'}`);
      
    } catch (error) {
      results.push({
        platform: testCase.platform,
        success: false,
        error: error.message
      });
      console.log(`${testCase.platform} → Python decryption: ❌ (${error.message})`);
    }
    
    fs.unlinkSync(testDataPath);
  }
  
  const allSuccessful = results.every(r => r.success);
  console.log(`\nFormat consistency result: ${allSuccessful ? '✅ CONSISTENT' : '❌ INCONSISTENT'}`);
  
  return allSuccessful;
}

// Run the comprehensive test suite
if (require.main === module) {
  runCrossPlatformTests()
    .then(async (summary) => {
      // Run format consistency test
      const formatConsistent = await testEncryptionFormatConsistency();
      
      console.log('\n🎉 Cross-Platform Test Suite Completed!');
      console.log('========================================');
      console.log(`Overall Success Rate: ${summary.overallSuccessRate.toFixed(2)}%`);
      console.log(`Format Consistency: ${formatConsistent ? 'PASS' : 'FAIL'}`);
      
      const allGood = summary.overallSuccessRate === 100 && formatConsistent;
      process.exit(allGood ? 0 : 1);
    })
    .catch(error => {
      console.error('💥 Cross-platform test suite failed:', error);
      process.exit(1);
    });
}

module.exports = { runCrossPlatformTests, testEncryptionFormatConsistency };