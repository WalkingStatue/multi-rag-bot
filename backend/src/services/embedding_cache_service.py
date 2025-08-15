"""
Intelligent embedding cache service with content-based hashing and LRU eviction.
"""
import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import redis.asyncio as redis
from dataclasses import dataclass, asdict
from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingCacheEntry:
    """Represents a cached embedding entry."""
    text_hash: str
    provider: str
    model: str
    embedding: List[float]
    created_at: float
    access_count: int
    last_accessed: float
    text_length: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddingCacheEntry':
        """Create from dictionary loaded from Redis."""
        return cls(**data)


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_entries: int = 0
    memory_usage_mb: float = 0.0
    hit_rate: float = 0.0
    evictions: int = 0
    
    def calculate_hit_rate(self):
        """Calculate and update hit rate."""
        if self.total_requests > 0:
            self.hit_rate = self.cache_hits / self.total_requests
        else:
            self.hit_rate = 0.0


class EmbeddingCacheService:
    """
    Intelligent embedding cache service with content-based hashing and LRU eviction.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the embedding cache service.
        
        Args:
            redis_url: Redis connection URL. Uses settings default if None.
        """
        self.redis_url = redis_url or settings.redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # Cache configuration
        self.cache_prefix = "embedding_cache:"
        self.stats_key = "embedding_cache:stats"
        self.max_cache_size = 10000  # Maximum number of cached embeddings
        self.default_ttl = 86400 * 7  # 7 days in seconds
        self.cleanup_interval = 3600  # 1 hour in seconds
        
        # Performance tracking
        self.stats = CacheStats()
        self._last_cleanup = time.time()
        
        # Text normalization settings
        self.normalize_whitespace = True
        self.case_sensitive = False
    
    async def initialize(self):
        """Initialize Redis connection and load stats."""
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
            logger.info("Connected to Redis for embedding cache")
            
            # Load existing stats
            await self._load_stats()
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            self.redis_client = None
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for consistent caching.
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        normalized = text
        
        if self.normalize_whitespace:
            # Normalize whitespace
            normalized = " ".join(normalized.split())
        
        if not self.case_sensitive:
            normalized = normalized.lower()
        
        return normalized.strip()
    
    def _generate_cache_key(self, text: str, provider: str, model: str) -> str:
        """
        Generate content-based cache key using SHA-256 hash.
        
        Args:
            text: Text content
            provider: Embedding provider
            model: Embedding model
            
        Returns:
            Cache key string
        """
        # Normalize text for consistent hashing
        normalized_text = self._normalize_text(text)
        
        # Create hash input combining text, provider, and model
        hash_input = f"{normalized_text}|{provider}|{model}"
        
        # Generate SHA-256 hash
        text_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        
        return f"{self.cache_prefix}{text_hash}"
    
    def _generate_text_hash(self, text: str) -> str:
        """
        Generate hash for text content only.
        
        Args:
            text: Text content
            
        Returns:
            Text hash string
        """
        normalized_text = self._normalize_text(text)
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
    
    async def get_cached_embedding(
        self, 
        text: str, 
        provider: str, 
        model: str
    ) -> Optional[List[float]]:
        """
        Retrieve cached embedding if available.
        
        Args:
            text: Text to get embedding for
            provider: Embedding provider
            model: Embedding model
            
        Returns:
            Cached embedding vector or None if not found
        """
        if not self.redis_client or not text.strip():
            return None
        
        try:
            cache_key = self._generate_cache_key(text, provider, model)
            
            # Get cached entry
            cached_data = await self.redis_client.hgetall(cache_key)
            
            if not cached_data:
                self.stats.cache_misses += 1
                self.stats.total_requests += 1
                return None
            
            # Parse cached entry
            entry = EmbeddingCacheEntry.from_dict({
                'text_hash': cached_data['text_hash'],
                'provider': cached_data['provider'],
                'model': cached_data['model'],
                'embedding': json.loads(cached_data['embedding']),
                'created_at': float(cached_data['created_at']),
                'access_count': int(cached_data['access_count']),
                'last_accessed': float(cached_data['last_accessed']),
                'text_length': int(cached_data['text_length'])
            })
            
            # Update access statistics
            entry.access_count += 1
            entry.last_accessed = time.time()
            
            # Update cache entry with new access stats
            await self.redis_client.hset(
                cache_key,
                mapping={
                    'access_count': entry.access_count,
                    'last_accessed': entry.last_accessed
                }
            )
            
            # Update performance stats
            self.stats.cache_hits += 1
            self.stats.total_requests += 1
            
            logger.debug(f"Cache hit for {provider}/{model}, text length: {len(text)}")
            
            return entry.embedding
            
        except Exception as e:
            logger.error(f"Error retrieving cached embedding: {e}")
            self.stats.cache_misses += 1
            self.stats.total_requests += 1
            return None
    
    async def cache_embedding(
        self,
        text: str,
        provider: str,
        model: str,
        embedding: List[float],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache an embedding with LRU eviction if needed.
        
        Args:
            text: Text that was embedded
            provider: Embedding provider
            model: Embedding model
            embedding: Embedding vector to cache
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            True if successfully cached, False otherwise
        """
        if not self.redis_client or not text.strip() or not embedding:
            return False
        
        try:
            cache_key = self._generate_cache_key(text, provider, model)
            text_hash = self._generate_text_hash(text)
            
            # Check if we need to evict entries first
            await self._ensure_cache_space()
            
            # Create cache entry
            entry = EmbeddingCacheEntry(
                text_hash=text_hash,
                provider=provider,
                model=model,
                embedding=embedding,
                created_at=time.time(),
                access_count=1,
                last_accessed=time.time(),
                text_length=len(text)
            )
            
            # Store in Redis with TTL
            cache_ttl = ttl or self.default_ttl
            
            await self.redis_client.hset(
                cache_key,
                mapping={
                    'text_hash': entry.text_hash,
                    'provider': entry.provider,
                    'model': entry.model,
                    'embedding': json.dumps(entry.embedding),
                    'created_at': entry.created_at,
                    'access_count': entry.access_count,
                    'last_accessed': entry.last_accessed,
                    'text_length': entry.text_length
                }
            )
            
            # Set TTL
            await self.redis_client.expire(cache_key, cache_ttl)
            
            logger.debug(f"Cached embedding for {provider}/{model}, text length: {len(text)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching embedding: {e}")
            return False
    
    async def get_cached_embeddings_batch(
        self,
        texts: List[str],
        provider: str,
        model: str
    ) -> Tuple[List[Optional[List[float]]], List[int]]:
        """
        Retrieve multiple cached embeddings efficiently.
        
        Args:
            texts: List of texts to get embeddings for
            provider: Embedding provider
            model: Embedding model
            
        Returns:
            Tuple of (embeddings_list, missing_indices)
            embeddings_list contains None for cache misses
            missing_indices contains indices of texts that need embedding
        """
        if not self.redis_client or not texts:
            return [None] * len(texts), list(range(len(texts)))
        
        embeddings = [None] * len(texts)
        missing_indices = []
        
        try:
            # Create pipeline for batch operations
            pipe = self.redis_client.pipeline()
            
            # Queue all cache key lookups
            cache_keys = []
            for i, text in enumerate(texts):
                if text.strip():
                    cache_key = self._generate_cache_key(text, provider, model)
                    cache_keys.append((i, cache_key))
                    pipe.hgetall(cache_key)
                else:
                    missing_indices.append(i)
            
            # Execute batch lookup
            results = await pipe.execute()
            
            # Process results
            update_pipe = self.redis_client.pipeline()
            
            for (text_idx, cache_key), cached_data in zip(cache_keys, results):
                if cached_data:
                    try:
                        # Parse cached entry
                        embedding = json.loads(cached_data['embedding'])
                        embeddings[text_idx] = embedding
                        
                        # Update access stats
                        access_count = int(cached_data['access_count']) + 1
                        last_accessed = time.time()
                        
                        update_pipe.hset(
                            cache_key,
                            mapping={
                                'access_count': access_count,
                                'last_accessed': last_accessed
                            }
                        )
                        
                        self.stats.cache_hits += 1
                        
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Invalid cache entry format: {e}")
                        missing_indices.append(text_idx)
                        self.stats.cache_misses += 1
                else:
                    missing_indices.append(text_idx)
                    self.stats.cache_misses += 1
            
            # Execute access count updates
            if update_pipe.command_stack:
                await update_pipe.execute()
            
            self.stats.total_requests += len(texts)
            
            logger.debug(
                f"Batch cache lookup: {len(texts) - len(missing_indices)}/{len(texts)} hits"
            )
            
        except Exception as e:
            logger.error(f"Error in batch cache lookup: {e}")
            # Return all as misses on error
            missing_indices = list(range(len(texts)))
            self.stats.cache_misses += len(texts)
            self.stats.total_requests += len(texts)
        
        return embeddings, missing_indices
    
    async def cache_embeddings_batch(
        self,
        texts: List[str],
        provider: str,
        model: str,
        embeddings: List[List[float]],
        ttl: Optional[int] = None
    ) -> int:
        """
        Cache multiple embeddings efficiently.
        
        Args:
            texts: List of texts that were embedded
            provider: Embedding provider
            model: Embedding model
            embeddings: List of embedding vectors to cache
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            Number of embeddings successfully cached
        """
        if not self.redis_client or len(texts) != len(embeddings):
            return 0
        
        try:
            # Check if we need to evict entries first
            await self._ensure_cache_space()
            
            # Create pipeline for batch operations
            pipe = self.redis_client.pipeline()
            cache_ttl = ttl or self.default_ttl
            cached_count = 0
            
            current_time = time.time()
            
            for text, embedding in zip(texts, embeddings):
                if not text.strip() or not embedding:
                    continue
                
                cache_key = self._generate_cache_key(text, provider, model)
                text_hash = self._generate_text_hash(text)
                
                # Create cache entry
                entry_data = {
                    'text_hash': text_hash,
                    'provider': provider,
                    'model': model,
                    'embedding': json.dumps(embedding),
                    'created_at': current_time,
                    'access_count': 1,
                    'last_accessed': current_time,
                    'text_length': len(text)
                }
                
                pipe.hset(cache_key, mapping=entry_data)
                pipe.expire(cache_key, cache_ttl)
                cached_count += 1
            
            # Execute batch operations
            if pipe.command_stack:
                await pipe.execute()
            
            logger.debug(f"Batch cached {cached_count} embeddings for {provider}/{model}")
            
            return cached_count
            
        except Exception as e:
            logger.error(f"Error in batch cache storage: {e}")
            return 0
    
    async def _ensure_cache_space(self):
        """Ensure cache doesn't exceed maximum size using LRU eviction."""
        try:
            # Get current cache size
            cache_keys = await self.redis_client.keys(f"{self.cache_prefix}*")
            current_size = len(cache_keys)
            
            if current_size >= self.max_cache_size:
                # Calculate how many entries to evict (10% of max size)
                evict_count = max(1, int(self.max_cache_size * 0.1))
                
                # Get entries with their last access times
                entries_with_access = []
                pipe = self.redis_client.pipeline()
                
                for key in cache_keys:
                    pipe.hget(key, 'last_accessed')
                
                access_times = await pipe.execute()
                
                for key, access_time in zip(cache_keys, access_times):
                    if access_time:
                        try:
                            entries_with_access.append((key, float(access_time)))
                        except (ValueError, TypeError):
                            # Invalid access time, mark for eviction
                            entries_with_access.append((key, 0.0))
                
                # Sort by last accessed time (oldest first)
                entries_with_access.sort(key=lambda x: x[1])
                
                # Evict oldest entries
                evict_keys = [key for key, _ in entries_with_access[:evict_count]]
                
                if evict_keys:
                    await self.redis_client.delete(*evict_keys)
                    self.stats.evictions += len(evict_keys)
                    
                    logger.info(f"Evicted {len(evict_keys)} old cache entries")
                
        except Exception as e:
            logger.error(f"Error during cache eviction: {e}")
    
    async def _load_stats(self):
        """Load cache statistics from Redis."""
        try:
            stats_data = await self.redis_client.hgetall(self.stats_key)
            
            if stats_data:
                self.stats.total_requests = int(stats_data.get('total_requests', 0))
                self.stats.cache_hits = int(stats_data.get('cache_hits', 0))
                self.stats.cache_misses = int(stats_data.get('cache_misses', 0))
                self.stats.evictions = int(stats_data.get('evictions', 0))
                self.stats.calculate_hit_rate()
                
        except Exception as e:
            logger.error(f"Error loading cache stats: {e}")
    
    async def _save_stats(self):
        """Save cache statistics to Redis."""
        try:
            self.stats.calculate_hit_rate()
            
            stats_data = {
                'total_requests': self.stats.total_requests,
                'cache_hits': self.stats.cache_hits,
                'cache_misses': self.stats.cache_misses,
                'evictions': self.stats.evictions,
                'hit_rate': self.stats.hit_rate,
                'last_updated': time.time()
            }
            
            await self.redis_client.hset(self.stats_key, mapping=stats_data)
            
        except Exception as e:
            logger.error(f"Error saving cache stats: {e}")
    
    async def get_cache_stats(self) -> CacheStats:
        """
        Get current cache performance statistics.
        
        Returns:
            Current cache statistics
        """
        try:
            # Update total entries count
            cache_keys = await self.redis_client.keys(f"{self.cache_prefix}*")
            self.stats.total_entries = len(cache_keys)
            
            # Estimate memory usage (rough calculation)
            if cache_keys:
                # Sample a few entries to estimate average size
                sample_size = min(10, len(cache_keys))
                sample_keys = cache_keys[:sample_size]
                
                total_sample_memory = 0
                for key in sample_keys:
                    memory_usage = await self.redis_client.memory_usage(key)
                    if memory_usage:
                        total_sample_memory += memory_usage
                
                if sample_size > 0:
                    avg_entry_size = total_sample_memory / sample_size
                    total_memory_bytes = avg_entry_size * len(cache_keys)
                    self.stats.memory_usage_mb = total_memory_bytes / (1024 * 1024)
            
            self.stats.calculate_hit_rate()
            
            # Save updated stats
            await self._save_stats()
            
        except Exception as e:
            logger.error(f"Error calculating cache stats: {e}")
        
        return self.stats
    
    async def clear_cache(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Clear cache entries, optionally filtered by provider/model.
        
        Args:
            provider: Optional provider filter
            model: Optional model filter
        """
        try:
            if provider is None and model is None:
                # Clear all cache entries
                cache_keys = await self.redis_client.keys(f"{self.cache_prefix}*")
                if cache_keys:
                    await self.redis_client.delete(*cache_keys)
                    logger.info(f"Cleared {len(cache_keys)} cache entries")
            else:
                # Filter by provider/model
                cache_keys = await self.redis_client.keys(f"{self.cache_prefix}*")
                keys_to_delete = []
                
                for key in cache_keys:
                    entry_data = await self.redis_client.hgetall(key)
                    if entry_data:
                        entry_provider = entry_data.get('provider')
                        entry_model = entry_data.get('model')
                        
                        should_delete = True
                        if provider and entry_provider != provider:
                            should_delete = False
                        if model and entry_model != model:
                            should_delete = False
                        
                        if should_delete:
                            keys_to_delete.append(key)
                
                if keys_to_delete:
                    await self.redis_client.delete(*keys_to_delete)
                    logger.info(f"Cleared {len(keys_to_delete)} cache entries for {provider}/{model}")
            
            # Reset stats if clearing all
            if provider is None and model is None:
                self.stats = CacheStats()
                await self._save_stats()
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    async def cleanup_expired_entries(self):
        """Clean up expired or invalid cache entries."""
        try:
            current_time = time.time()
            
            # Only run cleanup if enough time has passed
            if current_time - self._last_cleanup < self.cleanup_interval:
                return
            
            cache_keys = await self.redis_client.keys(f"{self.cache_prefix}*")
            cleaned_count = 0
            
            for key in cache_keys:
                try:
                    # Check if key still exists (might have expired)
                    exists = await self.redis_client.exists(key)
                    if not exists:
                        cleaned_count += 1
                        continue
                    
                    # Validate entry format
                    entry_data = await self.redis_client.hgetall(key)
                    if not entry_data or 'embedding' not in entry_data:
                        await self.redis_client.delete(key)
                        cleaned_count += 1
                        continue
                    
                    # Validate JSON format of embedding
                    try:
                        json.loads(entry_data['embedding'])
                    except json.JSONDecodeError:
                        await self.redis_client.delete(key)
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error validating cache entry {key}: {e}")
                    # Delete problematic entries
                    try:
                        await self.redis_client.delete(key)
                        cleaned_count += 1
                    except:
                        pass
            
            self._last_cleanup = current_time
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} invalid cache entries")
                
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")


# Global cache service instance
_cache_service: Optional[EmbeddingCacheService] = None


async def get_embedding_cache_service() -> EmbeddingCacheService:
    """
    Get the global embedding cache service instance.
    
    Returns:
        Initialized embedding cache service
    """
    global _cache_service
    
    if _cache_service is None:
        _cache_service = EmbeddingCacheService()
        await _cache_service.initialize()
    
    return _cache_service


async def close_embedding_cache_service():
    """Close the global embedding cache service."""
    global _cache_service
    
    if _cache_service:
        await _cache_service.close()
        _cache_service = None