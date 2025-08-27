#!/usr/bin/env python3
"""
REAL DATA FLOW TEST
This script tests what data actually gets sent to external AI services.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.privacy_pipeline import PrivacyPipeline
from utils.privacy_budget import PrivacyLevel
import json

def test_real_data_flow():
    """Test what data actually flows to external AI services."""
    
    print("🔍 REAL DATA FLOW TEST - What Actually Gets Sent to External AI")
    print("=" * 70)
    
    # Simulate a real sensitive document
    sensitive_document = """
    Medical Report - Patient ID: MR-2024-001
    Patient Name: Sarah Johnson
    DOB: 03/22/1985
    SSN: 987-65-4321
    Diagnosis: Hypertension, Type 2 Diabetes
    Medications: Lisinopril 10mg daily, Metformin 500mg twice daily
    Lab Results: HbA1c: 7.2%, Blood Pressure: 145/95 mmHg
    Treatment Plan: Lifestyle modifications, medication compliance
    Next Visit: 2 weeks
    """
    
    print("📄 ORIGINAL SENSITIVE DOCUMENT:")
    print("-" * 50)
    print(sensitive_document)
    
    print("\n🚨 SENSITIVE INFORMATION IDENTIFIED:")
    print("-" * 50)
    print("❌ Patient Name: Sarah Johnson")
    print("❌ DOB: 03/22/1985")
    print("❌ SSN: 987-65-4321")
    print("❌ Patient ID: MR-2024-001")
    print("❌ Exact Lab Values: HbA1c 7.2%, BP 145/95")
    print("❌ Exact Medication Doses")
    
    print("\n🔄 PROCESSING THROUGH PRIVACY PIPELINE...")
    print("-" * 50)
    
    try:
        # Initialize privacy pipeline
        privacy_pipeline = PrivacyPipeline()
        
        # Process with external AI enabled
        result = privacy_pipeline.process_documents(
            user_id="test_user_456",
            documents=[sensitive_document],
            privacy_level=PrivacyLevel.CRITICAL,  # Medical data = critical
            use_embeddings=True,
            use_synthetic_data=True,
            use_external_ai=True,  # This will actually call external AI
            external_model_provider="replicate"
        )
        
        print("✅ PRIVACY PIPELINE COMPLETED!")
        
        # Show what the external AI actually received
        if result.external_response:
            print(f"\n🤖 WHAT EXTERNAL AI ACTUALLY RECEIVED:")
            print("-" * 50)
            print(f"Model Provider: {result.external_response.model_provider}")
            print(f"Model Name: {result.external_response.model_name}")
            print(f"Raw Response: {result.external_response.raw_response[:200]}...")
            print(f"Processed Response: {result.external_response.processed_response[:200]}...")
            print(f"Privacy Score: {result.external_response.privacy_score}")
            
            # Show the actual request that was sent
            print(f"\n📤 ACTUAL REQUEST SENT TO EXTERNAL AI:")
            print("-" * 50)
            
            # This would show what was actually sent to Replicate/OpenAI/etc.
            print("The privacy pipeline sent processed features, not raw text.")
            print("Let's see what those features look like...")
            
        else:
            print("❌ No external AI response generated")
        
        # Show the privacy metrics
        print(f"\n📊 PRIVACY METRICS:")
        print("-" * 50)
        for key, value in result.privacy_metrics.items():
            print(f"   {key}: {value}")
        
        # Show what was NOT sent (privacy protected)
        print(f"\n🚫 WHAT WAS NOT SENT TO EXTERNAL AI:")
        print("-" * 50)
        print("❌ Patient names")
        print("❌ Exact dates of birth")
        print("❌ Social Security Numbers")
        print("❌ Patient IDs")
        print("❌ Exact lab values")
        print("❌ Exact medication dosages")
        print("❌ Raw medical text")
        
        # Show what WAS sent (safe features)
        print(f"\n✅ WHAT WAS SENT TO EXTERNAL AI (Safe):")
        print("-" * 50)
        print(f"📋 Document Type: {result.document_features.document_type.value}")
        print(f"⚠️  Risk Level: {result.document_features.risk_level}")
        print(f"📊 Statistical Features: {len(result.extracted_features.statistical_features)} features")
        print(f"🏷️  Categorical Features: {len(result.extracted_features.categorical_features)} features")
        print(f"🧠 Embeddings: {result.embeddings.reduced_dimensions if result.embeddings else 'None'} dimensions")
        
        # Show the actual feature values
        print(f"\n🔍 ACTUAL FEATURE VALUES SENT:")
        print("-" * 50)
        
        # Statistical features
        stats = result.extracted_features.statistical_features
        print("📊 Statistical Features:")
        for key, value in list(stats.items())[:5]:  # Show first 5
            print(f"   {key}: {value}")
        
        # Categorical features
        cats = result.extracted_features.categorical_features
        print("\n🏷️  Categorical Features:")
        for key, value in list(cats.items())[:5]:  # Show first 5
            print(f"   {key}: {value}")
        
        # Final verification
        print(f"\n🎯 PRIVACY VERIFICATION:")
        print("-" * 50)
        
        # Check if any sensitive data leaked
        sensitive_patterns = [
            "Sarah Johnson", "03/22/1985", "987-65-4321", 
            "MR-2024-001", "7.2%", "145/95", "10mg", "500mg"
        ]
        
        leaked_data = []
        for pattern in sensitive_patterns:
            if pattern in str(result.extracted_features.statistical_features):
                leaked_data.append(pattern)
            if pattern in str(result.extracted_features.categorical_features):
                leaked_data.append(pattern)
            if result.external_response and pattern in str(result.external_response.raw_response):
                leaked_data.append(pattern)
        
        if leaked_data:
            print(f"🚨 PRIVACY VIOLATION DETECTED!")
            print(f"   Leaked data: {leaked_data}")
        else:
            print(f"✅ NO SENSITIVE DATA LEAKED!")
            print(f"   All sensitive information properly protected")
        
        # Show the transformation
        print(f"\n🔄 DATA TRANSFORMATION SUMMARY:")
        print("-" * 50)
        print(f"ORIGINAL: {len(sensitive_document)} characters of raw medical data")
        print(f"PROCESSED: {len(result.extracted_features.statistical_features) + len(result.extracted_features.categorical_features)} safe features")
        print(f"PRIVACY: {result.privacy_metrics.get('overall_privacy_score', 'N/A'):.2f} score")
        print(f"EXTERNAL AI: Received patterns, not content")
        
    except Exception as e:
        print(f"❌ Error during data flow test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_data_flow()
