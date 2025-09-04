"""
Minimal tests for agent operations and artifact handling.
"""
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from services.mock_operations import MockOperationsService
from services.artifact_storage import ArtifactStorageService
from utils.auth import MockModeAuth, SignatureAuth
from compute.base_agent import BaseAgentProvider


class TestMockModeAuth:
    """Test mock mode authentication helper."""
    
    def test_mock_mode_bypasses_signature(self):
        """Test that mock mode returns fixed address without verification."""
        auth = MockModeAuth()
        
        with patch.object(auth, 'settings') as mock_settings:
            mock_settings.mock_mode = True
            
            # Should return mock address without calling signature verification
            result = auth.verify_signature_with_mock("test_data", "invalid_sig")
            assert result == "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    
    def test_production_mode_verifies_signature(self):
        """Test that production mode performs real verification."""
        auth = MockModeAuth()
        
        with patch.object(auth, 'settings') as mock_settings:
            mock_settings.mock_mode = False
            
            with patch.object(auth.signature_auth, 'verify_signature') as mock_verify:
                mock_verify.return_value = "0xRealAddress"
                
                result = auth.verify_signature_with_mock("test_data", "valid_sig")
                assert result == "0xRealAddress"
                mock_verify.assert_called_once_with("test_data", "valid_sig")


class TestAgentOperations:
    """Test agent operation basics."""
    
    async def test_mock_operations_routes_to_agents(self):
        """Test that MockOperationsService routes to correct agent."""
        service = MockOperationsService()
        
        # Mock the agent providers
        with patch.object(service, '_get_qwen_agent') as mock_qwen:
            with patch.object(service, '_get_gemini_agent') as mock_gemini:
                mock_qwen_instance = AsyncMock()
                mock_gemini_instance = AsyncMock()
                
                mock_qwen.return_value = mock_qwen_instance
                mock_gemini.return_value = mock_gemini_instance
                
                mock_qwen_instance.execute.return_value = {
                    "status": "succeeded",
                    "result": "qwen result"
                }
                mock_gemini_instance.execute.return_value = {
                    "status": "succeeded", 
                    "result": "gemini result"
                }
                
                # Test Qwen routing
                qwen_result = await service._handle_agent_operation(
                    "prompt_qwen_agent",
                    {"goal": "test goal"},
                    "test_id",
                    {},
                    "0xGrantee"
                )
                assert "qwen result" in str(qwen_result)
                
                # Test Gemini routing
                gemini_result = await service._handle_agent_operation(
                    "prompt_gemini_agent",
                    {"goal": "test goal"},
                    "test_id",
                    {},
                    "0xGrantee"
                )
                assert "gemini result" in str(gemini_result)


class TestArtifactStorage:
    """Test artifact storage basics."""
    
    async def test_artifact_encryption_and_storage(self):
        """Test that artifacts are encrypted before storage."""
        storage = ArtifactStorageService()
        
        # Mock S3 client
        mock_s3 = AsyncMock()
        storage._get_s3_client = Mock(return_value=mock_s3)
        
        # Test data
        operation_id = "test_op_123"
        artifact_path = "output.txt"
        content = b"test content"
        grantee = "0xTestGrantee"
        
        # Store artifact
        await storage.store_artifact(operation_id, artifact_path, content, grantee)
        
        # Verify S3 was called with encrypted content
        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args[1]
        
        # Content should be encrypted (different from original)
        assert call_args['Body'] != content
        assert call_args['Bucket'] == storage.bucket_name
        assert operation_id in call_args['Key']
    
    async def test_local_fallback_when_no_r2(self):
        """Test that storage falls back to local when R2 not configured."""
        storage = ArtifactStorageService()
        
        with patch.object(storage, '_is_configured', return_value=False):
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                # Store artifact locally
                await storage.store_artifact(
                    "local_op", 
                    "file.txt",
                    b"local content",
                    "0xGrantee"
                )
                
                # Should write to local file
                mock_open.assert_called()
                mock_file.write.assert_called()


class TestBaseAgent:
    """Test base agent async execution."""
    
    async def test_agent_runs_async(self):
        """Test that agents execute asynchronously."""
        
        class TestAgent(BaseAgentProvider):
            def get_cli_command(self):
                return "echo"
            
            def get_cli_args(self, prompt):
                return ["test"]
        
        agent = TestAgent()
        
        # Mock the async runner
        with patch.object(agent, '_run_agent_async') as mock_run:
            mock_run.return_value = {"status": "succeeded", "result": "test"}
            
            # Execute should return immediately
            result = await agent.execute("op_123", "test goal", {}, "0xGrantee")
            
            # Should have operation ID and status
            assert result["operation_id"] == "op_123"
            assert result["status"] == "pending"
            
            # Background task should be created
            assert "op_123" in agent._tasks


if __name__ == "__main__":
    # Run basic smoke tests
    print("Running agent and artifact tests...")
    
    # Test mock auth
    auth_test = TestMockModeAuth()
    auth_test.test_mock_mode_bypasses_signature()
    print("✅ Mock mode auth bypass works")
    
    auth_test.test_production_mode_verifies_signature()
    print("✅ Production mode auth verification works")
    
    # Test agent routing
    agent_test = TestAgentOperations()
    asyncio.run(agent_test.test_mock_operations_routes_to_agents())
    print("✅ Agent routing works")
    
    # Test artifact storage
    artifact_test = TestArtifactStorage()
    asyncio.run(artifact_test.test_artifact_encryption_and_storage())
    print("✅ Artifact encryption works")
    
    asyncio.run(artifact_test.test_local_fallback_when_no_r2())
    print("✅ Local storage fallback works")
    
    # Test async execution
    base_test = TestBaseAgent()
    asyncio.run(base_test.test_agent_runs_async())
    print("✅ Async agent execution works")
    
    print("\n✅ All tests passed!")