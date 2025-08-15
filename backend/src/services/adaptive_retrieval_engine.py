"""
Adaptive Retrieval Engine for intelligent document retrieval with adaptive thresholds.

This module provides intelligent document retrieval with provider-specific thresholds,
automatic threshold adjustment, and performance-based optimization.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import uuid

from sqlalchemy.orm import Session

from .adaptive_threshold_manager import (
    AdaptiveThresholdManager, 
    RetrievalContext, 
    ThresholdAdjustmentReason
)
from .vector_store import VectorService
from ..models.bot import Bot
from ..models.document import Document


logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    success: bool
    chunks: List[Dict[str, Any]]
    threshold_used: float
    total_attempts: int
    processing_time: float
    metadata: Dict[str, Any]
    fallback_used: bool = False
    error: Optional[str] = None


@dataclass
class OptimizationSuggestion:
    """Suggestion for retrieval optimization."""
    suggestion_type: str
    current_value: Any
    suggested_value: Any
    expected_improvement: str
    confidence: float
    metadata: Dict[str, Any]


class AdaptiveRetrievalEngine:
    """
    Intelligent document retrieval engine with adaptive similarity thresholds.
    
    Features:
    - Provider-specific threshold defaults
    - Automatic threshold adjustment when no results found
    - Performance tracking and optimization
    - Content-aware threshold calculation
    """
    
    def __init__(self, db: Session, vector_service: Optional[VectorService] = None):
        """
        Initialize the adaptive retrieval engine.
        
        Args:
            db: Database session
            vector_service: Optional vector service instance
        """
        self.db = db
        self.vector_service = vector_service or VectorService()
        self.threshold_manager = AdaptiveThresholdManager(db)
        
        # Configuration
        self.max_retry_attempts = 4
        self.enable_performance_tracking = True
        self.enable_adaptive_adjustment = True
        
    async def retrieve_relevant_chunks(
        self,
        bot_id: uuid.UUID,
        query_embedding: List[float],
        context: RetrievalContext,
        custom_threshold: Optional[float] = None,
        max_chunks: int = 5
    ) -> RetrievalResult:
        """
        Retrieve relevant chunks with adaptive threshold management.
        
        Args:
            bot_id: Bot identifier
            query_embedding: Query embedding vector
            context: Retrieval context information
            custom_threshold: Optional custom threshold to use
            max_chunks: Maximum number of chunks to retrieve
            
        Returns:
            RetrievalResult with chunks and metadata
        """
        start_time = time.time()
        
        try:
            # Get bot configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return RetrievalResult(
                    success=False,
                    chunks=[],
                    threshold_used=0.0,
                    total_attempts=0,
                    processing_time=time.time() - start_time,
                    metadata={},
                    error="Bot not found"
                )
            
            provider = bot.embedding_provider
            model = bot.embedding_model
            
            # Determine thresholds to try
            if custom_threshold is not None:
                # Validate custom threshold
                is_valid, issues = self.threshold_manager.validate_threshold_configuration(
                    provider, model, custom_threshold
                )
                if not is_valid:
                    logger.warning(f"Custom threshold validation issues: {issues}")
                
                thresholds_to_try = [custom_threshold]
                if self.enable_adaptive_adjustment:
                    # Add fallback thresholds
                    retry_thresholds = self.threshold_manager.get_retry_thresholds(
                        provider, model, custom_threshold
                    )[1:]  # Skip the first one (custom threshold)
                    thresholds_to_try.extend(retry_thresholds)
            else:
                # Calculate optimal threshold based on context
                optimal_threshold = self.threshold_manager.calculate_optimal_threshold(
                    provider, model, context
                )
                
                if self.enable_adaptive_adjustment:
                    thresholds_to_try = self.threshold_manager.get_retry_thresholds(
                        provider, model, optimal_threshold
                    )
                else:
                    thresholds_to_try = [optimal_threshold]
            
            # Try thresholds in order
            best_result = None
            total_attempts = 0
            
            for attempt, threshold in enumerate(thresholds_to_try):
                total_attempts += 1
                
                try:
                    logger.debug(f"Attempt {attempt + 1}: trying threshold {threshold}")
                    
                    # Perform vector search
                    chunks = await self.vector_service.search_relevant_chunks(
                        bot_id=str(bot_id),
                        query_embedding=query_embedding,
                        top_k=max_chunks,
                        score_threshold=threshold
                    )
                    
                    # Extract scores for analysis
                    result_scores = [chunk.get("score", 0.0) for chunk in chunks]
                    
                    # Track performance if enabled
                    if self.enable_performance_tracking:
                        adjustment_reason = None
                        if attempt > 0:
                            adjustment_reason = ThresholdAdjustmentReason.NO_RESULTS_FOUND.value
                        
                        await self.threshold_manager.track_retrieval_performance(
                            bot_id=bot_id,
                            threshold_used=threshold or 0.0,
                            provider=provider,
                            model=model,
                            query_text=context.query_text,
                            results_found=len(chunks),
                            result_scores=result_scores,
                            processing_time=time.time() - start_time,
                            success=len(chunks) > 0,
                            adjustment_reason=adjustment_reason
                        )
                    
                    # Check if we found good results
                    if chunks:
                        processing_time = time.time() - start_time
                        
                        logger.info(
                            f"Found {len(chunks)} chunks for bot {bot_id} "
                            f"with threshold {threshold} on attempt {attempt + 1}"
                        )
                        
                        return RetrievalResult(
                            success=True,
                            chunks=chunks,
                            threshold_used=threshold or 0.0,
                            total_attempts=total_attempts,
                            processing_time=processing_time,
                            metadata={
                                "provider": provider,
                                "model": model,
                                "optimal_threshold_calculated": optimal_threshold if custom_threshold is None else None,
                                "custom_threshold_used": custom_threshold is not None,
                                "adjustment_made": attempt > 0,
                                "score_stats": {
                                    "max": max(result_scores) if result_scores else None,
                                    "min": min(result_scores) if result_scores else None,
                                    "avg": sum(result_scores) / len(result_scores) if result_scores else None
                                }
                            },
                            fallback_used=attempt > 0
                        )
                    
                    # Store the result in case we need to return it as the best attempt
                    if best_result is None or (threshold is not None and len(chunks) > len(best_result.chunks)):
                        best_result = RetrievalResult(
                            success=len(chunks) > 0,
                            chunks=chunks,
                            threshold_used=threshold or 0.0,
                            total_attempts=total_attempts,
                            processing_time=time.time() - start_time,
                            metadata={
                                "provider": provider,
                                "model": model,
                                "attempt_number": attempt + 1,
                                "no_results_reason": "threshold_too_high" if threshold else "no_similar_content"
                            },
                            fallback_used=attempt > 0
                        )
                    
                    logger.debug(f"No results with threshold {threshold}, trying next...")
                    
                except Exception as e:
                    logger.warning(f"Search attempt {attempt + 1} failed with threshold {threshold}: {e}")
                    continue
            
            # No results found with any threshold
            processing_time = time.time() - start_time
            
            if best_result:
                best_result.processing_time = processing_time
                return best_result
            
            logger.info(f"No relevant chunks found for bot {bot_id} after {total_attempts} attempts")
            
            return RetrievalResult(
                success=True,  # Success but no results
                chunks=[],
                threshold_used=thresholds_to_try[0] if thresholds_to_try else 0.0,
                total_attempts=total_attempts,
                processing_time=processing_time,
                metadata={
                    "provider": provider,
                    "model": model,
                    "reason": "no_relevant_content",
                    "thresholds_tried": [t for t in thresholds_to_try if t is not None]
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error in adaptive retrieval for bot {bot_id}: {e}")
            
            return RetrievalResult(
                success=False,
                chunks=[],
                threshold_used=0.0,
                total_attempts=total_attempts,
                processing_time=processing_time,
                metadata={},
                error=f"Retrieval error: {str(e)}"
            )
    
    async def optimize_retrieval_parameters(
        self,
        bot_id: uuid.UUID,
        lookback_days: int = 7
    ) -> List[OptimizationSuggestion]:
        """
        Generate optimization suggestions based on retrieval performance history.
        
        Args:
            bot_id: Bot identifier
            lookback_days: Number of days to analyze
            
        Returns:
            List of optimization suggestions
        """
        try:
            suggestions = []
            
            # Get bot configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return suggestions
            
            provider = bot.embedding_provider
            model = bot.embedding_model
            
            # Get threshold recommendations
            threshold_recommendations = await self.threshold_manager.get_threshold_recommendations(
                bot_id, provider, model, lookback_days
            )
            
            for rec in threshold_recommendations:
                suggestions.append(OptimizationSuggestion(
                    suggestion_type="similarity_threshold",
                    current_value=rec.current_threshold,
                    suggested_value=rec.recommended_threshold,
                    expected_improvement=rec.reason,
                    confidence=rec.confidence,
                    metadata=rec.metadata
                ))
            
            # Analyze document collection characteristics
            doc_count = self.db.query(Document).filter(Document.bot_id == bot_id).count()
            
            if doc_count == 0:
                suggestions.append(OptimizationSuggestion(
                    suggestion_type="document_collection",
                    current_value=0,
                    suggested_value="Add documents",
                    expected_improvement="Enable RAG functionality by uploading relevant documents",
                    confidence=1.0,
                    metadata={"issue": "no_documents"}
                ))
            elif doc_count < 5:
                suggestions.append(OptimizationSuggestion(
                    suggestion_type="document_collection",
                    current_value=doc_count,
                    suggested_value="Add more documents",
                    expected_improvement="Improve answer quality with more diverse content",
                    confidence=0.8,
                    metadata={"issue": "few_documents"}
                ))
            
            # Check for provider-specific optimizations
            config = self.threshold_manager.get_provider_threshold_config(provider, model)
            
            if provider == "gemini" and config.default_threshold > 0.05:
                suggestions.append(OptimizationSuggestion(
                    suggestion_type="provider_optimization",
                    current_value=config.default_threshold,
                    suggested_value=0.01,
                    expected_improvement="Gemini embeddings work better with very low thresholds",
                    confidence=0.9,
                    metadata={"provider_specific": True}
                ))
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating optimization suggestions for bot {bot_id}: {e}")
            return []
    
    def get_threshold_info(self, provider: str, model: str) -> Dict[str, Any]:
        """
        Get threshold configuration information for a provider/model.
        
        Args:
            provider: Embedding provider
            model: Embedding model
            
        Returns:
            Dictionary with threshold information
        """
        try:
            return self.threshold_manager.get_provider_info(provider)
        except Exception as e:
            logger.error(f"Error getting threshold info for {provider}/{model}: {e}")
            return {}
    
    def calculate_adaptive_threshold(
        self,
        provider: str,
        model: str,
        content_type: str,
        document_count: int = 0,
        avg_document_length: Optional[float] = None
    ) -> float:
        """
        Calculate adaptive threshold for given context.
        
        Args:
            provider: Embedding provider
            model: Embedding model
            content_type: Type of content being searched
            document_count: Number of documents in collection
            avg_document_length: Average document length
            
        Returns:
            Calculated threshold value
        """
        try:
            context = RetrievalContext(
                bot_id=uuid.uuid4(),  # Dummy ID for calculation
                query_text="",  # Not used in calculation
                content_type=content_type,
                document_count=document_count,
                avg_document_length=avg_document_length
            )
            
            return self.threshold_manager.calculate_optimal_threshold(
                provider, model, context
            )
            
        except Exception as e:
            logger.error(f"Error calculating adaptive threshold: {e}")
            return 0.5  # Safe default
    
    async def get_performance_summary(
        self,
        bot_id: uuid.UUID,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get performance summary for a bot's retrieval operations.
        
        Args:
            bot_id: Bot identifier
            days: Number of days to analyze
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            from datetime import datetime, timedelta
            from ..models.threshold_performance import ThresholdPerformanceLog
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            logs = self.db.query(ThresholdPerformanceLog).filter(
                ThresholdPerformanceLog.bot_id == bot_id,
                ThresholdPerformanceLog.timestamp >= cutoff_date
            ).all()
            
            if not logs:
                return {
                    "total_queries": 0,
                    "success_rate": 0.0,
                    "avg_results_per_query": 0.0,
                    "avg_processing_time": 0.0,
                    "most_used_threshold": None,
                    "performance_trend": "insufficient_data"
                }
            
            total_queries = len(logs)
            successful_queries = sum(1 for log in logs if log.success)
            total_results = sum(log.results_found for log in logs)
            total_processing_time = sum(log.processing_time for log in logs)
            
            # Find most used threshold
            threshold_counts = {}
            for log in logs:
                threshold = log.threshold_used
                threshold_counts[threshold] = threshold_counts.get(threshold, 0) + 1
            
            most_used_threshold = max(threshold_counts.items(), key=lambda x: x[1])[0] if threshold_counts else None
            
            return {
                "total_queries": total_queries,
                "success_rate": successful_queries / total_queries,
                "avg_results_per_query": total_results / total_queries,
                "avg_processing_time": total_processing_time / total_queries,
                "most_used_threshold": most_used_threshold,
                "threshold_distribution": threshold_counts,
                "analysis_period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error getting performance summary for bot {bot_id}: {e}")
            return {"error": str(e)}