# XAI Block Explorer

## Production Explorer (Blockscout)

The XAI testnet uses **Blockscout** as its production block explorer, available at:

**https://testnet-explorer.xaiblockchain.com**

### Architecture

Since XAI is a Python-based blockchain (not EVM-native), we use an **RPC Adapter** to translate XAI's native API to EVM-compatible JSON-RPC format that Blockscout understands.

```
Blockscout UI (3001) → Blockscout Backend (4000) → RPC Adapter (8545) → Sentry Nodes (12570/12571)
```

### Key Features

- **Dual Sentry Failover**: Routes to fastest healthy sentry node automatically
- **Health Monitoring**: Checks both sentry nodes every 30 seconds
- **Full Indexing**: Blocks, transactions, and addresses indexed in PostgreSQL
- **REST API v2**: Full Blockscout API available at `/api/v2/*`

### Endpoints

| Service | URL |
|---------|-----|
| Explorer UI | https://testnet-explorer.xaiblockchain.com |
| API v2 | https://testnet-explorer.xaiblockchain.com/api/v2/* |
| RPC Health | https://testnet-explorer.xaiblockchain.com/rpc-health |
| Node Status | https://testnet-explorer.xaiblockchain.com/rpc-nodes |

### Deployment

The Blockscout stack runs on xai-testnet server:
- RPC Adapter: systemd service (`xai-rpc-adapter.service`)
- Blockscout: Docker Compose (`~/blockscout-adapter/deploy/docker-compose-blockscout.yml`)

---

## Legacy Explorer (Development)

The legacy explorer (below) was used during development. It consists of a FastAPI backend and a React frontend.

### Backend

```bash
cd explorer/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

Environment variables:

- `DATABASE_URL` (default: `postgresql://xai:xai@localhost/xai_explorer`)
- `XAI_NODE_URL` (default: `http://localhost:12001`)
- `CORS_ORIGINS` (comma-separated)
- `EXPLORER_REQUIRE_API_KEY` (`true`/`false`)
- `EXPLORER_API_KEY_SECRET_PATH`
- `HOST`, `PORT`

API docs are served at `http://localhost:8000/docs`.

### Frontend

```bash
cd explorer/frontend
npm install
npm run dev
```

By default the frontend expects the backend at `http://localhost:8000`.
