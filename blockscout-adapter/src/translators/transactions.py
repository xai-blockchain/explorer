"""
Transaction data translation: XAI format -> EVM format
"""

from .utils import to_hex, xai_address_to_evm, xai_hash_to_evm, xai_to_wei


def translate_transaction(xai_tx: dict, block_height: int = None, tx_index: int = 0) -> dict:
    """
    Translate XAI transaction to EVM transaction format

    XAI Transaction Fields:
    - txid, sender, recipient, amount
    - timestamp, nonce, signature
    - fee, data/memo

    EVM Transaction Fields:
    - hash, from, to, value
    - blockNumber, transactionIndex
    - gas, gasPrice, nonce, input
    """

    # Convert XAI amount to Wei (assuming 18 decimals)
    amount_wei = xai_to_wei(xai_tx.get("amount", 0))
    fee_wei = xai_to_wei(xai_tx.get("fee", 0))

    evm_tx = {
        # Identifiers
        "hash": xai_hash_to_evm(xai_tx.get("txid", "")),
        "blockHash": xai_hash_to_evm(xai_tx.get("block_hash", "")),
        "blockNumber": to_hex(block_height) if block_height else None,
        "transactionIndex": to_hex(tx_index),
        # Addresses
        "from": xai_address_to_evm(xai_tx.get("sender", "")),
        "to": xai_address_to_evm(xai_tx.get("recipient", "")),
        # Value
        "value": to_hex(amount_wei),
        # Gas (XAI doesn't use gas, estimate from fee)
        "gas": to_hex(21000),  # Standard transfer gas
        "gasPrice": to_hex(fee_wei // 21000) if fee_wei else to_hex(0),
        "maxFeePerGas": to_hex(0),
        "maxPriorityFeePerGas": to_hex(0),
        # Nonce
        "nonce": to_hex(xai_tx.get("nonce", 0)),
        # Input data (memo/data field)
        "input": "0x" + (xai_tx.get("data", "") or xai_tx.get("memo", "") or "").encode().hex(),
        # Type (legacy transaction)
        "type": "0x0",
        # Signature components (if available)
        "v": to_hex(xai_tx.get("v", 27)),
        "r": xai_hash_to_evm(xai_tx.get("r", "")),
        "s": xai_hash_to_evm(xai_tx.get("s", "")),
    }

    return evm_tx


def translate_transaction_receipt(xai_tx: dict, xai_block: dict = None, tx_index: int = 0) -> dict:
    """
    Create EVM transaction receipt from XAI transaction
    """

    block_height = xai_block.get("height", 0) if xai_block else 0

    # Determine status (XAI transactions are final if in block)
    status = "0x1" if xai_tx.get("confirmed", True) else "0x0"

    return {
        "transactionHash": xai_hash_to_evm(xai_tx.get("txid", "")),
        "transactionIndex": to_hex(tx_index),
        "blockHash": xai_hash_to_evm(xai_block.get("hash", "") if xai_block else ""),
        "blockNumber": to_hex(block_height),
        "from": xai_address_to_evm(xai_tx.get("sender", "")),
        "to": xai_address_to_evm(xai_tx.get("recipient", "")),
        "cumulativeGasUsed": to_hex(21000 * (tx_index + 1)),
        "gasUsed": to_hex(21000),
        "effectiveGasPrice": to_hex(0),
        "contractAddress": None,  # XAI MVP has no smart contracts
        "logs": [],  # No event logs in XAI MVP
        "logsBloom": "0x" + "0" * 512,
        "status": status,
        "type": "0x0",
    }
