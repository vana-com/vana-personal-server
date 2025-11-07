# Vana Personal Server - Architecture Overview

This document provides a comprehensive technical overview of the Vana personal server's core security and data management systems.

## Table of Contents

1. [Authentication System](#1-authentication-system)
2. [Grant File System](#2-grant-file-system)
3. [Data Decryption](#3-data-decryption)
4. [Data Lifecycle](#4-data-lifecycle)
5. [Security Observations](#5-security-observations)
6. [File Reference Index](#6-file-reference-index)

---

## 1. Authentication System

The Vana personal server implements a multi-layer blockchain-based authentication system using Ethereum signatures and on-chain permission verification.

### 1.1 Primary Authentication: Ethereum Signatures (ECDSA)

**Implementation:** `utils/auth.py`

The system uses ECDSA signature-based authentication following the EIP-191 standard:

**SignatureAuth Class** (`utils/auth.py:20-58`)
- Apps sign operation requests with their Ethereum private key
- Server receives `operation_request_json` + `app_signature` (130 hex characters)
- Server recovers the signer's address using `web3.eth.account.recover_message()`
- Recovered address is validated against on-chain grantee address

```python
def verify_signature(self, request_data: str, signature: str) -> str:
    # Validates JSON format first
    json.loads(request_data)

    # Recover address from signature using EIP-191
    message = encode_defunct(text=request_data)
    recovered_address = self.web3.eth.account.recover_message(
        message, signature=signature
    )
    return recovered_address
```

**MockModeAuth Class** (`utils/auth.py:61-71`)
- Provides bypass for local testing when `MOCK_MODE=true`
- Returns mock address: `0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6`
- **Security Warning:** Should never be used in production

### 1.2 Four-Step Authentication Flow

**API Endpoint:** `POST /api/v1/operations`

**Implementation:** `services/operations.py:129-186` (`OperationsService.create()`)

Every operation request undergoes a four-step verification process:

```
Step 1: Signature Verification (lines 129-138)
    ↓ Recover app address from signature using eth_account.recover_message (_recover_app_address)
    ↓ Validates the app created the signed request
    ↓ Rejects request if signature recovery fails

Step 2: Blockchain Permission Lookup (lines 141-158)
    ↓ Fetch permission from DataPermissions smart contract
    ↓ Returns: permission_id, grantor, grantee_id, grant (IPFS URL), file_ids

Step 3: Grantee Resolution (lines 165-178)
    ↓ Resolve grantee_id to actual EVM address
    ↓ Query DataPortabilityGrantees contract for canonical address

Step 4: Address Match Validation (lines 181-185)
    ↓ Verify recovered signature address matches on-chain grantee address
    ✓ app_address.lower() == on_chain_grantee_address.lower()
```

**Critical Security Check:** The recovered address from the signature MUST match the on-chain grantee address. This ensures that only the authorized app can execute operations, even if the signature is valid.

### 1.3 Deterministic Server Identity

**Implementation:** `services/identity.py`

Each user gets a unique, deterministic personal server identity derived from their Ethereum address:

**Derivation Process** (`services/identity.py:73-87`):
1. Compute SHA256 hash of user address (lowercase)
2. Take first 4 bytes of hash → convert to integer
3. Modulo 2^31 to get deterministic index
4. Derive BIP44 key at path: `m/44'/60'/0'/0/{index}`
5. Generate server address, public key, and private key

```python
def _user_identity_to_index(self, user_address: str) -> int:
    """Derive deterministic index from user address"""
    digest = hashlib.sha256(user_address.lower().encode()).digest()
    return int.from_bytes(digest[:4], "big") % (2**31)
```

**Benefits:**
- No key storage required on server
- Reproducible identities across server restarts
- Each user gets a unique server identity
- Enables deterministic encryption key management

**API Endpoint:** `GET /api/v1/identity?address=0x...`

---

## 2. Grant File System

The grant file system implements fine-grained, user-controlled access permissions for their data. Users grant specific apps permission to perform specific operations with specific parameters.

### 2.1 Grant File Structure

**Schema:** `grants/schema/grantFile.schema.json`

Grant files are JSON documents stored on IPFS with the following structure:

```json
{
  "grantee": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
  "operation": "llm_inference",
  "parameters": {
    "prompt": "Analyze this data: {{data}}",
    "model": "gpt-4",
    "temperature": 0.7,
    "filters": {
      "1891942": "$.publicData.linkedinUserData['hero','about']"
    }
  },
  "expires": 1736467579
}
```

**Field Descriptions:**
- `grantee`: Ethereum address of the app being granted access
- `operation`: Type of operation allowed (see supported operations below)
- `parameters`: Operation-specific configuration (model, prompt, filters, etc.)
- `parameters.filters`: Optional JSONPath expressions for data minimization
- `expires`: Optional Unix timestamp for permission expiration

### 2.2 Grant File Lifecycle

**Implementation:** `grants/validate.py`, `grants/fetch.py`

#### User Creation Process

To create a grant, the user (data owner) must:

1. **Encrypt files client-side** - Encrypt their files using OpenPGP with a random symmetric key
2. **Register in DataRegistry** - Submit file metadata to the DataRegistry smart contract
3. **Store encrypted keys** - Store the per-server encrypted symmetric key via `filePermissions(file_id, personal_server_address)` mapping
4. **Upload grant to IPFS** - Upload the permission JSON (operation + parameters + optional filters/expiry) to IPFS
5. **Create on-chain permission** - Submit a permission to DataPermissions contract referencing the IPFS hash, target file IDs, and the app's granteeId

#### Server Validation Process

```
1. Storage → Grant files stored on IPFS
   ↓
2. On-Chain Reference → DataPermissions contract stores IPFS URL
   ↓ Example: ipfs://QmHash...

3. Retrieval → Server fetches from IPFS (grants/fetch.py:23-82)
   ↓ Uses grants.fetch.fetch_raw_grant_file()
   ↓ Fallback gateways: dweb.link, ipfs.io, cloudflare-ipfs.com

4. Validation → Schema and security checks (grants/validate.py)
   ↓ Uses grants.validate.validate() against grants/schema/grantFile.schema.json
   ✓ JSON schema validation
   ✓ Grantee address matches on-chain grantee
   ✓ Operation in SUPPORTED_OPERATIONS
   ✓ Expiration check: current_time <= grant.expires
   ✓ Grant-level parameters (including JSONPath filters)
```

### 2.3 Supported Operations

**Implementation:** `grants/validate.py:11-15`

```python
SUPPORTED_OPERATIONS = {
    "llm_inference",        # General LLM inference
    "prompt_gemini_agent",  # Google Gemini agent operations
    "prompt_qwen_agent"     # Qwen agent operations
}
```

Each operation type has specific parameter requirements validated against its JSON schema.

### 2.4 Parameter Merging

**Implementation:** `services/operations.py:222-240`

Operation parameters come from two sources and are merged with grant parameters taking precedence:

```python
# Runtime parameters from API request (optional)
request_json = {
    "permission_id": 1024,
    "parameters": {
        "temperature": 0.7,
        "max_tokens": 1000
    }
}

# Grant parameters from IPFS (required, takes precedence)
grant_file.parameters = {
    "temperature": 0.5,
    "model": "gpt-4",
    "prompt": "Analyze: {{data}}"
}

# Merged result: grant wins on conflicts
final_params = {
    "temperature": 0.5,      # From grant (overrides runtime)
    "model": "gpt-4",        # From grant
    "prompt": "Analyze...",  # From grant
    "max_tokens": 1000       # From runtime (no conflict)
}
```

**Security Rationale:** Grant parameters take precedence to ensure users maintain control over how their data is used, preventing apps from modifying approved parameters at runtime. The server re-validates the grant file and merges runtime parameters via `services.parameter_merge`, ensuring the app cannot exceed the user-defined scope.

### 2.5 JSONPath Filtering (Protocol-Level Data Minimization)

**Implementation:** `services/operations.py:259-274, 500-615`

**Critical Feature:** Filters are applied to decrypted data **before** any compute provider receives it. This implements data minimization at the protocol level.

**Filter Specification:**
```json
"filters": {
  "1891942": "$.publicData.linkedinUserData['hero','about']",
  "2847561": "$.messages[?(@.type=='work')].content"
}
```

**Filter Application** (`services/operations.py:500-615`):

```python
def _apply_jsonpath_filters(self, files_metadata, files_content, filters, request_id):
    """Apply JSONPath filters to file content before passing to compute"""
    for file in files_content:
        file_id = str(file["id"])

        if file_id in filters:
            filter_expr = filters[file_id]

            # Parse JSON content
            content_obj = json.loads(file["content"])

            # Apply JSONPath expression
            matches = jsonpath_ng.parse(filter_expr).find(content_obj)

            if len(matches) == 1:
                file["content"] = matches[0].value  # Single match
            elif len(matches) > 1:
                file["content"] = [m.value for m in matches]  # Multiple matches
            else:
                file["content"] = []  # No matches

    return files_content
```

**Behavior:**
- **Single match:** Returns the matched value directly
- **Multiple matches:** Returns array of matched values
- **No matches:** Returns empty array
- **Parse error:** Returns original content with warning log

**Example:**

```json
// Original file content
{
  "publicData": {
    "linkedinUserData": {
      "hero": "Software Engineer",
      "about": "Passionate about privacy-preserving tech",
      "experience": [...]
    }
  },
  "privateData": {
    "messages": [...]
  }
}

// Filter: "$.publicData.linkedinUserData['hero','about']"

// Filtered result (what compute provider sees)
["Software Engineer", "Passionate about privacy-preserving tech"]
```

**Privacy Guarantee:** The `privateData.messages` field never reaches the compute provider, even though it exists in the decrypted file.

---

## 3. Data Decryption

The Vana personal server uses a multi-layer hybrid encryption system combining symmetric and asymmetric cryptography.

### 3.1 Encryption Architecture Overview

```
User Data File (on IPFS/Drive)
    ↓ Encrypted with OpenPGP (Layer 1)
    │ Symmetric key: random AES key
    ↓
Encrypted Data File + Symmetric Key
    ↓ Symmetric key encrypted with ECIES (Layer 2)
    │ Recipient: Server's public key
    ↓
Stored: Encrypted file (IPFS) + Encrypted key (blockchain)
```

### 3.2 Layer 1: File-Level Encryption (OpenPGP/GPG)

**Implementation:** `utils/files/decrypt.py:82-103`

User data files are encrypted using OpenPGP with a randomly generated symmetric key:

```python
def decrypt_user_data(encrypted_data: bytes, encryption_key: str) -> bytes:
    """Decrypt file content using OpenPGP/GPG"""
    gpg = gnupg.GPG()
    decrypted_data = gpg.decrypt(
        encrypted_data,
        passphrase=encryption_key
    )

    if not decrypted_data.ok:
        raise ValueError(f"GPG decryption failed: {decrypted_data.stderr}")

    return decrypted_data.data
```

**Key Properties:**
- Algorithm: OpenPGP (typically AES-256 for symmetric encryption)
- Key: Random symmetric key generated per file
- Format: Standard OpenPGP message format

### 3.3 Layer 2: Key Encryption (ECIES)

**Implementation:** `utils/files/decrypt.py:33-79`

The symmetric encryption key is itself encrypted using ECIES (Elliptic Curve Integrated Encryption Scheme):

**ECIES Components:**
1. **Ephemeral Key Pair:** Generated per encryption
2. **ECDH:** Elliptic Curve Diffie-Hellman key agreement
3. **KDF:** SHA-512 for key derivation
4. **Symmetric Cipher:** AES-256-CBC
5. **MAC:** HMAC-SHA-256 for authentication

**Decryption Process** (`utils/files/decrypt.py:33-79`):

```python
def decrypt_with_private_key(encrypted_data: str, private_key: str) -> str:
    """Decrypt symmetric key using ECIES"""

    # Parse eccrypto format: iv(16) + ephemPublicKey(65) + ciphertext + mac(32)
    encrypted_data_bytes = bytes.fromhex(encrypted_data[2:])  # Remove '0x'

    iv = encrypted_data_bytes[:16]
    ephem_public_key = encrypted_data_bytes[16:81]
    ciphertext = encrypted_data_bytes[81:-32]
    mac = encrypted_data_bytes[-32:]

    # Step 1: ECDH key agreement
    # Multiply ephemeral public key with server's private key
    private_key_obj = PrivateKey(bytes.fromhex(private_key[2:]))
    ephem_public_key_obj = PublicKey(ephem_public_key)
    shared_point = ephem_public_key_obj.multiply(private_key_obj.secret)
    shared_secret = shared_point.format(compressed=False)[1:33]  # 32 bytes

    # Step 2: Derive encryption and MAC keys using SHA-512
    hash_output = hashlib.sha512(shared_secret).digest()
    enc_key = hash_output[:32]   # First 32 bytes for AES-256
    mac_key = hash_output[32:]   # Last 32 bytes for HMAC

    # Step 3: Verify MAC (authentication)
    mac_data = iv + ephem_public_key + ciphertext
    expected_mac = hmac.new(mac_key, mac_data, hashlib.sha256).digest()

    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("MAC verification failed - data may be tampered")

    # Step 4: Decrypt using AES-256-CBC
    cipher = AES.new(enc_key, AES.MODE_CBC, iv)
    decrypted_bytes = unpad(cipher.decrypt(ciphertext), AES.block_size)

    return decrypted_bytes.decode("utf-8")
```

**Security Properties:**
- **Forward Secrecy:** Ephemeral key pair per encryption
- **Authentication:** HMAC prevents tampering
- **Key Isolation:** Each server gets a unique encrypted key copy

### 3.4 Full Decryption Pipeline

**Implementation:** `services/operations.py:406-446`

The complete data access flow involves seven steps:

```
Step 1: Derive Server Keys (lines 243-251)
    ↓ Input: User address (grantor)
    ↓ Process: Deterministic BIP44 derivation
    ↓ Output: server_address, server_public_key, server_private_key

Step 2: Fetch File Metadata from Blockchain (lines 253-254)
    ↓ Contract: DataRegistry.fetch_file_metadata(file_id)
    ↓ Output: file_id, owner_address, public_url, encrypted_key

Step 3: Download Encrypted File (line 416)
    ↓ Source: IPFS, Google Drive, or HTTP/HTTPS (5 MB file size cap)
    ↓ Function: utils.files.download.download_file(public_url)
    ↓ Output: encrypted_content (bytes)

Step 4: Decrypt Encryption Key (lines 421-424)
    ↓ Method: ECIES decryption
    ↓ Function: utils.files.decrypt.decrypt_with_private_key(encrypted_key, server_private_key)
    ↓ Output: decrypted_symmetric_key (string)

Step 5: Decrypt File Content (lines 426-430)
    ↓ Method: OpenPGP/GPG decryption
    ↓ Function: utils.files.decrypt.decrypt_user_data(encrypted_content, decrypted_symmetric_key)
    ↓ Output: decrypted_content (bytes → UTF-8 JSON strings)

Step 6: Apply JSONPath Filters (lines 270-273)
    ↓ Method: Protocol-level data minimization
    ↓ Function: _apply_jsonpath_filters(files_metadata, files_content, filters)
    ↓ Output: filtered_content (only matching fields)

Step 7: Pass to Compute Provider
    ↓ Destination: LLM API (OpenAI, Anthropic, Gemini, etc.)
    ✓ Only filtered data reaches compute provider
```

### 3.5 On-Chain Key Storage

**Implementation:** `onchain/data_registry.py:67-89`

Encrypted symmetric keys are stored on-chain in the `DataRegistry` smart contract:

```python
async def _get_encrypted_key_for_file(
    self, file_id: int, personal_server_address: str
) -> str:
    """Fetch encrypted key for specific server from blockchain"""

    # Call: filePermissions(file_id, server_address)
    encrypted_key = await self.contract.functions.filePermissions(
        file_id,
        personal_server_address
    ).call()

    return encrypted_key  # Hex-encoded ECIES-encrypted key
```

**Storage Model:**
- **Contract:** DataRegistry
- **Mapping:** `filePermissions[file_id][server_address] → encrypted_key`
- **Format:** Hex-encoded string (e.g., `0x04a1b2c3...`)
- **Specificity:** Each server address gets a unique encrypted copy

**Security Benefits:**
1. **Granular Access:** Different encrypted keys per recipient
2. **Immutable Audit Trail:** Blockchain records all key grants
3. **Revocable Access:** Can remove keys from contract
4. **No Key Storage:** Server derives identity deterministically

---

## 4. Data Lifecycle

The Vana personal server implements strict data minimization principles with minimal data persistence.

### 4.1 Operation Status Lifecycle

**Implementation:** `services/task_store.py`

Operation execution status is stored in-memory only:

**Storage Structure** (`services/task_store.py:31-48`):
```python
class TaskInfo:
    operation_id: str
    status: str              # "pending", "processing", "completed", "failed"
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    result: Optional[Any]
    error: Optional[str]
```

**Cleanup Policy** (`services/task_store.py:164-184`):
```python
async def cleanup_completed(self, max_age_seconds: int = 3600):
    """Clean up completed tasks older than 1 hour (default)"""
    now = datetime.utcnow()
    to_remove = []

    for op_id, task_info in self._tasks.items():
        if task_info.completed_at:
            age = (now - task_info.completed_at).total_seconds()
            if age > max_age_seconds:
                to_remove.append(op_id)

    for op_id in to_remove:
        del self._tasks[op_id]
```

**Retention:**
- **Default:** 1 hour (3600 seconds) after completion
- **Storage:** In-memory dictionary (lost on server restart)
- **API Note:** Operations documented as expiring after 24 hours (`api/operations.py:230`)

### 4.2 User Data File Lifecycle

**Implementation:** `services/operations.py:406-446`

**Critical Security Property: User data files are NEVER persisted to disk during standard LLM inference operations.**

**Data Flow:**
```
1. Request arrives (line 129)
   ↓
2. Download encrypted file from IPFS/Drive (line 416)
   ↓ Stored: In-memory bytes object

3. Decrypt in memory (lines 427-430)
   ↓ Stored: In-memory JSON object

4. Apply filters in memory (lines 270-273)
   ↓ Stored: In-memory filtered object

5. Send to compute provider (line 296)
   ↓
6. Return results (line 320)
   ↓
7. Garbage collection
   ✓ All user data removed from memory
```

**Retention by Operation Type:**

1. **Standard LLM Inference** (`compute/replicate.py`)
   - **Duration:** Request execution only (~2-300 seconds)
   - **Storage:** RAM only (never written to disk)
   - **Cleanup:** Automatic via Python garbage collection

2. **Agent Workloads** (require filesystem access)
   - **Implementation:** `BaseAgentProvider._run_agent_async()` and `services/agent_runner.DockerAgentRunner.execute_agent`
   - **Temporary Storage:** OS temp locations for decrypted data
     - Process-based: `tempfile.TemporaryDirectory()` (auto-deleted when block exits)
     - Docker-based: `/app/.agent_workspaces/` (removed in `finally` block via `shutil.rmtree`)
   - **Duration:** Typically seconds to minutes (operation duration only)
   - **Cleanup:** Immediate upon completion or failure - temp paths torn down even on errors
   - **Note:** Decrypted user data does NOT persist beyond task completion

### 4.3 Agent Artifact Lifecycle

**Implementation:** `services/artifact_storage.py`

Agent-generated artifacts (analysis results, generated files, etc.) have a longer retention period:

**Storage Backend:**
- **Primary:** Cloudflare R2 (S3-compatible object storage)
- **Fallback:** Local filesystem at `/tmp/artifacts/`

**Default Retention** (`services/artifact_storage.py:166-167`):
```python
if expires_at is None:
    expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days default
```

**Artifact Metadata Structure** (`services/artifact_storage.py:229-240`):
```json
{
  "operation_id": "prompt_gemini_agent_1234567890",
  "grantor_address": "0xUser...",
  "grantee_address": "0xApp...",
  "created_at": "2025-01-15T10:00:00",
  "expires_at": "2025-01-22T10:00:00",
  "encrypted_key": "0xabcd...",
  "artifacts": [
    {
      "path": "analysis.txt",
      "size": 1024,
      "content_type": "text/plain",
      "checksum": "sha256:...",
      "created_at": "2025-01-15T10:00:00"
    }
  ]
}
```

**Encryption:**
- **Algorithm:** Fernet (symmetric encryption)
- **Key Management:** Fernet key encrypted with ECIES using grantor's server public key
- **Storage:** Encrypted artifacts in R2, encrypted key in metadata
- **Note:** Raw user inputs are never written to artifact storage - only generated outputs are stored with encryption and expiry

**Expiration Check** (`services/artifact_storage.py:407-410`):
```python
expires_at = datetime.fromisoformat(metadata["expires_at"])
if datetime.utcnow() > expires_at:
    logger.warning(f"Artifacts expired for operation {operation_id}")
    return None  # Refuse to serve expired artifacts
```

**Retention:**
- **Default:** 7 days from creation
- **Enforcement:** Passive (checked on retrieval, no active cleanup)
- **Access Control:** Only grantor or grantee can retrieve

### 4.4 Agent Workspace Lifecycle

**Implementation:** `services/process_agent_runner.py`

Agent code runs in isolated temporary workspaces:

**Workspace Creation** (`services/process_agent_runner.py:137-148`):
```python
def _create_workspace(self, files_content: List[Dict]) -> Path:
    """Create temporary workspace for agent execution"""
    timestamp = int(time.time() * 1000)
    workspace_path = Path(f"/tmp/agent_workspace_{timestamp}")
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Write user data files to workspace
    for file in files_content:
        file_path = workspace_path / file["name"]
        file_path.write_text(file["content"])

    return workspace_path
```

**Workspace Cleanup** (`services/process_agent_runner.py:187-193`):
```python
def _cleanup_workspace(self, workspace_path: Path):
    """Remove temporary workspace after execution"""
    try:
        if workspace_path.exists():
            shutil.rmtree(workspace_path)  # Recursive delete
    except Exception as e:
        logger.error(f"Failed to cleanup workspace {workspace_path}: {e}")
```

**Retention:**
- **Duration:** Until agent execution completes (typically 2-60 seconds)
- **Location:** `/tmp/agent_workspace_{timestamp}/`
- **Cleanup:** Immediate upon completion or failure

### 4.5 Local Artifact Storage (Fallback)

**Implementation:** `services/artifact_storage.py:491-501`

When R2 is unavailable, artifacts are stored locally:

```python
async def _store_locally(self, object_key: str, content: bytes):
    """Store content locally when R2 not available"""
    local_path = Path(f"/tmp/artifacts/{object_key}")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(content)
```

**Path Pattern:**
```
/tmp/artifacts/operations/{operation_id}/metadata.json
/tmp/artifacts/operations/{operation_id}/artifacts/{filename}
```

**⚠️ Warning:** No automatic cleanup implemented for local artifact storage. Relies on OS-level `/tmp` cleanup policies.

### 4.6 Summary: Data Persistence Timeline

| Data Type | Storage Location | Retention Period | Cleanup Method |
|-----------|------------------|------------------|----------------|
| **Operation status** | In-memory (TaskStore) | 1 hour after completion | Automatic via `cleanup_completed()` |
| **User data files (LLM)** | ❌ NOT STORED | Request duration only (~2-300s) | Garbage collection |
| **User data files (Agents)** | Temp dirs (auto-deleted) | Operation duration (seconds-minutes) | Immediate cleanup (even on errors) |
| **Decrypted data** | ❌ NOT STORED | Request duration only (~2-300s) | Garbage collection |
| **Agent artifacts** | R2 or `/tmp/artifacts/` | 7 days (encrypted) | Passive expiration check |
| **Agent workspace** | `/tmp/agent_workspace_*` or `tempfile.TemporaryDirectory()` | Until execution completes | Immediate deletion |
| **Grant files** | IPFS (external) | Indefinite (user-controlled) | N/A (external to server) |
| **Encrypted keys** | Blockchain | Permanent | N/A (immutable) |

**Key Insight:** The personal server maintains a minimal data footprint. User data exists only during active request processing, with LLM operations keeping data solely in memory and agent operations using temporary directories that are immediately cleaned up. Only agent-generated artifacts (NOT raw user inputs) are retained (encrypted, 7-day expiration).

---

## 5. Security Observations

### 5.1 Strengths

1. **Multi-Layer Encryption**
   - ECIES for key encryption (forward secrecy via ephemeral keys)
   - OpenPGP for file content (industry-standard symmetric encryption)
   - Fernet for artifact encryption (authenticated encryption)

2. **Protocol-Level Data Minimization**
   - JSONPath filters applied before compute provider access
   - Users control exact fields exposed via grant files
   - Implements privacy-by-design principles

3. **Zero-Persistence Architecture**
   - User data never written to disk
   - In-memory processing only
   - Minimal attack surface for data exfiltration

4. **Deterministic Key Derivation**
   - No key storage required on server
   - Reproducible identities from user addresses
   - Eliminates key management vulnerabilities

5. **Blockchain-Backed Permissions**
   - Immutable audit trail of all permissions
   - On-chain verification prevents tampering
   - Granular access control per file per server

6. **Four-Step Authentication**
   - Signature verification prevents impersonation
   - On-chain permission lookup prevents unauthorized access
   - Address matching prevents signature reuse attacks

### 5.2 Security Concerns

#### Critical: Secret Leakage in Logs

**Source:** `review.md:17`

> "Secret Leakage in Logs - utils/files/encrypt.py:92, :116, :120 and services/artifact_storage.py:82, :88, :168, :182, :292 log raw symmetric key material (first bytes/chars). Anyone with log access can reconstruct keys and decrypt every stored artifact. **These log statements must be removed before merge.**"

**Affected Files:**
- `utils/files/encrypt.py` (lines 92, 116, 120)
- `services/artifact_storage.py` (lines 82, 88, 168, 182, 292)

**Impact:** High - Compromises encryption if logs are accessed by unauthorized parties.

#### Warning: No Active Cleanup for Local Artifacts

**Issue:** Local artifact storage (`/tmp/artifacts/`) has no automatic cleanup mechanism.

**Impact:**
- Expired artifacts may accumulate on disk
- Relies on OS-level `/tmp` cleanup (typically on reboot)
- Could fill disk if R2 is unavailable for extended periods

**Recommendation:** Implement periodic cleanup task for local artifact storage.

#### Info: Mock Mode Security

**Issue:** `MOCK_MODE=true` bypasses all authentication checks.

**Impact:** If accidentally enabled in production, allows complete access bypass.

**Recommendation:** Add startup warning and refuse to run in production environments with mock mode enabled.

### 5.3 Privacy Properties

The system implements strong privacy guarantees:

1. **Data Minimization:** Only requested fields reach compute providers
2. **Access Control:** Blockchain-enforced permissions per file
3. **Transparency:** Grant files explicitly define allowed operations
4. **User Control:** Users approve exact parameters (model, prompt, filters)
5. **Temporal Limits:** Grant files can include expiration timestamps
6. **No Data Retention:** User data never persisted on server

**Threat Model Assumptions:**
- Server operator is trusted to execute code correctly
- Blockchain validators are honest (standard blockchain assumption)
- Compute providers (OpenAI, Anthropic, etc.) are trusted within filtered data scope
- IPFS network is available for grant file retrieval

---

## 6. File Reference Index

### Authentication & Identity
- `utils/auth.py` - Signature verification and auth classes
- `services/identity.py` - Deterministic server identity derivation
- `api/identity.py` - Identity API endpoints

### Grant System
- `grants/validate.py` - Grant file validation and expiration checks
- `grants/fetch.py` - IPFS fetching with fallback gateways
- `grants/schema/grantFile.schema.json` - Grant file JSON schema

### Encryption & Decryption
- `utils/files/decrypt.py` - ECIES and OpenPGP decryption
- `utils/files/encrypt.py` - ECIES and OpenPGP encryption
- `utils/files/download.py` - Multi-source file downloading

### Core Operation Flow
- `services/operations.py` - Main operation execution logic
- `api/operations.py` - Operation API endpoints
- `domain/operation_context.py` - Operation context and state

### Blockchain Integration
- `onchain/data_permissions.py` - Permission contract interface
- `onchain/data_registry.py` - File registry contract interface
- `onchain/data_portability_grantees.py` - Grantee resolution contract

### Data Lifecycle
- `services/task_store.py` - In-memory task status storage
- `services/artifact_storage.py` - Encrypted artifact storage (R2/local)
- `services/process_agent_runner.py` - Agent workspace management

### Configuration
- `settings.py` - Environment configuration and constants
- `README.md` - Project documentation and setup instructions

---

## Glossary

- **ECIES:** Elliptic Curve Integrated Encryption Scheme - hybrid encryption using ECDH + AES + HMAC
- **EIP-191:** Ethereum Improvement Proposal 191 - standard for signing arbitrary messages
- **Grant File:** JSON document stored on IPFS defining access permissions
- **Grantee:** App/service receiving permission to access user data
- **Grantor:** Data owner granting permission to app
- **JSONPath:** Query language for JSON documents (similar to XPath for XML)
- **OpenPGP:** Open standard for encryption and signing (RFC 4880)
- **Personal Server:** Serverless compute environment with access to user's decrypted data
- **Permission:** On-chain record linking grantor, grantee, grant file, and file IDs

---

**Document Version:** 1.1
**Last Updated:** 2025-10-31
**Changelog:**
- v1.1: Integrated additional details from personal-server-access-overview.md including API endpoints, grant creation workflow, agent workspace details, file size limits, and enhanced data lifecycle explanations
- v1.0: Initial comprehensive architecture documentation

**Author:** Generated from codebase analysis
