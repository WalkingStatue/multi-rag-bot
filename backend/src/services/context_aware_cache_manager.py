"""
Context-Aware Cache Manager for Hybrid Retrieval System

This module implements intelligent caching strategies that consider context,
query characteristics, and temporal relevance for optimal cache performance.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from collections import OrderedDict, deque
import redis.asyncio as redis
import pickle

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategies for different content types."""
    AGGRESSIVE = "aggressive"  # Cache everything, long TTL
    MODERATE = "moderate"  # Cache selectively, medium TTL
    CONSERVATIVE = "conservative"  # Cache minimally, short TTL
    ADAPTIVE = "adaptive"  # Adjust based on usage patterns
    CONTEXT_SENSITIVE = "context_sensitive"  # Consider context heavily


class CacheInvalidationReason(Enum):
    """Reasons for cache invalidation."""
    TTL_EXPIRED = "ttl_expired"
    DOCUMENT_UPDATED = "document_updated"
    BOT_CONFIG_CHANGED = "bot_config_changed"
    CONTEXT_DRIFT = "context_drift"
    MANUAL_FLUSH = "manual_flush"
    LOW_HIT_RATE = "low_hit_rate"
    MEMORY_PRESSURE = "memory_pressure"


@dataclass
class CacheEntry:
    """Represents a cached hybrid response."""
    key: str
    content: str
    mode_used: str
    sources: List[str]
    query_hash: str
    context_hash: str
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: int = 3600  # Default 1 hour
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.created_at > self.ttl
    
    def update_access(self):
        """Update access statistics."""
        self.accessed_at = time.time()
        self.access_count += 1


@dataclass
class CacheStatistics:
    """Cache performance statistics."""
    total_hits: int = 0
    total_misses: int = 0
    total_evictions: int = 0
    total_invalidations: int = 0
    average_hit_rate: float = 0.0
    cache_size_bytes: int = 0
    entry_count: int = 0
    invalidation_reasons: Dict[str, int] = field(default_factory=dict)
    
    @property
    def hit_rate(self) -> float:
        """Calculate current hit rate."""
        total = self.total_hits + self.total_misses
        return self.total_hits / total if total > 0 else 0.0


