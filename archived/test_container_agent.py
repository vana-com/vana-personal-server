#!/usr/bin/env python3
"""
Test script to verify agent CLI tools are installed in Docker container.
Run this inside the container to verify the setup.
"""

import subprocess
import sys
import os
import json


def run_command(cmd, check=True):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            check=check
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr, e.returncode


def check_cli_tool(name, version_cmd):
    """Check if a CLI tool is installed."""
    print(f"\nChecking {name}...")
    
    # Check if tool exists
    stdout, stderr, code = run_command(f"which {name}", check=False)
    if code != 0:
        print(f"  ❌ {name} not found in PATH")
        return False
    
    print(f"  ✓ Found at: {stdout}")
    
    # Check version
    stdout, stderr, code = run_command(version_cmd, check=False)
    if code == 0 and stdout:
        print(f"  ✓ Version info: {stdout.split()[0] if stdout else 'unknown'}")
    else:
        print(f"  ⚠ Could not get version (may require auth)")
    
    return True


def check_python_packages():
    """Check required Python packages."""
    print("\nChecking Python packages...")
    
    required = ["pexpect", "web3", "httpx", "pydantic"]
    
    for package in required:
        try:
            __import__(package)
            print(f"  ✓ {package} installed")
        except ImportError:
            print(f"  ❌ {package} not installed")


def check_environment():
    """Check environment variables."""
    print("\nChecking environment variables...")
    
    env_vars = [
        "WALLET_MNEMONIC",
        "CHAIN_ID",
        "RPC_URL",
        "QWEN_API_KEY",
        "GEMINI_API_KEY",
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "MNEMONIC" in var:
                masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                print(f"  ✓ {var}: {masked}")
            else:
                print(f"  ✓ {var}: {value}")
        else:
            print(f"  ⚠ {var}: not set")


def test_agent_import():
    """Test if agent modules can be imported."""
    print("\nChecking agent modules...")
    
    modules = [
        "compute.base_agent",
        "compute.qwen_agent",
        "compute.gemini_agent",
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module} imports successfully")
        except ImportError as e:
            print(f"  ❌ {module} import failed: {e}")


def test_workspace_creation():
    """Test if we can create secure workspaces."""
    print("\nChecking workspace creation...")
    
    import tempfile
    import shutil
    
    try:
        # Create test workspace
        workspace = tempfile.mkdtemp(prefix="test_agent_")
        print(f"  ✓ Created workspace: {workspace}")
        
        # Check permissions
        import stat
        mode = os.stat(workspace).st_mode
        if mode & stat.S_IRWXU == stat.S_IRWXU:
            print(f"  ✓ Workspace has correct permissions (700)")
        
        # Cleanup
        shutil.rmtree(workspace)
        print(f"  ✓ Cleaned up workspace")
        
    except Exception as e:
        print(f"  ❌ Workspace test failed: {e}")


def main():
    print("=" * 60)
    print("Docker Container Agent Setup Verification")
    print("=" * 60)
    
    # Check CLI tools
    qwen_ok = check_cli_tool("qwen", "qwen --version")
    gemini_ok = check_cli_tool("gemini", "gemini --version")
    
    # Check Node.js and npm
    node_ok = check_cli_tool("node", "node --version")
    npm_ok = check_cli_tool("npm", "npm --version")
    
    # Check Python environment
    check_python_packages()
    check_environment()
    test_agent_import()
    test_workspace_creation()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if qwen_ok and gemini_ok:
        print("✅ Both agent CLI tools are installed")
    elif qwen_ok:
        print("⚠️  Only Qwen CLI is installed")
    elif gemini_ok:
        print("⚠️  Only Gemini CLI is installed")
    else:
        print("❌ No agent CLI tools found")
    
    if node_ok and npm_ok:
        print("✅ Node.js environment is ready")
    else:
        print("❌ Node.js environment issues")
    
    print("\nTo test inside Docker container:")
    print("  docker-compose exec personal-server python3 test_container_agent.py")
    
    print("\nTo test agent operations:")
    print("  1. Set up API keys or OAuth")
    print("  2. Deploy contracts and create permissions")
    print("  3. Submit operation requests via API")


if __name__ == "__main__":
    main()