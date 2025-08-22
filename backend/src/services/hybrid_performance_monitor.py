"""
Hybrid Performance Monitor and Configuration Management

This module provides comprehensive performance monitoring and dynamic configuration
management for the hybrid retrieval system.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from collections import deque, defaultdict
import numpy as np
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Column, String, Float, Integer, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


class MetricType(Enum):
    """Types of performance metrics."""
    RESPONSE_TIME = "response_time"
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    USER_SATISFACTION = "user_satisfaction"
    RESOURCE_USAGE = "resource_usage"
    CACHE_PERFORMANCE = "cache_performance"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


class OptimizationGoal(Enum):
    """Optimization goals for the system."""
    MINIMIZE_LATENCY = "minimize_latency"
    MAXIMIZE_ACCURACY = "maximize_accuracy"
    BALANCE_PERFORMANCE = "balance_performance"
    MAXIMIZE_THROUGHPUT = "maximize_throughput"
    MINIMIZE_COST = "minimize_cost"


@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    metric_type: MetricType
    value: float
    timestamp: float
    bot_id: Optional[str] = None
    user_id: Optional[str] = None
    query_id: Optional[str] = None
    mode_used: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedMetrics:
    """Aggregated performance metrics."""
    metric_type: MetricType
    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    p95: float
    p99: float
    sample_count: int
    time_window: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert for anomalies."""
    alert_type: str
    severity: str  # "low", "medium", "high", "critical"
    metric_type: MetricType
    current_value: float
    threshold: float
    message: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMetricDB(Base):
    """Database model for performance metrics."""
    __tablename__ = 'performance_metrics'
    
    id = Column(String, primary_key=True)
    metric_type = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    bot_id = Column(String)
    user_id = Column(String)
    query_id = Column(String)
    mode_used = Column(String)
    metric_metadata = Column(JSON)


