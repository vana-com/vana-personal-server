from typing import Optional
from entities import FileMetadata

class DataRegistry:
   def fetch_file_metadata(self, file_id: int) -> Optional[FileMetadata]:
      # TODO Call Data Registry Contract to fetch the file metadata
      # TODO Process the response and map to FileMetadata
      return FileMetadata(
         file_id=999,
         owner_address="0x213F323dB56fE83BFF1d4c65C5bE741cE75869c6",
         public_url="https://raw.githubusercontent.com/vana-com/data-portability-personal-server/refs/heads/maciej/next-steps/tests/personal_information.json.pgp",
         encrypted_key="0444507cbd80da6a686ce222d31389ffc9aef17eb7c9b041271b880d6ae44f7c1138de5b19940ac86e618b559436ad1ccf92738c5d0c3a5b8fdf039e50537707bafc4f5690082cc058b88c264d4026dfbbb1c050306658dcc58f5985b646dfc206a98573d40227954d141a5b4e565a107cd78ba796c476b14c838ba579c443a0e3"
      )