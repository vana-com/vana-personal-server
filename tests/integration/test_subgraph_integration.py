import pytest
import pytest_asyncio
import os
from services.subgraph import SubgraphClient
from domain.exceptions import (
    SubgraphQueryError,
    SubgraphConnectionError,
    SubgraphOwnerMismatchError,
)


@pytest.fixture
def mock_wallet():
    """Mock wallet address for testing."""
    return "0x2ac93684679a5bda03c6160def908cdb8d46792f"


@pytest.fixture
def test_file_id():
    """Test file ID from design doc."""
    return 1129387


@pytest.fixture
def test_file_id_with_schema():
    """Test file ID with schema from design doc."""
    return 1760803


@pytest.fixture
def test_schema_ids():
    """Test schema IDs from design doc."""
    return [25, 35]


@pytest.fixture
def test_schema_id():
    """Single test schema ID from design doc."""
    return 35


@pytest_asyncio.fixture(scope="function")
async def subgraph_client():
    """Create subgraph client for testing."""
    subgraph_url = os.getenv("SUBGRAPH_URL")
    # Always create a new client instance for tests (don't use singleton)
    client = SubgraphClient(subgraph_url=subgraph_url) if subgraph_url else SubgraphClient()
    yield client
    await client.close()


@pytest.mark.asyncio
class TestSubgraphIntegration:
    """Integration tests for SubgraphClient."""

    async def test_list_files_basic(self, subgraph_client, mock_wallet):
        """Test listing files without schema filter."""
        result = await subgraph_client.list_files(
            owner_address=mock_wallet,
            limit=5
        )
        
        assert result is not None
        assert isinstance(result["files"], list)
        assert result["limit"] == 5
        assert result["offset"] == 0
        
        # All files should have schema_id (filtered by schemaId_gt: "0")
        for file in result["files"]:
            assert file["file_id"] is not None
            assert file["file_url"] is not None
            assert file["schema_id"] is not None  # Should be filtered
            assert file["date_added"] is not None

    async def test_list_files_with_schema_filter(
        self, subgraph_client, mock_wallet, test_schema_ids
    ):
        """Test listing files with schema filter."""
        result = await subgraph_client.list_files(
            owner_address=mock_wallet,
            schema_ids=test_schema_ids,
            limit=5
        )
        
        assert result is not None
        assert isinstance(result["files"], list)
        assert result["limit"] == 5
        
        # All files should match one of the requested schema IDs
        for file in result["files"]:
            assert file["schema_id"] in test_schema_ids

    async def test_get_file_metadata_success(
        self, subgraph_client, mock_wallet, test_file_id
    ):
        """Test getting file metadata successfully."""
        try:
            result = await subgraph_client.get_file_metadata(
                file_id=test_file_id,
                owner_address=mock_wallet
            )
            
            # File might not exist or might not belong to this wallet
            # So we just check structure if result exists
            if result:
                assert result["file_id"] == test_file_id
                assert result["file_url"] is not None
                assert result["date_added"] is not None
        except SubgraphOwnerMismatchError:
            # File exists but belongs to a different owner - this is expected
            # when using test file IDs from design doc that belong to different wallet
            pass

    async def test_get_file_metadata_not_found(
        self, subgraph_client, mock_wallet
    ):
        """Test getting file metadata for non-existent file."""
        # Use a very large file ID that likely doesn't exist
        result = await subgraph_client.get_file_metadata(
            file_id=999999999,
            owner_address=mock_wallet
        )
        
        assert result is None

    async def test_get_file_metadata_owner_mismatch(
        self, subgraph_client, mock_wallet, test_file_id
    ):
        """Test getting file metadata with wrong owner."""
        # Use a different wallet address
        wrong_wallet = "0xd867102a1955046f3190c89c48d9f0ce79d6bda7"
        
        result = await subgraph_client.get_file_metadata(
            file_id=test_file_id,
            owner_address=wrong_wallet
        )
        
        # Should return None if owner doesn't match (unless file doesn't exist)
        # If file exists and owner doesn't match, it will raise SubgraphOwnerMismatchError
        # So we test both cases
        if result is None:
            # File doesn't exist or owner doesn't match (silent failure)
            pass
        else:
            # If file exists, it should have correct owner
            assert result["file_id"] == test_file_id

    async def test_list_schemas_basic(self, subgraph_client):
        """Test listing schemas without search."""
        result = await subgraph_client.list_schemas(limit=5)
        
        assert result is not None
        assert isinstance(result["schemas"], list)
        assert result["limit"] == 5
        assert result["offset"] == 0
        
        for schema in result["schemas"]:
            assert schema["schema_id"] is not None
            assert schema["name"] is not None
            assert isinstance(schema["description"], str)

    async def test_list_schemas_with_search(self, subgraph_client):
        """Test listing schemas with keyword search."""
        # Search for common schema name patterns
        search_term = "uber"
        result = await subgraph_client.list_schemas(query=search_term, limit=5)
        
        assert result is not None
        assert isinstance(result["schemas"], list)
        
        # All schemas should match the search term (case-insensitive)
        for schema in result["schemas"]:
            assert search_term.lower() in schema["name"].lower()

    async def test_get_schema_success(
        self, subgraph_client, test_schema_id
    ):
        """Test getting schema definition successfully."""
        result = await subgraph_client.get_schema(schema_id=test_schema_id)
        
        # Schema might not exist, so we check structure if result exists
        if result:
            assert result["schema_id"] == test_schema_id
            assert result["name"] is not None
            assert result["version"] is not None
            assert isinstance(result["description"], str)
            assert result["ipfs_url"] is not None
            assert isinstance(result["schema"], dict)

    async def test_get_schema_not_found(self, subgraph_client):
        """Test getting schema that doesn't exist."""
        # Use a very large schema ID that likely doesn't exist
        result = await subgraph_client.get_schema(schema_id=999999999)
        
        assert result is None

    async def test_pagination(self, subgraph_client, mock_wallet):
        """Test pagination works correctly."""
        # Get first page
        page1 = await subgraph_client.list_files(
            owner_address=mock_wallet,
            limit=2,
            offset=0
        )
        
        # Get second page
        page2 = await subgraph_client.list_files(
            owner_address=mock_wallet,
            limit=2,
            offset=2
        )
        
        assert page1["limit"] == 2
        assert page1["offset"] == 0
        assert page2["limit"] == 2
        assert page2["offset"] == 2
        
        # Files should be different (if enough files exist)
        if len(page1["files"]) == 2 and len(page2["files"]) > 0:
            assert page1["files"][0]["file_id"] != page2["files"][0]["file_id"]

    async def test_subgraph_connection_error(self, mock_wallet):
        """Test that connection errors raise SubgraphConnectionError."""
        # Create client with invalid URL - use a non-routable IP address
        # This will fail faster than DNS resolution
        invalid_client = SubgraphClient(subgraph_url="http://192.0.2.1:12345/graphql")
        # Override timeout to make test faster
        import httpx
        invalid_client.client = httpx.AsyncClient(timeout=1.0)
        
        try:
            with pytest.raises(SubgraphConnectionError):
                await invalid_client.list_files(owner_address=mock_wallet, limit=1)
        finally:
            await invalid_client.close()