class HybridRetrievalConfig:
    """
    Dynamic configuration management for hybrid retrieval system.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_default_config()
        
        if config_path:
            self._load_config_from_file()
        
        # Dynamic adjustment parameters
        self.adjustment_history = deque(maxlen=100)
        self.last_optimization = time.time()
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            "retrieval": {
                "max_chunks": 10,
                "min_chunks": 1,
                "default_chunks": 5,
                "similarity_thresholds": {
                    "openai": 0.3,
                    "gemini": 0.15,
                    "anthropic": 0.25,
                    "default": 0.3
                },
                "adaptive_threshold_enabled": True,
                "threshold_adjustment_rate": 0.05
            },
            "routing": {
                "default_mode": "adaptive",
                "fallback_enabled": True,
                "max_fallback_attempts": 3,
                "mode_weights": {
                    "pure_llm": 1.0,
                    "document_only": 1.0,
                    "hybrid_balanced": 1.5,
                    "hybrid_llm_heavy": 1.3,
                    "hybrid_document_heavy": 1.3
                },
                "learning_rate": 0.1
            },
            "caching": {
                "enabled": True,
                "strategy": "adaptive",
                "max_memory_mb": 512,
                "default_ttl": 3600,
                "min_ttl": 300,
                "max_ttl": 86400,
                "redis_enabled": True
            },
            "performance": {
                "monitoring_enabled": True,
                "metrics_retention_days": 30,
                "alert_thresholds": {
                    "response_time_p95": 2.0,  # seconds
                    "error_rate": 0.05,  # 5%
                    "cache_hit_rate_min": 0.3,  # 30%
                    "accuracy_min": 0.7  # 70%
                },
                "optimization_interval": 3600,  # 1 hour
                "optimization_goal": "balance_performance"
            },
            "blending": {
                "strategies": {
                    "weighted_combination": {"enabled": True, "weight": 1.0},
                    "llm_enhanced_documents": {"enabled": True, "weight": 0.8},
                    "document_extraction": {"enabled": True, "weight": 0.6},
                    "extractive_summarization": {"enabled": True, "weight": 0.7},
                    "comparative_synthesis": {"enabled": True, "weight": 0.9},
                    "creative_blending": {"enabled": True, "weight": 0.7}
                },
                "confidence_threshold": 0.5,
                "min_document_contribution": 0.1,
                "max_document_contribution": 0.9
            },
            "system": {
                "max_concurrent_requests": 100,
                "request_timeout": 30.0,
                "enable_graceful_degradation": True,
                "enable_auto_scaling": False,
                "log_level": "INFO"
            }
        }
    
    def _load_config_from_file(self):
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                file_config = json.load(f)
                self._merge_configs(self.config, file_config)
                logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
    
    def _merge_configs(self, base: Dict, update: Dict):
        """Recursively merge configuration dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path to config value
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any, persist: bool = False):
        """
        Set configuration value.
        
        Args:
            key_path: Dot-separated path to config value
            value: New value
            persist: Whether to save to file
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        old_value = config.get(keys[-1])
        config[keys[-1]] = value
        
        # Track adjustment
        self.adjustment_history.append({
            "key": key_path,
            "old_value": old_value,
            "new_value": value,
            "timestamp": time.time()
        })
        
        if persist and self.config_path:
            self._save_config()
        
        logger.debug(f"Config updated: {key_path} = {value}")
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
                logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
    
    def get_optimization_parameters(self) -> Dict[str, Any]:
        """Get parameters for system optimization."""
        return {
            "goal": self.get("performance.optimization_goal"),
            "routing_weights": self.get("routing.mode_weights"),
            "similarity_thresholds": self.get("retrieval.similarity_thresholds"),
            "cache_strategy": self.get("caching.strategy"),
            "blending_strategies": self.get("blending.strategies"),
            "learning_rate": self.get("routing.learning_rate")
        }
    
    def apply_optimization_results(self, optimizations: Dict[str, Any]):
        """Apply optimization results to configuration."""
        for key, value in optimizations.items():
            if "thresholds" in key:
                self.set(f"retrieval.similarity_thresholds.{key}", value)
            elif "weights" in key:
                self.set(f"routing.mode_weights.{key}", value)
            elif "cache" in key:
                self.set(f"caching.{key}", value)
        
        self.last_optimization = time.time()


class HybridPerformanceMonitor:
    """
    Comprehensive performance monitoring for hybrid retrieval system.
    """
    
    def __init__(
        self,
        db_session: Optional[Session] = None,
        config: Optional[HybridRetrievalConfig] = None
    ):
        """
        Initialize performance monitor.
        
        Args:
            db_session: Database session for persistence
            config: Configuration manager
        """
        self.db_session = db_session
        self.config = config or HybridRetrievalConfig()
        
        # In-memory metrics storage
        self.recent_metrics: deque = deque(maxlen=10000)
        self.metric_buffers: Dict[MetricType, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Alert management
        self.active_alerts: List[PerformanceAlert] = []
        self.alert_history: deque = deque(maxlen=100)
        
        # Optimization tracking
        self.optimization_history: deque = deque(maxlen=50)
        
        # Background tasks
        self._monitoring_task = None
        self._optimization_task = None
    
    async def initialize(self):
        """Initialize monitoring and start background tasks."""
        # Start monitoring task
        if self.config.get("performance.monitoring_enabled"):
            self._monitoring_task = asyncio.create_task(self._continuous_monitoring())
            
        # Start optimization task
        optimization_interval = self.config.get("performance.optimization_interval", 3600)
        self._optimization_task = asyncio.create_task(
            self._periodic_optimization(optimization_interval)
        )
        
        logger.info("Performance monitor initialized")
    
    async def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        bot_id: Optional[str] = None,
        user_id: Optional[str] = None,
        query_id: Optional[str] = None,
        mode_used: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a performance metric.
        
        Args:
            metric_type: Type of metric
            value: Metric value
            bot_id: Bot identifier
            user_id: User identifier
            query_id: Query identifier
            mode_used: Retrieval mode used
            metadata: Additional metadata
        """
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=time.time(),
            bot_id=bot_id,
            user_id=user_id,
            query_id=query_id,
            mode_used=mode_used,
            metadata=metadata or {}
        )
        
        # Add to in-memory storage
        self.recent_metrics.append(metric)
        self.metric_buffers[metric_type].append(metric)
        
        # Persist to database if available
        if self.db_session:
            await self._persist_metric(metric)
        
        # Check for alerts
        await self._check_alerts(metric)
    
    async def record_query_performance(
        self,
        query_id: str,
        bot_id: str,
        user_id: str,
        mode_used: str,
        response_time: float,
        confidence_score: float,
        cache_hit: bool,
        document_count: int,
        error: Optional[str] = None
    ):
        """Record comprehensive query performance metrics."""
        # Response time
        await self.record_metric(
            MetricType.RESPONSE_TIME,
            response_time,
            bot_id, user_id, query_id, mode_used,
            {"cache_hit": cache_hit, "document_count": document_count}
        )
        
        # Accuracy (approximated by confidence)
        await self.record_metric(
            MetricType.ACCURACY,
            confidence_score,
            bot_id, user_id, query_id, mode_used
        )
        
        # Error rate
        if error:
            await self.record_metric(
                MetricType.ERROR_RATE,
                1.0,
                bot_id, user_id, query_id, mode_used,
                {"error": error}
            )
        else:
            await self.record_metric(
                MetricType.ERROR_RATE,
                0.0,
                bot_id, user_id, query_id, mode_used
            )
    
    def get_aggregated_metrics(
        self,
        metric_type: MetricType,
        time_window: str = "1h",
        bot_id: Optional[str] = None
    ) -> AggregatedMetrics:
        """
        Get aggregated metrics for a time window.
        
        Args:
            metric_type: Type of metric
            time_window: Time window (e.g., "1h", "24h", "7d")
            bot_id: Optional bot filter
            
        Returns:
            Aggregated metrics
        """
        # Parse time window
        window_seconds = self._parse_time_window(time_window)
        cutoff_time = time.time() - window_seconds
        
        # Filter metrics
        metrics = [
            m for m in self.metric_buffers[metric_type]
            if m.timestamp >= cutoff_time and (bot_id is None or m.bot_id == bot_id)
        ]
        
        if not metrics:
            return AggregatedMetrics(
                metric_type=metric_type,
                mean=0.0, median=0.0, std_dev=0.0,
                min_value=0.0, max_value=0.0,
                p95=0.0, p99=0.0,
                sample_count=0,
                time_window=time_window
            )
        
        values = [m.value for m in metrics]
        
        return AggregatedMetrics(
            metric_type=metric_type,
            mean=np.mean(values),
            median=np.median(values),
            std_dev=np.std(values),
            min_value=np.min(values),
            max_value=np.max(values),
            p95=np.percentile(values, 95),
            p99=np.percentile(values, 99),
            sample_count=len(values),
            time_window=time_window
        )
    
    def get_mode_performance(
        self,
        time_window: str = "1h"
    ) -> Dict[str, Dict[str, float]]:
        """Get performance breakdown by retrieval mode."""
        window_seconds = self._parse_time_window(time_window)
        cutoff_time = time.time() - window_seconds
        
        mode_metrics = defaultdict(lambda: {
            "response_times": [],
            "accuracy_scores": [],
            "error_count": 0,
            "total_count": 0
        })
        
        for metric in self.recent_metrics:
            if metric.timestamp >= cutoff_time and metric.mode_used:
                mode_data = mode_metrics[metric.mode_used]
                mode_data["total_count"] += 1
                
                if metric.metric_type == MetricType.RESPONSE_TIME:
                    mode_data["response_times"].append(metric.value)
                elif metric.metric_type == MetricType.ACCURACY:
                    mode_data["accuracy_scores"].append(metric.value)
                elif metric.metric_type == MetricType.ERROR_RATE and metric.value > 0:
                    mode_data["error_count"] += 1
        
        # Calculate aggregates
        result = {}
        for mode, data in mode_metrics.items():
            result[mode] = {
                "avg_response_time": np.mean(data["response_times"]) if data["response_times"] else 0,
                "avg_accuracy": np.mean(data["accuracy_scores"]) if data["accuracy_scores"] else 0,
                "error_rate": data["error_count"] / max(data["total_count"], 1),
                "usage_count": data["total_count"]
            }
        
        return result
    
    async def optimize_system_parameters(self) -> Dict[str, Any]:
        """
        Optimize system parameters based on performance data.
        
        Returns:
            Optimization recommendations
        """
        goal = OptimizationGoal(self.config.get("performance.optimization_goal"))
        
        optimizations = {}
        
        # Get recent performance data
        response_metrics = self.get_aggregated_metrics(MetricType.RESPONSE_TIME, "1h")
        accuracy_metrics = self.get_aggregated_metrics(MetricType.ACCURACY, "1h")
        mode_performance = self.get_mode_performance("1h")
        
        # Optimize based on goal
        if goal == OptimizationGoal.MINIMIZE_LATENCY:
            optimizations.update(self._optimize_for_latency(response_metrics, mode_performance))
        elif goal == OptimizationGoal.MAXIMIZE_ACCURACY:
            optimizations.update(self._optimize_for_accuracy(accuracy_metrics, mode_performance))
        elif goal == OptimizationGoal.BALANCE_PERFORMANCE:
            optimizations.update(self._optimize_balanced(response_metrics, accuracy_metrics, mode_performance))
        
        # Apply optimizations
        if optimizations:
            self.config.apply_optimization_results(optimizations)
            
            # Track optimization
            self.optimization_history.append({
                "timestamp": time.time(),
                "goal": goal.value,
                "optimizations": optimizations,
                "metrics": {
                    "response_time_p95": response_metrics.p95,
                    "accuracy_mean": accuracy_metrics.mean
                }
            })
        
        return optimizations
    
    def _optimize_for_latency(
        self,
        response_metrics: AggregatedMetrics,
        mode_performance: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Optimize for minimum latency."""
        optimizations = {}
        
        # Increase cache aggressiveness
        if response_metrics.p95 > 2.0:
            optimizations["cache_strategy"] = "aggressive"
            optimizations["cache_ttl_multiplier"] = 1.5
        
        # Adjust mode weights to favor faster modes
        fastest_modes = sorted(
            mode_performance.items(),
            key=lambda x: x[1]["avg_response_time"]
        )[:3]
        
        for mode, _ in fastest_modes:
            optimizations[f"mode_weight_{mode}"] = 1.5
        
        # Reduce retrieval depth
        if response_metrics.mean > 1.5:
            current_max = self.config.get("retrieval.max_chunks", 10)
            optimizations["max_chunks"] = max(current_max - 2, 3)
        
        return optimizations
    
    def _optimize_for_accuracy(
        self,
        accuracy_metrics: AggregatedMetrics,
        mode_performance: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Optimize for maximum accuracy."""
        optimizations = {}
        
        # Adjust mode weights to favor accurate modes
        accurate_modes = sorted(
            mode_performance.items(),
            key=lambda x: x[1]["avg_accuracy"],
            reverse=True
        )[:3]
        
        for mode, _ in accurate_modes:
            optimizations[f"mode_weight_{mode}"] = 1.5
        
        # Increase retrieval depth for better context
        if accuracy_metrics.mean < 0.8:
            current_max = self.config.get("retrieval.max_chunks", 10)
            optimizations["max_chunks"] = min(current_max + 2, 15)
        
        # Lower similarity thresholds for more results
        if accuracy_metrics.mean < 0.7:
            for provider in ["openai", "gemini", "anthropic"]:
                current = self.config.get(f"retrieval.similarity_thresholds.{provider}", 0.3)
                optimizations[f"threshold_{provider}"] = max(current - 0.05, 0.1)
        
        return optimizations
    
    def _optimize_balanced(
        self,
        response_metrics: AggregatedMetrics,
        accuracy_metrics: AggregatedMetrics,
        mode_performance: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Optimize for balanced performance."""
        optimizations = {}
        
        # Calculate efficiency score for each mode
        mode_scores = {}
        for mode, perf in mode_performance.items():
            if perf["avg_response_time"] > 0:
                # Balance accuracy and speed
                efficiency = perf["avg_accuracy"] / (perf["avg_response_time"] ** 0.5)
                mode_scores[mode] = efficiency
        
        # Boost efficient modes
        if mode_scores:
            best_modes = sorted(mode_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            for mode, _ in best_modes:
                optimizations[f"mode_weight_{mode}"] = 1.3
        
        # Moderate cache strategy
        optimizations["cache_strategy"] = "moderate"
        
        # Adaptive chunk size
        if response_metrics.p95 > 3.0:
            optimizations["max_chunks"] = 7
        elif accuracy_metrics.mean < 0.6:
            optimizations["max_chunks"] = 10
        
        return optimizations
    
    async def _check_alerts(self, metric: PerformanceMetric):
        """Check if metric triggers any alerts."""
        thresholds = self.config.get("performance.alert_thresholds", {})
        
        alert = None
        
        if metric.metric_type == MetricType.RESPONSE_TIME:
            threshold = thresholds.get("response_time_p95", 2.0)
            if metric.value > threshold:
                alert = PerformanceAlert(
                    alert_type="high_response_time",
                    severity="high" if metric.value > threshold * 2 else "medium",
                    metric_type=metric.metric_type,
                    current_value=metric.value,
                    threshold=threshold,
                    message=f"Response time {metric.value:.2f}s exceeds threshold {threshold}s",
                    timestamp=time.time()
                )
        
        elif metric.metric_type == MetricType.ERROR_RATE:
            threshold = thresholds.get("error_rate", 0.05)
            recent_errors = [m for m in self.metric_buffers[MetricType.ERROR_RATE][-100:]]
            if recent_errors:
                error_rate = sum(m.value for m in recent_errors) / len(recent_errors)
                if error_rate > threshold:
                    alert = PerformanceAlert(
                        alert_type="high_error_rate",
                        severity="critical" if error_rate > 0.2 else "high",
                        metric_type=metric.metric_type,
                        current_value=error_rate,
                        threshold=threshold,
                        message=f"Error rate {error_rate:.2%} exceeds threshold {threshold:.2%}",
                        timestamp=time.time()
                    )
        
        if alert:
            self.active_alerts.append(alert)
            self.alert_history.append(alert)
            logger.warning(f"Performance alert: {alert.message}")
    
    def _parse_time_window(self, window: str) -> float:
        """Parse time window string to seconds."""
        unit_map = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        
        try:
            value = int(window[:-1])
            unit = window[-1]
            return value * unit_map.get(unit, 3600)
        except:
            return 3600  # Default 1 hour
    
    async def _store_metric_in_db(self, metric: PerformanceMetric):
        """Store metric in database."""
        try:
            db_metric = PerformanceMetricDB(
                id=str(uuid.uuid4()),
                metric_type=metric.metric_type.value,
                value=metric.value,
                timestamp=datetime.fromtimestamp(metric.timestamp),
                bot_id=metric.bot_id,
                user_id=metric.user_id,
                query_id=metric.query_id,
                mode_used=metric.mode_used,
                metric_metadata=metric.metadata
            )
            
            self.db_session.add(db_metric)
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Failed to store metric in database: {e}")
            self.db_session.rollback()
    
    async def _persist_metric(self, metric: PerformanceMetric):
        """Persist metric to database."""
        await self._store_metric_in_db(metric)
    
    async def _continuous_monitoring(self):
        """Continuous monitoring task."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Calculate current metrics
                for metric_type in MetricType:
                    aggregated = self.get_aggregated_metrics(metric_type, "5m")
                    
                    # Log summary
                    if aggregated.sample_count > 0:
                        logger.info(
                            f"{metric_type.value}: mean={aggregated.mean:.3f}, "
                            f"p95={aggregated.p95:.3f}, samples={aggregated.sample_count}"
                        )
                
                # Clean old alerts
                cutoff_time = time.time() - 3600  # Keep alerts for 1 hour
                self.active_alerts = [
                    a for a in self.active_alerts
                    if a.timestamp >= cutoff_time
                ]
                
            except Exception as e:
                logger.error(f"Error in monitoring task: {e}")
    
    async def _periodic_optimization(self, interval: float):
        """Periodic optimization task."""
        while True:
            try:
                await asyncio.sleep(interval)
                
                # Run optimization
                optimizations = await self.optimize_system_parameters()
                
                if optimizations:
                    logger.info(f"Applied system optimizations: {optimizations}")
                
            except Exception as e:
                logger.error(f"Error in optimization task: {e}")
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get metrics for dashboard display."""
        return {
            "current_performance": {
                "response_time": asdict(self.get_aggregated_metrics(MetricType.RESPONSE_TIME, "5m")),
                "accuracy": asdict(self.get_aggregated_metrics(MetricType.ACCURACY, "5m")),
                "error_rate": asdict(self.get_aggregated_metrics(MetricType.ERROR_RATE, "5m"))
            },
            "mode_breakdown": self.get_mode_performance("1h"),
            "active_alerts": [asdict(a) for a in self.active_alerts],
            "optimization_history": list(self.optimization_history)[-10:],
            "config_adjustments": list(self.config.adjustment_history)[-10:]
        }
    
    async def close(self):
        """Close monitor and clean up resources."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitor closed")
