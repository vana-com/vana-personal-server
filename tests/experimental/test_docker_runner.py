"""
Tests for Docker agent runner with comprehensive error cases.
"""
import pytest
import json
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from services.agent_runner import DockerAgentRunner, SENTINEL


class TestDockerAgentRunner:
    """Test Docker agent runner functionality."""
    
    @pytest.fixture
    def runner(self):
        """Create runner with mocked Docker client."""
        with patch('services.agent_runner.docker.from_env') as mock_docker:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_docker.return_value = mock_client
            
            runner = DockerAgentRunner(
                image_name="test-image",
                memory_limit="256m",
                timeout_sec=30
            )
            runner.docker_client = mock_client
            return runner
    
    def test_parse_agent_result_valid_json(self, runner):
        """Test parsing valid JSON from agent output."""
        output = """
        Starting agent...
        Processing files...
        {"status": "ok", "summary": "Task completed", "artifacts": ["out/result.txt"]}
        __AGENT_DONE__
        """
        
        result = runner._parse_agent_result(output)
        assert result is not None
        assert result["status"] == "ok"
        assert result["summary"] == "Task completed"
        assert "artifacts" in result
    
    def test_parse_agent_result_multiple_json(self, runner):
        """Test parsing chooses best JSON when multiple present."""
        output = """
        {"debug": "info"}
        {"status": "running"}
        {"status": "ok", "summary": "Done", "artifacts": [], "result": {}}
        """
        
        result = runner._parse_agent_result(output)
        assert result is not None
        # Should pick the most complete one
        assert "summary" in result
        assert "artifacts" in result
    
    def test_parse_agent_result_embedded_json(self, runner):
        """Test extracting JSON embedded in text."""
        output = """
        Agent output: {"status": "ok", "summary": "Analysis complete"} - finished
        """
        
        result = runner._parse_agent_result(output)
        assert result is not None
        assert result["status"] == "ok"
    
    def test_parse_agent_result_malformed_json(self, runner):
        """Test handling malformed JSON gracefully."""
        output = """
        {'status': 'ok', 'summary': 'Used single quotes'}
        """
        
        result = runner._parse_agent_result(output)
        # Should fix single quotes
        assert result is not None
        assert result["status"] == "ok"
    
    def test_parse_agent_result_no_json(self, runner):
        """Test handling output with no JSON."""
        output = """
        Just regular text output
        No JSON here
        """
        
        result = runner._parse_agent_result(output)
        assert result is None
    
    def test_parse_agent_result_partial_json(self, runner):
        """Test handling incomplete JSON."""
        output = """
        {"status": "ok", "summary": "Incomplete
        """
        
        result = runner._parse_agent_result(output)
        assert result is None
    
    def test_prepare_environment_security(self, runner):
        """Test environment preparation includes security settings."""
        env_vars = {"API_KEY": "secret"}
        
        env = runner._prepare_environment(env_vars)
        
        # Check security defaults
        assert env["CI"] == "1"
        assert env["NO_COLOR"] == "1"
        assert env["USER"] == "appuser"
        assert env["HOME"] == "/home/appuser"
        
        # Check custom vars included
        assert env["API_KEY"] == "secret"
    
    def test_collect_artifacts_success(self, runner):
        """Test artifact collection from workspace."""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test artifacts
            out_dir = os.path.join(tmpdir, "out")
            os.makedirs(out_dir)
            
            test_file = os.path.join(out_dir, "result.txt")
            with open(test_file, "w") as f:
                f.write("test content")
            
            from pathlib import Path
            artifacts = runner._collect_artifacts(Path(tmpdir), "test_op")
            
            assert len(artifacts) == 1
            assert artifacts[0]["name"] == "result.txt"
            assert artifacts[0]["content"] == b"test content"
    
    def test_collect_artifacts_no_output_dir(self, runner):
        """Test artifact collection when no output directory."""
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # No out/ directory created
            artifacts = runner._collect_artifacts(Path(tmpdir), "test_op")
            assert artifacts == []
    
    @pytest.mark.asyncio
    async def test_execute_agent_error_handling(self, runner):
        """Test error handling in agent execution."""
        with patch.object(runner, '_stage_workspace_files') as mock_stage:
            mock_stage.side_effect = Exception("Stage failed")
            
            result = await runner.execute_agent(
                agent_type="test",
                command="echo",
                args=["test"],
                workspace_files={},
                env_vars={},
                operation_id="test_001"
            )
            
            assert result["status"] == "error"
            assert "Stage failed" in result["summary"]
    
    def test_status_determination_with_sentinel(self, runner):
        """Test status determination when sentinel present."""
        # This tests the logic in _execute_container_async
        output_with_sentinel = f"Task output\n{SENTINEL}"
        output_with_error = f"error: something failed\n{SENTINEL}"
        
        # Would need to test through actual execution or refactor
        # the status determination logic into a separate method
        pass
    
    def test_stage_workspace_files_security(self, runner):
        """Test workspace file staging prevents directory traversal."""
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Try directory traversal attack
            files = {
                "../evil.txt": b"malicious",
                "../../etc/passwd": b"hacked",
                "normal.txt": b"safe"
            }
            
            runner._stage_workspace_files(workspace, files)
            
            # Only normal.txt should be created
            assert (workspace / "normal.txt").exists()
            assert not (workspace.parent / "evil.txt").exists()
            assert (workspace / "normal.txt").read_bytes() == b"safe"