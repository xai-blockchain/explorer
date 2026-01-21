"""
Account/Address data translation: XAI format -> EVM format
"""

from .utils import to_hex, xai_address_to_evm, xai_to_wei


def get_balance_response(xai_address_info: dict) -> str:
    """
    Get balance in Wei (hex) from XAI address info
    """
    balance_xai = xai_address_info.get("balance", 0)
    balance_wei = xai_to_wei(balance_xai)
    return to_hex(balance_wei)


def get_transaction_count(xai_address_info: dict) -> str:
    """
    Get nonce/transaction count from XAI address info
    """
    nonce = xai_address_info.get("nonce", 0)
    tx_count = xai_address_info.get("transaction_count", nonce)
    return to_hex(tx_count)


def get_code_response() -> str:
    """
    Get code at address - XAI MVP has no smart contracts
    Returns empty bytecode
    """
    return "0x"


def translate_address_info(xai_info: dict) -> dict:
    """
    Translate XAI address info to standardized format
    """
    return {
        "address": xai_address_to_evm(xai_info.get("address", "")),
        "balance": get_balance_response(xai_info),
        "nonce": get_transaction_count(xai_info),
        "code": get_code_response(),
        "is_contract": False,  # XAI MVP has no contracts
    }
