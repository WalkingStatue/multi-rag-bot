"""
Cache performance monitoring service for tracking and analyzing embedding cache performance.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import redis.asyncio as redis
from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CachePerformanceMetrics:
    """Cache performance metrics for a specific time period."""
    timestamp: float
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    avg_response_time_ms: float
    total_entries: int
    memory_usage_mb: float
    evictions: int
    provider_stats: Dict[str, Dict[str, int]]  # provider -> {hits, misses, requests}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachePerformanceMetrics':
        """Create from dictionary loaded from storage."""
        return cls(**data)


@dataclass
class CacheHitRateAnalysis:
    """Analysis of cache hit rates over time."""
    current_hit_rate: float
    avg_hit_rate_24h: float
    avg_hit_rate_7d: float
    trend: str  # 'improving', 'declining', 'stable'
    recommendations: List[str]


class CachePerformanceMonitor:
    """
    Service for monitoring and analyzing embedding cache performance.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the cache performance monitor.
        
        Args:
            redis_url: Redis connection URL. Uses settings default if None.
        """
        self.redis_url = redis_url or settings.redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # Monitoring configuration
        self.metrics_prefix = "cache_metrics:"
        self.performance_key = "cache_performance:current"
        self.history_key_prefix = "cache_history:"
        
        # Retention settings
        self.metrics_retention_days = 30
        self.snapshot_interval = 300  # 5 minutes
        
        # Performance tracking
        self._last_snapshot = 0.0
        self._request_times: List[float] = []
        self._provider_stats: Dict[str, Dict[str, int]] = {}
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Cache performance monitor initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache performance monitor: {e}")
            self.redis_client = None
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    async def record_cache_request(
        self, 
        provider: str, 
        model: str, 
        cache_hit: bool, 
        response_time_ms: float
    ):
        """
        Record a cache request for performance tracking.
        
        Args:
            provider: Embedding provider
            model: Embedding model
            cache_hit: Whether the request was a cache hit
            response_time_ms: Response time in milliseconds
        """
        if not self.redis_client:
            return
        
        try:
            # Record response time
            self._request_times.append(response_time_ms)
            
            # Keep only recent response times (last 1000 requests)
            if len(self._request_times) > 1000:
                self._request_times = self._request_times[-1000:]
            
            # Update provider stats
            provider_key = f"{provider}/{model}"
            if provider_key not in self._provider_stats:
                self._provider_stats[provider_key] = {
                    'hits': 0,
                    'misses': 0,
                    'requests': 0
                }
            
            self._provider_stats[provider_key]['requests'] += 1
            if cache_hit:
                self._provider_stats[provider_key]['hits'] += 1
            else:
                self._provider_stats[provider_key]['misses'] += 1
            
            # Take periodic snapshots
            current_time = time.time()
            if current_time - self._last_snapshot >= self.snapshot_interval:
                await self._take_performance_snapshot()
                self._last_snapshot = current_time
                
        except Exception as e:
            logger.error(f"Error recording cache request: {e}")
    
    async def _take_performance_snapshot(self):
        """Take a snapshot of current cache performance."""
        try:
            from .embedding_cache_service import get_embedding_cache_service
            
            # Get current cache stats
            cache_service = await get_embedding_cache_service()
            cache_stats = await cache_service.get_cache_stats()
            
            # Calculate average response time
            avg_response_time = 0.0
            if self._request_times:
                avg_response_time = sum(self._request_times) / len(self._request_times)
            
            # Create metrics snapshot
            metrics = CachePerformanceMetrics(
                timestamp=time.time(),
                total_requests=cache_stats.total_requests,
                cache_hits=cache_stats.cache_hits,
                cache_misses=cache_stats.cache_misses,
                hit_rate=cache_stats.hit_rate,
                avg_response_time_ms=avg_response_time,
                total_entries=cache_stats.total_entries,
                memory_usage_mb=cache_stats.memory_usage_mb,
                evictions=cache_stats.evictions,
                provider_stats=self._provider_stats.copy()
            )
            
            # Store current performance
            await self.redis_client.hset(
                self.performance_key,
                mapping=metrics.to_dict()
            )
            
            # Store in history with timestamp key
            history_key = f"{self.history_key_prefix}{int(metrics.timestamp)}"
            await self.redis_client.hset(
                history_key,
                mapping=metrics.to_dict()
            )
            
            # Set TTL for history entry
            await self.redis_client.expire(
                history_key, 
                self.metrics_retention_days * 24 * 3600
            )
            
            # Clean up old provider stats
            self._provider_stats.clear()
            self._request_times.clear()
            
        except Exception as e:
            logger.error(f"Error taking performance snapshot: {e}")
    
    async def get_current_performance(self) -> Optional[CachePerformanceMetrics]:
        """
        Get current cache performance metrics.
        
        Returns:
            Current performance metrics or None if not available
        """
        if not self.redis_client:
            return None
        
        try:
            metrics_data = await self.redis_client.hgetall(self.performance_key)
            
            if not metrics_data:
                return None
            
            # Convert string values back to appropriate types
            converted_data = {}
            for key, value in metrics_data.items():
                if key in ['timestamp', 'hit_rate', 'avg_response_time_ms', 'memory_usage_mb']:
                    converted_data[key] = float(value)
                elif key in ['total_requests', 'cache_hits', 'cache_misses', 'total_entries', 'evictions']:
                    converted_data[key] = int(value)
                elif key == 'provider_stats':
                    import json
                    converted_data[key] = json.loads(value) if value else {}
                else:
                    converted_data[key] = value
            
            return CachePerformanceMetrics.from_dict(converted_data)
            
        except Exception as e:
            logger.error(f"Error getting current performance: {e}")
            return None
    
    async def get_performance_history(
        self, 
        hours: int = 24
    ) -> List[CachePerformanceMetrics]:
        """
        Get cache performance history for the specified time period.
        
        Args:
            hours: Number of hours of history to retrieve
            
        Returns:
            List of performance metrics ordered by timestamp
        """
        if not self.redis_client:
            return []
        
        try:
            # Calculate time range
            end_time = time.time()
            start_time = end_time - (hours * 3600)
            
            # Get all history keys
            history_keys = await self.redis_client.keys(f"{self.history_key_prefix}*")
            
            # Filter keys by timestamp
            valid_keys = []
            for key in history_keys:
                try:
                    timestamp_str = key.replace(self.history_key_prefix, "")
                    timestamp = float(timestamp_str)
                    if start_time <= timestamp <= end_time:
                        valid_keys.append((key, timestamp))
                except ValueError:
                    continue
            
            # Sort by timestamp
            valid_keys.sort(key=lambda x: x[1])
            
            # Retrieve metrics data
            metrics_list = []
            for key, timestamp in valid_keys:
                try:
                    metrics_data = await self.redis_client.hgetall(key)
                    if metrics_data:
                        # Convert string values back to appropriate types
                        converted_data = {}
                        for field, value in metrics_data.items():
                            if field in ['timestamp', 'hit_rate', 'avg_response_time_ms', 'memory_usage_mb']:
                                converted_data[field] = float(value)
                            elif field in ['total_requests', 'cache_hits', 'cache_misses', 'total_entries', 'evictions']:
                                converted_data[field] = int(value)
                            elif field == 'provider_stats':
                                import json
                                converted_data[field] = json.loads(value) if value else {}
                            else:
                                converted_data[field] = value
                        
                        metrics_list.append(CachePerformanceMetrics.from_dict(converted_data))
                        
                except Exception as e:
                    logger.warning(f"Error parsing metrics from {key}: {e}")
                    continue
            
            return metrics_list
            
        except Exception as e:
            logger.error(f"Error getting performance history: {e}")
            return []
    
    async def analyze_hit_rate_trends(self) -> CacheHitRateAnalysis:
        """
        Analyze cache hit rate trends and provide recommendations.
        
        Returns:
            Hit rate analysis with trends and recommendations
        """
        try:
            # Get current performance
            current_metrics = await self.get_current_performance()
            current_hit_rate = current_metrics.hit_rate if current_metrics else 0.0
            
            # Get 24-hour history
            history_24h = await self.get_performance_history(24)
            avg_hit_rate_24h = 0.0
            if history_24h:
                avg_hit_rate_24h = sum(m.hit_rate for m in history_24h) / len(history_24h)
            
            # Get 7-day history
            history_7d = await self.get_performance_history(24 * 7)
            avg_hit_rate_7d = 0.0
            if history_7d:
                avg_hit_rate_7d = sum(m.hit_rate for m in history_7d) / len(history_7d)
            
            # Determine trend
            trend = "stable"
            if current_hit_rate > avg_hit_rate_24h + 0.05:
                trend = "improving"
            elif current_hit_rate < avg_hit_rate_24h - 0.05:
                trend = "declining"
            
            # Generate recommendations
            recommendations = []
            
            if current_hit_rate < 0.3:
                recommendations.append("Cache hit rate is very low. Consider increasing cache TTL or reviewing cache invalidation policies.")
            elif current_hit_rate < 0.5:
                recommendations.append("Cache hit rate could be improved. Review frequently accessed content patterns.")
            
            if trend == "declining":
                recommendations.append("Cache hit rate is declining. Check for recent configuration changes or increased cache invalidation.")
            
            if current_metrics and current_metrics.evictions > 0:
                recommendations.append("Cache evictions detected. Consider increasing cache size limit.")
            
            if not recommendations:
                recommendations.append("Cache performance is good. Continue monitoring for optimization opportunities.")
            
            return CacheHitRateAnalysis(
                current_hit_rate=current_hit_rate,
                avg_hit_rate_24h=avg_hit_rate_24h,
                avg_hit_rate_7d=avg_hit_rate_7d,
                trend=trend,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error analyzing hit rate trends: {e}")
            return CacheHitRateAnalysis(
                current_hit_rate=0.0,
                avg_hit_rate_24h=0.0,
                avg_hit_rate_7d=0.0,
                trend="unknown",
                recommendations=["Error analyzing cache performance. Check system logs."]
            )
    
    async def get_provider_performance_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """
        Get cache performance breakdown by provider and model.
        
        Returns:
            Dictionary with provider/model performance statistics
        """
        try:
            current_metrics = await self.get_current_performance()
            
            if not current_metrics or not current_metrics.provider_stats:
                return {}
            
            breakdown = {}
            
            for provider_model, stats in current_metrics.provider_stats.items():
                requests = stats.get('requests', 0)
                hits = stats.get('hits', 0)
                misses = stats.get('misses', 0)
                
                hit_rate = hits / requests if requests > 0 else 0.0
                
                breakdown[provider_model] = {
                    'requests': requests,
                    'hits': hits,
                    'misses': misses,
                    'hit_rate': hit_rate,
                    'performance_rating': self._calculate_performance_rating(hit_rate, requests)
                }
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Error getting provider performance breakdown: {e}")
            return {}
    
    def _calculate_performance_rating(self, hit_rate: float, requests: int) -> str:
        """
        Calculate performance rating based on hit rate and request volume.
        
        Args:
            hit_rate: Cache hit rate (0.0 to 1.0)
            requests: Number of requests
            
        Returns:
            Performance rating string
        """
        if requests < 10:
            return "insufficient_data"
        elif hit_rate >= 0.8:
            return "excellent"
        elif hit_rate >= 0.6:
            return "good"
        elif hit_rate >= 0.4:
            return "fair"
        else:
            return "poor"
    
    async def cleanup_old_metrics(self):
        """Clean up old performance metrics beyond retention period."""
        try:
            cutoff_time = time.time() - (self.metrics_retention_days * 24 * 3600)
            
            # Get all history keys
            history_keys = await self.redis_client.keys(f"{self.history_key_prefix}*")
            
            deleted_count = 0
            for key in history_keys:
                try:
                    timestamp_str = key.replace(self.history_key_prefix, "")
                    timestamp = float(timestamp_str)
                    
                    if timestamp < cutoff_time:
                        await self.redis_client.delete(key)
                        deleted_count += 1
                        
                except ValueError:
                    # Invalid timestamp format, delete it
                    await self.redis_client.delete(key)
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old cache metrics")
                
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")


# Global performance monitor instance
_performance_monitor: Optional[CachePerformanceMonitor] = None


async def get_cache_performance_monitor() -> CachePerformanceMonitor:
    """
    Get the global cache performance monitor instance.
    
    Returns:
        Initialized cache performance monitor
    """
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = CachePerformanceMonitor()
        await _performance_monitor.initialize()
    
    return _performance_monitor


async def close_cache_performance_monitor():
    """Close the global cache performance monitor."""
    global _performance_monitor
    
    if _performance_monitor:
        await _performance_monitor.close()
        _performance_monitor = None