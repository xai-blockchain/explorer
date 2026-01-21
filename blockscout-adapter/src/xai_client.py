"""
XAI Node HTTP Client
Connects to XAI sentry nodes and fetches blockchain data
Supports multiple nodes with health-based load balancing and automatic failover
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class NodeHealth:
    """Track health status of a single node"""

    url: str
    is_healthy: bool = True
    last_check: float = 0
    consecutive_failures: int = 0
    response_time_ms: float = 0
    chain_height: int = 0
    last_error: str = ""

    def mark_success(self, response_time_ms: float, chain_height: int = 0):
        self.is_healthy = True
        self.consecutive_failures = 0
        self.response_time_ms = response_time_ms
        self.last_check = time.time()
        if chain_height > 0:
            self.chain_height = chain_height
        self.last_error = ""

    def mark_failure(self, error: str):
        self.consecutive_failures += 1
        self.last_error = error
        self.last_check = time.time()
        # Mark unhealthy after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.is_healthy = False


@dataclass
class XAIClientConfig:
    """Configuration for multi-node XAI client"""

    # List of node URLs (supports multiple sentries)
    node_urls: list[str] = field(
        default_factory=lambda: ["http://127.0.0.1:12570", "http://127.0.0.1:12571"]
    )
    timeout: float = 30.0
    max_retries: int = 3
    health_check_interval: float = 30.0  # seconds between health checks
    # Load balancing strategy: "round_robin", "fastest", "random"
    load_balance_strategy: str = "fastest"

    # Legacy support for primary/fallback
    @classmethod
    def from_primary_fallback(cls, primary: str, fallback: str, **kwargs):
        return cls(node_urls=[primary, fallback], **kwargs)


class XAIClient:
    """
    Async client for XAI blockchain nodes with multi-node support

    Features:
    - Health-based load balancing across multiple sentry nodes
    - Automatic failover when a node becomes unhealthy
    - Periodic health checks with chain height verification
    - Response time tracking for optimal node selection
    """

    def __init__(self, config: XAIClientConfig = None):
        self.config = config or XAIClientConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._nodes: dict[str, NodeHealth] = {
            url: NodeHealth(url=url) for url in self.config.node_urls
        }
        self._current_index = 0
        self._health_check_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.config.timeout)
        # Initial health check on all nodes
        await self._check_all_nodes_health()
        # Start background health checker
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        return self

    async def __aexit__(self, *args):
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()

    async def _health_check_loop(self):
        """Background task to periodically check node health"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._check_all_nodes_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _check_all_nodes_health(self):
        """Check health of all configured nodes"""
        tasks = [self._check_node_health(url) for url in self._nodes.keys()]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Log health status
        healthy = [n for n in self._nodes.values() if n.is_healthy]
        logger.info(
            f"Node health: {len(healthy)}/{len(self._nodes)} healthy, "
            f"heights: {[n.chain_height for n in healthy]}"
        )

    async def _check_node_health(self, url: str):
        """Check health of a single node"""
        node = self._nodes[url]
        start = time.time()

        try:
            response = await self._client.get(f"{url}/stats", timeout=5.0)
            response.raise_for_status()
            data = response.json()
            response_time = (time.time() - start) * 1000

            node.mark_success(
                response_time_ms=response_time, chain_height=data.get("chain_height", 0)
            )
            logger.debug(
                f"Node {url} healthy: height={node.chain_height}, " f"latency={response_time:.0f}ms"
            )
        except Exception as e:
            node.mark_failure(str(e))
            logger.warning(f"Node {url} health check failed: {e}")

    def _select_node(self) -> str:
        """Select best node based on configured strategy"""
        healthy_nodes = [n for n in self._nodes.values() if n.is_healthy]

        if not healthy_nodes:
            # All nodes unhealthy, try all anyway
            logger.warning("All nodes unhealthy, using all nodes for failover")
            return self.config.node_urls[0]

        strategy = self.config.load_balance_strategy

        if strategy == "round_robin":
            self._current_index = (self._current_index + 1) % len(healthy_nodes)
            return healthy_nodes[self._current_index].url

        elif strategy == "fastest":
            # Select node with lowest response time
            fastest = min(healthy_nodes, key=lambda n: n.response_time_ms)
            return fastest.url

        elif strategy == "random":
            return random.choice(healthy_nodes).url

        else:
            # Default to first healthy
            return healthy_nodes[0].url

    def _get_ordered_nodes(self) -> list[str]:
        """Get nodes ordered by preference for failover"""
        # Start with selected node, then healthy nodes, then unhealthy
        selected = self._select_node()
        healthy = [n.url for n in self._nodes.values() if n.is_healthy and n.url != selected]
        unhealthy = [n.url for n in self._nodes.values() if not n.is_healthy]

        return [selected] + healthy + unhealthy

    async def _request(self, endpoint: str, method: str = "GET", data: dict = None) -> dict:
        """Make request with automatic failover across all nodes"""
        urls = self._get_ordered_nodes()
        last_error = None

        for url in urls:
            node = self._nodes[url]
            start = time.time()

            try:
                full_url = f"{url}{endpoint}"
                if method == "GET":
                    response = await self._client.get(full_url)
                else:
                    response = await self._client.post(full_url, json=data)
                response.raise_for_status()

                # Update node health on success
                response_time = (time.time() - start) * 1000
                node.mark_success(response_time_ms=response_time)

                return response.json()

            except Exception as e:
                last_error = e
                node.mark_failure(str(e))
                logger.warning(f"Request to {url}{endpoint} failed: {e}")
                continue

        raise last_error

    # === Health & Status Methods ===

    def get_nodes_status(self) -> list[dict]:
        """Get status of all configured nodes"""
        return [
            {
                "url": node.url,
                "is_healthy": node.is_healthy,
                "chain_height": node.chain_height,
                "response_time_ms": round(node.response_time_ms, 2),
                "consecutive_failures": node.consecutive_failures,
                "last_error": node.last_error,
                "last_check": node.last_check,
            }
            for node in self._nodes.values()
        ]

    def get_healthy_node_count(self) -> int:
        """Get count of healthy nodes"""
        return sum(1 for n in self._nodes.values() if n.is_healthy)

    # === Core Data Methods ===

    async def get_stats(self) -> dict:
        """Get node stats including chain height"""
        return await self._request("/stats")

    async def get_block(self, height_or_hash: str | int) -> dict:
        """Get block by height or hash"""
        return await self._request(f"/block/{height_or_hash}")

    async def get_latest_block(self) -> dict:
        """Get the latest block"""
        stats = await self.get_stats()
        return await self.get_block(stats["chain_height"])

    async def get_blocks(self, start: int, end: int) -> list[dict]:
        """Get range of blocks"""
        return await self._request(f"/blocks?start={start}&end={end}")

    async def get_transaction(self, txid: str) -> dict:
        """Get transaction by ID"""
        return await self._request(f"/transaction/{txid}")

    async def get_address(self, address: str) -> dict:
        """Get address info including balance"""
        return await self._request(f"/address/{address}")

    async def get_address_transactions(self, address: str, limit: int = 100) -> list[dict]:
        """Get transactions for an address"""
        return await self._request(f"/address/{address}/transactions?limit={limit}")

    async def get_mempool(self) -> dict:
        """Get pending transactions"""
        return await self._request("/mempool")

    async def get_peers(self) -> list[dict]:
        """Get connected peers"""
        return await self._request("/peers")
