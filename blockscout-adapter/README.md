# XAI Blockscout RPC Adapter

Translates EVM JSON-RPC calls to XAI blockchain API, enabling Blockscout block
explorer integration.

## Quick Start

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp config/.env.example .env
# Edit .env with your XAI node URLs

# Run locally
uvicorn src.main:app --host 0.0.0.0 --port 8545 --reload
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_PRIMARY_URL` | `http://127.0.0.1:12570` | Primary XAI sentry node |
| `XAI_FALLBACK_URL` | `http://127.0.0.1:12571` | Fallback XAI sentry node |
| `XAI_CHAIN_ID` | `1337` | Chain ID for EVM compatibility |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

## Supported RPC Methods

| Method | Description |
|--------|-------------|
| `eth_blockNumber` | Get current block height |
| `eth_getBlockByNumber` | Get block by number |
| `eth_getBlockByHash` | Get block by hash |
| `eth_getTransactionByHash` | Get transaction details |
| `eth_getTransactionReceipt` | Get transaction receipt |
| `eth_getBalance` | Get address balance |
| `eth_getTransactionCount` | Get address nonce |
| `eth_chainId` | Get chain ID |
| `eth_gasPrice` | Get gas price (mock) |
| `net_version` | Get network version |
| `web3_clientVersion` | Get client version |

## Testing

```bash
# Run tests
pytest tests/ -v

# Test RPC endpoint
curl -X POST http://localhost:8545/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

## Docker

```bash
# Build and run
docker-compose up -d

# Full stack (adapter + Blockscout)
docker-compose --profile full up -d
```

## Deployment

See `deploy/deploy.sh` for automated deployment to xai-testnet server.

```bash
# Copy to server
scp -r . xai-testnet:~/blockscout-adapter/

# SSH and deploy
ssh xai-testnet
cd ~/blockscout-adapter
./deploy/deploy.sh
```

## Architecture

```text
┌─────────────────┐
│   Blockscout    │
│    Backend      │
└────────┬────────┘
         │ JSON-RPC
┌────────▼────────┐
│   RPC Adapter   │
│   (FastAPI)     │
│   Port: 8545    │
└────────┬────────┘
         │ XAI API
┌────────▼────────┐
│   XAI Sentry    │
│     Nodes       │
└─────────────────┘
```
