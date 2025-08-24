"""
Mock operations service for local testing without blockchain.

This module provides a mock implementation that bypasses blockchain validation
and creates test data for agent testing.
"""

import json
import logging
import time
from typing import Optional

from domain.entities import GrantFile
from services.operations import ExecuteResponse, GetResponse
from settings import get_settings

logger = logging.getLogger(__name__)


class MockOperationsService:
    """Mock operations service for testing agent integration."""
    
    def __init__(self):
        self.settings = get_settings()
        # Create shared agent instances to preserve state
        self._qwen_agent = None
        self._gemini_agent = None
        logger.info("[MOCK] Mock operations service initialized")
    
    def _get_qwen_agent(self):
        """Get shared Qwen agent instance."""
        if self._qwen_agent is None:
            from compute.qwen_agent import QwenCodeAgentProvider
            self._qwen_agent = QwenCodeAgentProvider()
        return self._qwen_agent
    
    def _get_gemini_agent(self):
        """Get shared Gemini agent instance."""
        if self._gemini_agent is None:
            from compute.gemini_agent import GeminiAgentProvider
            self._gemini_agent = GeminiAgentProvider()
        return self._gemini_agent
    
    async def create(
        self,
        request_json: str,
        signature: str,
        request_id: str
    ) -> ExecuteResponse:
        """
        Execute a mock operation for testing.
        
        Creates test grant files and permissions based on permission_id:
        - 3072: Qwen agent test
        - 4096: Gemini agent test
        - Others: Standard LLM inference
        """
        # Parse the request JSON
        try:
            operation_request = json.loads(request_json)
        except json.JSONDecodeError as e:
            logger.error(f"[MOCK] Failed to parse request JSON: {e}")
            raise ValueError(f"Invalid JSON: {e}")
        
        permission_id = operation_request.get("permission_id")
        app_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"  # Mock app address
        logger.info(f"[MOCK] Processing mock operation with permission_id: {permission_id} [RequestID: {request_id}]")
        
        # Create mock permission data
        mock_permission = {
            "id": permission_id or 1,
            "grantor": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",  # Test address
            "grantee": app_address or "0x0000000000000000000000000000000000000000",
            "url": "mock://grant-file",
            "file_ids": ["mock-file-1", "mock-file-2"]
        }
        
        # Get rich mock data and dynamic goals
        from services.mock_data import get_mock_data_for_permission
        mock_files_content, dynamic_goal = get_mock_data_for_permission(permission_id)
        
        # Create mock grant file based on permission_id
        if permission_id in [3001, 3002, 3072]:  # Qwen operations
            mock_grant_file = GrantFile(
                grantee=mock_permission["grantee"],
                operation="prompt_qwen_agent",
                parameters={
                    "goal": dynamic_goal
                }
            )
            logger.info(f"[MOCK] Created Qwen agent grant file with goal: {dynamic_goal[:100]}...")
        elif permission_id in [4001, 4002, 4096, 9999]:  # Gemini operations
            mock_grant_file = GrantFile(
                grantee=mock_permission["grantee"],
                operation="prompt_gemini_agent",
                parameters={
                    "goal": dynamic_goal
                }
            )
            logger.info(f"[MOCK] Created Gemini agent grant file with goal: {dynamic_goal[:100]}...")
        else:
            # Default LLM inference
            mock_grant_file = GrantFile(
                grantee=mock_permission["grantee"],
                operation="llm_inference",
                parameters={
                    "prompt": "Analyze this personal data and provide insights: {{data}}",
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7
                }
            )
            logger.info("[MOCK] Created default LLM inference grant file")
        
        # Route to appropriate provider
        try:
            if mock_grant_file.operation == "prompt_qwen_agent":
                logger.info(f"[MOCK] Routing to Qwen agent provider [RequestID: {request_id}]")
                agent_provider = self._get_qwen_agent()
                result = agent_provider.execute(mock_grant_file, mock_files_content)
            elif mock_grant_file.operation == "prompt_gemini_agent":
                logger.info(f"[MOCK] Routing to Gemini agent provider [RequestID: {request_id}]")
                agent_provider = self._get_gemini_agent()
                result = agent_provider.execute(mock_grant_file, mock_files_content)
            else:
                # Mock standard compute response
                logger.info(f"[MOCK] Using mock compute response [RequestID: {request_id}]")
                result = ExecuteResponse(
                    id=f"mock_{int(time.time() * 1000)}",
                    created_at=time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
                )
            
            logger.info(f"[MOCK] Operation completed successfully, operation ID: {result.id} [RequestID: {request_id}]")
            return result
            
        except Exception as e:
            logger.error(f"[MOCK] Operation failed: {str(e)} [RequestID: {request_id}]")
            raise
    
    def get(self, operation_id: str) -> GetResponse:
        """Get mock operation status."""
        logger.info(f"[MOCK] Getting status for operation {operation_id}")
        
        # Route based on operation ID prefix
        try:
            if operation_id.startswith("qwen_"):
                agent_provider = self._get_qwen_agent()
                return agent_provider.get(operation_id)
            elif operation_id.startswith("gemini_"):
                agent_provider = self._get_gemini_agent()
                return agent_provider.get(operation_id)
            else:
                # Return mock completed status
                return GetResponse(
                    id=operation_id,
                    status="succeeded",
                    started_at=time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                    finished_at=time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                    result=json.dumps({
                        "mock": True,
                        "message": "This is a mock result for testing",
                        "operation_id": operation_id
                    })
                )
        except Exception as e:
            logger.error(f"[MOCK] Failed to get operation {operation_id}: {str(e)}")
            raise
    
    def cancel(self, operation_id: str) -> bool:
        """Cancel mock operation."""
        logger.info(f"[MOCK] Cancelling operation {operation_id}")
        return True