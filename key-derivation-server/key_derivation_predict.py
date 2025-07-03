import json
import traceback
import sys
from cog import Secret
from key_derivation_server import KeyDerivationServer

class Predictor:
    def setup(self):
        """Setup the key derivation server."""
        pass

    def predict(
        self, 
        user_address: str
    ) -> str:
        """
        Derive deterministic keys for a user's server based on their address.
        
        Args:
            user_address: User's Ethereum address
            
        Returns:
            JSON string with derived keys and metadata
        """
        try:
            # Create key derivation server
            key_server = KeyDerivationServer()
            
            # Execute key derivation
            result = key_server.derive_user_server_keys(user_address)
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error in key derivation: {str(e)}\n{traceback.format_exc()}"
            print(error_msg, file=sys.stderr)
            
            error_result = {
                "error": str(e),
                "user_address": user_address
            }
            return json.dumps(error_result, indent=2) 