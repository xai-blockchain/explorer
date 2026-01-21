"""Tests for XAI to EVM data translators"""

import pytest
from src.translators.accounts import get_balance_response, get_transaction_count
from src.translators.blocks import translate_block, translate_block_number
from src.translators.transactions import translate_transaction, translate_transaction_receipt
from src.translators.utils import (
    from_hex,
    pad_hex,
    timestamp_to_hex,
    to_hex,
    wei_to_xai,
    xai_address_to_evm,
    xai_hash_to_evm,
    xai_to_wei,
)


class TestUtils:
    """Test utility functions"""

    def test_to_hex(self):
        assert to_hex(0) == "0x0"
        assert to_hex(255) == "0xff"
        assert to_hex(1000000) == "0xf4240"

    def test_from_hex(self):
        assert from_hex("0x0") == 0
        assert from_hex("0xff") == 255
        assert from_hex("0xf4240") == 1000000
        assert from_hex(100) == 100  # Handle int input

    def test_pad_hex(self):
        assert pad_hex("0x1", 4) == "0x0001"
        assert pad_hex("abc", 6) == "0x000abc"

    def test_xai_hash_to_evm(self):
        # Empty hash
        result = xai_hash_to_evm("")
        assert result == "0x" + "0" * 64

        # Short hash - should be padded
        result = xai_hash_to_evm("abc123")
        assert len(result) == 66  # 0x + 64 chars
        assert result.startswith("0x")

        # Full-length hash
        full_hash = "a" * 64
        result = xai_hash_to_evm(full_hash)
        assert result == "0x" + full_hash

    def test_xai_address_to_evm(self):
        # Empty address
        result = xai_address_to_evm("")
        assert result == "0x" + "0" * 40

        # EVM format address
        evm_addr = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        result = xai_address_to_evm(evm_addr)
        assert len(result) == 42
        assert result == evm_addr.lower()

        # XAI format address (should be hashed)
        xai_addr = "xai1abc123def456"
        result = xai_address_to_evm(xai_addr)
        assert len(result) == 42
        assert result.startswith("0x")

    def test_wei_conversions(self):
        # 1 XAI = 10^18 Wei
        assert wei_to_xai(10**18) == 1.0
        assert xai_to_wei(1.0) == 10**18

        # 0.5 XAI
        assert wei_to_xai(5 * 10**17) == 0.5
        assert xai_to_wei(0.5) == 5 * 10**17

    def test_timestamp_to_hex(self):
        assert timestamp_to_hex(0) == "0x0"
        # 1704067200 is 2024-01-01 00:00:00 UTC
        assert timestamp_to_hex(1704067200.0) == hex(1704067200)


class TestBlockTranslator:
    """Test block translation"""

    def test_translate_block_minimal(self):
        """Test with minimal XAI block data"""
        xai_block = {
            "height": 100,
            "hash": "abc123",
            "previous_hash": "def456",
            "timestamp": 1704067200,
            "miner": "0x" + "1" * 40,
            "transactions": [],
        }

        result = translate_block(xai_block)

        assert result["number"] == "0x64"  # 100 in hex
        assert result["parentHash"].startswith("0x")
        assert result["miner"].startswith("0x")
        assert result["transactions"] == []

    def test_translate_block_with_transactions(self):
        """Test block with transaction hashes"""
        xai_block = {
            "height": 100,
            "hash": "abc123",
            "previous_hash": "def456",
            "timestamp": 1704067200,
            "miner": "0x" + "1" * 40,
            "transactions": [{"txid": "tx1"}, {"txid": "tx2"}],
        }

        result = translate_block(xai_block, include_txs=False)
        assert len(result["transactions"]) == 2

    def test_translate_block_number(self):
        """Test block number parameter translation"""
        chain_height = 1000

        assert translate_block_number("latest", chain_height) == 1000
        assert translate_block_number("pending", chain_height) == 1000
        assert translate_block_number("earliest", chain_height) == 0
        assert translate_block_number("0x64", chain_height) == 100
        assert translate_block_number(50, chain_height) == 50


class TestTransactionTranslator:
    """Test transaction translation"""

    def test_translate_transaction(self):
        """Test basic transaction translation"""
        xai_tx = {
            "txid": "tx123",
            "sender": "0x" + "1" * 40,
            "recipient": "0x" + "2" * 40,
            "amount": 1.5,
            "fee": 0.001,
            "nonce": 5,
        }

        result = translate_transaction(xai_tx, block_height=100, tx_index=0)

        assert result["hash"].startswith("0x")
        assert result["from"].startswith("0x")
        assert result["to"].startswith("0x")
        assert result["blockNumber"] == "0x64"
        assert result["transactionIndex"] == "0x0"
        assert result["nonce"] == "0x5"

    def test_translate_transaction_receipt(self):
        """Test transaction receipt translation"""
        xai_tx = {
            "txid": "tx123",
            "sender": "0x" + "1" * 40,
            "recipient": "0x" + "2" * 40,
            "confirmed": True,
        }
        xai_block = {"height": 100, "hash": "block123"}

        result = translate_transaction_receipt(xai_tx, xai_block)

        assert result["status"] == "0x1"
        assert result["blockNumber"] == "0x64"
        assert result["logs"] == []


class TestAccountTranslator:
    """Test account/address translation"""

    def test_get_balance_response(self):
        """Test balance formatting"""
        xai_info = {"balance": 100.0}
        result = get_balance_response(xai_info)

        # 100 XAI = 100 * 10^18 Wei
        expected = hex(100 * 10**18)
        assert result == expected

    def test_get_transaction_count(self):
        """Test nonce/tx count formatting"""
        xai_info = {"nonce": 10, "transaction_count": 15}
        result = get_transaction_count(xai_info)

        assert result == "0xf"  # 15 in hex

    def test_get_transaction_count_fallback(self):
        """Test fallback to nonce if tx_count missing"""
        xai_info = {"nonce": 10}
        result = get_transaction_count(xai_info)

        assert result == "0xa"  # 10 in hex


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
