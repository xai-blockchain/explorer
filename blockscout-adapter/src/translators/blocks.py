"""
Block data translation: XAI format -> EVM format
"""

from typing import Any
from .utils import (
    to_hex, xai_hash_to_evm, xai_address_to_evm,
    timestamp_to_hex, xai_to_wei
)


def translate_block(xai_block: dict, include_txs: bool = False) -> dict:
    """
    Translate XAI block to EVM block format

    XAI Block Fields:
    - height, hash, previous_hash, timestamp
    - miner, difficulty, nonce
    - transactions (list)
    - merkle_root, state_root

    EVM Block Fields:
    - number, hash, parentHash, timestamp
    - miner, difficulty, nonce
    - transactions, transactionsRoot, stateRoot
    - gasUsed, gasLimit, size, etc.
    """

    # Handle missing fields gracefully
    height = xai_block.get("height", 0)

    evm_block = {
        # Core identifiers
        "number": to_hex(height),
        "hash": xai_hash_to_evm(xai_block.get("hash", "")),
        "parentHash": xai_hash_to_evm(xai_block.get("previous_hash", "")),

        # Timestamps
        "timestamp": timestamp_to_hex(xai_block.get("timestamp", 0)),

        # Mining info
        "miner": xai_address_to_evm(xai_block.get("miner", "")),
        "difficulty": to_hex(xai_block.get("difficulty", 1)),
        "totalDifficulty": to_hex(xai_block.get("total_difficulty", height)),
        "nonce": to_hex(xai_block.get("nonce", 0)),

        # Roots (merkle/state)
        "transactionsRoot": xai_hash_to_evm(
            xai_block.get("merkle_root", "")
        ),
        "stateRoot": xai_hash_to_evm(xai_block.get("state_root", "")),
        "receiptsRoot": xai_hash_to_evm(""),  # XAI may not have this

        # Gas (XAI doesn't use gas, provide defaults)
        "gasUsed": to_hex(xai_block.get("gas_used", 0)),
        "gasLimit": to_hex(xai_block.get("gas_limit", 30000000)),
        "baseFeePerGas": to_hex(0),  # No EIP-1559 in XAI

        # Size
        "size": to_hex(xai_block.get("size", 1000)),

        # Extra
        "extraData": "0x",
        "logsBloom": "0x" + "0" * 512,
        "mixHash": xai_hash_to_evm(""),
        "sha3Uncles": xai_hash_to_evm(""),
        "uncles": [],

        # Withdrawals (not applicable)
        "withdrawals": [],
        "withdrawalsRoot": xai_hash_to_evm(""),
    }

    # Handle transactions
    xai_txs = xai_block.get("transactions", [])
    if include_txs:
        from .transactions import translate_transaction
        evm_block["transactions"] = [
            translate_transaction(tx, height, idx)
            for idx, tx in enumerate(xai_txs)
        ]
    else:
        # Just return transaction hashes
        evm_block["transactions"] = [
            xai_hash_to_evm(tx.get("txid", tx) if isinstance(tx, dict) else tx)
            for tx in xai_txs
        ]

    return evm_block


def translate_block_number(block_param: str | int, chain_height: int) -> int:
    """
    Translate block number parameter to actual block number
    Handles: "latest", "earliest", "pending", hex numbers
    """
    if isinstance(block_param, int):
        return block_param

    if block_param == "latest" or block_param == "pending":
        return chain_height

    if block_param == "earliest":
        return 0

    # Hex string
    if block_param.startswith("0x"):
        return int(block_param, 16)

    return int(block_param)
