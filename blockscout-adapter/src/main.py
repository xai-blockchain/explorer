"""
XAI Blockscout RPC Adapter
FastAPI application providing EVM JSON-RPC interface
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .rpc_handler import RPCHandler, RPCRequest
from .xai_client import XAIClient, XAIClientConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
# Support multiple nodes via comma-separated list
XAI_NODE_URLS = os.getenv(
    "XAI_NODE_URLS",
    os.getenv("XAI_PRIMARY_URL", "http://127.0.0.1:12570")
    + ","
    + os.getenv("XAI_FALLBACK_URL", "http://127.0.0.1:12571"),
).split(",")
XAI_CHAIN_ID = int(os.getenv("XAI_CHAIN_ID", "1337"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
LOAD_BALANCE_STRATEGY = os.getenv("LOAD_BALANCE_STRATEGY", "fastest")
HEALTH_CHECK_INTERVAL = float(os.getenv("HEALTH_CHECK_INTERVAL", "30"))

# Global instances
xai_client: XAIClient = None
rpc_handler: RPCHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global xai_client, rpc_handler

    # Startup
    config = XAIClientConfig(
        node_urls=[url.strip() for url in XAI_NODE_URLS if url.strip()],
        load_balance_strategy=LOAD_BALANCE_STRATEGY,
        health_check_interval=HEALTH_CHECK_INTERVAL,
    )
    xai_client = XAIClient(config)
    await xai_client.__aenter__()

    rpc_handler = RPCHandler(xai_client, chain_id=XAI_CHAIN_ID)

    logger.info(f"XAI RPC Adapter started - Chain ID: {XAI_CHAIN_ID}")
    logger.info(f"Configured nodes: {config.node_urls}")
    logger.info(f"Load balance strategy: {LOAD_BALANCE_STRATEGY}")

    yield

    # Shutdown
    await xai_client.__aexit__(None, None, None)
    logger.info("XAI RPC Adapter stopped")


app = FastAPI(
    title="XAI Blockscout RPC Adapter",
    description="Translates EVM JSON-RPC calls to XAI blockchain API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: list = []
    id: int | str = 1


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Any = None
    error: dict = None
    id: int | str = 1


class BatchRequest(BaseModel):
    requests: list[JSONRPCRequest]


# Routes


@app.post("/")
@app.post("/rpc")
async def json_rpc(request: Request):
    """
    Handle JSON-RPC requests (single or batch)
    """
    body = await request.json()

    # Handle batch requests
    if isinstance(body, list):
        responses = []
        for req_data in body:
            rpc_req = RPCRequest(
                method=req_data.get("method", ""),
                params=req_data.get("params", []),
                id=req_data.get("id", 1),
                jsonrpc=req_data.get("jsonrpc", "2.0"),
            )
            response = await rpc_handler.handle(rpc_req)
            resp_dict = {"jsonrpc": response.jsonrpc, "id": response.id}
            if response.error:
                resp_dict["error"] = response.error
            else:
                resp_dict["result"] = response.result
            responses.append(resp_dict)
        return responses

    # Single request
    rpc_req = RPCRequest(
        method=body.get("method", ""),
        params=body.get("params", []),
        id=body.get("id", 1),
        jsonrpc=body.get("jsonrpc", "2.0"),
    )

    response = await rpc_handler.handle(rpc_req)

    resp_dict = {"jsonrpc": response.jsonrpc, "id": response.id}
    if response.error:
        resp_dict["error"] = response.error
    else:
        resp_dict["result"] = response.result

    return resp_dict


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        stats = await xai_client.get_stats()
        nodes_status = xai_client.get_nodes_status()
        healthy_count = xai_client.get_healthy_node_count()

        return {
            "status": "healthy" if healthy_count > 0 else "degraded",
            "chain_height": stats.get("chain_height", 0),
            "chain_id": XAI_CHAIN_ID,
            "adapter_version": "1.0.0",
            "nodes": {
                "total": len(nodes_status),
                "healthy": healthy_count,
                "load_balance_strategy": LOAD_BALANCE_STRATEGY,
            },
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "nodes": xai_client.get_nodes_status() if xai_client else [],
        }


@app.get("/nodes")
async def nodes_status():
    """Get detailed status of all configured XAI nodes"""
    return {
        "nodes": xai_client.get_nodes_status(),
        "healthy_count": xai_client.get_healthy_node_count(),
        "total_count": len(xai_client.get_nodes_status()),
        "load_balance_strategy": LOAD_BALANCE_STRATEGY,
    }


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "XAI Blockscout RPC Adapter",
        "version": "1.0.0",
        "chain_id": XAI_CHAIN_ID,
        "endpoints": {"rpc": "POST /rpc", "health": "GET /health"},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8545)
