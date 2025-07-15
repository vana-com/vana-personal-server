import logging
from typing import Optional

from .grant_files import retrieve_grant_file
from .grant_validation import validate_grant, GrantValidationOptions, GrantValidationError
from .grant_models import GrantFile

logger = logging.getLogger(__name__)


def fetch_grant(grant_url: str) -> Optional[GrantFile]:
    """
    Fetch and validate a grant file from IPFS.
    
    Args:
        grant_url: URL of the grant file (e.g., "ipfs://QmHash...")
        
    Returns:
        Validated GrantFile or None if validation fails
        
    Raises:
        NetworkError: When grant file cannot be retrieved from IPFS
        GrantValidationError: When grant file is invalid
    """
    try:
        # Retrieve the grant file from IPFS
        grant_file = retrieve_grant_file(grant_url)
        
        # Validate the grant (skip schema validation since we already have a GrantFile)
        validate_grant(grant_file, GrantValidationOptions(
            schema=False,  # Skip schema validation since we already have a valid GrantFile
            throw_on_error=True
        ))
        
        logger.info(f"Successfully validated grant from {grant_url}")
        return grant_file
        
    except GrantValidationError as e:
        logger.error(f"Grant validation failed for {grant_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch grant from {grant_url}: {e}")
        return None 