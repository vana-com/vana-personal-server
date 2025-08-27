#!/usr/bin/env python3
"""
Script to query real blockchain data for testing.
This will help us find real permission IDs and grantee addresses.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from web3 import AsyncWeb3
from onchain.chain import get_chain, get_contract_address
from onchain.abi import get_abi

async def query_blockchain_data():
    """Query real blockchain data for testing purposes."""
    
    # Use Moksha testnet (chain_id=14800)
    chain_id = 14800
    chain = get_chain(chain_id)
    
    print(f"🔗 Connecting to Chain {chain_id}")
    print(f"🌐 RPC URL: {chain.url}")
    
    # Connect to the blockchain
    web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(chain.url))
    
    try:
        # Check connection
        latest_block = await web3.eth.block_number
        print(f"✅ Connected! Latest block: {latest_block}")
        
        # Query DataPermissions contract
        permissions_address = get_contract_address(chain_id, "DataPermissions")
        permissions_abi = get_abi("DataPermissions")
        permissions_contract = web3.eth.contract(
            address=permissions_address, 
            abi=permissions_abi
        )
        
        print(f"\n📋 DataPermissions Contract: {permissions_address}")
        
        # Try to get permission count or query recent permissions
        try:
            # Try to call a function to get permission count
            print("🔍 Attempting to query permission count...")
            
            # Try different common function names
            possible_functions = ['permissionCount', 'totalPermissions', 'count', 'getPermissionCount']
            
            for func_name in possible_functions:
                try:
                    if hasattr(permissions_contract.functions, func_name):
                        func = getattr(permissions_contract.functions, func_name)
                        result = await func().call()
                        print(f"✅ {func_name}(): {result}")
                        break
                except Exception as e:
                    print(f"❌ {func_name}() failed: {e}")
                    continue
            
            # Try to query some recent permissions
            print("\n🔍 Querying recent permissions...")
            for permission_id in range(1, 11):  # Try first 10 permission IDs
                try:
                    permission_data = await permissions_contract.functions.permissions(permission_id).call()
                    print(f"✅ Permission {permission_id}: {permission_data}")
                    
                    # Parse the permission data
                    if len(permission_data) >= 8:
                        grantor = permission_data[1]
                        grantee_id = permission_data[3]
                        grant = permission_data[4]
                        file_ids = permission_data[7]
                        
                        print(f"   Grantor: {grantor}")
                        print(f"   Grantee ID: {grantee_id}")
                        print(f"   Grant: {grant}")
                        print(f"   File IDs: {file_ids}")
                        print()
                        
                except Exception as e:
                    print(f"❌ Permission {permission_id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Failed to query permissions: {e}")
        
        # Query DataPortabilityGrantees contract
        grantees_address = get_contract_address(chain_id, "DataPortabilityGrantees")
        grantees_abi = get_abi("DataPortabilityGrantees")
        grantees_contract = web3.eth.contract(
            address=grantees_address, 
            abi=grantees_abi
        )
        
        print(f"\n👥 DataPortabilityGrantees Contract: {grantees_address}")
        
        # Try to query some grantees
        try:
            print("🔍 Querying grantees...")
            for grantee_id in range(1, 6):  # Try first 5 grantee IDs
                try:
                    grantee_info = await grantees_contract.functions.grantees(grantee_id).call()
                    print(f"✅ Grantee {grantee_id}: {grantee_info}")
                except Exception as e:
                    print(f"❌ Grantee {grantee_id}: {e}")
                    continue
        except Exception as e:
            print(f"❌ Failed to query grantees: {e}")
            
    except Exception as e:
        print(f"❌ Failed to connect to blockchain: {e}")
    finally:
        await web3.provider.disconnect()

if __name__ == "__main__":
    asyncio.run(query_blockchain_data())
