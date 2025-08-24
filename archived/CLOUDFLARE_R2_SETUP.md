# Cloudflare R2 Setup for Artifact Storage

## 🚀 **Quick Setup (5 minutes)**

### **1. Create R2 Storage**

1. Log into Cloudflare Dashboard
2. Go to **R2 Object Storage** → **Create bucket**
3. Name: `personal-server-artifacts` (or any name you prefer)
4. Location: **Automatic** (recommended)
5. Click **Create bucket**

### **2. Generate API Token**

1. In Cloudflare Dashboard → **R2** → **Manage R2 API tokens**
2. Click **Create API token**
3. **Token name**: `personal-server-artifacts`
4. **Permissions**: 
   - ✅ **Object Read & Write**
   - ✅ **Bucket Read** (for bucket operations)
5. **TTL**: No expiration (or set as needed)
6. Click **Create API token**
7. **Copy the token details** (you'll need them for .env)

### **3. Get Account ID**

1. In Cloudflare Dashboard → Right sidebar → **Account ID**
2. Copy the Account ID

### **4. Update .env File**

Add these lines to your `.env` file:

```bash
# Cloudflare R2 Configuration
R2_ACCOUNT_ID=your_account_id_here
R2_ACCESS_KEY_ID=your_access_key_id_here
R2_SECRET_ACCESS_KEY=your_secret_access_key_here
R2_BUCKET_NAME=personal-server-artifacts
```

### **5. Test the Setup**

```bash
# Rebuild and restart
make down
make build
make up

# Test artifact storage
python3 test_personal_data.py
```

## 📊 **What You Get**

### **Free Tier Benefits**
- **10 GB** storage free
- **1 million** Class A operations (uploads)
- **10 million** Class B operations (downloads)
- **No egress fees** (unlike S3!)

### **Features**
- ✅ **Encrypted artifacts** (client-side encryption)
- ✅ **Access control** (only original grantee can access)
- ✅ **Automatic expiration** (7 days default)
- ✅ **Local fallback** (works without R2 configured)
- ✅ **S3-compatible API** (easy migration)

## 🔧 **How It Works**

### **Storage Flow**
```
Agent creates files → Encrypt with unique key → Upload to R2 → Store metadata
```

### **Access Flow**
```
Client requests artifact → Verify access → Download from R2 → Decrypt → Return
```

### **Security Model**
- Each operation gets a **unique encryption key**
- Artifacts encrypted **before** upload to R2
- Only **original grantee** can access artifacts
- Keys stored encrypted in metadata
- **Automatic cleanup** after expiration

## 📁 **Bucket Structure**

```
personal-server-artifacts/
└── operations/
    ├── gemini_1755985390841/
    │   ├── metadata.json           # Operation metadata (encrypted keys)
    │   └── artifacts/
    │       ├── privacy_audit.md    # Encrypted artifact
    │       └── recommendations.txt # Encrypted artifact
    └── qwen_1755985405123/
        ├── metadata.json
        └── artifacts/
            └── knowledge_base.py
```

## 🔍 **Testing Without R2**

If R2 isn't configured, the system automatically falls back to local storage in `/tmp/artifacts/`. This is perfect for development but artifacts won't persist across container restarts.

## 💰 **Cost Estimation**

**Typical Usage:**
- 100 operations/month
- 2 artifacts per operation (5MB each)
- 7-day retention

**Monthly Cost:**
- Storage: 1GB × $0.015 = **$0.015**
- Operations: 200 uploads × $4.50/million = **$0.001**
- **Total: ~$0.02/month** 🎉

Compare to S3: ~$0.10/month (5x more expensive due to egress fees)

## 🛡️ **Security Best Practices**

### **API Token Security**
- Use **minimum required permissions**
- Set **appropriate TTL** (not forever)
- **Rotate tokens** periodically
- Store in **environment variables** (never in code)

### **Bucket Security**
- Enable **bucket notifications** for monitoring
- Set up **lifecycle policies** for cleanup
- Use **CORS policies** if needed for web access
- Monitor **access patterns** for anomalies

## 📈 **Monitoring**

### **Key Metrics to Watch**
- Storage usage (approaching free tier limit)
- Request patterns (unusual access)
- Error rates (authentication failures)
- Cost trends (monthly spend)

### **Cloudflare Analytics**
1. Go to **R2** → **Your bucket** → **Analytics**
2. Monitor:
   - Requests over time
   - Storage usage
   - Bandwidth (should be minimal due to encryption)

## 🚨 **Troubleshooting**

### **"Access Denied" Errors**
- Check API token has correct permissions
- Verify account ID is correct
- Ensure bucket name matches exactly

### **"Bucket Not Found" Errors**
- Verify bucket name in R2_BUCKET_NAME
- Check bucket exists in correct account
- Ensure region is set to 'auto'

### **Connection Errors**
- Check account ID format
- Verify endpoint URL format
- Test connectivity to Cloudflare

### **Performance Issues**
- Monitor request rates (throttling)
- Check artifact sizes (large files slower)
- Verify network connectivity

## 🔄 **Migration Path**

**Current**: In-memory artifact storage
**Step 1**: Hybrid (R2 + memory fallback)
**Step 2**: R2-only with proper cleanup
**Step 3**: Advanced features (CDN, analytics, etc.)

The implementation is designed for **zero-downtime migration** - it works with or without R2 configured!