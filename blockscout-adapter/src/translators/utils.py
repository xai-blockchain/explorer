"""
Utility functions for EVM data format conversion
"""

import hashlib
from typing import Any


def to_hex(value: int) -> str:
    """Convert integer to 0x-prefixed hex string"""
    return hex(value)


def from_hex(value: str) -> int:
    """Convert 0x-prefixed hex to integer"""
    if isinstance(value, int):
        return value
    return int(value, 16) if value.startswith("0x") else int(value)


def pad_hex(value: str, length: int = 64) -> str:
    """Pad hex string to specified length"""
    clean = value[2:] if value.startswith("0x") else value
    return "0x" + clean.zfill(length)


def xai_hash_to_evm(xai_hash: str) -> str:
    """
    Convert XAI hash format to EVM 32-byte hash
    XAI uses different hash format, normalize to 0x + 64 hex chars
    """
    if not xai_hash:
        return "0x" + "0" * 64

    clean = xai_hash.replace("0x", "")
    # Ensure 64 chars (32 bytes)
    if len(clean) < 64:
        clean = clean.zfill(64)
    elif len(clean) > 64:
        clean = clean[:64]

    return "0x" + clean


def xai_address_to_evm(xai_address: str) -> str:
    """
    Convert XAI address to EVM 20-byte address format
    XAI addresses may differ from EVM format
    """
    if not xai_address:
        return "0x" + "0" * 40

    # If already EVM format
    if xai_address.startswith("0x") and len(xai_address) == 42:
        return xai_address.lower()

    # Convert XAI format to EVM (hash the address if needed)
    if xai_address.startswith("xai"):
        # Hash to create deterministic 20-byte address
        hash_bytes = hashlib.sha256(xai_address.encode()).digest()[:20]
        return "0x" + hash_bytes.hex()

    # Pad/truncate to 40 hex chars
    clean = xai_address.replace("0x", "")
    if len(clean) < 40:
        clean = clean.zfill(40)
    elif len(clean) > 40:
        clean = clean[:40]

    return "0x" + clean.lower()


def wei_to_xai(wei: int) -> float:
    """Convert Wei to XAI (18 decimals)"""
    return wei / 10**18


def xai_to_wei(xai: float) -> int:
    """Convert XAI to Wei"""
    return int(xai * 10**18)


def timestamp_to_hex(ts: float) -> str:
    """Convert timestamp to hex"""
    return to_hex(int(ts))
