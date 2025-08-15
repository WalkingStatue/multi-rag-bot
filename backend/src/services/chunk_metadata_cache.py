"""
Chunk metadata caching system to reduce database queries and optimize access patterns.
Implements requirements 6.3, 6.5 for task 7.2.
"""
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Set
from uuid import UUID
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

import redis
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..core.config import settings
from ..models.document import DocumentChunk
from ..services.optimized_chunk_storage import OptimizedChunkStorage

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Cached chunk metadata structure."""
    id: str
    document_id: str
    bot_id: str
    chunk_index: int
    content_length: int
    embedding_id: Optional[str]
    metadata: Dict[str, Any]
    created_at: str
    last_accessed: Optional[str] = None
    access_count: int = 0


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    total_cached_items: int
    memory_usage_mb: float


@dataclass
class AccessPattern:
    """Chunk access pattern analysis."""
    chunk_id: str
    access_count: int
    last_accessed: datetime
    access_frequency: float  # accesses per day
    is_hot: bool  # frequently accessed


class ChunkMetadataCache:
    """
    Chunk metadata caching system with access pattern analysis and optimization.
    """
    
    def __init__(
        self,
        db: Session,
        redis_client: Optional[redis.Redis] = None,
        cache_ttl: int = 3600,  # 1 hour default TTL
        max_cache_size: int = 10000  # Maximum cached items per bot
    ):
        """
        Initialize chunk metadata cache.
        
        Args:
            db: Database session
            redis_client: Redis client instance
            cache_ttl: Cache TTL in seconds
            max_cache_size: Maximum cached items per bot
        """
        self.db = db
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        
        # Initialize Redis client
        if redis_client:
            self.redis = redis_client
        else:
            try:
                redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379')
                self.redis = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis.ping()
                logger.info("Redis connection established for chunk metadata cache")
            except Exception as e:
                logger.warning(f"Redis not available, using in-memory cache: {e}")
                self.redis = None
        
        # In-memory fallback cache
        self._memory_cache: Dict[str, ChunkMetadata] = {}
        self._access_patterns: Dict[str, AccessPattern] = {}
        self._cache_stats = {
            'requests': 0,
            'hits': 0,
            'misses': 0
        }
    
    def _get_cache_key(self, chunk_id: str, prefix: str = "chunk_meta") -> str:
        """Generate cache key for chunk metadata."""
        return f"{prefix}:{chunk_id}"
    
    def _get_bot_cache_key(self, bot_id: str, prefix: str = "bot_chunks") -> str:
        """Generate cache key for bot's chunk list."""
        return f"{prefix}:{bot_id}"
    
    def _get_access_pattern_key(self, chunk_id: str) -> str:
        """Generate cache key for access patterns."""
        return f"access_pattern:{chunk_id}"
    
    async def get_chunk_metadata(
        self,
        chunk_id: str,
        include_content_length: bool = True
    ) -> Optional[ChunkMetadata]:
        """
        Get chunk metadata from cache or database.
        
        Args:
            chunk_id: Chunk identifier
            include_content_length: Whether to include content length
            
        Returns:
            ChunkMetadata if found, None otherwise
        """
        self._cache_stats['requests'] += 1
        cache_key = self._get_cache_key(chunk_id)
        
        # Try cache first
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            self._cache_stats['hits'] += 1
            metadata = ChunkMetadata(**cached_data)
            await self._update_access_pattern(chunk_id)
            return metadata
        
        # Cache miss - fetch from database
        self._cache_stats['misses'] += 1
        metadata = await self._fetch_chunk_metadata_from_db(chunk_id, include_content_length)
        
        if metadata:
            # Cache the result
            await self._set_in_cache(cache_key, asdict(metadata))
            await self._update_access_pattern(chunk_id)
        
        return metadata
    
    async def get_multiple_chunk_metadata(
        self,
        chunk_ids: List[str],
        include_content_length: bool = True
    ) -> Dict[str, ChunkMetadata]:
        """
        Get metadata for multiple chunks efficiently.
        
        Args:
            chunk_ids: List of chunk identifiers
            include_content_length: Whether to include content length
            
        Returns:
            Dictionary mapping chunk IDs to metadata
        """
        result = {}
        cache_misses = []
        
        # Check cache for all chunks
        for chunk_id in chunk_ids:
            self._cache_stats['requests'] += 1
            cache_key = self._get_cache_key(chunk_id)
            cached_data = await self._get_from_cache(cache_key)
            
            if cached_data:
                self._cache_stats['hits'] += 1
                result[chunk_id] = ChunkMetadata(**cached_data)
                await self._update_access_pattern(chunk_id)
            else:
                self._cache_stats['misses'] += 1
                cache_misses.append(chunk_id)
        
        # Fetch missing chunks from database in batch
        if cache_misses:
            db_metadata = await self._fetch_multiple_chunk_metadata_from_db(
                cache_misses, include_content_length
            )
            
            # Cache the results and update access patterns
            for chunk_id, metadata in db_metadata.items():
                result[chunk_id] = metadata
                cache_key = self._get_cache_key(chunk_id)
                await self._set_in_cache(cache_key, asdict(metadata))
                await self._update_access_pattern(chunk_id)
        
        return result
    
    async def cache_bot_chunks(self, bot_id: UUID, force_refresh: bool = False) -> int:
        """
        Pre-cache metadata for all chunks belonging to a bot.
        
        Args:
            bot_id: Bot identifier
            force_refresh: Whether to force refresh cached data
            
        Returns:
            Number of chunks cached
        """
        bot_cache_key = self._get_bot_cache_key(str(bot_id))
        
        # Check if bot chunks are already cached
        if not force_refresh:
            cached_chunk_ids = await self._get_from_cache(bot_cache_key)
            if cached_chunk_ids:
                logger.debug(f"Bot {bot_id} chunks already cached: {len(cached_chunk_ids)} chunks")
                return len(cached_chunk_ids)
        
        # Fetch all chunk metadata for the bot
        chunks = self.db.query(DocumentChunk).filter(
            DocumentChunk.bot_id == bot_id
        ).all()
        
        cached_count = 0
        chunk_ids = []
        
        # Cache each chunk's metadata
        for chunk in chunks:
            chunk_id = str(chunk.id)
            chunk_ids.append(chunk_id)
            
            metadata = ChunkMetadata(
                id=chunk_id,
                document_id=str(chunk.document_id),
                bot_id=str(chunk.bot_id),
                chunk_index=chunk.chunk_index,
                content_length=len(chunk.content) if chunk.content else 0,
                embedding_id=chunk.embedding_id,
                metadata=chunk.chunk_metadata or {},
                created_at=chunk.created_at.isoformat()
            )
            
            cache_key = self._get_cache_key(chunk_id)
            await self._set_in_cache(cache_key, asdict(metadata))
            cached_count += 1
        
        # Cache the list of chunk IDs for this bot
        await self._set_in_cache(bot_cache_key, chunk_ids, ttl=self.cache_ttl * 2)
        
        logger.info(f"Cached metadata for {cached_count} chunks for bot {bot_id}")
        return cached_count
    
    async def invalidate_chunk_cache(self, chunk_id: str) -> bool:
        """
        Invalidate cache for a specific chunk.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            True if cache was invalidated
        """
        cache_key = self._get_cache_key(chunk_id)
        access_key = self._get_access_pattern_key(chunk_id)
        
        success = True
        
        # Remove from cache
        if not await self._delete_from_cache(cache_key):
            success = False
        
        # Remove access pattern
        if not await self._delete_from_cache(access_key):
            success = False
        
        # Remove from memory cache
        if chunk_id in self._memory_cache:
            del self._memory_cache[chunk_id]
        
        if chunk_id in self._access_patterns:
            del self._access_patterns[chunk_id]
        
        return success
    
    async def invalidate_bot_cache(self, bot_id: UUID) -> int:
        """
        Invalidate all cached data for a bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Number of cache entries invalidated
        """
        bot_cache_key = self._get_bot_cache_key(str(bot_id))
        
        # Get list of cached chunk IDs
        cached_chunk_ids = await self._get_from_cache(bot_cache_key)
        if not cached_chunk_ids:
            return 0
        
        invalidated_count = 0
        
        # Invalidate each chunk's cache
        for chunk_id in cached_chunk_ids:
            if await self.invalidate_chunk_cache(chunk_id):
                invalidated_count += 1
        
        # Remove bot's chunk list cache
        await self._delete_from_cache(bot_cache_key)
        
        logger.info(f"Invalidated cache for {invalidated_count} chunks for bot {bot_id}")
        return invalidated_count
    
    async def update_chunk_metadata(
        self,
        chunk_id: str,
        updated_metadata: Dict[str, Any],
        maintain_consistency: bool = True
    ) -> bool:
        """
        Update chunk metadata in cache and optionally in database.
        
        Args:
            chunk_id: Chunk identifier
            updated_metadata: Updated metadata fields
            maintain_consistency: Whether to update database as well
            
        Returns:
            True if update successful
        """
        try:
            # Update database if consistency is required
            if maintain_consistency:
                chunk = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id == UUID(chunk_id)
                ).first()
                
                if not chunk:
                    return False
                
                # Update chunk metadata in database
                if 'chunk_metadata' in updated_metadata:
                    chunk.chunk_metadata = updated_metadata['chunk_metadata']
                
                self.db.commit()
            
            # Update cache
            cache_key = self._get_cache_key(chunk_id)
            cached_data = await self._get_from_cache(cache_key)
            
            if cached_data:
                # Update cached metadata
                for key, value in updated_metadata.items():
                    if key in cached_data:
                        cached_data[key] = value
                
                await self._set_in_cache(cache_key, cached_data)
            
            return True
            
        except Exception as e:
            if maintain_consistency:
                self.db.rollback()
            logger.error(f"Error updating chunk metadata for {chunk_id}: {e}")
            return False
    
    async def analyze_access_patterns(self, bot_id: UUID) -> Dict[str, Any]:
        """
        Analyze chunk access patterns for optimization recommendations.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Access pattern analysis and optimization recommendations
        """
        try:
            # Get all access patterns for bot's chunks
            bot_cache_key = self._get_bot_cache_key(str(bot_id))
            cached_chunk_ids = await self._get_from_cache(bot_cache_key)
            
            if not cached_chunk_ids:
                return {'error': 'No cached chunks found for bot'}
            
            access_patterns = []
            hot_chunks = []
            cold_chunks = []
            
            for chunk_id in cached_chunk_ids:
                pattern = await self._get_access_pattern(chunk_id)
                if pattern:
                    access_patterns.append(pattern)
                    
                    if pattern.is_hot:
                        hot_chunks.append(pattern)
                    elif pattern.access_count == 0:
                        cold_chunks.append(pattern)
            
            # Calculate statistics
            total_accesses = sum(p.access_count for p in access_patterns)
            avg_access_frequency = sum(p.access_frequency for p in access_patterns) / len(access_patterns) if access_patterns else 0
            
            # Generate recommendations
            recommendations = []
            
            if len(hot_chunks) > 0:
                recommendations.append(
                    f"Consider increasing cache TTL for {len(hot_chunks)} frequently accessed chunks"
                )
            
            if len(cold_chunks) > len(cached_chunk_ids) * 0.3:  # More than 30% cold
                recommendations.append(
                    f"Consider reducing cache size - {len(cold_chunks)} chunks are rarely accessed"
                )
            
            if avg_access_frequency > 10:  # High frequency
                recommendations.append(
                    "Consider implementing chunk pre-loading for this bot due to high access frequency"
                )
            
            return {
                'total_chunks': len(cached_chunk_ids),
                'analyzed_patterns': len(access_patterns),
                'hot_chunks': len(hot_chunks),
                'cold_chunks': len(cold_chunks),
                'total_accesses': total_accesses,
                'avg_access_frequency': avg_access_frequency,
                'recommendations': recommendations,
                'top_accessed_chunks': sorted(access_patterns, key=lambda x: x.access_count, reverse=True)[:10]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing access patterns for bot {bot_id}: {e}")
            return {'error': str(e)}
    
    async def optimize_cache_for_bot(self, bot_id: UUID) -> Dict[str, Any]:
        """
        Optimize cache configuration based on access patterns.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Optimization results and actions taken
        """
        try:
            analysis = await self.analyze_access_patterns(bot_id)
            
            if 'error' in analysis:
                return analysis
            
            actions_taken = []
            
            # Pre-cache hot chunks with longer TTL
            hot_chunks = analysis.get('top_accessed_chunks', [])[:20]  # Top 20
            for pattern in hot_chunks:
                if pattern.access_count > 5:  # Frequently accessed
                    cache_key = self._get_cache_key(pattern.chunk_id)
                    # Extend TTL for hot chunks
                    cached_data = await self._get_from_cache(cache_key)
                    if cached_data:
                        await self._set_in_cache(cache_key, cached_data, ttl=self.cache_ttl * 3)
                        actions_taken.append(f"Extended TTL for hot chunk {pattern.chunk_id[:8]}")
            
            # Remove cold chunks from cache to free memory
            cold_threshold = datetime.now() - timedelta(days=7)
            removed_cold = 0
            
            for pattern in analysis.get('top_accessed_chunks', []):
                if (pattern.access_count == 0 and 
                    pattern.last_accessed < cold_threshold):
                    await self.invalidate_chunk_cache(pattern.chunk_id)
                    removed_cold += 1
            
            if removed_cold > 0:
                actions_taken.append(f"Removed {removed_cold} cold chunks from cache")
            
            # Implement cache warming for frequently accessed bot
            if analysis.get('avg_access_frequency', 0) > 5:
                await self.cache_bot_chunks(bot_id, force_refresh=True)
                actions_taken.append("Warmed cache for high-frequency bot")
            
            return {
                'optimization_completed': True,
                'actions_taken': actions_taken,
                'cache_efficiency_improved': len(actions_taken) > 0,
                'analysis_summary': {
                    'total_chunks': analysis.get('total_chunks', 0),
                    'hot_chunks': analysis.get('hot_chunks', 0),
                    'cold_chunks': analysis.get('cold_chunks', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error optimizing cache for bot {bot_id}: {e}")
            return {'error': str(e)}
    
    async def get_cache_statistics(self) -> CacheStats:
        """
        Get cache performance statistics.
        
        Returns:
            CacheStats with performance metrics
        """
        try:
            total_requests = self._cache_stats['requests']
            cache_hits = self._cache_stats['hits']
            cache_misses = self._cache_stats['misses']
            hit_rate = cache_hits / total_requests if total_requests > 0 else 0.0
            
            # Get memory usage
            memory_usage_mb = 0.0
            if self.redis:
                try:
                    info = self.redis.info('memory')
                    memory_usage_mb = info.get('used_memory', 0) / (1024 * 1024)
                except:
                    pass
            else:
                # Estimate memory usage for in-memory cache
                memory_usage_mb = len(self._memory_cache) * 0.001  # Rough estimate
            
            total_cached_items = len(self._memory_cache)
            if self.redis:
                try:
                    total_cached_items = self.redis.dbsize()
                except:
                    pass
            
            return CacheStats(
                total_requests=total_requests,
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                hit_rate=hit_rate,
                total_cached_items=total_cached_items,
                memory_usage_mb=memory_usage_mb
            )
            
        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}")
            return CacheStats(0, 0, 0, 0.0, 0, 0.0)
    
    async def cleanup_expired_cache(self) -> int:
        """
        Clean up expired cache entries and optimize memory usage.
        
        Returns:
            Number of entries cleaned up
        """
        try:
            cleaned_count = 0
            
            if self.redis:
                # Redis handles TTL automatically, but we can clean up access patterns
                pattern_keys = []
                try:
                    pattern_keys = self.redis.keys("access_pattern:*")
                except:
                    pass
                
                for key in pattern_keys:
                    try:
                        # Check if the corresponding chunk cache exists
                        chunk_id = key.split(":", 1)[1]
                        chunk_cache_key = self._get_cache_key(chunk_id)
                        
                        if not self.redis.exists(chunk_cache_key):
                            self.redis.delete(key)
                            cleaned_count += 1
                    except:
                        continue
            else:
                # Clean up in-memory cache
                current_time = datetime.now()
                expired_keys = []
                
                for chunk_id, metadata in self._memory_cache.items():
                    # Simple TTL check (would need to track creation time in real implementation)
                    if chunk_id in self._access_patterns:
                        pattern = self._access_patterns[chunk_id]
                        if (current_time - pattern.last_accessed).total_seconds() > self.cache_ttl:
                            expired_keys.append(chunk_id)
                
                for key in expired_keys:
                    if key in self._memory_cache:
                        del self._memory_cache[key]
                    if key in self._access_patterns:
                        del self._access_patterns[key]
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired cache entries")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            return 0
    
    # Private helper methods
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache (Redis or memory)."""
        try:
            if self.redis:
                value = self.redis.get(key)
                return json.loads(value) if value else None
            else:
                return self._memory_cache.get(key)
        except Exception as e:
            logger.debug(f"Cache get error for key {key}: {e}")
            return None
    
    async def _set_in_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (Redis or memory)."""
        try:
            ttl = ttl or self.cache_ttl
            
            if self.redis:
                self.redis.setex(key, ttl, json.dumps(value, default=str))
            else:
                self._memory_cache[key] = value
                # Note: In-memory cache doesn't implement TTL in this simple version
            
            return True
        except Exception as e:
            logger.debug(f"Cache set error for key {key}: {e}")
            return False
    
    async def _delete_from_cache(self, key: str) -> bool:
        """Delete value from cache (Redis or memory)."""
        try:
            if self.redis:
                return bool(self.redis.delete(key))
            else:
                if key in self._memory_cache:
                    del self._memory_cache[key]
                    return True
                return False
        except Exception as e:
            logger.debug(f"Cache delete error for key {key}: {e}")
            return False
    
    async def _fetch_chunk_metadata_from_db(
        self,
        chunk_id: str,
        include_content_length: bool
    ) -> Optional[ChunkMetadata]:
        """Fetch chunk metadata from database."""
        try:
            chunk = self.db.query(DocumentChunk).filter(
                DocumentChunk.id == UUID(chunk_id)
            ).first()
            
            if not chunk:
                return None
            
            return ChunkMetadata(
                id=chunk_id,
                document_id=str(chunk.document_id),
                bot_id=str(chunk.bot_id),
                chunk_index=chunk.chunk_index,
                content_length=len(chunk.content) if include_content_length and chunk.content else 0,
                embedding_id=chunk.embedding_id,
                metadata=chunk.chunk_metadata or {},
                created_at=chunk.created_at.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error fetching chunk metadata from DB for {chunk_id}: {e}")
            return None
    
    async def _fetch_multiple_chunk_metadata_from_db(
        self,
        chunk_ids: List[str],
        include_content_length: bool
    ) -> Dict[str, ChunkMetadata]:
        """Fetch multiple chunk metadata from database efficiently."""
        try:
            uuid_ids = [UUID(chunk_id) for chunk_id in chunk_ids]
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.id.in_(uuid_ids)
            ).all()
            
            result = {}
            for chunk in chunks:
                chunk_id = str(chunk.id)
                metadata = ChunkMetadata(
                    id=chunk_id,
                    document_id=str(chunk.document_id),
                    bot_id=str(chunk.bot_id),
                    chunk_index=chunk.chunk_index,
                    content_length=len(chunk.content) if include_content_length and chunk.content else 0,
                    embedding_id=chunk.embedding_id,
                    metadata=chunk.chunk_metadata or {},
                    created_at=chunk.created_at.isoformat()
                )
                result[chunk_id] = metadata
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching multiple chunk metadata from DB: {e}")
            return {}
    
    async def _update_access_pattern(self, chunk_id: str) -> None:
        """Update access pattern for a chunk."""
        try:
            current_time = datetime.now()
            access_key = self._get_access_pattern_key(chunk_id)
            
            # Get existing pattern
            pattern_data = await self._get_from_cache(access_key)
            
            if pattern_data:
                pattern = AccessPattern(**pattern_data)
                pattern.access_count += 1
                pattern.last_accessed = current_time
                
                # Calculate frequency (accesses per day)
                days_since_creation = max((current_time - datetime.fromisoformat(pattern_data.get('created_at', current_time.isoformat()))).days, 1)
                pattern.access_frequency = pattern.access_count / days_since_creation
                pattern.is_hot = pattern.access_frequency > 2  # More than 2 accesses per day
            else:
                pattern = AccessPattern(
                    chunk_id=chunk_id,
                    access_count=1,
                    last_accessed=current_time,
                    access_frequency=1.0,
                    is_hot=False
                )
            
            # Store updated pattern
            pattern_dict = asdict(pattern)
            pattern_dict['last_accessed'] = pattern.last_accessed.isoformat()
            await self._set_in_cache(access_key, pattern_dict, ttl=self.cache_ttl * 7)  # Longer TTL for patterns
            
            # Also update in-memory patterns for quick access
            self._access_patterns[chunk_id] = pattern
            
        except Exception as e:
            logger.debug(f"Error updating access pattern for {chunk_id}: {e}")
    
    async def _get_access_pattern(self, chunk_id: str) -> Optional[AccessPattern]:
        """Get access pattern for a chunk."""
        try:
            # Check in-memory first
            if chunk_id in self._access_patterns:
                return self._access_patterns[chunk_id]
            
            # Check cache
            access_key = self._get_access_pattern_key(chunk_id)
            pattern_data = await self._get_from_cache(access_key)
            
            if pattern_data:
                pattern_data['last_accessed'] = datetime.fromisoformat(pattern_data['last_accessed'])
                pattern = AccessPattern(**pattern_data)
                self._access_patterns[chunk_id] = pattern
                return pattern
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting access pattern for {chunk_id}: {e}")
            return None