"""Tests for JSON-RPC handler"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.rpc_handler import RPCHandler, RPCRequest


@pytest.fixture
def mock_xai_client():
    """Create a mock XAI client"""
    client = AsyncMock()

    # Default responses
    client.get_stats.return_value = {"chain_height": 1000}
    client.get_block.return_value = {
        "height": 100,
        "hash": "abc123",
        "previous_hash": "def456",
        "timestamp": 1704067200,
        "miner": "0x" + "1" * 40,
        "transactions": []
    }
    client.get_transaction.return_value = {
        "txid": "tx123",
        "sender": "0x" + "1" * 40,
        "recipient": "0x" + "2" * 40,
        "amount": 1.0,
        "block_height": 100
    }
    client.get_address.return_value = {
        "address": "0x" + "1" * 40,
        "balance": 100.0,
        "nonce": 5
    }
    client.get_peers.return_value = [{"id": "peer1"}, {"id": "peer2"}]

    return client


@pytest.fixture
def rpc_handler(mock_xai_client):
    """Create RPC handler with mock client"""
    return RPCHandler(mock_xai_client, chain_id=1337)


class TestBlockMethods:
    """Test block-related RPC methods"""

    @pytest.mark.asyncio
    async def test_eth_block_number(self, rpc_handler, mock_xai_client):
        """Test eth_blockNumber"""
        request = RPCRequest(method="eth_blockNumber", params=[], id=1)
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result == "0x3e8"  # 1000 in hex
        mock_xai_client.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_eth_get_block_by_number_latest(self, rpc_handler, mock_xai_client):
        """Test eth_getBlockByNumber with 'latest'"""
        request = RPCRequest(
            method="eth_getBlockByNumber",
            params=["latest", False],
            id=1
        )
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result is not None
        assert "number" in response.result

    @pytest.mark.asyncio
    async def test_eth_get_block_by_number_hex(self, rpc_handler, mock_xai_client):
        """Test eth_getBlockByNumber with hex number"""
        request = RPCRequest(
            method="eth_getBlockByNumber",
            params=["0x64", False],
            id=1
        )
        response = await rpc_handler.handle(request)

        assert response.error is None
        mock_xai_client.get_block.assert_called()

    @pytest.mark.asyncio
    async def test_eth_get_block_by_hash(self, rpc_handler, mock_xai_client):
        """Test eth_getBlockByHash"""
        request = RPCRequest(
            method="eth_getBlockByHash",
            params=["0x" + "a" * 64, False],
            id=1
        )
        response = await rpc_handler.handle(request)

        assert response.error is None


class TestTransactionMethods:
    """Test transaction-related RPC methods"""

    @pytest.mark.asyncio
    async def test_eth_get_transaction_by_hash(self, rpc_handler, mock_xai_client):
        """Test eth_getTransactionByHash"""
        request = RPCRequest(
            method="eth_getTransactionByHash",
            params=["0x" + "a" * 64],
            id=1
        )
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result is not None
        mock_xai_client.get_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_eth_get_transaction_receipt(self, rpc_handler, mock_xai_client):
        """Test eth_getTransactionReceipt"""
        request = RPCRequest(
            method="eth_getTransactionReceipt",
            params=["0x" + "a" * 64],
            id=1
        )
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result is not None
        assert response.result["status"] == "0x1"


class TestAccountMethods:
    """Test account-related RPC methods"""

    @pytest.mark.asyncio
    async def test_eth_get_balance(self, rpc_handler, mock_xai_client):
        """Test eth_getBalance"""
        request = RPCRequest(
            method="eth_getBalance",
            params=["0x" + "1" * 40, "latest"],
            id=1
        )
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result.startswith("0x")
        mock_xai_client.get_address.assert_called_once()

    @pytest.mark.asyncio
    async def test_eth_get_transaction_count(self, rpc_handler, mock_xai_client):
        """Test eth_getTransactionCount"""
        request = RPCRequest(
            method="eth_getTransactionCount",
            params=["0x" + "1" * 40],
            id=1
        )
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result == "0x5"  # nonce=5 from fixture

    @pytest.mark.asyncio
    async def test_eth_get_code(self, rpc_handler):
        """Test eth_getCode (should return empty for XAI)"""
        request = RPCRequest(
            method="eth_getCode",
            params=["0x" + "1" * 40, "latest"],
            id=1
        )
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result == "0x"


class TestChainInfoMethods:
    """Test chain info RPC methods"""

    @pytest.mark.asyncio
    async def test_eth_chain_id(self, rpc_handler):
        """Test eth_chainId"""
        request = RPCRequest(method="eth_chainId", params=[], id=1)
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result == "0x539"  # 1337 in hex

    @pytest.mark.asyncio
    async def test_net_version(self, rpc_handler):
        """Test net_version"""
        request = RPCRequest(method="net_version", params=[], id=1)
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result == "1337"

    @pytest.mark.asyncio
    async def test_web3_client_version(self, rpc_handler):
        """Test web3_clientVersion"""
        request = RPCRequest(method="web3_clientVersion", params=[], id=1)
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert "XAI" in response.result

    @pytest.mark.asyncio
    async def test_eth_gas_price(self, rpc_handler):
        """Test eth_gasPrice"""
        request = RPCRequest(method="eth_gasPrice", params=[], id=1)
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result.startswith("0x")

    @pytest.mark.asyncio
    async def test_eth_syncing(self, rpc_handler):
        """Test eth_syncing"""
        request = RPCRequest(method="eth_syncing", params=[], id=1)
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result is False

    @pytest.mark.asyncio
    async def test_eth_get_logs(self, rpc_handler):
        """Test eth_getLogs (should return empty for XAI MVP)"""
        request = RPCRequest(method="eth_getLogs", params=[{}], id=1)
        response = await rpc_handler.handle(request)

        assert response.error is None
        assert response.result == []


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_unknown_method(self, rpc_handler):
        """Test handling of unknown methods"""
        request = RPCRequest(method="eth_unknownMethod", params=[], id=1)
        response = await rpc_handler.handle(request)

        assert response.error is not None
        assert response.error["code"] == -32601
        assert "not found" in response.error["message"]

    @pytest.mark.asyncio
    async def test_xai_client_error(self, rpc_handler, mock_xai_client):
        """Test handling of XAI client errors"""
        mock_xai_client.get_stats.side_effect = Exception("Connection failed")

        request = RPCRequest(method="eth_blockNumber", params=[], id=1)
        response = await rpc_handler.handle(request)

        assert response.error is not None
        assert response.error["code"] == -32000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
