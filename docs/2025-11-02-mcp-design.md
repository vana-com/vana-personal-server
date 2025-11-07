# MCP Design - Vana Personal Server

## Goal

Showcase data portability by allowing LLMs to access a user's data on the Vana network through the Personal Server and Model Context Protocol (MCP). LLMs can securely access user files stored on Vana, enabling workflows like "import my ChatGPT memories into Claude" or using personal data as context for LLMs.

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────┐
│         Vana Personal Server (Google Cloud Run)            │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Core Services (Existing)                │  │
│  │  - Authentication (signature verification)           │  │
│  │  - Grant validation (IPFS + blockchain)              │  │
│  │  - Data decryption (ECIES + OpenPGP)                 │  │
│  │  - Operations (LLM inference, agents)                │  │
│  └──────────────┬──────────────┬────────────────────────┘  │
│                 │              │                           │
│  ┌──────────────▼──────────┐  ┌▼────────────────────────┐  │
│  │   REST API (Existing)   │  │   MCP API (New)         │  │
│  │   /api/v1/*             │  │   /mcp                  │  │
│  │   - operations          │  │   - resources/list      │  │
│  │   - identity            │  │   - resources/read      │  │
│  │   - artifacts           │  │   - tools/*             │  │
│  └──────────────┬──────────┘  └──────────────┬──────────┘  │
│                 │                            │             │
└─────────────────┼────────────────────────────┼─────────────┘
                  │                            │
                  ▼                            ▼
         ┌───────────────┐              ┌──────────────┐
         │   Replicate   │              │   Subgraph   │
         │  (Hosted LLM) │              │ (Data Query) │
         └───────────────┘              └──────────────┘
```

The MCP server will be an extension of the personal server, sharing the same codebase and deployment. We’ll use [FastMCP](https://github.com/jlowin/fastmcp/), a popular Python-based MCP framework, to integrate it into the personal server. The resources and tools that the MCP exposes will be implemented by consuming onchain data via the subgraph.

## Authentication

Signature verification with static message, passed as an `Authorization` header in the MCP client config. 

1. User signs a static message in the Vana App: `"Vana Personal Server Auth Key"`  
2. Signature is a part of the MCP client config, ready to copy from the Vana App  
3. User configures their MCP client of choice (Claude Desktop, Cursor, etc) with details from \#2  
4. When user prompts “Use the vana MCP to…”  
   1. Claude Desktop as the MCP client sends signature in header: `Authorization: Bearer 0x<signature>`  
   2. Personal Server (running on the cloud or local) receives the request  
   3. Personal Server uses FastMCP's `AuthenticationMiddleware` extracts token  
   4. Personal Server recovers the wallet address recovered from signature  
   5. Personal Server performs the task (list files, fetch contents of file, etc) and response is returned to the MCP Client (Claude desktop)  
5. Claude Desktop now has context of the user’s file

**Implementation**: `mcp_server/auth_provider.py` \- inherits from FastMCP's `TokenVerifier`

### Security Tradeoffs

* Static message simplifies auth (stateless per-request validation), no nonce or timestamp component in the message, ie: **signature doesn’t expire**.  
  * Time-based signatures can prevent replay attacks, but require the user to update their MCP client config each time the signature expires  
* API token or OAuth authentication methods will require extra infrastructure, adding overhead for both local and cloud personal server deployments

## Integration with Vana App

The user-specific MCP configuration is revealed in the Vana App's Advanced Settings → MCP Configuration where it can be easily copied and imported into Claude, Gemini, Cursor, ChatGPT, or any other MCP client. 

```
{
  "mcpServers": {
    "vana-personal-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://server.vana.com/mcp",    --> or "http://localhost:8000/mcp" for local
        "--transport",
        "http-only",
        "--header",
        "Authorization: Bearer ${VANA_SIG}"
      ],
      "env": {
        "VANA_SIG": "0x<signature>"
      }
    }
  }
}
```

### User Flow

1. User navigates to Advanced Settings  
2. User clicks “Connect MCP”, signs a message, and MCP config appears  
3. User copies signature to Claude Desktop config  
4. User prompts Claude “import my ChatGPT data into my Claude memories”

## Deployment

We’ll reuse the docker image and Google Cloud Run service as the existing Personal Server. Cloud Run exposes only one port, so we’ll need to run both the REST API and MCP server on the same FastAPI instance:

* REST API: `/api/v1/*` endpoints  
* MCP: `/mcp` endpoint (mounted ASGI app)

### Implementation

1. Using FastMCP, generate MCP ASGI app: `mcp_app = mcp.http_app(path='/')`  
2. Create FastAPI with MCP lifespan: `FastAPI(lifespan=mcp_app.lifespan)`  
3. Mount MCP app: `app.mount("/mcp", mcp_app)`  
4. Single uvicorn server serves both on port 8000

## Out of Scope (Future Enhancements)

The following are deferred to keep initial scope focused:

* Permission management MCP tools (viewing/checking grants from apps)  
* LLM inference and agent execution MCP tools  
* Cross-file aggregation and analytics  
* MCP tools for advanced subgraph queries  
* MCP usage being recorded onchain