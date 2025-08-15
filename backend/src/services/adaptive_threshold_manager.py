"""
Adaptive Similarity Threshold Manager for RAG pipeline optimization.

This module provides provider-specific threshold defaults and adaptive threshold
adjustment based on retrieval performance and content analysis.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models.bot import Bot
from ..models.threshold_performance import ThresholdPerformanceLog


logger = logging.getLogger(__name__)


class ThresholdAdjustmentReason(Enum):
    """Reasons for threshold adjustments."""
    NO_RESULTS_FOUND = "no_results_found"
    LOW_QUALITY_RESULTS = "low_quality_results"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    CONTENT_ANALYSIS = "content_analysis"
    PROVIDER_CHARACTERISTICS = "provider_characteristics"


@dataclass
class ThresholdConfiguration:
    """Configuration for similarity thresholds."""
    provider: str
    model: str
    default_threshold: float
    min_threshold: float
    max_threshold: float
    adjustment_step: float
    retry_thresholds: List[float]
    content_type_adjustments: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalContext:
    """Context information for retrieval operations."""
    bot_id: uuid.UUID
    query_text: str
    content_type: Optional[str] = None
    document_count: int = 0
    avg_document_length: Optional[float] = None
    session_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None


@dataclass
class ThresholdRecommendation:
    """Recommendation for threshold optimization."""
    current_threshold: float
    recommended_threshold: float
    confidence: float
    reason: str
    expected_improvement: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval performance tracking."""
    bot_id: uuid.UUID
    timestamp: datetime
    threshold_used: float
    results_found: int
    avg_score: Optional[float]
    max_score: Optional[float]
    min_score: Optional[float]
    query_length: int
    processing_time: float
    success: bool
    adjustment_reason: Optional[str] = None


