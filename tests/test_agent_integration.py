"""
Integration tests for agent providers with mocked Docker execution.
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from domain.entities import GrantFile
from compute.qwen_agent import QwenCodeAgentProvider
from compute.gemini_agent import GeminiAgentProvider
from services.task_store import TaskStatus


class TestAgentProviderIntegration:
    """Test agent providers with full BaseCompute interface."""
    
    @pytest.fixture
    def mock_docker_runner(self):
        """Create mock Docker runner."""
        runner = MagicMock()
        runner.execute_agent = AsyncMock(return_value={
            "status": "ok",
            "summary": "Task completed",
            "result": {"test": "data"},
            "artifacts": [
                {
                    "name": "result.txt",
                    "content": b"test output",
                    "size": 11,
                    "artifact_path": "out/result.txt"
                }
            ],
            "logs": [],
            "stdout": "Agent output"
        })
        return runner
    
    @pytest.fixture
    def mock_task_store(self):
        """Create mock task store."""
        store = MagicMock()
        store.create_task = AsyncMock()
        store.update_status = AsyncMock()
        store.set_async_task = AsyncMock()
        store.get_task = AsyncMock()
        store.cancel_task = AsyncMock(return_value=True)
        return store
    
    @pytest.fixture
    def mock_artifact_storage(self):
        """Create mock artifact storage."""
        storage = MagicMock()
        storage.store_artifact = AsyncMock()
        return storage
    
    @pytest.mark.asyncio
    async def test_qwen_agent_execute(self, mock_docker_runner, mock_task_store, mock_artifact_storage):
        """Test Qwen agent execute method."""
        agent = QwenCodeAgentProvider()
        agent._docker_runner = mock_docker_runner
        agent._task_store = mock_task_store
        agent._artifact_storage = mock_artifact_storage
        
        grant_file = GrantFile(
            grantee="0x123",
            operation="prompt_qwen_agent",
            parameters={"goal": "Test task"}
        )
        
        result = await agent.execute(grant_file, ["test file"])
        
        assert result.id is not None
        assert "qwen_" in result.id
        assert result.created_at is not None
        
        # Verify task was created
        mock_task_store.create_task.assert_called_once()
        mock_task_store.set_async_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_gemini_agent_execute(self, mock_docker_runner, mock_task_store, mock_artifact_storage):
        """Test Gemini agent execute method."""
        agent = GeminiAgentProvider()
        agent._docker_runner = mock_docker_runner
        agent._task_store = mock_task_store
        agent._artifact_storage = mock_artifact_storage
        
        grant_file = GrantFile(
            grantee="0x456",
            operation="prompt_gemini_agent",
            parameters={"goal": "Analyze data"}
        )
        
        result = await agent.execute(grant_file, ["data content"])
        
        assert result.id is not None
        assert "gemini_" in result.id
        assert result.created_at is not None
    
    @pytest.mark.asyncio
    async def test_agent_get_status(self, mock_task_store):
        """Test agent get method for status checking."""
        agent = QwenCodeAgentProvider()
        agent._task_store = mock_task_store
        
        # Mock task info
        task_info = MagicMock()
        task_info.status = TaskStatus.SUCCEEDED
        task_info.started_at = MagicMock()
        task_info.started_at.isoformat.return_value = "2024-01-01T00:00:00"
        task_info.completed_at = MagicMock()
        task_info.completed_at.isoformat.return_value = "2024-01-01T00:01:00"
        task_info.result = {"status": "ok", "summary": "Done"}
        
        mock_task_store.get_task.return_value = task_info
        
        response = await agent.get("test_123")
        
        assert response.id == "test_123"
        assert response.status == "succeeded"
        assert response.started_at is not None
        assert response.finished_at is not None
        assert "Done" in response.result
    
    @pytest.mark.asyncio
    async def test_agent_cancel(self, mock_task_store):
        """Test agent cancel method."""
        agent = GeminiAgentProvider()
        agent._task_store = mock_task_store
        
        result = await agent.cancel("test_456")
        
        assert result is True
        mock_task_store.cancel_task.assert_called_once_with("test_456")
    
    @pytest.mark.asyncio
    async def test_agent_get_not_found(self, mock_task_store):
        """Test agent get with non-existent task."""
        agent = QwenCodeAgentProvider()
        agent._task_store = mock_task_store
        mock_task_store.get_task.return_value = None
        
        with pytest.raises(ValueError, match="Operation .* not found"):
            await agent.get("nonexistent")
    
    @pytest.mark.asyncio
    async def test_agent_invalid_grant_parameters(self):
        """Test agent with invalid grant parameters."""
        agent = QwenCodeAgentProvider()
        
        # Missing goal parameter
        grant_file = GrantFile(
            grantee="0x789",
            operation="prompt_qwen_agent",
            parameters={}
        )
        
        with pytest.raises(ValueError, match="requires 'goal' parameter"):
            await agent.execute(grant_file, [])
    
    def test_agent_cli_command_methods(self):
        """Test agent CLI command generation methods."""
        qwen = QwenCodeAgentProvider()
        assert qwen.get_cli_command() == "qwen"
        args = qwen.get_cli_args("test prompt")
        assert "-p" in args
        assert "test prompt" in args
        
        gemini = GeminiAgentProvider()
        assert gemini.get_cli_command() == "gemini"
        args = gemini.get_cli_args("test prompt")
        assert "-y" in args
        assert "-p" in args
    
    def test_agent_env_overrides(self):
        """Test environment variable overrides for agents."""
        with patch('compute.qwen_agent.get_settings') as mock_settings:
            settings = MagicMock()
            settings.qwen_api_url = "https://api.example.com"
            settings.qwen_model_name = "qwen-model"
            settings.qwen_api_key = "secret-key"
            settings.qwen_timeout_sec = 180
            settings.qwen_max_stdout_mb = 2
            settings.qwen_cli_path = None
            mock_settings.return_value = settings
            
            agent = QwenCodeAgentProvider()
            env = agent.get_env_overrides()
            
            assert env["OPENAI_API_KEY"] == "secret-key"
            assert env["OPENAI_BASE_URL"] == "https://api.example.com"
            assert env["OPENAI_MODEL"] == "qwen-model"