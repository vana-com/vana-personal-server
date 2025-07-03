# Personal Server

Personal server for data portability. 

## Deploy to Replicate

### Prerequisites
- Replicate account and API token
- Python 3.8+ installed locally

### Steps

1. **Install Replicate CLI**
   ```bash
   pip install cog
   ```

2. **Login to Replicate**
   ```bash
   cog login
   ```

4. **Deploy the model**
   ```bash
   cog push r8.im/vana-com/personal-server
   ```
5. **Test the deployment**
   Note: `DataRegistry` contains stubbed url and encryption key before we start getting them from the blockchain

   ```bash
   cd /benchmarks && python replicate_client.py
   ```

   ```bash
   curl -X POST "https://api.replicate.com/v1/predictions" \
  -H "Authorization: Token r8_..." \
  -H "Content-Type: application/json" \
  -d '{
    "version": "vana-com/personal-server:19274a078cad175d8c8712a4b6f46e9baa0b56686b28b6d8fc965f813327cc4e",
    "input": {
      "replicate_api_token": "r8_...",
      "signature": "309d2e8a267ec9347ecd7a8878a87f95bb1be8cc6d3e096764111291756b9e6c0ac7631ea5bc970aa2127fcc5a6fa8a979652e6403c8b550fcd3bcd7e7e148d11c",
      "request_json": "{\"user_address\": \"0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4\", \"file_ids\": [999], \"operation\": \"llm_inference\", \"parameters\": {\"prompt\": \"Analyze personality: {{data}}\"}}"
    }
  }'
  ```