class AdaptiveThresholdManager:
    """
    Manager for adaptive similarity threshold optimization.
    
    Provides provider-specific defaults, automatic threshold adjustment,
    and performance-based optimization recommendations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the adaptive threshold manager.
        
        Args:
            db: Database session
        """
        self.db = db
        self._threshold_configs = self._initialize_provider_configs()
        self._performance_cache: Dict[str, List[RetrievalMetrics]] = {}
        self._cache_ttl = timedelta(hours=1)
        self._min_samples_for_optimization = 10
        
    def _initialize_provider_configs(self) -> Dict[str, ThresholdConfiguration]:
        """Initialize provider-specific threshold configurations."""
        configs = {
            "openai": ThresholdConfiguration(
                provider="openai",
                model="text-embedding-3-small",
                default_threshold=0.7,
                min_threshold=0.3,
                max_threshold=0.95,
                adjustment_step=0.1,
                retry_thresholds=[0.7, 0.5, 0.3, 0.1],
                content_type_adjustments={
                    "technical": 0.05,  # Slightly higher for technical content
                    "conversational": -0.05,  # Slightly lower for conversational
                    "code": 0.1,  # Higher for code similarity
                    "legal": 0.08,  # Higher for legal documents
                },
                metadata={
                    "embedding_dimension": 1536,
                    "distance_metric": "cosine",
                    "optimal_range": [0.6, 0.8]
                }
            ),
            "gemini": ThresholdConfiguration(
                provider="gemini",
                model="text-embedding-004",
                default_threshold=0.01,  # Very low for Gemini embeddings
                min_threshold=0.001,
                max_threshold=0.5,
                adjustment_step=0.01,
                retry_thresholds=[0.01, 0.005, 0.001, None],  # None = no threshold
                content_type_adjustments={
                    "technical": 0.005,
                    "conversational": -0.002,
                    "code": 0.01,
                    "legal": 0.008,
                },
                metadata={
                    "embedding_dimension": 768,
                    "distance_metric": "cosine",
                    "optimal_range": [0.005, 0.05],
                    "note": "Gemini embeddings typically have very low similarity scores"
                }
            ),
            "anthropic": ThresholdConfiguration(
                provider="anthropic",
                model="claude-3-haiku",
                default_threshold=0.6,
                min_threshold=0.2,
                max_threshold=0.9,
                adjustment_step=0.1,
                retry_thresholds=[0.6, 0.4, 0.2, 0.1],
                content_type_adjustments={
                    "technical": 0.05,
                    "conversational": -0.05,
                    "code": 0.1,
                    "legal": 0.08,
                },
                metadata={
                    "embedding_dimension": 1024,
                    "distance_metric": "cosine",
                    "optimal_range": [0.5, 0.75]
                }
            ),
            "openrouter": ThresholdConfiguration(
                provider="openrouter",
                model="text-embedding-3-small",  # Default model
                default_threshold=0.7,
                min_threshold=0.3,
                max_threshold=0.95,
                adjustment_step=0.1,
                retry_thresholds=[0.7, 0.5, 0.3, 0.1],
                content_type_adjustments={
                    "technical": 0.05,
                    "conversational": -0.05,
                    "code": 0.1,
                    "legal": 0.08,
                },
                metadata={
                    "embedding_dimension": 1536,
                    "distance_metric": "cosine",
                    "optimal_range": [0.6, 0.8],
                    "note": "Uses OpenAI-compatible models"
                }
            )
        }
        
        return configs
    
    def get_provider_threshold_config(
        self, 
        provider: str, 
        model: Optional[str] = None
    ) -> ThresholdConfiguration:
        """
        Get threshold configuration for a provider and model.
        
        Args:
            provider: Embedding provider name
            model: Optional model name (uses default if None)
            
        Returns:
            ThresholdConfiguration for the provider
            
        Raises:
            ValueError: If provider is not supported
        """
        if provider not in self._threshold_configs:
            raise ValueError(f"Unsupported provider: {provider}")
        
        config = self._threshold_configs[provider]
        
        # Create a copy with model-specific adjustments if needed
        if model and model != config.model:
            # For now, use the same config but update the model name
            # In the future, we could have model-specific configurations
            config = ThresholdConfiguration(
                provider=provider,
                model=model,
                default_threshold=config.default_threshold,
                min_threshold=config.min_threshold,
                max_threshold=config.max_threshold,
                adjustment_step=config.adjustment_step,
                retry_thresholds=config.retry_thresholds.copy(),
                content_type_adjustments=config.content_type_adjustments.copy(),
                metadata=config.metadata.copy()
            )
        
        return config
    
    def calculate_optimal_threshold(
        self,
        provider: str,
        model: str,
        context: RetrievalContext
    ) -> float:
        """
        Calculate optimal similarity threshold based on provider characteristics and content.
        
        Args:
            provider: Embedding provider name
            model: Embedding model name
            context: Retrieval context information
            
        Returns:
            Calculated optimal threshold
        """
        try:
            config = self.get_provider_threshold_config(provider, model)
            base_threshold = config.default_threshold
            
            # Apply content type adjustments
            if context.content_type and context.content_type in config.content_type_adjustments:
                adjustment = config.content_type_adjustments[context.content_type]
                base_threshold += adjustment
                logger.debug(f"Applied content type adjustment for {context.content_type}: {adjustment}")
            
            # Apply document collection size adjustments
            if context.document_count > 0:
                # For larger collections, slightly increase threshold to be more selective
                if context.document_count > 100:
                    base_threshold += 0.02
                elif context.document_count > 1000:
                    base_threshold += 0.05
            
            # Apply document length adjustments
            if context.avg_document_length:
                # For longer documents, slightly decrease threshold as chunks might be more specific
                if context.avg_document_length > 2000:
                    base_threshold -= 0.02
                elif context.avg_document_length > 5000:
                    base_threshold -= 0.05
            
            # Ensure threshold is within valid range
            final_threshold = max(
                config.min_threshold,
                min(config.max_threshold, base_threshold)
            )
            
            logger.debug(
                f"Calculated threshold for {provider}/{model}: {final_threshold} "
                f"(base: {config.default_threshold}, adjusted: {base_threshold})"
            )
            
            return final_threshold
            
        except Exception as e:
            logger.error(f"Error calculating optimal threshold: {e}")
            # Return a safe default
            return 0.5
    
    def get_retry_thresholds(
        self,
        provider: str,
        model: str,
        initial_threshold: Optional[float] = None
    ) -> List[Optional[float]]:
        """
        Get list of thresholds to try in order for adaptive retry.
        
        Args:
            provider: Embedding provider name
            model: Embedding model name
            initial_threshold: Optional initial threshold to start with
            
        Returns:
            List of thresholds to try (None means no threshold)
        """
        try:
            config = self.get_provider_threshold_config(provider, model)
            
            if initial_threshold is not None:
                # Create custom retry sequence starting from initial threshold
                retry_thresholds = [initial_threshold]
                
                # Add progressively lower thresholds
                current = initial_threshold
                while current > config.min_threshold:
                    current -= config.adjustment_step
                    if current >= config.min_threshold:
                        retry_thresholds.append(current)
                
                # Add the minimum threshold if not already included
                if retry_thresholds[-1] != config.min_threshold:
                    retry_thresholds.append(config.min_threshold)
                
                # Add None (no threshold) as final fallback
                retry_thresholds.append(None)
                
                return retry_thresholds
            else:
                # Use predefined retry sequence
                return config.retry_thresholds.copy()
                
        except Exception as e:
            logger.error(f"Error getting retry thresholds: {e}")
            # Return safe defaults
            return [0.5, 0.3, 0.1, None]
    
    def validate_threshold_configuration(
        self,
        provider: str,
        model: str,
        custom_threshold: float
    ) -> Tuple[bool, List[str]]:
        """
        Validate custom threshold configuration.
        
        Args:
            provider: Embedding provider name
            model: Embedding model name
            custom_threshold: Custom threshold to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            config = self.get_provider_threshold_config(provider, model)
            
            # Check if threshold is within valid range
            if custom_threshold < config.min_threshold:
                issues.append(
                    f"Threshold {custom_threshold} is below minimum {config.min_threshold} "
                    f"for {provider}/{model}"
                )
            
            if custom_threshold > config.max_threshold:
                issues.append(
                    f"Threshold {custom_threshold} is above maximum {config.max_threshold} "
                    f"for {provider}/{model}"
                )
            
            # Check if threshold is in optimal range
            optimal_range = config.metadata.get("optimal_range")
            if optimal_range and len(optimal_range) == 2:
                min_optimal, max_optimal = optimal_range
                if not (min_optimal <= custom_threshold <= max_optimal):
                    issues.append(
                        f"Threshold {custom_threshold} is outside optimal range "
                        f"[{min_optimal}, {max_optimal}] for {provider}/{model}"
                    )
            
            # Provider-specific validations
            if provider == "gemini" and custom_threshold > 0.1:
                issues.append(
                    "Gemini embeddings typically require very low thresholds (< 0.1). "
                    f"Consider using {config.default_threshold} instead."
                )
            
            return len(issues) == 0, issues
            
        except Exception as e:
            logger.error(f"Error validating threshold configuration: {e}")
            return False, [f"Validation error: {str(e)}"]
    
    async def track_retrieval_performance(
        self,
        bot_id: uuid.UUID,
        threshold_used: float,
        provider: str,
        model: str,
        query_text: str,
        results_found: int,
        result_scores: List[float],
        processing_time: float,
        success: bool,
        adjustment_reason: Optional[str] = None
    ) -> None:
        """
        Track retrieval performance for threshold optimization.
        
        Args:
            bot_id: Bot identifier
            threshold_used: Similarity threshold that was used
            provider: Embedding provider
            model: Embedding model
            query_text: Original query text
            results_found: Number of results found
            result_scores: List of similarity scores
            processing_time: Time taken for retrieval
            success: Whether the retrieval was successful
            adjustment_reason: Optional reason for threshold adjustment
        """
        try:
            # Calculate score statistics
            avg_score = sum(result_scores) / len(result_scores) if result_scores else None
            max_score = max(result_scores) if result_scores else None
            min_score = min(result_scores) if result_scores else None
            
            # Create performance log entry
            performance_log = ThresholdPerformanceLog(
                bot_id=bot_id,
                threshold_used=threshold_used,
                provider=provider,
                model=model,
                query_length=len(query_text),
                query_hash=self._hash_query(query_text),
                results_found=results_found,
                avg_score=avg_score,
                max_score=max_score,
                min_score=min_score,
                processing_time=processing_time,
                success=success,
                adjustment_reason=adjustment_reason,
                additional_metadata={
                    "score_distribution": {
                        "count": len(result_scores),
                        "std_dev": self._calculate_std_dev(result_scores) if result_scores else None
                    }
                }
            )
            
            self.db.add(performance_log)
            self.db.commit()
            
            # Update in-memory cache
            cache_key = f"{bot_id}_{provider}_{model}"
            if cache_key not in self._performance_cache:
                self._performance_cache[cache_key] = []
            
            metrics = RetrievalMetrics(
                bot_id=bot_id,
                timestamp=datetime.utcnow(),
                threshold_used=threshold_used,
                results_found=results_found,
                avg_score=avg_score,
                max_score=max_score,
                min_score=min_score,
                query_length=len(query_text),
                processing_time=processing_time,
                success=success,
                adjustment_reason=adjustment_reason
            )
            
            self._performance_cache[cache_key].append(metrics)
            
            # Keep only recent metrics in cache
            cutoff_time = datetime.utcnow() - self._cache_ttl
            self._performance_cache[cache_key] = [
                m for m in self._performance_cache[cache_key]
                if m.timestamp > cutoff_time
            ]
            
            logger.debug(f"Tracked retrieval performance for bot {bot_id}")
            
        except Exception as e:
            logger.error(f"Error tracking retrieval performance: {e}")
    
    def _hash_query(self, query_text: str) -> str:
        """Create a privacy-preserving hash of the query text."""
        import hashlib
        return hashlib.sha256(query_text.encode()).hexdigest()
    
    def _calculate_std_dev(self, scores: List[float]) -> float:
        """Calculate standard deviation of scores."""
        if len(scores) < 2:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((x - mean) ** 2 for x in scores) / len(scores)
        return variance ** 0.5
    
    async def get_threshold_recommendations(
        self,
        bot_id: uuid.UUID,
        provider: str,
        model: str,
        lookback_days: int = 7
    ) -> List[ThresholdRecommendation]:
        """
        Get threshold optimization recommendations based on performance history.
        
        Args:
            bot_id: Bot identifier
            provider: Embedding provider
            model: Embedding model
            lookback_days: Number of days to analyze
            
        Returns:
            List of threshold recommendations
        """
        try:
            recommendations = []
            
            # Get performance history from database
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            performance_logs = self.db.query(ThresholdPerformanceLog).filter(
                ThresholdPerformanceLog.bot_id == bot_id,
                ThresholdPerformanceLog.provider == provider,
                ThresholdPerformanceLog.model == model,
                ThresholdPerformanceLog.timestamp >= cutoff_date
            ).order_by(ThresholdPerformanceLog.timestamp.desc()).all()
            
            if len(performance_logs) < self._min_samples_for_optimization:
                return []
            
            # Analyze performance patterns
            threshold_performance = {}
            for log in performance_logs:
                threshold = log.threshold_used
                if threshold not in threshold_performance:
                    threshold_performance[threshold] = {
                        "success_rate": 0,
                        "avg_results": 0,
                        "avg_score": 0,
                        "avg_processing_time": 0,
                        "count": 0
                    }
                
                perf = threshold_performance[threshold]
                perf["success_rate"] += 1 if log.success else 0
                perf["avg_results"] += log.results_found
                perf["avg_score"] += log.avg_score or 0
                perf["avg_processing_time"] += log.processing_time
                perf["count"] += 1
            
            # Calculate averages
            for threshold, perf in threshold_performance.items():
                count = perf["count"]
                perf["success_rate"] = perf["success_rate"] / count
                perf["avg_results"] = perf["avg_results"] / count
                perf["avg_score"] = perf["avg_score"] / count
                perf["avg_processing_time"] = perf["avg_processing_time"] / count
            
            # Find optimal threshold based on performance
            best_threshold = None
            best_score = 0
            
            for threshold, perf in threshold_performance.items():
                # Composite score: success rate + result quality - processing time penalty
                composite_score = (
                    perf["success_rate"] * 0.4 +
                    min(perf["avg_results"] / 5.0, 1.0) * 0.3 +  # Normalize to 0-1
                    (perf["avg_score"] or 0) * 0.2 +
                    max(0, 1 - perf["avg_processing_time"] / 5.0) * 0.1  # Processing time penalty
                )
                
                if composite_score > best_score:
                    best_score = composite_score
                    best_threshold = threshold
            
            # Generate recommendations
            if best_threshold is not None:
                current_config = self.get_provider_threshold_config(provider, model)
                current_threshold = current_config.default_threshold
                
                if abs(best_threshold - current_threshold) > 0.05:  # Significant difference
                    confidence = min(best_score, 0.95)  # Cap confidence at 95%
                    
                    recommendations.append(ThresholdRecommendation(
                        current_threshold=current_threshold,
                        recommended_threshold=best_threshold,
                        confidence=confidence,
                        reason=f"Performance analysis shows {best_threshold:.3f} performs better",
                        expected_improvement=best_score - 0.5,  # Baseline score
                        metadata={
                            "analysis_period_days": lookback_days,
                            "samples_analyzed": len(performance_logs),
                            "performance_metrics": threshold_performance[best_threshold]
                        }
                    ))
            
            # Check for common issues and provide specific recommendations
            no_results_count = sum(1 for log in performance_logs if log.results_found == 0)
            if no_results_count > len(performance_logs) * 0.3:  # More than 30% no results
                config = self.get_provider_threshold_config(provider, model)
                lower_threshold = max(config.min_threshold, config.default_threshold - 0.2)
                
                recommendations.append(ThresholdRecommendation(
                    current_threshold=config.default_threshold,
                    recommended_threshold=lower_threshold,
                    confidence=0.8,
                    reason="High rate of queries with no results - consider lowering threshold",
                    metadata={
                        "no_results_rate": no_results_count / len(performance_logs),
                        "issue_type": "high_no_results_rate"
                    }
                ))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating threshold recommendations: {e}")
            return []
    
    def get_supported_providers(self) -> List[str]:
        """Get list of supported providers."""
        return list(self._threshold_configs.keys())
    
    def get_provider_info(self, provider: str) -> Dict[str, Any]:
        """
        Get detailed information about a provider's threshold configuration.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary with provider threshold information
        """
        try:
            config = self.get_provider_threshold_config(provider)
            return {
                "provider": config.provider,
                "default_model": config.model,
                "default_threshold": config.default_threshold,
                "threshold_range": [config.min_threshold, config.max_threshold],
                "adjustment_step": config.adjustment_step,
                "retry_thresholds": config.retry_thresholds,
                "content_type_adjustments": config.content_type_adjustments,
                "metadata": config.metadata
            }
        except Exception as e:
            logger.error(f"Error getting provider info for {provider}: {e}")
            return {}