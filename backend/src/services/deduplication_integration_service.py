"""
Integration service for intelligent chunk deduplication system.
Provides unified API for all deduplication operations and reporting.
Implements requirements 10.1, 10.2, 10.3, 10.4, 10.5 for tasks 11.1 and 11.2.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime

from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.document import Document, DocumentChunk
from ..models.bot import Bot
from ..services.chunk_deduplication_service import (
    ChunkDeduplicationService,
    DeduplicationConfig,
    DeduplicationResult
)
from ..services.deduplication_manager import (
    DeduplicationManager,
    DeduplicationPolicy,
    ConflictResolutionStrategy,
    DeduplicationReport
)
from ..services.deduplication_audit_service import DeduplicationAuditService
from ..services.vector_store import VectorService

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationOperationRequest:
    """Request for deduplication operation."""
    bot_id: UUID
    operation_type: str  # 'full_bot', 'document', 'chunk_list', 'reprocessing'
    target_ids: Optional[List[UUID]] = None  # Document IDs or chunk IDs
    user_id: Optional[UUID] = None
    config_override: Optional[Dict[str, Any]] = None
    force_execution: bool = False


@dataclass
class DeduplicationSummary:
    """Summary of deduplication status and recommendations."""
    bot_id: UUID
    total_chunks: int
    potential_duplicates: int
    active_conflicts: int
    last_deduplication: Optional[datetime]
    efficiency_score: float  # 0.0 to 1.0
    recommendations: List[str]
    policy_status: Dict[str, Any]
    performance_metrics: Dict[str, Any]


class DeduplicationIntegrationService:
    """
    Unified integration service for all deduplication operations.
    Provides high-level API for content-based deduplication with
    conflict resolution and comprehensive reporting.
    """
    
    def __init__(self, db: Session):
        """
        Initialize deduplication integration service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.vector_service = VectorService()
        self.deduplication_service = ChunkDeduplicationService(db, self.vector_service)
        self.audit_service = DeduplicationAuditService(db)
        self.manager = DeduplicationManager(
            db, self.vector_service, self.deduplication_service, self.audit_service
        )
    
    async def execute_deduplication_operation(
        self,
        request: DeduplicationOperationRequest
    ) -> Dict[str, Any]:
        """
        Execute a deduplication operation based on the request type.
        
        Args:
            request: Deduplication operation request
            
        Returns:
            Operation result with detailed information
        """
        try:
            logger.info(
                f"Starting deduplication operation {request.operation_type} "
                f"for bot {request.bot_id}"
            )
            
            # Validate request
            validation_result = await self._validate_operation_request(request)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'operation_type': request.operation_type
                }
            
            # Execute based on operation type
            if request.operation_type == 'full_bot':
                result = await self._execute_full_bot_deduplication(request)
            elif request.operation_type == 'document':
                result = await self._execute_document_deduplication(request)
            elif request.operation_type == 'chunk_list':
                result = await self._execute_chunk_list_deduplication(request)
            elif request.operation_type == 'reprocessing':
                result = await self._execute_reprocessing_deduplication(request)
            else:
                return {
                    'success': False,
                    'error': f"Unknown operation type: {request.operation_type}"
                }
            
            # Add operation metadata
            result['operation_metadata'] = {
                'operation_type': request.operation_type,
                'bot_id': str(request.bot_id),
                'user_id': str(request.user_id) if request.user_id else None,
                'timestamp': datetime.utcnow().isoformat(),
                'force_execution': request.force_execution
            }
            
            logger.info(
                f"Completed deduplication operation {request.operation_type} "
                f"for bot {request.bot_id}: success={result.get('success', False)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing deduplication operation: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation_type': request.operation_type
            }
    
    async def _validate_operation_request(
        self,
        request: DeduplicationOperationRequest
    ) -> Dict[str, Any]:
        """
        Validate deduplication operation request.
        
        Args:
            request: Operation request to validate
            
        Returns:
            Validation result
        """
        try:
            # Check if bot exists
            bot = self.db.query(Bot).filter(Bot.id == request.bot_id).first()
            if not bot:
                return {'valid': False, 'error': 'Bot not found'}
            
            # Check if deduplication is enabled for the bot
            policy = await self.manager._get_bot_policy(request.bot_id)
            if not policy.enabled and not request.force_execution:
                return {
                    'valid': False,
                    'error': 'Deduplication is disabled for this bot. Use force_execution to override.'
                }
            
            # Validate target IDs if provided
            if request.target_ids:
                if request.operation_type == 'document':
                    # Validate document IDs
                    existing_docs = self.db.query(Document).filter(
                        Document.id.in_(request.target_ids)
                    ).count()
                    if existing_docs != len(request.target_ids):
                        return {'valid': False, 'error': 'Some document IDs not found'}
                
                elif request.operation_type == 'chunk_list':
                    # Validate chunk IDs
                    existing_chunks = self.db.query(DocumentChunk).filter(
                        DocumentChunk.id.in_(request.target_ids)
                    ).count()
                    if existing_chunks != len(request.target_ids):
                        return {'valid': False, 'error': 'Some chunk IDs not found'}
            
            return {'valid': True}
            
        except Exception as e:
            return {'valid': False, 'error': f"Validation error: {str(e)}"}
    
    async def _execute_full_bot_deduplication(
        self,
        request: DeduplicationOperationRequest
    ) -> Dict[str, Any]:
        """
        Execute deduplication for all chunks in a bot.
        
        Args:
            request: Operation request
            
        Returns:
            Operation result
        """
        try:
            # Get policy and configuration
            policy = await self.manager._get_bot_policy(request.bot_id)
            
            # Apply config override if provided
            if request.config_override:
                config_dict = asdict(policy)
                config_dict.update(request.config_override)
                
                # Handle enum conversion
                if 'conflict_resolution_strategy' in config_dict:
                    strategy_value = config_dict['conflict_resolution_strategy']
                    if isinstance(strategy_value, str):
                        config_dict['conflict_resolution_strategy'] = ConflictResolutionStrategy(strategy_value)
                
                policy = DeduplicationPolicy(**config_dict)
            
            # Get all chunks for the bot
            all_chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.bot_id == request.bot_id
            ).all()
            
            if len(all_chunks) < 2:
                return {
                    'success': True,
                    'message': 'Insufficient chunks for deduplication',
                    'chunks_analyzed': len(all_chunks),
                    'operations_performed': 0
                }
            
            # Execute deduplication in batches
            chunk_ids = [chunk.id for chunk in all_chunks]
            batch_size = policy.batch_size
            
            total_merged = 0
            total_removed = 0
            total_preserved = 0
            total_conflicts = 0
            all_decisions = []
            
            for i in range(0, len(chunk_ids), batch_size):
                batch_chunk_ids = chunk_ids[i:i + batch_size]
                
                # Detect and resolve conflicts for this batch
                conflicts = await self.manager._detect_conflicts(
                    request.bot_id, batch_chunk_ids, policy
                )
                total_conflicts += len(conflicts)
                
                # Resolve conflicts
                for conflict in conflicts:
                    await self.manager._resolve_conflict(
                        conflict, policy, request.user_id
                    )
                
                # Perform deduplication on remaining chunks
                dedup_config = DeduplicationConfig(
                    high_similarity_threshold=policy.similarity_threshold,
                    conservative_preservation=(
                        policy.conflict_resolution_strategy == ConflictResolutionStrategy.CONSERVATIVE
                    )
                )
                
                batch_result = await self.deduplication_service.deduplicate_chunks(
                    bot_id=request.bot_id,
                    chunk_ids=batch_chunk_ids,
                    config=dedup_config
                )
                
                if batch_result.success:
                    total_merged += batch_result.merged_chunks
                    total_removed += batch_result.removed_chunks
                    total_preserved += batch_result.preserved_chunks
                    all_decisions.extend(batch_result.decisions)
            
            # Record in audit trail
            if all_decisions:
                await self.audit_service.record_batch_deduplication(
                    bot_id=request.bot_id,
                    decisions=all_decisions,
                    user_id=request.user_id,
                    batch_metadata={
                        'operation_type': 'full_bot_deduplication',
                        'total_chunks_analyzed': len(all_chunks),
                        'batch_count': (len(chunk_ids) + batch_size - 1) // batch_size
                    }
                )
            
            return {
                'success': True,
                'chunks_analyzed': len(all_chunks),
                'chunks_merged': total_merged,
                'chunks_removed': total_removed,
                'chunks_preserved': total_preserved,
                'conflicts_detected': total_conflicts,
                'decisions_made': len(all_decisions),
                'batches_processed': (len(chunk_ids) + batch_size - 1) // batch_size
            }
            
        except Exception as e:
            logger.error(f"Error in full bot deduplication: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_document_deduplication(
        self,
        request: DeduplicationOperationRequest
    ) -> Dict[str, Any]:
        """
        Execute deduplication for specific documents.
        
        Args:
            request: Operation request
            
        Returns:
            Operation result
        """
        try:
            if not request.target_ids:
                return {'success': False, 'error': 'Document IDs required'}
            
            results = []
            
            for document_id in request.target_ids:
                # Get chunks for this document
                doc_chunks = self.db.query(DocumentChunk).filter(
                    and_(
                        DocumentChunk.bot_id == request.bot_id,
                        DocumentChunk.document_id == document_id
                    )
                ).all()
                
                if len(doc_chunks) < 2:
                    results.append({
                        'document_id': str(document_id),
                        'success': True,
                        'message': 'Insufficient chunks for deduplication',
                        'chunks_analyzed': len(doc_chunks)
                    })
                    continue
                
                # Execute deduplication for this document
                chunk_ids = [chunk.id for chunk in doc_chunks]
                
                dedup_result = await self.deduplication_service.deduplicate_chunks(
                    bot_id=request.bot_id,
                    chunk_ids=chunk_ids
                )
                
                if dedup_result.success:
                    # Record in audit trail
                    await self.audit_service.record_batch_deduplication(
                        bot_id=request.bot_id,
                        decisions=dedup_result.decisions,
                        user_id=request.user_id,
                        batch_metadata={
                            'operation_type': 'document_deduplication',
                            'document_id': str(document_id)
                        }
                    )
                
                results.append({
                    'document_id': str(document_id),
                    'success': dedup_result.success,
                    'chunks_analyzed': len(doc_chunks),
                    'chunks_merged': dedup_result.merged_chunks,
                    'chunks_removed': dedup_result.removed_chunks,
                    'chunks_preserved': dedup_result.preserved_chunks,
                    'error': dedup_result.error
                })
            
            # Calculate totals
            total_success = sum(1 for r in results if r['success'])
            total_merged = sum(r.get('chunks_merged', 0) for r in results)
            total_removed = sum(r.get('chunks_removed', 0) for r in results)
            
            return {
                'success': total_success == len(request.target_ids),
                'documents_processed': len(request.target_ids),
                'documents_successful': total_success,
                'total_chunks_merged': total_merged,
                'total_chunks_removed': total_removed,
                'document_results': results
            }
            
        except Exception as e:
            logger.error(f"Error in document deduplication: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_chunk_list_deduplication(
        self,
        request: DeduplicationOperationRequest
    ) -> Dict[str, Any]:
        """
        Execute deduplication for specific chunks.
        
        Args:
            request: Operation request
            
        Returns:
            Operation result
        """
        try:
            if not request.target_ids:
                return {'success': False, 'error': 'Chunk IDs required'}
            
            # Validate chunks belong to the bot
            valid_chunks = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.bot_id == request.bot_id,
                    DocumentChunk.id.in_(request.target_ids)
                )
            ).all()
            
            if len(valid_chunks) != len(request.target_ids):
                return {
                    'success': False,
                    'error': 'Some chunks do not belong to the specified bot'
                }
            
            # Execute deduplication
            dedup_result = await self.deduplication_service.deduplicate_chunks(
                bot_id=request.bot_id,
                chunk_ids=request.target_ids
            )
            
            if dedup_result.success:
                # Record in audit trail
                await self.audit_service.record_batch_deduplication(
                    bot_id=request.bot_id,
                    decisions=dedup_result.decisions,
                    user_id=request.user_id,
                    batch_metadata={
                        'operation_type': 'chunk_list_deduplication',
                        'chunk_count': len(request.target_ids)
                    }
                )
            
            return {
                'success': dedup_result.success,
                'chunks_analyzed': len(request.target_ids),
                'chunks_merged': dedup_result.merged_chunks,
                'chunks_removed': dedup_result.removed_chunks,
                'chunks_preserved': dedup_result.preserved_chunks,
                'decisions_made': len(dedup_result.decisions),
                'error': dedup_result.error
            }
            
        except Exception as e:
            logger.error(f"Error in chunk list deduplication: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_reprocessing_deduplication(
        self,
        request: DeduplicationOperationRequest
    ) -> Dict[str, Any]:
        """
        Execute deduplication during document reprocessing.
        
        Args:
            request: Operation request
            
        Returns:
            Operation result
        """
        try:
            if not request.target_ids:
                return {'success': False, 'error': 'Document IDs required for reprocessing'}
            
            results = []
            
            for document_id in request.target_ids:
                report = await self.manager.process_document_reprocessing_deduplication(
                    bot_id=request.bot_id,
                    document_id=document_id,
                    user_id=request.user_id
                )
                
                results.append({
                    'document_id': str(document_id),
                    'success': report.status == 'completed',
                    'old_chunks_removed': report.chunks_removed,
                    'chunks_merged': report.chunks_merged,
                    'chunks_preserved': report.chunks_preserved,
                    'conflicts_detected': report.conflicts_detected,
                    'conflicts_resolved': report.conflicts_resolved,
                    'processing_time_seconds': report.processing_time_seconds,
                    'error': report.error_message
                })
            
            # Calculate totals
            total_success = sum(1 for r in results if r['success'])
            total_old_removed = sum(r.get('old_chunks_removed', 0) for r in results)
            total_merged = sum(r.get('chunks_merged', 0) for r in results)
            
            return {
                'success': total_success == len(request.target_ids),
                'documents_processed': len(request.target_ids),
                'documents_successful': total_success,
                'total_old_chunks_removed': total_old_removed,
                'total_chunks_merged': total_merged,
                'document_results': results
            }
            
        except Exception as e:
            logger.error(f"Error in reprocessing deduplication: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_deduplication_summary(
        self,
        bot_id: UUID
    ) -> DeduplicationSummary:
        """
        Get comprehensive deduplication summary for a bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Deduplication summary with status and recommendations
        """
        try:
            # Get comprehensive statistics
            stats = await self.manager.get_deduplication_statistics_with_conflicts(bot_id)
            
            # Get last deduplication timestamp
            audit_result = await self.audit_service.query_audit_trail(
                bot_id=bot_id,
                limit=1
            )
            
            last_deduplication = None
            if audit_result.entries:
                last_deduplication = audit_result.entries[0].timestamp
            
            # Calculate efficiency score
            total_chunks = stats.get('total_chunks', 0)
            potential_duplicates = stats.get('potential_duplicate_chunks', 0)
            
            if total_chunks > 0:
                efficiency_score = 1.0 - (potential_duplicates / total_chunks)
            else:
                efficiency_score = 1.0
            
            # Generate recommendations
            recommendations = self._generate_summary_recommendations(stats, efficiency_score)
            
            # Get policy status
            policy = await self.manager._get_bot_policy(bot_id)
            policy_status = {
                'enabled': policy.enabled,
                'auto_deduplicate_on_upload': policy.auto_deduplicate_on_upload,
                'conflict_resolution_strategy': policy.conflict_resolution_strategy.value,
                'similarity_threshold': policy.similarity_threshold
            }
            
            # Get performance metrics
            performance_metrics = {
                'active_operations': stats.get('performance_metrics', {}).get('active_operations', 0),
                'avg_processing_time': stats.get('performance_metrics', {}).get('avg_processing_time', 0),
                'recent_operations': stats.get('audit_statistics', {}).get('total_operations', 0)
            }
            
            return DeduplicationSummary(
                bot_id=bot_id,
                total_chunks=total_chunks,
                potential_duplicates=potential_duplicates,
                active_conflicts=stats.get('conflict_management', {}).get('active_conflicts', 0),
                last_deduplication=last_deduplication,
                efficiency_score=efficiency_score,
                recommendations=recommendations,
                policy_status=policy_status,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            logger.error(f"Error getting deduplication summary for bot {bot_id}: {e}")
            return DeduplicationSummary(
                bot_id=bot_id,
                total_chunks=0,
                potential_duplicates=0,
                active_conflicts=0,
                last_deduplication=None,
                efficiency_score=0.0,
                recommendations=[f"Error getting summary: {str(e)}"],
                policy_status={},
                performance_metrics={}
            )
    
    def _generate_summary_recommendations(
        self,
        stats: Dict[str, Any],
        efficiency_score: float
    ) -> List[str]:
        """
        Generate recommendations based on deduplication statistics.
        
        Args:
            stats: Deduplication statistics
            efficiency_score: Calculated efficiency score
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Efficiency-based recommendations
        if efficiency_score < 0.7:
            recommendations.append(
                "Low deduplication efficiency detected. Consider running full bot deduplication."
            )
        elif efficiency_score < 0.9:
            recommendations.append(
                "Moderate duplication detected. Periodic deduplication recommended."
            )
        
        # Conflict-based recommendations
        active_conflicts = stats.get('conflict_management', {}).get('active_conflicts', 0)
        if active_conflicts > 0:
            recommendations.append(
                f"{active_conflicts} active conflicts require resolution. "
                "Review conflicts in the management interface."
            )
        
        # Policy-based recommendations
        policy_config = stats.get('policy_configuration', {})
        if not policy_config.get('enabled', True):
            recommendations.append(
                "Deduplication is disabled. Enable it to improve storage efficiency."
            )
        
        if not policy_config.get('auto_deduplicate_on_upload', False):
            recommendations.append(
                "Consider enabling auto-deduplication on upload for better efficiency."
            )
        
        # Performance-based recommendations
        performance = stats.get('performance_metrics', {})
        if performance.get('avg_processing_time', 0) > 300:  # 5 minutes
            recommendations.append(
                "Long processing times detected. Consider reducing batch size or "
                "scheduling deduplication during off-peak hours."
            )
        
        # Volume-based recommendations
        total_chunks = stats.get('total_chunks', 0)
        if total_chunks > 10000:
            recommendations.append(
                "Large chunk collection detected. Consider implementing "
                "automated deduplication schedules."
            )
        
        return recommendations
    
    async def configure_bot_deduplication(
        self,
        bot_id: UUID,
        policy_config: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Configure deduplication policy for a bot.
        
        Args:
            bot_id: Bot identifier
            policy_config: Policy configuration dictionary
            user_id: Optional user making the configuration
            
        Returns:
            Configuration result
        """
        try:
            # Convert config dict to policy object
            # Handle enum conversion
            if 'conflict_resolution_strategy' in policy_config:
                strategy_value = policy_config['conflict_resolution_strategy']
                if isinstance(strategy_value, str):
                    policy_config['conflict_resolution_strategy'] = ConflictResolutionStrategy(strategy_value)
            
            policy = DeduplicationPolicy(**policy_config)
            
            # Configure through manager
            result = await self.manager.configure_deduplication_policy(
                bot_id=bot_id,
                policy=policy,
                user_id=user_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error configuring bot deduplication: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_conflict_resolution_interface(
        self,
        bot_id: UUID
    ) -> Dict[str, Any]:
        """
        Get conflict resolution interface data.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Conflict resolution interface data
        """
        try:
            # Get active conflicts
            active_conflicts = await self.manager.get_active_conflicts(bot_id)
            
            # Get policy information
            policy = await self.manager._get_bot_policy(bot_id)
            
            # Get resolution statistics
            audit_stats = await self.audit_service.get_deduplication_statistics(bot_id)
            
            return {
                'active_conflicts': active_conflicts,
                'policy_configuration': {
                    'conflict_resolution_strategy': policy.conflict_resolution_strategy.value,
                    'similarity_threshold': policy.similarity_threshold,
                    'enable_cross_document_deduplication': policy.enable_cross_document_deduplication
                },
                'resolution_statistics': {
                    'total_operations': audit_stats.get('total_operations', 0),
                    'operations_by_type': audit_stats.get('operations_by_type', {}),
                    'recent_operations': audit_stats.get('recent_operations', [])
                },
                'available_actions': [
                    'merge',
                    'preserve',
                    'remove_first',
                    'remove_second'
                ],
                'resolution_strategies': [strategy.value for strategy in ConflictResolutionStrategy]
            }
            
        except Exception as e:
            logger.error(f"Error getting conflict resolution interface: {e}")
            return {'error': str(e)}
    
    async def resolve_conflict_manually(
        self,
        case_id: str,
        action: str,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Manually resolve a deduplication conflict.
        
        Args:
            case_id: Conflict case identifier
            action: Resolution action
            user_id: User resolving the conflict
            
        Returns:
            Resolution result
        """
        try:
            result = await self.manager.manual_conflict_resolution(
                case_id=case_id,
                action=action,
                user_id=user_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error resolving conflict manually: {e}")
            return {'success': False, 'error': str(e)}