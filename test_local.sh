#!/bin/bash

# Test the operations endpoint locally
curl -X POST http://localhost:8001/api/v1/operations \
  -H "Content-Type: application/json" \
  -d '{
    "app_signature": "0xb4bc4c5364ea0a01a4fd1ab0dde406798c54c1583049c70522c57cb0a5d4733d542d2a467b99a1f30ebd74edec75f55e5597e7481cd60dea1574440c8c286c071c",
    "operation_request_json": "{\"permission_id\":47}"
  }'