"""
Cache analytics service for detailed performance analysis and optimization recommendations.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import redis.asyncio as redis
from ..core.config import settings
from .embedding_cache_service import get_embedding_cache_service
from .cache_performance_monitor import get_cache_performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class CacheOptimizationRecommendation:
    """Cache optimization recommendation."""
    type: str  # 'performance', 'memory', 'hit_rate', 'maintenance'
    priority: str  # 'high', 'medium', 'low'
    title: str
    description: str
    action: str
    estimated_impact: str


@dataclass
class CacheUsagePattern:
    """Cache usage pattern analysis."""
    provider_model: str
    request_count: int
    hit_rate: float
    avg_response_time_ms: float
    memory_usage_mb: float
    last_accessed: float
    access_frequency: str  # 'high', 'medium', 'low'


@dataclass
class CacheHealthReport:
    """Comprehensive cache health report."""
    overall_health: str  # 'excellent', 'good', 'fair', 'poor'
    hit_rate: float
    memory_efficiency: float
    response_time_ms: float
    error_rate: float
    recommendations: List[CacheOptimizationRecommendation]
    usage_patterns: List[CacheUsagePattern]
    trends: Dict[str, str]


class CacheAnalyticsService:
    """
    Service for analyzing cache performance and providing optimization recommendations.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the cache analytics service.
        
        Args:
            redis_url: Redis connection URL. Uses settings default if None.
        """
        self.redis_url = redis_url or settings.redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # Analytics configuration
        self.analytics_prefix = "cache_analytics:"
        self.usage_patterns_key = "usage_patterns"
        self.optimization_history_key = "optimization_history"
        
        # Analysis thresholds
        self.excellent_hit_rate = 0.8
        self.good_hit_rate = 0.6
        self.fair_hit_rate = 0.4
        self.max_response_time_ms = 100
        self.memory_efficiency_threshold = 0.8
    
    async def initialize(self):
        """Initialize the cache analytics service."""
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
            logger.info("Cache analytics service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache analytics service: {e}")
            self.redis_client = None
            raise
    
    async def close(self):
        """Close the cache analytics service."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    async def analyze_usage_patterns(self) -> List[CacheUsagePattern]:
        """
        Analyze cache usage patterns by provider/model.
        
        Returns:
            List of usage patterns
        """
        try:
            performance_monitor = await get_cache_performance_monitor()
            provider_breakdown = await performance_monitor.get_provider_performance_breakdown()
            
            patterns = []
            
            for provider_model, stats in provider_breakdown.items():
                # Calculate access frequency
                requests = stats.get('requests', 0)
                if requests > 100:
                    frequency = 'high'
                elif requests > 20:
                    frequency = 'medium'
                else:
                    frequency = 'low'
                
                pattern = CacheUsagePattern(
                    provider_model=provider_model,
                    request_count=requests,
                    hit_rate=stats.get('hit_rate', 0.0),
                    avg_response_time_ms=0.0,  # Would need to track this separately
                    memory_usage_mb=0.0,  # Would need to estimate based on cache entries
                    last_accessed=time.time(),  # Approximate
                    access_frequency=frequency
                )
                
                patterns.append(pattern)
            
            # Sort by request count (most used first)
            patterns.sort(key=lambda x: x.request_count, reverse=True)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing usage patterns: {e}")
            return []
    
    async def generate_optimization_recommendations(self) -> List[CacheOptimizationRecommendation]:
        """
        Generate cache optimization recommendations based on current performance.
        
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        try:
            # Get current cache stats
            cache_service = await get_embedding_cache_service()
            cache_stats = await cache_service.get_cache_stats()
            
            performance_monitor = await get_cache_performance_monitor()
            hit_rate_analysis = await performance_monitor.analyze_hit_rate_trends()
            
            # Hit rate recommendations
            if cache_stats.hit_rate < self.fair_hit_rate:
                recommendations.append(CacheOptimizationRecommendation(
                    type='hit_rate',
                    priority='high',
                    title='Low Cache Hit Rate',
                    description=f'Current hit rate is {cache_stats.hit_rate:.2f}, which is below optimal levels.',
                    action='Implement cache warming strategies for frequently accessed content',
                    estimated_impact='Could improve hit rate by 20-30%'
                ))
            elif cache_stats.hit_rate < self.good_hit_rate:
                recommendations.append(CacheOptimizationRecommendation(
                    type='hit_rate',
                    priority='medium',
                    title='Moderate Cache Hit Rate',
                    description=f'Current hit rate is {cache_stats.hit_rate:.2f}, with room for improvement.',
                    action='Review and optimize cache key generation and text normalization',
                    estimated_impact='Could improve hit rate by 10-15%'
                ))
            
            # Memory usage recommendations
            if cache_stats.memory_usage_mb > 1000:  # 1GB threshold
                recommendations.append(CacheOptimizationRecommendation(
                    type='memory',
                    priority='high',
                    title='High Memory Usage',
                    description=f'Cache is using {cache_stats.memory_usage_mb:.1f}MB of memory.',
                    action='Implement more aggressive LRU eviction or add TTL-based cleanup',
                    estimated_impact='Could reduce memory usage by 30-50%'
                ))
            elif cache_stats.memory_usage_mb > 500:  # 500MB threshold
                recommendations.append(CacheOptimizationRecommendation(
                    type='memory',
                    priority='medium',
                    title='Moderate Memory Usage',
                    description=f'Cache is using {cache_stats.memory_usage_mb:.1f}MB of memory.',
                    action='Monitor memory growth and consider implementing cleanup policies',
                    estimated_impact='Prevent future memory issues'
                ))
            
            # Eviction recommendations
            if cache_stats.evictions > 100:
                recommendations.append(CacheOptimizationRecommendation(
                    type='performance',
                    priority='medium',
                    title='Frequent Cache Evictions',
                    description=f'{cache_stats.evictions} cache evictions detected.',
                    action='Increase cache size limit or optimize cache key strategy',
                    estimated_impact='Reduce cache misses and improve performance'
                ))
            
            # Trend-based recommendations
            if hit_rate_analysis.trend == 'declining':
                recommendations.append(CacheOptimizationRecommendation(
                    type='performance',
                    priority='high',
                    title='Declining Hit Rate Trend',
                    description='Cache hit rate has been declining over time.',
                    action='Investigate recent changes and implement corrective measures',
                    estimated_impact='Prevent further performance degradation'
                ))
            
            # Maintenance recommendations
            if cache_stats.total_entries > 10000:
                recommendations.append(CacheOptimizationRecommendation(
                    type='maintenance',
                    priority='low',
                    title='Large Cache Size',
                    description=f'Cache contains {cache_stats.total_entries} entries.',
                    action='Implement regular maintenance and cleanup procedures',
                    estimated_impact='Improve cache efficiency and reduce lookup times'
                ))
            
            # Sort recommendations by priority
            priority_order = {'high': 3, 'medium': 2, 'low': 1}
            recommendations.sort(key=lambda x: priority_order.get(x.priority, 0), reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {e}")
            return []
    
    async def calculate_cache_health_score(self) -> Tuple[str, float]:
        """
        Calculate overall cache health score.
        
        Returns:
            Tuple of (health_rating, score)
        """
        try:
            cache_service = await get_embedding_cache_service()
            cache_stats = await cache_service.get_cache_stats()
            
            # Calculate component scores (0-1 scale)
            hit_rate_score = min(cache_stats.hit_rate / self.excellent_hit_rate, 1.0)
            
            # Memory efficiency (inverse of memory usage relative to entries)
            if cache_stats.total_entries > 0:
                memory_per_entry = cache_stats.memory_usage_mb / cache_stats.total_entries
                memory_efficiency = max(0, 1.0 - (memory_per_entry / 10.0))  # 10MB per entry as baseline
            else:
                memory_efficiency = 1.0
            
            # Eviction rate (lower is better)
            if cache_stats.total_requests > 0:
                eviction_rate = cache_stats.evictions / cache_stats.total_requests
                eviction_score = max(0, 1.0 - (eviction_rate * 10))  # 10% eviction rate = 0 score
            else:
                eviction_score = 1.0
            
            # Calculate weighted overall score
            overall_score = (
                hit_rate_score * 0.4 +
                memory_efficiency * 0.3 +
                eviction_score * 0.3
            )
            
            # Determine health rating
            if overall_score >= 0.8:
                health_rating = 'excellent'
            elif overall_score >= 0.6:
                health_rating = 'good'
            elif overall_score >= 0.4:
                health_rating = 'fair'
            else:
                health_rating = 'poor'
            
            return health_rating, overall_score
            
        except Exception as e:
            logger.error(f"Error calculating cache health score: {e}")
            return 'unknown', 0.0
    
    async def analyze_performance_trends(self) -> Dict[str, str]:
        """
        Analyze performance trends over time.
        
        Returns:
            Dictionary of trend analyses
        """
        try:
            performance_monitor = await get_cache_performance_monitor()
            hit_rate_analysis = await performance_monitor.analyze_hit_rate_trends()
            
            trends = {
                'hit_rate': hit_rate_analysis.trend,
                'overall_performance': 'stable'  # Would need more historical data
            }
            
            # Analyze 24-hour vs 7-day trends
            if hit_rate_analysis.avg_hit_rate_24h > hit_rate_analysis.avg_hit_rate_7d + 0.05:
                trends['recent_improvement'] = 'improving'
            elif hit_rate_analysis.avg_hit_rate_24h < hit_rate_analysis.avg_hit_rate_7d - 0.05:
                trends['recent_improvement'] = 'declining'
            else:
                trends['recent_improvement'] = 'stable'
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing performance trends: {e}")
            return {}
    
    async def generate_health_report(self) -> CacheHealthReport:
        """
        Generate comprehensive cache health report.
        
        Returns:
            Complete health report with recommendations
        """
        try:
            # Get basic stats
            cache_service = await get_embedding_cache_service()
            cache_stats = await cache_service.get_cache_stats()
            
            # Calculate health score
            health_rating, health_score = await self.calculate_cache_health_score()
            
            # Get recommendations
            recommendations = await self.generate_optimization_recommendations()
            
            # Get usage patterns
            usage_patterns = await self.analyze_usage_patterns()
            
            # Get trends
            trends = await self.analyze_performance_trends()
            
            # Calculate memory efficiency
            if cache_stats.total_entries > 0:
                memory_per_entry = cache_stats.memory_usage_mb / cache_stats.total_entries
                memory_efficiency = max(0, 1.0 - (memory_per_entry / 10.0))
            else:
                memory_efficiency = 1.0
            
            report = CacheHealthReport(
                overall_health=health_rating,
                hit_rate=cache_stats.hit_rate,
                memory_efficiency=memory_efficiency,
                response_time_ms=0.0,  # Would need to track this
                error_rate=0.0,  # Would need to track this
                recommendations=recommendations,
                usage_patterns=usage_patterns,
                trends=trends
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating health report: {e}")
            return CacheHealthReport(
                overall_health='unknown',
                hit_rate=0.0,
                memory_efficiency=0.0,
                response_time_ms=0.0,
                error_rate=1.0,
                recommendations=[],
                usage_patterns=[],
                trends={}
            )
    
    async def get_cache_statistics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics summary.
        
        Returns:
            Statistics summary dictionary
        """
        try:
            cache_service = await get_embedding_cache_service()
            cache_stats = await cache_service.get_cache_stats()
            
            performance_monitor = await get_cache_performance_monitor()
            current_performance = await performance_monitor.get_current_performance()
            
            health_rating, health_score = await self.calculate_cache_health_score()
            
            summary = {
                'health': {
                    'rating': health_rating,
                    'score': health_score
                },
                'performance': {
                    'hit_rate': cache_stats.hit_rate,
                    'total_requests': cache_stats.total_requests,
                    'cache_hits': cache_stats.cache_hits,
                    'cache_misses': cache_stats.cache_misses
                },
                'storage': {
                    'total_entries': cache_stats.total_entries,
                    'memory_usage_mb': cache_stats.memory_usage_mb,
                    'evictions': cache_stats.evictions
                },
                'trends': await self.analyze_performance_trends()
            }
            
            if current_performance:
                summary['recent_performance'] = {
                    'avg_response_time_ms': current_performance.avg_response_time_ms,
                    'provider_breakdown': current_performance.provider_stats
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting cache statistics summary: {e}")
            return {'error': str(e)}
    
    async def export_analytics_data(self, format: str = 'json') -> Dict[str, Any]:
        """
        Export comprehensive analytics data.
        
        Args:
            format: Export format ('json', 'csv')
            
        Returns:
            Analytics data in requested format
        """
        try:
            health_report = await self.generate_health_report()
            stats_summary = await self.get_cache_statistics_summary()
            
            export_data = {
                'timestamp': time.time(),
                'health_report': asdict(health_report),
                'statistics_summary': stats_summary,
                'export_format': format
            }
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting analytics data: {e}")
            return {'error': str(e)}


# Global cache analytics service instance
_analytics_service: Optional[CacheAnalyticsService] = None


async def get_cache_analytics_service() -> CacheAnalyticsService:
    """
    Get the global cache analytics service instance.
    
    Returns:
        Initialized cache analytics service
    """
    global _analytics_service
    
    if _analytics_service is None:
        _analytics_service = CacheAnalyticsService()
        await _analytics_service.initialize()
    
    return _analytics_service


async def close_cache_analytics_service():
    """Close the global cache analytics service."""
    global _analytics_service
    
    if _analytics_service:
        await _analytics_service.close()
        _analytics_service = None