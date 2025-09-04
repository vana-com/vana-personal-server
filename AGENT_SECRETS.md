# Agent API Keys Required

## Secrets to Add in GCP Secret Manager

For each environment (corsali-development and corsali-production), ensure these secrets exist:

### Required Secrets
- `WALLET_MNEMONIC` - Wallet mnemonic for key derivation
- `REPLICATE_API_TOKEN` - Replicate API token for LLM inference  

### Agent-Specific Secrets (Optional)
- `QWEN_API_KEY` - API key for Qwen agent
  - Only needed if using `prompt_qwen_agent` operation
  - Get from: Qwen/Alibaba Cloud console
  
- `GEMINI_API_KEY` - Google API key for Gemini agent
  - Only needed if using `prompt_gemini_agent` operation  
  - Get from: https://makersuite.google.com/app/apikey

## How to Add Secrets

### Development Environment
```bash
# Add Qwen API key
echo -n "your-qwen-api-key" | gcloud secrets create QWEN_API_KEY \
  --data-file=- \
  --project=corsali-development

# Add Gemini API key  
echo -n "your-gemini-api-key" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- \
  --project=corsali-development
```

### Production Environment
```bash
# Add Qwen API key
echo -n "your-qwen-api-key" | gcloud secrets create QWEN_API_KEY \
  --data-file=- \
  --project=corsali-production

# Add Gemini API key
echo -n "your-gemini-api-key" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- \
  --project=corsali-production
```

## Verify Secrets Exist
```bash
# Development
gcloud secrets list --project=corsali-development

# Production  
gcloud secrets list --project=corsali-production
```

## Notes
- The GitHub Actions workflow automatically injects these secrets into Cloud Run
- If secrets don't exist, the agents will fail when invoked
- You can add secrets even after deployment - Cloud Run will pick them up on next container start