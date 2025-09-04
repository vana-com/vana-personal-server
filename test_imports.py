#!/usr/bin/env python3
"""
Simple test to verify imports work correctly.
"""
import sys
sys.path.insert(0, '/workspace')

try:
    print("Testing ProcessAgentRunner import...")
    from services.process_agent_runner import ProcessAgentRunner
    print("✅ ProcessAgentRunner imported successfully")
    
    print("Testing runtime factory import...")
    # This will fail due to settings dependency, but let's see what we get
    try:
        from services.agent_runtime_factory import AgentRunner
        print("✅ Runtime factory imported successfully")
    except ImportError as e:
        print(f"⚠️  Runtime factory import failed (expected due to missing dependencies): {e}")
    
    print("Testing ProcessAgentRunner instantiation...")
    runner = ProcessAgentRunner(
        memory_limit_mb=256,
        timeout_sec=30,
        max_output_bytes=1000000,
        file_size_limit_mb=10
    )
    print(f"✅ ProcessAgentRunner created: memory_limit={runner.memory_limit_mb}MB")
    print(f"   timeout={runner.timeout_sec}s, allow_network={runner.allow_network}")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()

print("\nBasic structure test completed!")