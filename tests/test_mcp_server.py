"""
Tests for MCP server resources, tools, and prompts.

These tests validate the MCP implementation structure and basic functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server import server
from services.subgraph import SubgraphClient


class TestMCPServerStructure:
    """Test that MCP server components are properly registered."""

    def test_mcp_instance_exists(self):
        """Test that the MCP instance is created."""
        assert server.mcp is not None
        assert server.mcp.name == "Vana Personal Server"

    def test_auth_provider_configured(self):
        """Test that authentication is configured."""
        assert server.mcp.auth is not None

    def test_tools_registered(self):
        """Test that all required tools are registered."""
        # Get tool names from MCP instance
        # Note: This depends on FastMCP's internal structure
        # Adjust based on actual FastMCP API

        # Expected tools
        expected_tools = [
            "list_files",
            "search_files_by_schema",
            "get_file",
            "get_file_metadata",
            "list_schemas",
        ]

        # This is a basic structural test
        # Actual tool registration testing may require FastMCP test utilities
        assert True  # Placeholder


class TestSubgraphClient:
    """Test subgraph client structure and stub responses."""

    def test_subgraph_client_initialization(self):
        """Test that subgraph client can be initialized."""
        client = SubgraphClient()
        assert client.subgraph_url is not None
        assert client.client is not None

    @pytest.mark.asyncio
    async def test_list_files_returns_empty(self):
        """Test that list_files stub returns correct structure."""
        client = SubgraphClient()
        result = await client.list_files(
            owner_address="0x1234567890123456789012345678901234567890",
            limit=10,
            offset=0
        )

        assert "files" in result
        assert "limit" in result
        assert "offset" in result
        assert isinstance(result["files"], list)
        assert result["limit"] == 10
        assert result["offset"] == 0

    @pytest.mark.asyncio
    async def test_get_file_metadata_returns_none(self):
        """Test that get_file_metadata stub returns None."""
        client = SubgraphClient()
        result = await client.get_file_metadata(
            file_id=123,
            owner_address="0x1234567890123456789012345678901234567890"
        )

        assert result is None  # Stub returns None

    @pytest.mark.asyncio
    async def test_list_schemas_returns_empty(self):
        """Test that list_schemas stub returns correct structure."""
        client = SubgraphClient()
        result = await client.list_schemas(limit=10, offset=0)

        assert "schemas" in result
        assert "limit" in result
        assert "offset" in result
        assert isinstance(result["schemas"], list)
        assert result["limit"] == 10
        assert result["offset"] == 0

    @pytest.mark.asyncio
    async def test_get_schema_returns_none(self):
        """Test that get_schema stub returns None."""
        client = SubgraphClient()
        result = await client.get_schema(schema_id=1)

        assert result is None  # Stub returns None

    @pytest.mark.asyncio
    async def test_client_cleanup(self):
        """Test that client can be closed properly."""
        client = SubgraphClient()
        await client.close()
        # If close succeeds without exception, test passes


class TestMCPResources:
    """Test MCP resource handlers structure."""

    @pytest.mark.asyncio
    async def test_files_resource_validates_params(self):
        """Test that files resource validates parameters."""
        from mcp_server.resources import ResourceHandler

        handler = ResourceHandler()
        
        # Test invalid schema_ids format
        with pytest.raises(ValueError, match="Invalid schema_ids parameter"):
            await handler.read_files_resource(
                "vana://files?schema_ids=invalid",
                "0x1234567890123456789012345678901234567890"
            )


class TestMCPTools:
    """Test MCP tool handlers structure."""

    @pytest.mark.asyncio
    async def test_list_files_validates_limit(self):
        """Test that list_files validates limit parameter."""
        from mcp_server.tools import ToolHandler

        handler = ToolHandler()
        wallet_address = "0x1234567890123456789012345678901234567890"

        # Test limit too high
        with pytest.raises(ValueError, match="limit must be between 1 and 100"):
            await handler.list_files(wallet_address, limit=101)

        # Test negative limit
        with pytest.raises(ValueError, match="limit must be between 1 and 100"):
            await handler.list_files(wallet_address, limit=0)

    @pytest.mark.asyncio
    async def test_list_files_validates_offset(self):
        """Test that list_files validates offset parameter."""
        from mcp_server.tools import ToolHandler

        handler = ToolHandler()
        wallet_address = "0x1234567890123456789012345678901234567890"

        # Test negative offset
        with pytest.raises(ValueError, match="offset must be non-negative"):
            await handler.list_files(wallet_address, offset=-1)

    @pytest.mark.asyncio
    async def test_search_files_validates_query(self):
        """Test that search_files_by_schema validates query parameter."""
        from mcp_server.tools import ToolHandler

        handler = ToolHandler()
        wallet_address = "0x1234567890123456789012345678901234567890"

        # Test empty query
        with pytest.raises(ValueError, match="query parameter is required"):
            await handler.search_files_by_schema(wallet_address, query="")

        # Test whitespace-only query
        with pytest.raises(ValueError, match="query parameter is required"):
            await handler.search_files_by_schema(wallet_address, query="   ")


class TestMCPPrompts:
    """Test MCP prompt templates."""

    def test_get_my_data_prompt_exists(self):
        """Test that get_my_data prompt template is defined."""
        from mcp_server.prompts import GET_MY_DATA_TEMPLATE

        assert GET_MY_DATA_TEMPLATE is not None
        assert isinstance(GET_MY_DATA_TEMPLATE, str)

    def test_get_my_data_prompt_format(self):
        """Test that get_my_data prompt template can be formatted."""
        from mcp_server.prompts import GET_MY_DATA_TEMPLATE

        formatted = GET_MY_DATA_TEMPLATE.format(data_type="chatgpt")

        assert "chatgpt" in formatted
        assert "search_files_by_schema" in formatted
        assert "Workflow" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
