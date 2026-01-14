"""
EVM JSON-RPC Method Handler
Routes JSON-RPC calls to appropriate XAI client methods
"""

import logging
from typing import Any, Callable
from dataclasses import dataclass

from .xai_client import XAIClient
from .translators.blocks import translate_block, translate_block_number
from .translators.transactions import (
    translate_transaction, translate_transaction_receipt
)
from .translators.accounts import (
    get_balance_response, get_transaction_count, get_code_response
)
from .translators.utils import to_hex, xai_hash_to_evm

logger = logging.getLogger(__name__)


@dataclass
class RPCRequest:
    method: str
    params: list
    id: int | str
    jsonrpc: str = "2.0"


@dataclass
class RPCResponse:
    result: Any
    id: int | str
    jsonrpc: str = "2.0"
    error: dict = None


class RPCHandler:
    """
    Handles EVM JSON-RPC method calls by translating to XAI API

    Supported Methods:
    - eth_blockNumber
    - eth_getBlockByNumber
    - eth_getBlockByHash
    - eth_getTransactionByHash
    - eth_getTransactionReceipt
    - eth_getBalance
    - eth_getTransactionCount
    - eth_getCode
    - eth_chainId
    - eth_gasPrice
    - net_version
    - web3_clientVersion
    """

    def __init__(self, xai_client: XAIClient, chain_id: int = 1337):
        self.xai = xai_client
        self.chain_id = chain_id
        self._chain_height = 0

        # Method routing table
        self._methods: dict[str, Callable] = {
            # Block methods
            "eth_blockNumber": self._eth_block_number,
            "eth_getBlockByNumber": self._eth_get_block_by_number,
            "eth_getBlockByHash": self._eth_get_block_by_hash,

            # Transaction methods
            "eth_getTransactionByHash": self._eth_get_transaction_by_hash,
            "eth_getTransactionReceipt": self._eth_get_transaction_receipt,
            "eth_getTransactionByBlockNumberAndIndex":
                self._eth_get_tx_by_block_and_index,

            # Account methods
            "eth_getBalance": self._eth_get_balance,
            "eth_getTransactionCount": self._eth_get_transaction_count,
            "eth_getCode": self._eth_get_code,

            # Chain info
            "eth_chainId": self._eth_chain_id,
            "eth_gasPrice": self._eth_gas_price,
            "net_version": self._net_version,
            "web3_clientVersion": self._web3_client_version,

            # Sync status
            "eth_syncing": self._eth_syncing,

            # Logs (empty for MVP)
            "eth_getLogs": self._eth_get_logs,

            # Additional methods for Blockscout compatibility
            "eth_getBlockTransactionCountByNumber": self._eth_get_block_tx_count_by_number,
            "eth_getBlockTransactionCountByHash": self._eth_get_block_tx_count_by_hash,
            "eth_getUncleCountByBlockNumber": self._eth_get_uncle_count,
            "eth_getUncleCountByBlockHash": self._eth_get_uncle_count,
            "net_listening": self._net_listening,
            "net_peerCount": self._net_peer_count,
            "eth_protocolVersion": self._eth_protocol_version,
            "eth_call": self._eth_call,
            "eth_estimateGas": self._eth_estimate_gas,
            "eth_getStorageAt": self._eth_get_storage_at,
        }

    async def handle(self, request: RPCRequest) -> RPCResponse:
        """Process a JSON-RPC request"""
        method = request.method

        if method not in self._methods:
            return RPCResponse(
                result=None,
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            )

        try:
            result = await self._methods[method](request.params)
            return RPCResponse(result=result, id=request.id)
        except Exception as e:
            logger.error(f"RPC error for {method}: {e}")
            return RPCResponse(
                result=None,
                id=request.id,
                error={
                    "code": -32000,
                    "message": str(e)
                }
            )

    # === Block Methods ===

    async def _eth_block_number(self, params: list) -> str:
        stats = await self.xai.get_stats()
        self._chain_height = stats["chain_height"]
        return to_hex(self._chain_height)

    async def _eth_get_block_by_number(self, params: list) -> dict | None:
        block_param = params[0] if params else "latest"
        include_txs = params[1] if len(params) > 1 else False

        stats = await self.xai.get_stats()
        self._chain_height = stats["chain_height"]

        block_num = translate_block_number(block_param, self._chain_height)

        try:
            xai_block = await self.xai.get_block(block_num)
            return translate_block(xai_block, include_txs)
        except Exception:
            return None

    async def _eth_get_block_by_hash(self, params: list) -> dict | None:
        block_hash = params[0] if params else None
        include_txs = params[1] if len(params) > 1 else False

        if not block_hash:
            return None

        try:
            xai_block = await self.xai.get_block(block_hash)
            return translate_block(xai_block, include_txs)
        except Exception:
            return None

    async def _eth_get_block_tx_count_by_number(self, params: list) -> str:
        block_param = params[0] if params else "latest"

        stats = await self.xai.get_stats()
        block_num = translate_block_number(block_param, stats["chain_height"])

        try:
            xai_block = await self.xai.get_block(block_num)
            tx_count = len(xai_block.get("transactions", []))
            return to_hex(tx_count)
        except Exception:
            return to_hex(0)

    async def _eth_get_block_tx_count_by_hash(self, params: list) -> str:
        block_hash = params[0] if params else None
        if not block_hash:
            return to_hex(0)

        try:
            xai_block = await self.xai.get_block(block_hash)
            tx_count = len(xai_block.get("transactions", []))
            return to_hex(tx_count)
        except Exception:
            return to_hex(0)

    # === Transaction Methods ===

    async def _eth_get_transaction_by_hash(self, params: list) -> dict | None:
        tx_hash = params[0] if params else None
        if not tx_hash:
            return None

        try:
            xai_tx = await self.xai.get_transaction(tx_hash)
            block_height = xai_tx.get("block_height")
            return translate_transaction(xai_tx, block_height)
        except Exception:
            return None

    async def _eth_get_transaction_receipt(self, params: list) -> dict | None:
        tx_hash = params[0] if params else None
        if not tx_hash:
            return None

        try:
            xai_tx = await self.xai.get_transaction(tx_hash)
            block_height = xai_tx.get("block_height")
            xai_block = await self.xai.get_block(block_height) if block_height else None
            return translate_transaction_receipt(xai_tx, xai_block)
        except Exception:
            return None

    async def _eth_get_tx_by_block_and_index(self, params: list) -> dict | None:
        block_param = params[0] if params else "latest"
        tx_index = int(params[1], 16) if len(params) > 1 else 0

        stats = await self.xai.get_stats()
        block_num = translate_block_number(block_param, stats["chain_height"])

        try:
            xai_block = await self.xai.get_block(block_num)
            txs = xai_block.get("transactions", [])
            if tx_index < len(txs):
                return translate_transaction(txs[tx_index], block_num, tx_index)
            return None
        except Exception:
            return None

    # === Account Methods ===

    async def _eth_get_balance(self, params: list) -> str:
        address = params[0] if params else None
        # block_param = params[1] if len(params) > 1 else "latest"

        if not address:
            return to_hex(0)

        try:
            xai_info = await self.xai.get_address(address)
            return get_balance_response(xai_info)
        except Exception:
            return to_hex(0)

    async def _eth_get_transaction_count(self, params: list) -> str:
        address = params[0] if params else None

        if not address:
            return to_hex(0)

        try:
            xai_info = await self.xai.get_address(address)
            return get_transaction_count(xai_info)
        except Exception:
            return to_hex(0)

    async def _eth_get_code(self, params: list) -> str:
        # XAI MVP has no smart contracts
        return get_code_response()

    async def _eth_get_storage_at(self, params: list) -> str:
        # XAI MVP has no smart contracts/storage
        return "0x0000000000000000000000000000000000000000000000000000000000000000"

    # === Chain Info Methods ===

    async def _eth_chain_id(self, params: list) -> str:
        return to_hex(self.chain_id)

    async def _eth_gas_price(self, params: list) -> str:
        # XAI doesn't use gas, return minimal value
        return to_hex(1000000000)  # 1 Gwei

    async def _net_version(self, params: list) -> str:
        return str(self.chain_id)

    async def _web3_client_version(self, params: list) -> str:
        return "XAI-Blockscout-Adapter/1.0.0"

    async def _eth_syncing(self, params: list) -> bool | dict:
        # Return False when synced
        return False

    async def _eth_get_logs(self, params: list) -> list:
        # XAI MVP has no event logs
        return []

    async def _eth_get_uncle_count(self, params: list) -> str:
        # XAI has no uncles
        return to_hex(0)

    async def _net_listening(self, params: list) -> bool:
        return True

    async def _net_peer_count(self, params: list) -> str:
        try:
            peers = await self.xai.get_peers()
            return to_hex(len(peers))
        except Exception:
            return to_hex(0)

    async def _eth_protocol_version(self, params: list) -> str:
        return to_hex(65)  # ETH protocol version

    async def _eth_call(self, params: list) -> str:
        # XAI has no smart contracts, return empty
        return "0x"

    async def _eth_estimate_gas(self, params: list) -> str:
        # Return standard transfer gas
        return to_hex(21000)
