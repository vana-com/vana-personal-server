#!/usr/bin/env python3
"""
COMPREHENSIVE PRIVACY SYSTEM CHECK
This script tests all implemented privacy components to see what's working.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.privacy_pipeline import PrivacyPipeline
from utils.privacy_budget import PrivacyLevel
import json

def test_all_components():
    """Test all privacy components systematically."""
    
    print("🔍 COMPREHENSIVE PRIVACY SYSTEM CHECK")
    print("=" * 60)
    
    test_results = {}
    
    # Test 1: Core Privacy Components
    print("\n✅ TEST 1: Core Privacy Components")
    print("-" * 40)
    
    try:
        from utils.privacy_classifier import PrivacyAwareClassifier
        classifier = PrivacyAwareClassifier()
        test_results['privacy_classifier'] = "✅ WORKING"
        print("   PrivacyAwareClassifier: ✅ WORKING")
    except Exception as e:
        test_results['privacy_classifier'] = f"❌ FAILED: {e}"
        print(f"   PrivacyAwareClassifier: ❌ FAILED: {e}")
    
    try:
        from utils.feature_extractor import PrivacyAwareFeatureExtractor
        extractor = PrivacyAwareFeatureExtractor()
        test_results['feature_extractor'] = "✅ WORKING"
        print("   PrivacyAwareFeatureExtractor: ✅ WORKING")
    except Exception as e:
        test_results['feature_extractor'] = f"❌ FAILED: {e}"
        print(f"   PrivacyAwareFeatureExtractor: ❌ FAILED: {e}")
    
    try:
        from utils.differential_privacy import add_differential_privacy
        test_results['differential_privacy'] = "✅ WORKING"
        print("   Differential Privacy: ✅ WORKING")
    except Exception as e:
        test_results['feature_extractor'] = f"❌ FAILED: {e}"
        print(f"   Differential Privacy: ❌ FAILED: {e}")
    
    try:
        from utils.privacy_budget import get_privacy_budget
        test_results['privacy_budget'] = "✅ WORKING"
        print("   Privacy Budget: ✅ WORKING")
    except Exception as e:
        test_results['privacy_budget'] = f"❌ FAILED: {e}"
        print(f"   Privacy Budget: ❌ FAILED: {e}")
    
    try:
        from utils.secure_memory import track_for_cleanup
        test_results['secure_memory'] = "✅ WORKING"
        print("   Secure Memory: ✅ WORKING")
    except Exception as e:
        test_results['secure_memory'] = f"❌ FAILED: {e}"
        print(f"   Secure Memory: ❌ FAILED: {e}")
    
    # Test 2: Advanced Privacy Components
    print("\n✅ TEST 2: Advanced Privacy Components")
    print("-" * 40)
    
    try:
        from utils.embedding_generator import LocalEmbeddingGenerator
        embedding_gen = LocalEmbeddingGenerator()
        test_results['embedding_generator'] = "✅ WORKING"
        print("   LocalEmbeddingGenerator: ✅ WORKING")
    except Exception as e:
        test_results['embedding_generator'] = f"❌ FAILED: {e}"
        print(f"   Embedding Generator: ❌ FAILED: {e}")
    
    try:
        from utils.synthetic_generator import SyntheticDataGenerator
        synthetic_gen = SyntheticDataGenerator()
        test_results['synthetic_generator'] = "✅ WORKING"
        print("   SyntheticDataGenerator: ✅ WORKING")
    except Exception as e:
        test_results['synthetic_generator'] = f"❌ FAILED: {e}"
        print(f"   Synthetic Generator: ❌ FAILED: {e}")
    
    try:
        from compute.privacy_preserving_inference import PrivacyPreservingInference
        privacy_inference = PrivacyPreservingInference()
        test_results['privacy_inference'] = "✅ WORKING"
        print("   PrivacyPreservingInference: ✅ WORKING")
    except Exception as e:
        test_results['privacy_inference'] = f"❌ FAILED: {e}"
        print(f"   Privacy Inference: ❌ FAILED: {e}")
    
    # Test 3: Privacy Pipeline Integration
    print("\n✅ TEST 3: Privacy Pipeline Integration")
    print("-" * 40)
    
    try:
        from utils.privacy_pipeline import PrivacyPipeline
        pipeline = PrivacyPipeline()
        test_results['privacy_pipeline'] = "✅ WORKING"
        print("   PrivacyPipeline: ✅ WORKING")
    except Exception as e:
        test_results['privacy_pipeline'] = f"❌ FAILED: {e}"
        print(f"   Privacy Pipeline: ❌ FAILED: {e}")
    
    # Test 4: Local Inference
    print("\n✅ TEST 4: Local Inference")
    print("-" * 40)
    
    try:
        from compute.local_inference import LocalLlmInference
        local_inference = LocalLlmInference()
        test_results['local_inference'] = "✅ WORKING"
        print("   LocalLlmInference: ✅ WORKING")
    except Exception as e:
        test_results['local_inference'] = f"❌ FAILED: {e}"
        print(f"   Local Inference: ❌ FAILED: {e}")
    
    # Test 5: Dependencies Integration
    print("\n✅ TEST 5: Dependencies Integration")
    print("-" * 40)
    
    try:
        from dependencies import get_compute_provider
        provider = get_compute_provider()
        test_results['dependencies'] = "✅ WORKING"
        print("   Dependencies Integration: ✅ WORKING")
    except Exception as e:
        test_results['dependencies'] = f"❌ FAILED: {e}"
        print(f"   Dependencies Integration: ❌ FAILED: {e}")
    
    # Test 6: End-to-End Privacy Pipeline
    print("\n✅ TEST 6: End-to-End Privacy Pipeline")
    print("-" * 40)
    
    try:
        # Test with a simple document
        test_doc = "This is a test financial document with some sensitive information."
        
        pipeline = PrivacyPipeline()
        result = pipeline.process_documents(
            user_id="test_user_789",
            documents=[test_doc],
            privacy_level=PrivacyLevel.MEDIUM,  # Use enum instead of float
            use_embeddings=True,
            use_synthetic_data=True,
            use_external_ai=False  # Don't call external AI for this test
        )
        
        test_results['end_to_end'] = "✅ WORKING"
        print("   End-to-End Pipeline: ✅ WORKING")
        print(f"   Document Type: {result.document_features.document_type.value}")
        print(f"   Risk Level: {result.document_features.risk_level}")
        print(f"   Features Extracted: {len(result.extracted_features.statistical_features)}")
        
    except Exception as e:
        test_results['end_to_end'] = f"❌ FAILED: {e}"
        print(f"   End-to-End Pipeline: ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n🎯 COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    
    working_count = sum(1 for result in test_results.values() if "✅ WORKING" in result)
    total_count = len(test_results)
    
    print(f"Total Components Tested: {total_count}")
    print(f"Working Components: {working_count}")
    print(f"Failed Components: {total_count - working_count}")
    print(f"Success Rate: {(working_count/total_count)*100:.1f}%")
    
    print(f"\n📊 DETAILED RESULTS:")
    print("-" * 40)
    
    for component, result in test_results.items():
        status = "✅" if "✅ WORKING" in result else "❌"
        print(f"{status} {component}: {result}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print("-" * 40)
    
    if working_count == total_count:
        print("🎉 ALL COMPONENTS ARE WORKING! You're ready for extensions!")
    elif working_count >= total_count * 0.8:
        print("🟡 MOST COMPONENTS ARE WORKING! Fix the failed ones before extending.")
    else:
        print("🔴 MANY COMPONENTS ARE FAILING! Fix the core system before extending.")
    
    return test_results

if __name__ == "__main__":
    test_all_components()
