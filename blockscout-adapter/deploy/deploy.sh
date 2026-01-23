#!/bin/bash
# XAI Blockscout Deployment Script
# Run on xai-testnet server

set -e

echo "=== XAI Blockscout Deployment ==="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
ADAPTER_DIR="/home/ubuntu/blockscout-adapter"
BLOCKSCOUT_DIR="/home/ubuntu/blockscout"
FRONTEND_DIR="/home/ubuntu/blockscout-frontend"

# Step 1: Deploy RPC Adapter
echo -e "${GREEN}[1/5] Deploying RPC Adapter...${NC}"

# Create directory
mkdir -p "$ADAPTER_DIR"

# Check if files exist (assume they were copied via scp)
if [ ! -f "$ADAPTER_DIR/src/main.py" ]; then
    echo -e "${YELLOW}Please copy adapter files first:${NC}"
    echo "  scp -r ~/blockchain-projects/xai-explorer/blockscout-adapter/* xai-testnet:~/blockscout-adapter/"
    exit 1
fi

# Create virtual environment
cd "$ADAPTER_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install systemd service
sudo cp deploy/xai-rpc-adapter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable xai-rpc-adapter
sudo systemctl restart xai-rpc-adapter

echo "RPC Adapter deployed. Checking health..."
sleep 3
curl -s http://127.0.0.1:8545/health | jq .

# Step 2: Install Prerequisites
echo -e "${GREEN}[2/5] Installing prerequisites...${NC}"

sudo apt-get update
sudo apt-get install -y \
    erlang \
    elixir \
    postgresql \
    postgresql-contrib \
    nodejs \
    npm \
    git \
    make \
    gcc \
    g++ \
    libtool \
    automake \
    autoconf \
    certbot \
    python3-certbot-nginx

# Step 3: Setup PostgreSQL
echo -e "${GREEN}[3/5] Setting up PostgreSQL...${NC}"

# Create database (may fail if already exists)
sudo -u postgres psql -c "CREATE USER blockscout WITH PASSWORD 'blockscout_xai_$(openssl rand -hex 8)';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE blockscout OWNER blockscout;" 2>/dev/null || true
sudo -u postgres psql -d blockscout -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" 2>/dev/null || true
sudo -u postgres psql -d blockscout -c "CREATE EXTENSION IF NOT EXISTS btree_gist;" 2>/dev/null || true

# Step 4: Clone and setup Blockscout Backend
echo -e "${GREEN}[4/5] Setting up Blockscout Backend...${NC}"

if [ ! -d "$BLOCKSCOUT_DIR" ]; then
    git clone https://github.com/blockscout/blockscout.git "$BLOCKSCOUT_DIR"
fi

cd "$BLOCKSCOUT_DIR"
git fetch origin
git checkout v6.3.0

# Create .env if not exists
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
DATABASE_URL=postgresql://blockscout:CHANGE_ME@localhost:5432/blockscout
ETHEREUM_JSONRPC_HTTP_URL=http://127.0.0.1:8545
ETHEREUM_JSONRPC_TRACE_URL=http://127.0.0.1:8545
CHAIN_ID=1337
COIN=XAI
COIN_NAME=XAI
NETWORK=XAI Testnet
SUBNETWORK=MVP Testnet
INDEXER_DISABLE_PENDING_TRANSACTIONS_FETCHER=true
INDEXER_DISABLE_INTERNAL_TRANSACTIONS_FETCHER=true
API_V2_ENABLED=true
ENABLE_SOURCIFY_INTEGRATION=false
DISABLE_KNOWN_TOKENS=true
SHOW_PRICE_CHART=false
SHOW_TXS_CHART=true
PORT=4000
EOF
    echo -e "${YELLOW}Please edit $BLOCKSCOUT_DIR/.env with correct database password${NC}"
fi

# Install Elixir dependencies
mix local.hex --force
mix local.rebar --force
mix deps.get

# Compile
MIX_ENV=prod mix compile

# Migrate database
MIX_ENV=prod mix do ecto.create, ecto.migrate

# Install backend service
sudo cp "$ADAPTER_DIR/deploy/blockscout-backend.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable blockscout-backend

# Step 5: Setup Blockscout Frontend
echo -e "${GREEN}[5/5] Setting up Blockscout Frontend...${NC}"

if [ ! -d "$FRONTEND_DIR" ]; then
    git clone https://github.com/blockscout/frontend.git "$FRONTEND_DIR"
fi

cd "$FRONTEND_DIR"
npm install

# Create .env.local
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_HOST=localhost
NEXT_PUBLIC_API_PORT=4000
NEXT_PUBLIC_API_PROTOCOL=http
NEXT_PUBLIC_NETWORK_NAME=XAI Testnet
NEXT_PUBLIC_NETWORK_SHORT_NAME=XAI
NEXT_PUBLIC_NETWORK_ID=1337
NEXT_PUBLIC_NETWORK_CURRENCY_NAME=XAI
NEXT_PUBLIC_NETWORK_CURRENCY_SYMBOL=XAI
NEXT_PUBLIC_NETWORK_CURRENCY_DECIMALS=18
NEXT_PUBLIC_IS_TESTNET=true
NEXT_PUBLIC_HAS_BEACON_CHAIN=false
NEXT_PUBLIC_AD_BANNER_PROVIDER=none
NEXT_PUBLIC_AD_TEXT_PROVIDER=none
EOF

npm run build

# Install frontend service
sudo cp "$ADAPTER_DIR/deploy/blockscout-frontend.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable blockscout-frontend

# Setup NGINX
sudo cp "$ADAPTER_DIR/deploy/nginx-blockscout.conf" /etc/nginx/sites-available/blockscout
sudo ln -sf /etc/nginx/sites-available/blockscout /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Services status:"
echo "  sudo systemctl status xai-rpc-adapter"
echo "  sudo systemctl status blockscout-backend"
echo "  sudo systemctl status blockscout-frontend"
echo ""
echo "Start all services:"
echo "  sudo systemctl start xai-rpc-adapter blockscout-backend blockscout-frontend"
echo ""
echo "Get SSL certificate:"
echo "  sudo certbot --nginx -d testnet-explorer.xaiblockchain.com"
