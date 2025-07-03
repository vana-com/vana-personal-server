from typing import Optional
from entities import FileMetadata

class DataRegistry:
   def fetch_file_metadata(self, file_id: int) -> Optional[FileMetadata]:
      # TODO Call Data Registry Contract to fetch the file metadata
      # TODO Process the response and map to FileMetadata
      return FileMetadata(
         file_id=999,
         owner_address="0x213F323dB56fE83BFF1d4c65C5bE741cE75869c6",
         public_url="https://httpbin.org/bytes/1024",  # Test URL that returns random bytes
         encryption_key="test_encryption_key_123"
      )