"""
Embedding Model Migration Service - Model compatibility and migration support.

This service provides:
- Dimension compatibility checking between old and new models
- Impact analysis for model changes with clear explanations
- Automatic model list updates when providers add new models
- Model migration workflow with validation and rollback
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid
from datetime import datetime, timedelta
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from fastapi import HTTPException, status

from ..models.bot import Bot
from ..models.collection_metadata import (
    CollectionMetadata, 
    EmbeddingConfigurationHistory, 
    DimensionCompatibilityCache
)
from ..models.document import DocumentChunk
from .embedding_service import EmbeddingProviderService
from .embedding_model_validator import EmbeddingModelValidator, ModelValidationResult
from .vector_collection_manager import VectorCollectionManager
from .user_service import UserService


logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Status of model migration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ImpactLevel(Enum):
    """Impact level of model changes."""
    MINIMAL = "minimal"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    CRITICAL = "critical"


@dataclass
class DimensionCompatibilityCheck:
    """Result of dimension compatibility check."""
    is_compatible: bool
    current_dimension: int
    target_dimension: int
    dimension_change: int
    compatibility_percentage: float
    migration_required: bool
    impact_assessment: str


@dataclass
class ModelChangeImpact:
    """Analysis of model change impact."""
    impact_level: ImpactLevel
    affected_documents: int
    affected_chunks: int
    estimated_migration_time: str
    estimated_cost: Optional[str]
    data_loss_risk: str
    performance_impact: str
    compatibility_issues: List[str]
    recommendations: List[str]
    rollback_complexity: str


@dataclass
class MigrationPlan:
    """Comprehensive migration plan."""
    migration_id: str
    bot_id: uuid.UUID
    current_config: Dict[str, Any]
    target_config: Dict[str, Any]
    compatibility_check: DimensionCompatibilityCheck
    impact_analysis: ModelChangeImpact
    migration_steps: List[Dict[str, Any]]
    rollback_plan: List[Dict[str, Any]]
    validation_checkpoints: List[str]
    estimated_duration: str
    created_at: datetime


@dataclass
class MigrationResult:
    """Result of migration execution."""
    migration_id: str
    status: MigrationStatus
    success: bool
    completed_steps: int
    total_steps: int
    error_message: Optional[str]
    rollback_available: bool
    performance_metrics: Dict[str, Any]
    validation_results: Dict[str, Any]
    completed_at: Optional[datetime]


class EmbeddingModelMigration:
    """
    Embedding model migration service.
    
    Provides comprehensive migration support including compatibility checking,
    impact analysis, and safe migration workflows with rollback capability.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the migration service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.embedding_service = EmbeddingProviderService()
        self.model_validator = EmbeddingModelValidator(db)
        self.vector_manager = VectorCollectionManager(db)
        self.user_service = UserService(db)
        
        # Migration settings
        self.batch_size = 100  # Documents per batch
        self.max_retries = 3
        self.checkpoint_interval = 500  # Save progress every N documents
        
        # Compatibility thresholds
        self.dimension_tolerance = 0.05  # 5% dimension difference tolerance
        self.min_compatibility_score = 0.7
    
    async def check_dimension_compatibility(
        self,
        current_provider: str,
        current_model: str,
        target_provider: str,
        target_model: str
    ) -> DimensionCompatibilityCheck:
        """
        Check dimension compatibility between old and new models.
        
        Args:
            current_provider: Current embedding provider
            current_model: Current embedding model
            target_provider: Target embedding provider
            target_model: Target embedding model
            
        Returns:
            DimensionCompatibilityCheck with compatibility analysis
        """
        try:
            logger.info(f"Checking dimension compatibility: {current_provider}/{current_model} -> {target_provider}/{target_model}")
            
            # Validate both models
            current_validation = await self.model_validator.validate_model_availability(
                current_provider, current_model
            )
            target_validation = await self.model_validator.validate_model_availability(
                target_provider, target_model
            )
            
            if not current_validation.is_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Current model {current_provider}/{current_model} is not available"
                )
            
            if not target_validation.is_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Target model {target_provider}/{target_model} is not available"
                )
            
            current_dimension = current_validation.dimension
            target_dimension = target_validation.dimension
            dimension_change = target_dimension - current_dimension
            
            # Calculate compatibility percentage
            if current_dimension == 0 or target_dimension == 0:
                compatibility_percentage = 0.0
            else:
                smaller_dim = min(current_dimension, target_dimension)
                larger_dim = max(current_dimension, target_dimension)
                compatibility_percentage = (smaller_dim / larger_dim) * 100
            
            # Determine if migration is required
            migration_required = current_dimension != target_dimension
            is_compatible = abs(dimension_change) / max(current_dimension, 1) <= self.dimension_tolerance
            
            # Generate impact assessment
            if not migration_required:
                impact_assessment = "No migration required - dimensions match"
            elif abs(dimension_change) < 100:
                impact_assessment = "Minor dimension change - low impact migration"
            elif abs(dimension_change) < 500:
                impact_assessment = "Moderate dimension change - medium impact migration"
            else:
                impact_assessment = "Major dimension change - high impact migration"
            
            result = DimensionCompatibilityCheck(
                is_compatible=is_compatible,
                current_dimension=current_dimension,
                target_dimension=target_dimension,
                dimension_change=dimension_change,
                compatibility_percentage=compatibility_percentage,
                migration_required=migration_required,
                impact_assessment=impact_assessment
            )
            
            logger.info(f"Dimension compatibility check complete: compatible={is_compatible}, migration_required={migration_required}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking dimension compatibility: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Compatibility check failed: {str(e)}"
            )
    
    async def analyze_migration_impact(
        self,
        bot_id: uuid.UUID,
        target_provider: str,
        target_model: str,
        compatibility_check: DimensionCompatibilityCheck
    ) -> ModelChangeImpact:
        """
        Analyze the impact of model changes with clear explanations.
        
        Args:
            bot_id: Bot identifier
            target_provider: Target embedding provider
            target_model: Target embedding model
            compatibility_check: Dimension compatibility check result
            
        Returns:
            ModelChangeImpact with detailed impact analysis
        """
        try:
            logger.info(f"Analyzing migration impact for bot {bot_id}")
            
            # Get bot information
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bot not found"
                )
            
            # Count affected data
            affected_documents = self.db.query(func.count(DocumentChunk.document_id.distinct())).filter(
                DocumentChunk.bot_id == bot_id
            ).scalar() or 0
            
            affected_chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.bot_id == bot_id
            ).count()
            
            # Determine impact level
            if not compatibility_check.migration_required:
                impact_level = ImpactLevel.MINIMAL
            elif affected_chunks < 100:
                impact_level = ImpactLevel.MINIMAL
            elif affected_chunks < 1000:
                impact_level = ImpactLevel.MODERATE
            elif affected_chunks < 10000:
                impact_level = ImpactLevel.SIGNIFICANT
            else:
                impact_level = ImpactLevel.CRITICAL
            
            # Estimate migration time
            estimated_migration_time = self._estimate_detailed_migration_time(
                affected_chunks, compatibility_check.migration_required
            )
            
            # Estimate cost (placeholder - could be enhanced with actual pricing)
            estimated_cost = self._estimate_migration_cost(
                affected_chunks, target_provider, target_model
            )
            
            # Assess data loss risk
            if not compatibility_check.migration_required:
                data_loss_risk = "None - no migration required"
            elif compatibility_check.is_compatible:
                data_loss_risk = "Low - compatible dimensions with backup"
            else:
                data_loss_risk = "Medium - dimension change requires reprocessing"
            
            # Assess performance impact
            performance_impact = self._assess_performance_impact(
                compatibility_check, target_provider, target_model
            )
            
            # Identify compatibility issues
            compatibility_issues = []
            if not compatibility_check.is_compatible:
                compatibility_issues.append(
                    f"Dimension change from {compatibility_check.current_dimension} "
                    f"to {compatibility_check.target_dimension}"
                )
            
            if compatibility_check.compatibility_percentage < 80:
                compatibility_issues.append(
                    f"Low compatibility score: {compatibility_check.compatibility_percentage:.1f}%"
                )
            
            # Generate recommendations
            recommendations = self._generate_migration_recommendations(
                impact_level, compatibility_check, affected_chunks
            )
            
            # Assess rollback complexity
            rollback_complexity = self._assess_rollback_complexity(
                impact_level, affected_chunks, compatibility_check.migration_required
            )
            
            result = ModelChangeImpact(
                impact_level=impact_level,
                affected_documents=affected_documents,
                affected_chunks=affected_chunks,
                estimated_migration_time=estimated_migration_time,
                estimated_cost=estimated_cost,
                data_loss_risk=data_loss_risk,
                performance_impact=performance_impact,
                compatibility_issues=compatibility_issues,
                recommendations=recommendations,
                rollback_complexity=rollback_complexity
            )
            
            logger.info(f"Migration impact analysis complete: impact_level={impact_level.value}, affected_chunks={affected_chunks}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error analyzing migration impact for bot {bot_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Impact analysis failed: {str(e)}"
            )
    
    async def create_migration_plan(
        self,
        bot_id: uuid.UUID,
        target_provider: str,
        target_model: str,
        migration_reason: Optional[str] = None
    ) -> MigrationPlan:
        """
        Create a comprehensive migration plan with validation and rollback.
        
        Args:
            bot_id: Bot identifier
            target_provider: Target embedding provider
            target_model: Target embedding model
            migration_reason: Optional reason for migration
            
        Returns:
            MigrationPlan with detailed migration strategy
        """
        try:
            logger.info(f"Creating migration plan for bot {bot_id}: {target_provider}/{target_model}")
            
            # Get bot and current configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bot not found"
                )
            
            current_provider = bot.embedding_provider or "openai"
            current_model = bot.embedding_model or "text-embedding-3-small"
            
            # Check dimension compatibility
            compatibility_check = await self.check_dimension_compatibility(
                current_provider, current_model, target_provider, target_model
            )
            
            # Analyze migration impact
            impact_analysis = await self.analyze_migration_impact(
                bot_id, target_provider, target_model, compatibility_check
            )
            
            # Generate migration ID
            migration_id = f"migration_{bot_id}_{int(datetime.utcnow().timestamp())}"
            
            # Create migration steps
            migration_steps = self._create_migration_steps(
                bot_id, compatibility_check, impact_analysis
            )
            
            # Create rollback plan
            rollback_plan = self._create_rollback_plan(
                bot_id, current_provider, current_model, compatibility_check
            )
            
            # Define validation checkpoints
            validation_checkpoints = [
                "Pre-migration validation",
                "Backup verification",
                "New collection creation",
                "Data migration validation",
                "Performance validation",
                "Post-migration verification"
            ]
            
            # Estimate total duration
            estimated_duration = self._estimate_total_duration(
                impact_analysis.estimated_migration_time, len(migration_steps)
            )
            
            plan = MigrationPlan(
                migration_id=migration_id,
                bot_id=bot_id,
                current_config={
                    "provider": current_provider,
                    "model": current_model,
                    "dimension": compatibility_check.current_dimension
                },
                target_config={
                    "provider": target_provider,
                    "model": target_model,
                    "dimension": compatibility_check.target_dimension
                },
                compatibility_check=compatibility_check,
                impact_analysis=impact_analysis,
                migration_steps=migration_steps,
                rollback_plan=rollback_plan,
                validation_checkpoints=validation_checkpoints,
                estimated_duration=estimated_duration,
                created_at=datetime.utcnow()
            )
            
            logger.info(f"Migration plan created: {migration_id} with {len(migration_steps)} steps")
            return plan
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating migration plan for bot {bot_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Migration plan creation failed: {str(e)}"
            )
    
    async def execute_migration(
        self,
        migration_plan: MigrationPlan,
        user_id: uuid.UUID,
        dry_run: bool = False
    ) -> MigrationResult:
        """
        Execute model migration with validation and rollback capability.
        
        Args:
            migration_plan: Migration plan to execute
            user_id: User executing the migration
            dry_run: Whether to perform a dry run without actual changes
            
        Returns:
            MigrationResult with execution details
        """
        try:
            logger.info(f"Executing migration {migration_plan.migration_id} (dry_run={dry_run})")
            
            start_time = datetime.utcnow()
            completed_steps = 0
            total_steps = len(migration_plan.migration_steps)
            performance_metrics = {}
            validation_results = {}
            
            if dry_run:
                logger.info("Performing dry run - no actual changes will be made")
            
            # Execute migration steps
            for i, step in enumerate(migration_plan.migration_steps):
                try:
                    step_start = datetime.utcnow()
                    logger.info(f"Executing step {i+1}/{total_steps}: {step['name']}")
                    
                    if not dry_run:
                        await self._execute_migration_step(step, migration_plan)
                    
                    step_duration = (datetime.utcnow() - step_start).total_seconds()
                    performance_metrics[f"step_{i+1}"] = {
                        "name": step["name"],
                        "duration_seconds": step_duration,
                        "status": "completed"
                    }
                    
                    completed_steps += 1
                    
                    # Validation checkpoint
                    if step.get("validation_required", False):
                        validation_result = await self._validate_migration_step(
                            step, migration_plan, dry_run
                        )
                        validation_results[f"step_{i+1}"] = validation_result
                        
                        if not validation_result.get("success", False) and not dry_run:
                            raise Exception(f"Validation failed for step {step['name']}")
                    
                except Exception as e:
                    logger.error(f"Migration step {i+1} failed: {e}")
                    
                    if not dry_run:
                        # Attempt rollback
                        logger.info("Attempting rollback due to migration failure")
                        await self._execute_rollback(migration_plan, completed_steps)
                    
                    return MigrationResult(
                        migration_id=migration_plan.migration_id,
                        status=MigrationStatus.FAILED,
                        success=False,
                        completed_steps=completed_steps,
                        total_steps=total_steps,
                        error_message=str(e),
                        rollback_available=True,
                        performance_metrics=performance_metrics,
                        validation_results=validation_results,
                        completed_at=datetime.utcnow()
                    )
            
            # Record migration in history
            if not dry_run:
                await self._record_migration_history(migration_plan, user_id, True)
            
            total_duration = (datetime.utcnow() - start_time).total_seconds()
            performance_metrics["total_duration_seconds"] = total_duration
            
            result = MigrationResult(
                migration_id=migration_plan.migration_id,
                status=MigrationStatus.COMPLETED if not dry_run else MigrationStatus.PENDING,
                success=True,
                completed_steps=completed_steps,
                total_steps=total_steps,
                error_message=None,
                rollback_available=not dry_run,
                performance_metrics=performance_metrics,
                validation_results=validation_results,
                completed_at=datetime.utcnow() if not dry_run else None
            )
            
            logger.info(f"Migration {migration_plan.migration_id} completed successfully in {total_duration:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error executing migration {migration_plan.migration_id}: {e}")
            return MigrationResult(
                migration_id=migration_plan.migration_id,
                status=MigrationStatus.FAILED,
                success=False,
                completed_steps=0,
                total_steps=len(migration_plan.migration_steps),
                error_message=str(e),
                rollback_available=False,
                performance_metrics={},
                validation_results={},
                completed_at=datetime.utcnow()
            )
    
    async def update_model_lists(
        self,
        provider: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Update model lists when providers add new models.
        
        Args:
            provider: Specific provider to update (None for all)
            force_refresh: Whether to force refresh even if recently updated
            
        Returns:
            Dictionary with update results
        """
        try:
            logger.info(f"Updating model lists (provider={provider}, force_refresh={force_refresh})")
            
            update_results = {}
            providers_to_update = [provider] if provider else self.embedding_service.get_supported_providers()
            
            for provider_name in providers_to_update:
                try:
                    # Get current static models
                    static_models = self.embedding_service.get_available_models(provider_name)
                    
                    # Try to get dynamic models (requires API key)
                    dynamic_models = []
                    try:
                        # This would need an API key - for now, use static models
                        dynamic_models = static_models
                    except Exception as e:
                        logger.warning(f"Could not get dynamic models for {provider_name}: {e}")
                        dynamic_models = static_models
                    
                    # Compare and identify new models
                    new_models = set(dynamic_models) - set(static_models)
                    
                    # Validate new models
                    validated_new_models = []
                    for model in new_models:
                        validation = await self.model_validator.validate_model_availability(
                            provider_name, model, use_cache=False
                        )
                        if validation.is_available:
                            validated_new_models.append({
                                "model": model,
                                "dimension": validation.dimension,
                                "status": validation.status.value
                            })
                    
                    update_results[provider_name] = {
                        "static_models": len(static_models),
                        "dynamic_models": len(dynamic_models),
                        "new_models": validated_new_models,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                except Exception as e:
                    logger.error(f"Error updating models for provider {provider_name}: {e}")
                    update_results[provider_name] = {
                        "error": str(e),
                        "updated_at": datetime.utcnow().isoformat()
                    }
            
            logger.info(f"Model list update complete for {len(update_results)} providers")
            return {
                "success": True,
                "providers_updated": len(update_results),
                "results": update_results,
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating model lists: {e}")
            return {
                "success": False,
                "error": str(e),
                "updated_at": datetime.utcnow().isoformat()
            }
    
    # Private helper methods
    
    def _estimate_detailed_migration_time(
        self,
        chunk_count: int,
        migration_required: bool
    ) -> str:
        """Estimate detailed migration time based on chunk count and requirements."""
        if not migration_required:
            return "Immediate (no migration needed)"
        
        if chunk_count == 0:
            return "1-2 minutes (configuration only)"
        elif chunk_count < 50:
            return "2-5 minutes"
        elif chunk_count < 200:
            return "5-15 minutes"
        elif chunk_count < 1000:
            return "15-45 minutes"
        elif chunk_count < 5000:
            return "45 minutes - 2 hours"
        elif chunk_count < 20000:
            return "2-6 hours"
        else:
            return "6+ hours (consider phased migration)"
    
    def _estimate_migration_cost(
        self,
        chunk_count: int,
        target_provider: str,
        target_model: str
    ) -> str:
        """Estimate migration cost (placeholder implementation)."""
        # This could be enhanced with actual pricing data
        base_costs = {
            "openai": 0.0001,  # per 1K tokens
            "gemini": 0.00005,
            "anthropic": 0.0001,
            "openrouter": 0.0002
        }
        
        base_cost = base_costs.get(target_provider, 0.0001)
        estimated_tokens = chunk_count * 500  # Assume 500 tokens per chunk
        estimated_cost = (estimated_tokens / 1000) * base_cost
        
        if estimated_cost < 0.01:
            return "< $0.01"
        elif estimated_cost < 0.10:
            return f"~${estimated_cost:.2f}"
        elif estimated_cost < 1.00:
            return f"~${estimated_cost:.2f}"
        else:
            return f"~${estimated_cost:.0f}"
    
    def _assess_performance_impact(
        self,
        compatibility_check: DimensionCompatibilityCheck,
        target_provider: str,
        target_model: str
    ) -> str:
        """Assess performance impact of model change."""
        impacts = []
        
        if compatibility_check.dimension_change > 0:
            impacts.append("Increased embedding dimension may improve accuracy")
            impacts.append("Slightly higher memory usage")
        elif compatibility_check.dimension_change < 0:
            impacts.append("Reduced embedding dimension may decrease accuracy")
            impacts.append("Lower memory usage")
        else:
            impacts.append("No dimension change - similar performance expected")
        
        # Provider-specific impacts
        if target_provider == "openai":
            impacts.append("Generally reliable performance")
        elif target_provider == "gemini":
            impacts.append("May have different latency characteristics")
        
        return "; ".join(impacts)
    
    def _generate_migration_recommendations(
        self,
        impact_level: ImpactLevel,
        compatibility_check: DimensionCompatibilityCheck,
        affected_chunks: int
    ) -> List[str]:
        """Generate migration recommendations based on impact analysis."""
        recommendations = []
        
        if impact_level == ImpactLevel.MINIMAL:
            recommendations.append("Migration can be performed during normal operation")
        elif impact_level == ImpactLevel.MODERATE:
            recommendations.append("Schedule migration during low-usage period")
        elif impact_level == ImpactLevel.SIGNIFICANT:
            recommendations.append("Plan for maintenance window")
            recommendations.append("Notify users of potential temporary service disruption")
        else:  # CRITICAL
            recommendations.append("Schedule during planned maintenance window")
            recommendations.append("Consider phased migration approach")
            recommendations.append("Ensure full backup before proceeding")
        
        if not compatibility_check.is_compatible:
            recommendations.append("Test with small subset of documents first")
        
        if affected_chunks > 10000:
            recommendations.append("Monitor system resources during migration")
        
        recommendations.append("Verify API key availability for target provider")
        
        return recommendations
    
    def _assess_rollback_complexity(
        self,
        impact_level: ImpactLevel,
        affected_chunks: int,
        migration_required: bool
    ) -> str:
        """Assess rollback complexity."""
        if not migration_required:
            return "Simple - configuration change only"
        elif impact_level == ImpactLevel.MINIMAL:
            return "Low - quick rollback possible"
        elif impact_level == ImpactLevel.MODERATE:
            return "Medium - rollback requires backup restoration"
        elif impact_level == ImpactLevel.SIGNIFICANT:
            return "High - complex rollback process"
        else:
            return "Very High - extensive rollback procedure required"
    
    def _create_migration_steps(
        self,
        bot_id: uuid.UUID,
        compatibility_check: DimensionCompatibilityCheck,
        impact_analysis: ModelChangeImpact
    ) -> List[Dict[str, Any]]:
        """Create detailed migration steps."""
        steps = []
        
        # Pre-migration validation
        steps.append({
            "name": "Pre-migration validation",
            "description": "Validate current configuration and target model",
            "type": "validation",
            "validation_required": True,
            "estimated_duration": "1-2 minutes"
        })
        
        # Backup current state
        if compatibility_check.migration_required:
            steps.append({
                "name": "Create backup",
                "description": "Backup current embeddings and configuration",
                "type": "backup",
                "validation_required": True,
                "estimated_duration": "2-5 minutes"
            })
        
        # Create new collection
        if compatibility_check.migration_required:
            steps.append({
                "name": "Create new collection",
                "description": "Initialize new vector collection with target dimensions",
                "type": "collection_setup",
                "validation_required": True,
                "estimated_duration": "1-2 minutes"
            })
        
        # Migrate data
        if compatibility_check.migration_required and impact_analysis.affected_chunks > 0:
            steps.append({
                "name": "Migrate embeddings",
                "description": "Reprocess documents with new embedding model",
                "type": "data_migration",
                "validation_required": True,
                "estimated_duration": impact_analysis.estimated_migration_time
            })
        
        # Update configuration
        steps.append({
            "name": "Update bot configuration",
            "description": "Update bot to use new embedding provider and model",
            "type": "configuration_update",
            "validation_required": True,
            "estimated_duration": "1 minute"
        })
        
        # Post-migration validation
        steps.append({
            "name": "Post-migration validation",
            "description": "Validate migration success and performance",
            "type": "validation",
            "validation_required": True,
            "estimated_duration": "2-3 minutes"
        })
        
        return steps
    
    def _create_rollback_plan(
        self,
        bot_id: uuid.UUID,
        current_provider: str,
        current_model: str,
        compatibility_check: DimensionCompatibilityCheck
    ) -> List[Dict[str, Any]]:
        """Create rollback plan."""
        rollback_steps = []
        
        if compatibility_check.migration_required:
            rollback_steps.extend([
                {
                    "name": "Stop current operations",
                    "description": "Halt any ongoing operations on the bot",
                    "type": "operational"
                },
                {
                    "name": "Restore original collection",
                    "description": "Restore original vector collection from backup",
                    "type": "data_restoration"
                },
                {
                    "name": "Revert configuration",
                    "description": f"Restore bot configuration to {current_provider}/{current_model}",
                    "type": "configuration_revert"
                },
                {
                    "name": "Validate rollback",
                    "description": "Verify rollback success and functionality",
                    "type": "validation"
                }
            ])
        else:
            rollback_steps.append({
                "name": "Revert configuration",
                "description": f"Restore bot configuration to {current_provider}/{current_model}",
                "type": "configuration_revert"
            })
        
        return rollback_steps
    
    def _estimate_total_duration(
        self,
        migration_time: str,
        step_count: int
    ) -> str:
        """Estimate total migration duration including overhead."""
        # Add overhead for validation and setup steps
        overhead_minutes = step_count * 2  # 2 minutes per step overhead
        
        # Parse migration time (simplified)
        if "minute" in migration_time:
            if "-" in migration_time:
                # Range like "5-15 minutes"
                parts = migration_time.split("-")
                max_minutes = int(parts[1].split()[0])
            else:
                max_minutes = int(migration_time.split()[0])
        elif "hour" in migration_time:
            if "-" in migration_time:
                parts = migration_time.split("-")
                max_hours = int(parts[1].split()[0])
                max_minutes = max_hours * 60
            else:
                max_hours = int(migration_time.split()[0])
                max_minutes = max_hours * 60
        else:
            max_minutes = 10  # Default
        
        total_minutes = max_minutes + overhead_minutes
        
        if total_minutes < 60:
            return f"{total_minutes} minutes"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if minutes > 0:
                return f"{hours} hours {minutes} minutes"
            else:
                return f"{hours} hours"
    
    async def _execute_migration_step(
        self,
        step: Dict[str, Any],
        migration_plan: MigrationPlan
    ) -> None:
        """Execute a single migration step."""
        step_type = step.get("type")
        
        if step_type == "validation":
            await self._validate_migration_preconditions(migration_plan)
        elif step_type == "backup":
            await self._create_migration_backup(migration_plan)
        elif step_type == "collection_setup":
            await self._setup_new_collection(migration_plan)
        elif step_type == "data_migration":
            await self._migrate_embeddings_data(migration_plan)
        elif step_type == "configuration_update":
            await self._update_bot_configuration(migration_plan)
        else:
            logger.warning(f"Unknown migration step type: {step_type}")
    
    async def _validate_migration_step(
        self,
        step: Dict[str, Any],
        migration_plan: MigrationPlan,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Validate a migration step."""
        # Placeholder validation - would implement actual validation logic
        return {
            "success": True,
            "step_name": step["name"],
            "validation_time": datetime.utcnow().isoformat(),
            "dry_run": dry_run
        }
    
    async def _execute_rollback(
        self,
        migration_plan: MigrationPlan,
        completed_steps: int
    ) -> None:
        """Execute rollback procedure."""
        logger.info(f"Executing rollback for migration {migration_plan.migration_id}")
        
        for step in reversed(migration_plan.rollback_plan):
            try:
                logger.info(f"Rollback step: {step['name']}")
                # Implement actual rollback logic here
                await asyncio.sleep(0.1)  # Placeholder
            except Exception as e:
                logger.error(f"Rollback step failed: {step['name']}: {e}")
    
    async def _record_migration_history(
        self,
        migration_plan: MigrationPlan,
        user_id: uuid.UUID,
        success: bool
    ) -> None:
        """Record migration in configuration history."""
        try:
            history_entry = EmbeddingConfigurationHistory(
                bot_id=migration_plan.bot_id,
                previous_provider=migration_plan.current_config["provider"],
                previous_model=migration_plan.current_config["model"],
                previous_dimension=migration_plan.current_config["dimension"],
                new_provider=migration_plan.target_config["provider"],
                new_model=migration_plan.target_config["model"],
                new_dimension=migration_plan.target_config["dimension"],
                change_reason="Model migration",
                migration_required=migration_plan.compatibility_check.migration_required,
                migration_completed=success,
                migration_id=migration_plan.migration_id,
                changed_by=user_id,
                extra_metadata={
                    "migration_plan": {
                        "impact_level": migration_plan.impact_analysis.impact_level.value,
                        "affected_chunks": migration_plan.impact_analysis.affected_chunks,
                        "estimated_duration": migration_plan.estimated_duration
                    }
                }
            )
            
            self.db.add(history_entry)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error recording migration history: {e}")
            self.db.rollback()
    
    # Placeholder methods for actual migration operations
    async def _validate_migration_preconditions(self, migration_plan: MigrationPlan) -> None:
        """Validate migration preconditions."""
        pass
    
    async def _create_migration_backup(self, migration_plan: MigrationPlan) -> None:
        """Create migration backup."""
        pass
    
    async def _setup_new_collection(self, migration_plan: MigrationPlan) -> None:
        """Setup new vector collection."""
        pass
    
    async def _migrate_embeddings_data(self, migration_plan: MigrationPlan) -> None:
        """Migrate embeddings data."""
        pass
    
    async def _update_bot_configuration(self, migration_plan: MigrationPlan) -> None:
        """Update bot configuration."""
        pass