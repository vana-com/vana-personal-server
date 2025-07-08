import json
import traceback
import sys
from identity_server import IdentityServer

class Predictor:
    def setup(self):
        """Setup the key derivation server."""
        pass

    def predict(
        self, 
        user_address: str
    ) -> str:
        """
        Derive deterministic address for a user's server based on their address.
        This address will be stored in the smart contract.
        
        Args:
            user_address: User's Ethereum address
            
        Returns:
            JSON string with the derived address
        """
        try:
            # Create key derivation server (uses environment variable)
            identity_server = IdentityServer()
            
            # Execute address derivation
            derived_address = identity_server.derive_user_server_address(user_address)
            
            result = {
                "user_address": user_address,
                "derived_address": derived_address
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_msg = f"Error in key derivation: {str(e)}\n{traceback.format_exc()}"
            print(error_msg, file=sys.stderr)
            
            error_result = {
                "error": str(e),
                "user_address": user_address
            }
            return json.dumps(error_result, indent=2) 