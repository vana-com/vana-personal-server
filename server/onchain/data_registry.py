from typing import Optional
from ..entities import FileMetadata

class DataRegistry:
   def fetch_file_metadata(self, file_id: int) -> Optional[FileMetadata]:
      # TODO Call Data Registry Contract to fetch the file metadata
      # TODO Process the response and map to FileMetadata
      return FileMetadata(
         file_id=file_id,
         owner_address="owner_address",
         public_url="https://raw.githubusercontent.com/ItzCrazyKns/Perplexica/dfb532e4d3c293664f6d61cf6ff0e540377226fa/package.json", # random URL
         encryption_key="encryption_key"
      )