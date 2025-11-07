"""
Schema caching functionality for MCP resources.

Provides LRU cache for schema metadata and content to improve performance
and reduce redundant IPFS fetches.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from cachetools import LRUCache

from services.subgraph import get_subgraph_client

logger = logging.getLogger(__name__)

# Cache configuration
SCHEMA_CACHE_SIZE = 100


@dataclass
class CachedSchema:
    """Schema cache entry containing metadata and optional content."""
    schema_id: int
    name: str
    dialect: str
    definition_url: str
    created_at: str
    version: Optional[str] = None
    description: str = ""
    schema_content: str = ""  # Store as string to support all dialects (json, sqlite, etc.)
    
    def is_content_loaded(self) -> bool:
        """Check if schema content has been loaded from IPFS."""
        return bool(self.schema_content)


class SchemaCache:
    """
    LRU cache for schema metadata and content.
    
    Provides caching functionality with background prepopulation
    for improved performance.
    """
    
    def __init__(self, cache_size: int = SCHEMA_CACHE_SIZE):
        """
        Initialize schema cache.
        
        Args:
            cache_size: Maximum number of schemas to cache (default: SCHEMA_CACHE_SIZE)
        """
        self.cache: LRUCache[int, CachedSchema] = LRUCache(maxsize=cache_size)
        self._prepopulate_started = False
        self.subgraph = get_subgraph_client()
    
    def get(self, schema_id: int) -> Optional[CachedSchema]:
        """
        Get schema from cache.
        
        Args:
            schema_id: The schema ID to retrieve
            
        Returns:
            CachedSchema if found, None otherwise
        """
        return self.cache.get(schema_id)
    
    def __contains__(self, schema_id: int) -> bool:
        """Check if schema is in cache."""
        return schema_id in self.cache
    
    def __getitem__(self, schema_id: int) -> CachedSchema:
        """Get schema from cache."""
        return self.cache[schema_id]
    
    def __setitem__(self, schema_id: int, cached_schema: CachedSchema) -> None:
        """Store schema in cache."""
        self.cache[schema_id] = cached_schema
    
    def clear(self) -> None:
        """Clear all cached schemas."""
        self.cache.clear()
    
    def __len__(self) -> int:
        """Get number of cached schemas."""
        return len(self.cache)
    
    async def ensure_prepopulate_started(self):
        """Start background prepopulation task if not already started."""
        if not self._prepopulate_started:
            self._prepopulate_started = True
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self._prepopulate_schema_cache())
                logger.info("Started background task to prepopulate schema cache")
            except RuntimeError:
                logger.warning("Could not start background prepopulation task. Cache will be populated on demand.")
    
    async def _prepopulate_schema_cache(self):
        """
        Background task to prepopulate schema cache with JSON schemas.
        
        Fetches all JSON schemas from subgraph and populates cache up to SCHEMA_CACHE_SIZE.
        Errors are logged but don't stop the process.
        """
        try:
            logger.info("Starting schema cache prepopulation for JSON schemas")
            offset = 0
            limit = 100
            schemas_added = 0
            
            while schemas_added < SCHEMA_CACHE_SIZE:
                # Fetch schemas with dialect="json"
                try:
                    result = await self.subgraph.list_schemas(
                        query=None,
                        dialect="json",
                        limit=limit,
                        offset=offset
                    )
                    
                    schemas = result.get("schemas", [])
                    if not schemas:
                        # No more schemas to fetch
                        break
                    
                    # Process each schema
                    for schema_info in schemas:
                        if schemas_added >= SCHEMA_CACHE_SIZE:
                            break
                        
                        schema_id = schema_info["schema_id"]
                        
                        # Skip if already in cache
                        if schema_id in self.cache:
                            continue
                        
                        try:
                            # First get schema metadata from subgraph (includes dialect and definitionUrl)
                            schema_metadata = await self._get_schema_metadata(schema_id)
                            if not schema_metadata:
                                continue
                            
                            dialect = schema_metadata.get("dialect", "json")
                            definition_url = schema_metadata.get("definitionUrl", "")
                            created_at = schema_metadata.get("createdAt", "")
                            subgraph_name = schema_metadata.get("name", "")
                            
                            # Then fetch full schema definition from IPFS (includes description)
                            schema_def = await self.subgraph.get_schema(schema_id)
                            if schema_def:
                                # Prioritize name and description from IPFS schema
                                ipfs_name = schema_def.get("name", "")
                                ipfs_description = schema_def.get("description", "")  # Only in IPFS
                                
                                # Convert schema content to string (supports all dialects)
                                schema_content_raw = schema_def.get("schema", {})
                                if isinstance(schema_content_raw, dict):
                                    schema_content_str = json.dumps(schema_content_raw)
                                else:
                                    schema_content_str = str(schema_content_raw)
                                
                                # Create cache entry with full content
                                cached = CachedSchema(
                                    schema_id=schema_id,
                                    name=ipfs_name if ipfs_name else subgraph_name,
                                    dialect=dialect,  # From subgraph
                                    definition_url=definition_url,  # From subgraph (definitionUrl)
                                    created_at=created_at,  # From subgraph
                                    version=schema_def.get("version"),
                                    description=ipfs_description,  # Only from IPFS
                                    schema_content=schema_content_str  # Store as string
                                )
                                self.cache[schema_id] = cached
                                schemas_added += 1
                        except Exception as e:
                            logger.warning(f"Failed to fetch schema {schema_id} for cache prepopulation: {e}")
                            continue
                    
                    # If we got fewer schemas than requested, we're done
                    if len(schemas) < limit:
                        break
                    
                    offset += limit
                    
                except Exception as e:
                    logger.error(f"Error during schema cache prepopulation: {e}")
                    break
            
            logger.info(f"Schema cache prepopulation completed. Added {schemas_added} schemas to cache.")
        except Exception as e:
            logger.error(f"Unexpected error in schema cache prepopulation: {e}")
    
    async def _get_schema_metadata(self, schema_id: int) -> Optional[dict]:
        """
        Get schema metadata from subgraph (without IPFS fetch).
        
        Returns dialect, definitionUrl, name, and createdAt from subgraph.
        
        Args:
            schema_id: The schema ID to retrieve
            
        Returns:
            Dictionary with schema metadata or None if not found
        """
        query = """
        query GetSchemaMetadata($id: ID!) {
          schema(id: $id) {
            id
            name
            dialect
            definitionUrl
            createdAt
          }
        }
        """
        
        variables = {
            "id": str(schema_id)
        }
        
        try:
            data = await self.subgraph._query(query, variables)
            schema_data = data.get("schema")
            return schema_data
        except Exception as e:
            logger.error(f"Error getting schema metadata for {schema_id}: {e}")
            return None