class ContextualCacheKey:
    """Generates context-aware cache keys."""
    
    @staticmethod
    def generate(
        query: str,
        bot_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_depth: int = 0
    ) -> str:
        """
        Generate a context-aware cache key.
        
        Args:
            query: User query
            bot_id: Bot identifier
            user_id: User identifier
            context: Additional context
            conversation_depth: Depth of conversation
            
        Returns:
            Unique cache key
        """
        # Create base key components
        key_components = {
            "query": query.lower().strip(),
            "bot_id": str(bot_id),
            "user_id": str(user_id),
            "conv_depth": min(conversation_depth, 5)  # Cap depth for key stability
        }
        
        # Add relevant context
        if context:
            # Only include stable context elements
            stable_context = {
                "intent": context.get("intent"),
                "domain": context.get("domain"),
                "complexity_tier": int(context.get("complexity", 0) * 10) / 10  # Round to tier
            }
            key_components["context"] = stable_context
        
        # Generate hash
        key_string = json.dumps(key_components, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        return f"hybrid_cache:{bot_id}:{key_hash}"
    
    @staticmethod
    def generate_context_hash(context: Dict[str, Any]) -> str:
        """Generate hash for context comparison."""
        context_string = json.dumps(context, sort_keys=True, default=str)
        return hashlib.md5(context_string.encode()).hexdigest()[:8]


class AdaptiveTTLCalculator:
    """Calculates adaptive TTL based on content characteristics."""
    
    def __init__(self):
        """Initialize TTL calculator."""
        self.base_ttl = 3600  # 1 hour base
        self.min_ttl = 300  # 5 minutes minimum
        self.max_ttl = 86400  # 24 hours maximum
    
    def calculate_ttl(
        self,
        query_characteristics: Dict[str, Any],
        content_type: str,
        confidence_score: float,
        temporal_relevance: float
    ) -> int:
        """
        Calculate adaptive TTL for cache entry.
        
        Args:
            query_characteristics: Query analysis results
            content_type: Type of content
            confidence_score: Confidence in response
            temporal_relevance: How time-sensitive the content is
            
        Returns:
            TTL in seconds
        """
        ttl = self.base_ttl
        
        # Adjust for temporal relevance
        if temporal_relevance > 0.7:
            ttl *= 0.25  # Very time-sensitive, short cache
        elif temporal_relevance > 0.4:
            ttl *= 0.5  # Moderately time-sensitive
        
        # Adjust for confidence
        if confidence_score > 0.9:
            ttl *= 1.5  # High confidence, longer cache
        elif confidence_score < 0.5:
            ttl *= 0.5  # Low confidence, shorter cache
        
        # Adjust for content type
        content_multipliers = {
            "factual": 2.0,  # Facts change slowly
            "conversational": 0.3,  # Conversations are dynamic
            "analytical": 1.0,  # Standard caching
            "creative": 0.5,  # Creative content is unique
        }
        
        content_multiplier = content_multipliers.get(content_type, 1.0)
        ttl *= content_multiplier
        
        # Ensure within bounds
        return max(self.min_ttl, min(int(ttl), self.max_ttl))


class ContextDriftDetector:
    """Detects when context has drifted significantly."""
    
    def __init__(self, drift_threshold: float = 0.3):
        """
        Initialize drift detector.
        
        Args:
            drift_threshold: Threshold for detecting significant drift
        """
        self.drift_threshold = drift_threshold
        self.context_history = deque(maxlen=10)
    
    def detect_drift(
        self,
        current_context: Dict[str, Any],
        cached_context_hash: str
    ) -> bool:
        """
        Detect if context has drifted significantly.
        
        Args:
            current_context: Current context
            cached_context_hash: Hash of cached context
            
        Returns:
            True if significant drift detected
        """
        current_hash = ContextualCacheKey.generate_context_hash(current_context)
        
        # Simple hash comparison
        if current_hash != cached_context_hash:
            # Calculate drift score based on context differences
            drift_score = self._calculate_drift_score(current_context)
            return drift_score > self.drift_threshold
        
        return False
    
    def _calculate_drift_score(self, current_context: Dict[str, Any]) -> float:
        """Calculate drift score from context history."""
        if not self.context_history:
            self.context_history.append(current_context)
            return 0.0
        
        # Compare with recent contexts
        differences = []
        for hist_context in self.context_history:
            diff = self._context_difference(current_context, hist_context)
            differences.append(diff)
        
        # Add current to history
        self.context_history.append(current_context)
        
        # Return average difference
        return sum(differences) / len(differences) if differences else 0.0
    
    def _context_difference(self, ctx1: Dict, ctx2: Dict) -> float:
        """Calculate difference between two contexts."""
        diff_score = 0.0
        total_keys = set(ctx1.keys()) | set(ctx2.keys())
        
        for key in total_keys:
            val1 = ctx1.get(key)
            val2 = ctx2.get(key)
            
            if val1 != val2:
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    # Numerical difference
                    diff_score += abs(val1 - val2) / max(abs(val1), abs(val2), 1)
                else:
                    # Categorical difference
                    diff_score += 1.0
        
        return diff_score / len(total_keys) if total_keys else 0.0


class ContextAwareCacheManager:
    """
    Manages intelligent caching for hybrid retrieval system with context awareness.
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
        max_memory_mb: int = 512
    ):
        """
        Initialize context-aware cache manager.
        
        Args:
            redis_client: Redis client for distributed caching
            strategy: Default caching strategy
            max_memory_mb: Maximum memory usage in MB
        """
        self.redis_client = redis_client
        self.strategy = strategy
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # Local cache for fast access
        self.local_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_local_entries = 1000
        
        # Components
        self.ttl_calculator = AdaptiveTTLCalculator()
        self.drift_detector = ContextDriftDetector()
        
        # Statistics
        self.statistics = CacheStatistics()
        
        # Invalidation tracking
        self.invalidation_queue: deque = deque(maxlen=100)
        
        # Background tasks
        self._cleanup_task = None
    
    async def initialize(self):
        """Initialize cache manager and start background tasks."""
        if self.redis_client:
            await self.redis_client.ping()
            logger.info("Connected to Redis for distributed caching")
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Context-aware cache manager initialized")
    
    async def get(
        self,
        query: str,
        bot_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_depth: int = 0
    ) -> Optional[CacheEntry]:
        """
        Get cached response if available and valid.
        
        Args:
            query: User query
            bot_id: Bot identifier
            user_id: User identifier
            context: Current context
            conversation_depth: Conversation depth
            
        Returns:
            Cached entry if found and valid, None otherwise
        """
        # Generate cache key
        cache_key = ContextualCacheKey.generate(
            query, bot_id, user_id, context, conversation_depth
        )
        
        # Check local cache first
        if cache_key in self.local_cache:
            entry = self.local_cache[cache_key]
            
            # Validate entry
            if self._validate_entry(entry, context):
                entry.update_access()
                self.statistics.total_hits += 1
                
                # Move to end (LRU)
                self.local_cache.move_to_end(cache_key)
                
                logger.debug(f"Cache hit for key: {cache_key}")
                return entry
            else:
                # Invalid entry, remove it
                await self._invalidate_entry(cache_key, CacheInvalidationReason.CONTEXT_DRIFT)
        
        # Check Redis if available
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    entry = pickle.loads(cached_data)
                    
                    if self._validate_entry(entry, context):
                        entry.update_access()
                        self.statistics.total_hits += 1
                        
                        # Add to local cache
                        await self._add_to_local_cache(cache_key, entry)
                        
                        logger.debug(f"Redis cache hit for key: {cache_key}")
                        return entry
                    else:
                        await self._invalidate_entry(cache_key, CacheInvalidationReason.CONTEXT_DRIFT)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        self.statistics.total_misses += 1
        logger.debug(f"Cache miss for key: {cache_key}")
        return None
    
    async def set(
        self,
        query: str,
        bot_id: str,
        user_id: str,
        response: Any,
        context: Optional[Dict[str, Any]] = None,
        conversation_depth: int = 0,
        query_characteristics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Cache a hybrid response with context awareness.
        
        Args:
            query: User query
            bot_id: Bot identifier
            user_id: User identifier
            response: Hybrid response to cache
            context: Context information
            conversation_depth: Conversation depth
            query_characteristics: Query analysis results
            
        Returns:
            True if successfully cached
        """
        # Determine if response should be cached
        if not self._should_cache(response, query_characteristics):
            logger.debug("Response not suitable for caching")
            return False
        
        # Generate cache key
        cache_key = ContextualCacheKey.generate(
            query, bot_id, user_id, context, conversation_depth
        )
        
        # Calculate adaptive TTL
        ttl = self.ttl_calculator.calculate_ttl(
            query_characteristics or {},
            context.get("intent", "unknown") if context else "unknown",
            response.confidence_score if hasattr(response, 'confidence_score') else 0.5,
            query_characteristics.get("temporal_relevance", 0.0) if query_characteristics else 0.0
        )
        
        # Create cache entry
        entry = CacheEntry(
            key=cache_key,
            content=response.content if hasattr(response, 'content') else str(response),
            mode_used=response.mode_used.value if hasattr(response, 'mode_used') else "unknown",
            sources=response.sources_used if hasattr(response, 'sources_used') else [],
            query_hash=hashlib.md5(query.encode()).hexdigest()[:8],
            context_hash=ContextualCacheKey.generate_context_hash(context) if context else "",
            created_at=time.time(),
            accessed_at=time.time(),
            ttl=ttl,
            confidence_score=response.confidence_score if hasattr(response, 'confidence_score') else 0.5,
            metadata={
                "query_characteristics": query_characteristics,
                "context": context,
                "conversation_depth": conversation_depth
            }
        )
        
        # Add to local cache
        await self._add_to_local_cache(cache_key, entry)
        
        # Add to Redis if available
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    ttl,
                    pickle.dumps(entry)
                )
                logger.debug(f"Cached to Redis with TTL {ttl}s: {cache_key}")
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        self.statistics.entry_count += 1
        logger.debug(f"Cached response with TTL {ttl}s: {cache_key}")
        return True
    
    def _should_cache(
        self,
        response: Any,
        query_characteristics: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if response should be cached."""
        # Don't cache low confidence responses
        if hasattr(response, 'confidence_score') and response.confidence_score < 0.3:
            return False
        
        # Don't cache pure conversational responses
        if query_characteristics and query_characteristics.get("intent") == "conversational":
            if query_characteristics.get("conversation_depth", 0) < 2:
                return False
        
        # Don't cache if explicitly marked as non-cacheable
        if hasattr(response, 'metadata') and response.metadata.get("no_cache"):
            return False
        
        # Apply strategy-specific rules
        if self.strategy == CacheStrategy.CONSERVATIVE:
            # Only cache high confidence, non-temporal content
            if hasattr(response, 'confidence_score') and response.confidence_score < 0.7:
                return False
            if query_characteristics and query_characteristics.get("temporal_relevance", 0) > 0.5:
                return False
        
        return True
    
    def _validate_entry(
        self,
        entry: CacheEntry,
        current_context: Optional[Dict[str, Any]]
    ) -> bool:
        """Validate cache entry against current context."""
        # Check TTL
        if entry.is_expired():
            return False
        
        # Check context drift
        if current_context and entry.context_hash:
            if self.drift_detector.detect_drift(current_context, entry.context_hash):
                return False
        
        # Check hit rate (adaptive strategy)
        if self.strategy == CacheStrategy.ADAPTIVE:
            if entry.access_count > 5:
                hit_rate = entry.access_count / max(time.time() - entry.created_at, 1)
                if hit_rate < 0.001:  # Less than 1 hit per 1000 seconds
                    return False
        
        return True
    
    async def _add_to_local_cache(self, key: str, entry: CacheEntry):
        """Add entry to local cache with LRU eviction."""
        # Check memory pressure
        if len(self.local_cache) >= self.max_local_entries:
            # Evict least recently used
            evicted_key, evicted_entry = self.local_cache.popitem(last=False)
            self.statistics.total_evictions += 1
            logger.debug(f"Evicted from local cache: {evicted_key}")
        
        self.local_cache[key] = entry
    
    async def _invalidate_entry(
        self,
        key: str,
        reason: CacheInvalidationReason
    ):
        """Invalidate a cache entry."""
        # Remove from local cache
        if key in self.local_cache:
            del self.local_cache[key]
        
        # Remove from Redis
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        # Track invalidation
        self.statistics.total_invalidations += 1
        self.statistics.invalidation_reasons[reason.value] = \
            self.statistics.invalidation_reasons.get(reason.value, 0) + 1
        
        # Add to invalidation queue
        self.invalidation_queue.append({
            "key": key,
            "reason": reason.value,
            "timestamp": time.time()
        })
        
        logger.debug(f"Invalidated cache entry: {key} (reason: {reason.value})")
    
    async def invalidate_bot_cache(self, bot_id: str):
        """Invalidate all cache entries for a bot."""
        pattern = f"hybrid_cache:{bot_id}:*"
        
        # Clear from local cache
        keys_to_remove = [k for k in self.local_cache.keys() if k.startswith(f"hybrid_cache:{bot_id}:")]
        for key in keys_to_remove:
            await self._invalidate_entry(key, CacheInvalidationReason.BOT_CONFIG_CHANGED)
        
        # Clear from Redis
        if self.redis_client:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor, match=pattern, count=100
                    )
                    if keys:
                        await self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
                logger.info(f"Invalidated all cache entries for bot {bot_id}")
            except Exception as e:
                logger.error(f"Redis pattern delete error: {e}")
    
    async def invalidate_document_cache(self, bot_id: str, document_id: str):
        """Invalidate cache entries related to a specific document."""
        # This would require tracking which cache entries use which documents
        # For now, invalidate all bot cache when document changes
        await self.invalidate_bot_cache(bot_id)
        logger.info(f"Invalidated cache for document {document_id} in bot {bot_id}")
    
    async def _periodic_cleanup(self):
        """Periodically clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Clean local cache
                expired_keys = []
                for key, entry in self.local_cache.items():
                    if entry.is_expired():
                        expired_keys.append(key)
                
                for key in expired_keys:
                    await self._invalidate_entry(key, CacheInvalidationReason.TTL_EXPIRED)
                
                # Update statistics
                self.statistics.average_hit_rate = self.statistics.hit_rate
                self.statistics.cache_size_bytes = sum(
                    len(pickle.dumps(entry)) for entry in self.local_cache.values()
                )
                
                # Check memory pressure
                if self.statistics.cache_size_bytes > self.max_memory_bytes:
                    # Evict entries with lowest access rates
                    entries_by_access = sorted(
                        self.local_cache.items(),
                        key=lambda x: x[1].access_count / max(time.time() - x[1].created_at, 1)
                    )
                    
                    # Evict bottom 20%
                    evict_count = len(entries_by_access) // 5
                    for key, _ in entries_by_access[:evict_count]:
                        await self._invalidate_entry(key, CacheInvalidationReason.MEMORY_PRESSURE)
                
                logger.info(f"Cache cleanup: {len(expired_keys)} expired, "
                          f"hit_rate={self.statistics.hit_rate:.2%}, "
                          f"size={self.statistics.cache_size_bytes / 1024 / 1024:.1f}MB")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "hit_rate": self.statistics.hit_rate,
            "total_hits": self.statistics.total_hits,
            "total_misses": self.statistics.total_misses,
            "total_evictions": self.statistics.total_evictions,
            "total_invalidations": self.statistics.total_invalidations,
            "entry_count": len(self.local_cache),
            "cache_size_mb": self.statistics.cache_size_bytes / 1024 / 1024,
            "invalidation_reasons": self.statistics.invalidation_reasons,
            "recent_invalidations": list(self.invalidation_queue)[-10:]
        }
    
    def get_strategy_recommendation(
        self,
        recent_performance: Dict[str, float]
    ) -> CacheStrategy:
        """Recommend optimal cache strategy based on performance."""
        hit_rate = recent_performance.get("hit_rate", 0)
        avg_response_time = recent_performance.get("avg_response_time", 0)
        temporal_content_ratio = recent_performance.get("temporal_ratio", 0)
        
        if hit_rate > 0.7 and temporal_content_ratio < 0.3:
            return CacheStrategy.AGGRESSIVE
        elif hit_rate > 0.5:
            return CacheStrategy.MODERATE
        elif temporal_content_ratio > 0.6:
            return CacheStrategy.CONSERVATIVE
        else:
            return CacheStrategy.ADAPTIVE
    
    async def optimize_cache_parameters(self):
        """Optimize cache parameters based on usage patterns."""
        # Analyze recent performance
        if self.statistics.hit_rate < 0.3 and self.strategy != CacheStrategy.CONSERVATIVE:
            logger.info("Low hit rate detected, switching to conservative strategy")
            self.strategy = CacheStrategy.CONSERVATIVE
        elif self.statistics.hit_rate > 0.7 and self.strategy != CacheStrategy.AGGRESSIVE:
            logger.info("High hit rate detected, switching to aggressive strategy")
            self.strategy = CacheStrategy.AGGRESSIVE
        
        # Adjust TTL calculator based on invalidation patterns
        if self.statistics.invalidation_reasons.get(CacheInvalidationReason.CONTEXT_DRIFT.value, 0) > 50:
            self.ttl_calculator.base_ttl = max(self.ttl_calculator.base_ttl * 0.8, 600)
            logger.info(f"High context drift, reduced base TTL to {self.ttl_calculator.base_ttl}")
    
    async def close(self):
        """Close cache manager and clean up resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Context-aware cache manager closed")
