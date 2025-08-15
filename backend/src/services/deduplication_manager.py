"""
Deduplication management service with conflict resolution and configuration.
Implements requirements 10.3, 10.5 for task 11.2.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from uuid import UUID
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from sqlalchemy.dialects.postgresql import insert

from ..core.database import get_db
from ..models.document import Document, DocumentChunk
from ..models.bot import Bot
from ..services.chunk_deduplication_service import (
    ChunkDeduplicationService, 
    DeduplicationConfig,
    DeduplicationResult
)
from ..services.deduplication_audit_service import DeduplicationAuditService
from ..services.vector_store import VectorService

logger = logging.getLogger(__name__)


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving deduplication conflicts."""
    CONSERVATIVE = "conservative"  # Preserve when uncertain
    AGGRESSIVE = "aggressive"     # Merge when possible
    MANUAL = "manual"            # Require manual review
    OLDEST_WINS = "oldest_wins"  # Prefer older content
    NEWEST_WINS = "newest_wins"  # Prefer newer content
    LONGEST_WINS = "longest_wins"  # Prefer longer content


@dataclass
class DeduplicationPolicy:
    """Policy configuration for deduplication operations."""
    enabled: bool = True
    auto_deduplicate_on_upload: bool = False
    conflict_resolution_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.CONSERVATIVE
    similarity_threshold: float = 0.95
    batch_size: int = 100
    max_processing_time_minutes: int = 30
    preserve_source_attribution: bool = True
    require_metadata_compatibility: bool = True
    enable_cross_document_deduplication: bool = True
    retention_days: int = 365


@dataclass
class ConflictResolutionCase:
    """Represents a deduplication conflict requiring resolution."""
    case_id: str
    bot_id: UUID
    chunk_ids: List[UUID]
    similarity_scores: List[float]
    conflict_type: str  # 'ambiguous_similarity', 'metadata_conflict', 'cross_document'
    suggested_action: str
    confidence_score: float
    created_at: datetime
    resolved: bool = False
    resolution_action: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None


@dataclass
class DeduplicationReport:
    """Comprehensive report of deduplication operations."""
    bot_id: UUID
    operation_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str  # 'running', 'completed', 'failed', 'cancelled'
    total_chunks_analyzed: int
    duplicate_groups_found: int
    chunks_merged: int
    chunks_removed: int
    chunks_preserved: int
    conflicts_detected: int
    conflicts_resolved: int
    processing_time_seconds: float
    error_message: Optional[str] = None
    detailed_results: Optional[Dict[str, Any]] = None


class DeduplicationManager:
    """
    Comprehensive deduplication management service with conflict resolution,
    old chunk removal, and configurable policies.
    """
    
    def __init__(
        self, 
        db: Session, 
        vector_service: VectorService = None,
        deduplication_service: ChunkDeduplicationService = None,
        audit_service: DeduplicationAuditService = None
    ):
        """
        Initialize deduplication manager.
        
        Args:
            db: Database session
            vector_service: Vector service instance
            deduplication_service: Deduplication service instance
            audit_service: Audit service instance
        """
        self.db = db
        self.vector_service = vector_service or VectorService()
        self.deduplication_service = deduplication_service or ChunkDeduplicationService(db, vector_service)
        self.audit_service = audit_service or DeduplicationAuditService(db)
        
        # Store active conflicts and operations
        self.active_conflicts: Dict[str, ConflictResolutionCase] = {}
        self.active_operations: Dict[str, DeduplicationReport] = {}
    
    async def configure_deduplication_policy(
        self,
        bot_id: UUID,
        policy: DeduplicationPolicy,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Configure deduplication policy for a bot.
        
        Args:
            bot_id: Bot identifier
            policy: Deduplication policy configuration
            user_id: Optional user making the configuration
            
        Returns:
            Configuration result
        """
        try:
            # Validate policy configuration
            validation_result = self._validate_policy(policy)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'suggestions': validation_result.get('suggestions', [])
                }
            
            # Store policy in bot metadata or separate configuration table
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return {'success': False, 'error': 'Bot not found'}
            
            # Update bot configuration with deduplication policy
            if not hasattr(bot, 'deduplication_config'):
                bot.deduplication_config = {}
            
            bot.deduplication_config = asdict(policy)
            self.db.commit()
            
            # Record configuration change in audit trail
            await self.audit_service.record_deduplication_decision(
                bot_id=bot_id,
                decision=self._create_config_decision(policy),
                user_id=user_id,
                additional_metadata={'policy_change': True}
            )
            
            logger.info(f"Updated deduplication policy for bot {bot_id}")
            
            return {
                'success': True,
                'policy': asdict(policy),
                'validation_warnings': validation_result.get('warnings', [])
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error configuring deduplication policy for bot {bot_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_policy(self, policy: DeduplicationPolicy) -> Dict[str, Any]:
        """
        Validate deduplication policy configuration.
        
        Args:
            policy: Policy to validate
            
        Returns:
            Validation result with errors and suggestions
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Validate similarity threshold
        if not 0.5 <= policy.similarity_threshold <= 1.0:
            errors.append("Similarity threshold must be between 0.5 and 1.0")
        elif policy.similarity_threshold < 0.8:
            warnings.append("Low similarity threshold may result in false positives")
        
        # Validate batch size
        if policy.batch_size < 10 or policy.batch_size > 1000:
            errors.append("Batch size must be between 10 and 1000")
        
        # Validate processing time
        if policy.max_processing_time_minutes < 5 or policy.max_processing_time_minutes > 120:
            errors.append("Max processing time must be between 5 and 120 minutes")
        
        # Validate retention days
        if policy.retention_days < 30:
            warnings.append("Short retention period may affect audit compliance")
        
        # Strategy-specific validations
        if policy.conflict_resolution_strategy == ConflictResolutionStrategy.AGGRESSIVE:
            if policy.similarity_threshold > 0.9:
                suggestions.append("Consider lowering similarity threshold for aggressive strategy")
        
        return {
            'valid': len(errors) == 0,
            'error': '; '.join(errors) if errors else None,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def _create_config_decision(self, policy: DeduplicationPolicy):
        """Create a mock decision for configuration changes."""
        from ..services.chunk_deduplication_service import DeduplicationDecision
        
        return DeduplicationDecision(
            decision_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            action='configure',
            primary_chunk_id=UUID('00000000-0000-0000-0000-000000000000'),
            duplicate_chunk_ids=[],
            similarity_score=0.0,
            reason=f"Policy configuration: {policy.conflict_resolution_strategy.value}",
            preserved_metadata=asdict(policy),
            source_attribution=[]
        )
    
    async def process_document_reprocessing_deduplication(
        self,
        bot_id: UUID,
        document_id: UUID,
        user_id: Optional[UUID] = None
    ) -> DeduplicationReport:
        """
        Handle deduplication during document reprocessing with old chunk removal.
        
        Args:
            bot_id: Bot identifier
            document_id: Document identifier
            user_id: Optional user initiating the operation
            
        Returns:
            Deduplication report
        """
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            # Get deduplication policy
            policy = await self._get_bot_policy(bot_id)
            
            # Create operation report
            report = DeduplicationReport(
                bot_id=bot_id,
                operation_id=operation_id,
                start_time=start_time,
                end_time=None,
                status='running',
                total_chunks_analyzed=0,
                duplicate_groups_found=0,
                chunks_merged=0,
                chunks_removed=0,
                chunks_preserved=0,
                conflicts_detected=0,
                conflicts_resolved=0,
                processing_time_seconds=0.0
            )
            
            self.active_operations[operation_id] = report
            
            # Step 1: Remove old chunks for the document
            old_chunks_removed = await self._remove_old_document_chunks(
                bot_id, document_id, policy
            )
            report.chunks_removed += old_chunks_removed
            
            # Step 2: Get all chunks for the document (new ones)
            new_chunks = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.bot_id == bot_id,
                    DocumentChunk.document_id == document_id
                )
            ).all()
            
            report.total_chunks_analyzed = len(new_chunks)
            
            if len(new_chunks) < 2:
                report.status = 'completed'
                report.end_time = datetime.utcnow()
                report.processing_time_seconds = (report.end_time - start_time).total_seconds()
                return report
            
            # Step 3: Detect and resolve conflicts
            chunk_ids = [chunk.id for chunk in new_chunks]
            conflicts = await self._detect_conflicts(bot_id, chunk_ids, policy)
            report.conflicts_detected = len(conflicts)
            
            # Step 4: Resolve conflicts based on policy
            resolved_conflicts = 0
            for conflict in conflicts:
                resolution_result = await self._resolve_conflict(conflict, policy, user_id)
                if resolution_result['resolved']:
                    resolved_conflicts += 1
            
            report.conflicts_resolved = resolved_conflicts
            
            # Step 5: Perform deduplication on remaining chunks
            dedup_config = DeduplicationConfig(
                high_similarity_threshold=policy.similarity_threshold,
                conservative_preservation=(
                    policy.conflict_resolution_strategy == ConflictResolutionStrategy.CONSERVATIVE
                )
            )
            
            dedup_result = await self.deduplication_service.deduplicate_chunks(
                bot_id=bot_id,
                chunk_ids=chunk_ids,
                config=dedup_config
            )
            
            if dedup_result.success:
                report.duplicate_groups_found = len(dedup_result.decisions)
                report.chunks_merged = dedup_result.merged_chunks
                report.chunks_preserved = dedup_result.preserved_chunks
                
                # Record in audit trail
                await self.audit_service.record_batch_deduplication(
                    bot_id=bot_id,
                    decisions=dedup_result.decisions,
                    user_id=user_id,
                    batch_metadata={
                        'operation_id': operation_id,
                        'document_id': str(document_id),
                        'operation_type': 'document_reprocessing'
                    }
                )
            
            # Complete operation
            report.status = 'completed'
            report.end_time = datetime.utcnow()
            report.processing_time_seconds = (report.end_time - start_time).total_seconds()
            
            logger.info(
                f"Completed document reprocessing deduplication for document {document_id}: "
                f"removed {old_chunks_removed} old chunks, "
                f"merged {report.chunks_merged} duplicates"
            )
            
            return report
            
        except Exception as e:
            report.status = 'failed'
            report.error_message = str(e)
            report.end_time = datetime.utcnow()
            report.processing_time_seconds = (report.end_time - start_time).total_seconds()
            
            logger.error(f"Error in document reprocessing deduplication: {e}")
            return report
        
        finally:
            # Clean up active operation
            if operation_id in self.active_operations:
                del self.active_operations[operation_id]
    
    async def _remove_old_document_chunks(
        self,
        bot_id: UUID,
        document_id: UUID,
        policy: DeduplicationPolicy
    ) -> int:
        """
        Remove old chunks for a document during reprocessing.
        
        Args:
            bot_id: Bot identifier
            document_id: Document identifier
            policy: Deduplication policy
            
        Returns:
            Number of chunks removed
        """
        try:
            # Get existing chunks for the document
            existing_chunks = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.bot_id == bot_id,
                    DocumentChunk.document_id == document_id
                )
            ).all()
            
            if not existing_chunks:
                return 0
            
            # Remove from vector store first
            embedding_ids = [chunk.embedding_id for chunk in existing_chunks if chunk.embedding_id]
            if embedding_ids:
                await self.vector_service.delete_document_chunks(str(bot_id), embedding_ids)
            
            # Remove from database
            chunk_count = len(existing_chunks)
            self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.bot_id == bot_id,
                    DocumentChunk.document_id == document_id
                )
            ).delete(synchronize_session=False)
            
            self.db.commit()
            
            logger.info(f"Removed {chunk_count} old chunks for document {document_id}")
            return chunk_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing old chunks for document {document_id}: {e}")
            return 0
    
    async def _detect_conflicts(
        self,
        bot_id: UUID,
        chunk_ids: List[UUID],
        policy: DeduplicationPolicy
    ) -> List[ConflictResolutionCase]:
        """
        Detect deduplication conflicts that require special handling.
        
        Args:
            bot_id: Bot identifier
            chunk_ids: List of chunk IDs to analyze
            policy: Deduplication policy
            
        Returns:
            List of detected conflicts
        """
        try:
            conflicts = []
            
            # Detect similarities
            similarities = await self.deduplication_service.detect_chunk_similarities(
                bot_id=bot_id,
                chunk_ids=chunk_ids,
                similarity_threshold=0.7  # Lower threshold to catch ambiguous cases
            )
            
            # Group similarities and identify conflicts
            for similarity in similarities:
                conflict_type = None
                confidence_score = similarity.similarity_score
                
                # Check for ambiguous similarity (medium confidence)
                if 0.7 <= similarity.similarity_score < policy.similarity_threshold:
                    conflict_type = 'ambiguous_similarity'
                    confidence_score = 0.5
                
                # Check for metadata conflicts
                elif not similarity.metadata_compatibility:
                    conflict_type = 'metadata_conflict'
                    confidence_score = 0.3
                
                # Check for cross-document conflicts if enabled
                elif policy.enable_cross_document_deduplication:
                    chunk1 = self.db.query(DocumentChunk).filter(
                        DocumentChunk.id == similarity.chunk1_id
                    ).first()
                    chunk2 = self.db.query(DocumentChunk).filter(
                        DocumentChunk.id == similarity.chunk2_id
                    ).first()
                    
                    if chunk1 and chunk2 and chunk1.document_id != chunk2.document_id:
                        conflict_type = 'cross_document'
                        confidence_score = 0.4
                
                if conflict_type:
                    case_id = str(uuid.uuid4())
                    conflict = ConflictResolutionCase(
                        case_id=case_id,
                        bot_id=bot_id,
                        chunk_ids=[similarity.chunk1_id, similarity.chunk2_id],
                        similarity_scores=[similarity.similarity_score],
                        conflict_type=conflict_type,
                        suggested_action=self._suggest_conflict_action(
                            conflict_type, similarity, policy
                        ),
                        confidence_score=confidence_score,
                        created_at=datetime.utcnow()
                    )
                    
                    conflicts.append(conflict)
                    self.active_conflicts[case_id] = conflict
            
            logger.debug(f"Detected {len(conflicts)} conflicts for bot {bot_id}")
            return conflicts
            
        except Exception as e:
            logger.error(f"Error detecting conflicts for bot {bot_id}: {e}")
            return []
    
    def _suggest_conflict_action(
        self,
        conflict_type: str,
        similarity,
        policy: DeduplicationPolicy
    ) -> str:
        """
        Suggest action for resolving a conflict based on policy.
        
        Args:
            conflict_type: Type of conflict
            similarity: Similarity information
            policy: Deduplication policy
            
        Returns:
            Suggested action
        """
        strategy = policy.conflict_resolution_strategy
        
        if conflict_type == 'ambiguous_similarity':
            if strategy == ConflictResolutionStrategy.CONSERVATIVE:
                return 'preserve_both'
            elif strategy == ConflictResolutionStrategy.AGGRESSIVE:
                return 'merge_if_compatible'
            else:
                return 'manual_review'
        
        elif conflict_type == 'metadata_conflict':
            if strategy == ConflictResolutionStrategy.CONSERVATIVE:
                return 'preserve_both'
            elif strategy == ConflictResolutionStrategy.OLDEST_WINS:
                return 'keep_oldest'
            elif strategy == ConflictResolutionStrategy.NEWEST_WINS:
                return 'keep_newest'
            else:
                return 'manual_review'
        
        elif conflict_type == 'cross_document':
            if policy.enable_cross_document_deduplication:
                return 'merge_with_attribution'
            else:
                return 'preserve_both'
        
        return 'manual_review'
    
    async def _resolve_conflict(
        self,
        conflict: ConflictResolutionCase,
        policy: DeduplicationPolicy,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Resolve a deduplication conflict based on suggested action.
        
        Args:
            conflict: Conflict to resolve
            policy: Deduplication policy
            user_id: Optional user resolving the conflict
            
        Returns:
            Resolution result
        """
        try:
            action = conflict.suggested_action
            
            if action == 'preserve_both':
                # Mark chunks to be preserved
                conflict.resolved = True
                conflict.resolution_action = 'preserved'
                conflict.resolved_at = datetime.utcnow()
                conflict.resolved_by = user_id
                
                return {'resolved': True, 'action': 'preserved', 'chunks_affected': 0}
            
            elif action == 'merge_if_compatible':
                # Attempt merge if metadata is compatible
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id.in_(conflict.chunk_ids)
                ).all()
                
                if len(chunks) == 2:
                    # Check compatibility and merge
                    primary_chunk = chunks[0] if chunks[0].created_at <= chunks[1].created_at else chunks[1]
                    duplicate_chunk = chunks[1] if primary_chunk == chunks[0] else chunks[0]
                    
                    # Perform merge
                    decision = await self.deduplication_service._merge_chunks(
                        primary_chunk, [duplicate_chunk]
                    )
                    
                    conflict.resolved = True
                    conflict.resolution_action = 'merged'
                    conflict.resolved_at = datetime.utcnow()
                    conflict.resolved_by = user_id
                    
                    return {'resolved': True, 'action': 'merged', 'chunks_affected': 1}
            
            elif action in ['keep_oldest', 'keep_newest']:
                # Keep one chunk based on age
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id.in_(conflict.chunk_ids)
                ).all()
                
                if len(chunks) == 2:
                    if action == 'keep_oldest':
                        keep_chunk = chunks[0] if chunks[0].created_at <= chunks[1].created_at else chunks[1]
                        remove_chunk = chunks[1] if keep_chunk == chunks[0] else chunks[0]
                    else:  # keep_newest
                        keep_chunk = chunks[0] if chunks[0].created_at >= chunks[1].created_at else chunks[1]
                        remove_chunk = chunks[1] if keep_chunk == chunks[0] else chunks[0]
                    
                    # Remove the non-selected chunk
                    if remove_chunk.embedding_id:
                        await self.vector_service.delete_document_chunks(
                            str(conflict.bot_id), [remove_chunk.embedding_id]
                        )
                    
                    self.db.delete(remove_chunk)
                    self.db.commit()
                    
                    conflict.resolved = True
                    conflict.resolution_action = action
                    conflict.resolved_at = datetime.utcnow()
                    conflict.resolved_by = user_id
                    
                    return {'resolved': True, 'action': action, 'chunks_affected': 1}
            
            elif action == 'manual_review':
                # Leave for manual resolution
                return {'resolved': False, 'action': 'requires_manual_review', 'chunks_affected': 0}
            
            return {'resolved': False, 'action': 'unknown', 'chunks_affected': 0}
            
        except Exception as e:
            logger.error(f"Error resolving conflict {conflict.case_id}: {e}")
            return {'resolved': False, 'action': 'error', 'error': str(e), 'chunks_affected': 0}
    
    async def _get_bot_policy(self, bot_id: UUID) -> DeduplicationPolicy:
        """
        Get deduplication policy for a bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Deduplication policy (default if not configured)
        """
        try:
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            
            if bot and hasattr(bot, 'deduplication_config') and bot.deduplication_config:
                # Convert dict back to DeduplicationPolicy
                config_dict = bot.deduplication_config
                
                # Handle enum conversion
                if 'conflict_resolution_strategy' in config_dict:
                    strategy_value = config_dict['conflict_resolution_strategy']
                    if isinstance(strategy_value, str):
                        config_dict['conflict_resolution_strategy'] = ConflictResolutionStrategy(strategy_value)
                
                return DeduplicationPolicy(**config_dict)
            
            # Return default policy
            return DeduplicationPolicy()
            
        except Exception as e:
            logger.warning(f"Error getting policy for bot {bot_id}, using default: {e}")
            return DeduplicationPolicy()
    
    async def get_deduplication_statistics_with_conflicts(
        self,
        bot_id: UUID
    ) -> Dict[str, Any]:
        """
        Get comprehensive deduplication statistics including conflict information.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Comprehensive statistics
        """
        try:
            # Get basic deduplication statistics
            basic_stats = await self.deduplication_service.get_deduplication_statistics(bot_id)
            
            # Get audit statistics
            audit_stats = await self.audit_service.get_deduplication_statistics(bot_id)
            
            # Get active conflicts
            active_conflicts = [
                conflict for conflict in self.active_conflicts.values()
                if conflict.bot_id == bot_id and not conflict.resolved
            ]
            
            # Get resolved conflicts from recent operations
            resolved_conflicts_count = len([
                conflict for conflict in self.active_conflicts.values()
                if conflict.bot_id == bot_id and conflict.resolved
            ])
            
            # Get policy information
            policy = await self._get_bot_policy(bot_id)
            
            comprehensive_stats = {
                **basic_stats,
                'audit_statistics': audit_stats,
                'conflict_management': {
                    'active_conflicts': len(active_conflicts),
                    'resolved_conflicts': resolved_conflicts_count,
                    'conflict_types': {},
                    'resolution_strategies': {
                        'current_strategy': policy.conflict_resolution_strategy.value,
                        'auto_resolution_enabled': policy.conflict_resolution_strategy != ConflictResolutionStrategy.MANUAL
                    }
                },
                'policy_configuration': {
                    'enabled': policy.enabled,
                    'auto_deduplicate_on_upload': policy.auto_deduplicate_on_upload,
                    'similarity_threshold': policy.similarity_threshold,
                    'cross_document_deduplication': policy.enable_cross_document_deduplication
                },
                'performance_metrics': {
                    'active_operations': len(self.active_operations),
                    'avg_processing_time': self._calculate_avg_processing_time(bot_id)
                }
            }
            
            # Count conflict types
            for conflict in active_conflicts:
                conflict_type = conflict.conflict_type
                comprehensive_stats['conflict_management']['conflict_types'][conflict_type] = \
                    comprehensive_stats['conflict_management']['conflict_types'].get(conflict_type, 0) + 1
            
            return comprehensive_stats
            
        except Exception as e:
            logger.error(f"Error getting comprehensive statistics for bot {bot_id}: {e}")
            return {'error': str(e)}
    
    def _calculate_avg_processing_time(self, bot_id: UUID) -> float:
        """Calculate average processing time for recent operations."""
        try:
            recent_operations = [
                op for op in self.active_operations.values()
                if op.bot_id == bot_id and op.status == 'completed'
            ]
            
            if not recent_operations:
                return 0.0
            
            total_time = sum(op.processing_time_seconds for op in recent_operations)
            return total_time / len(recent_operations)
            
        except Exception:
            return 0.0
    
    async def manual_conflict_resolution(
        self,
        case_id: str,
        action: str,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Manually resolve a deduplication conflict.
        
        Args:
            case_id: Conflict case identifier
            action: Resolution action ('merge', 'preserve', 'remove_first', 'remove_second')
            user_id: User resolving the conflict
            
        Returns:
            Resolution result
        """
        try:
            if case_id not in self.active_conflicts:
                return {'success': False, 'error': 'Conflict case not found'}
            
            conflict = self.active_conflicts[case_id]
            
            if conflict.resolved:
                return {'success': False, 'error': 'Conflict already resolved'}
            
            # Apply manual resolution
            if action == 'merge':
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id.in_(conflict.chunk_ids)
                ).all()
                
                if len(chunks) >= 2:
                    primary_chunk = chunks[0]
                    duplicate_chunks = chunks[1:]
                    
                    decision = await self.deduplication_service._merge_chunks(
                        primary_chunk, duplicate_chunks
                    )
                    
                    # Record in audit trail
                    await self.audit_service.record_deduplication_decision(
                        bot_id=conflict.bot_id,
                        decision=decision,
                        user_id=user_id,
                        additional_metadata={
                            'manual_resolution': True,
                            'case_id': case_id
                        }
                    )
            
            elif action == 'preserve':
                # Mark as preserved
                pass
            
            elif action in ['remove_first', 'remove_second']:
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id.in_(conflict.chunk_ids)
                ).all()
                
                if len(chunks) >= 2:
                    remove_chunk = chunks[0] if action == 'remove_first' else chunks[1]
                    
                    # Remove from vector store
                    if remove_chunk.embedding_id:
                        await self.vector_service.delete_document_chunks(
                            str(conflict.bot_id), [remove_chunk.embedding_id]
                        )
                    
                    # Remove from database
                    self.db.delete(remove_chunk)
                    self.db.commit()
            
            # Mark conflict as resolved
            conflict.resolved = True
            conflict.resolution_action = action
            conflict.resolved_at = datetime.utcnow()
            conflict.resolved_by = user_id
            
            logger.info(f"Manually resolved conflict {case_id} with action {action}")
            
            return {
                'success': True,
                'case_id': case_id,
                'action': action,
                'resolved_at': conflict.resolved_at.isoformat()
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error manually resolving conflict {case_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_active_conflicts(self, bot_id: UUID) -> List[Dict[str, Any]]:
        """
        Get active conflicts for a bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            List of active conflicts
        """
        try:
            active_conflicts = [
                conflict for conflict in self.active_conflicts.values()
                if conflict.bot_id == bot_id and not conflict.resolved
            ]
            
            # Convert to serializable format
            conflicts_data = []
            for conflict in active_conflicts:
                # Get chunk information
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id.in_(conflict.chunk_ids)
                ).all()
                
                chunk_info = []
                for chunk in chunks:
                    chunk_info.append({
                        'id': str(chunk.id),
                        'content_preview': chunk.content[:200] + '...' if len(chunk.content) > 200 else chunk.content,
                        'document_id': str(chunk.document_id),
                        'created_at': chunk.created_at.isoformat(),
                        'metadata': chunk.chunk_metadata or {}
                    })
                
                conflicts_data.append({
                    'case_id': conflict.case_id,
                    'conflict_type': conflict.conflict_type,
                    'similarity_scores': conflict.similarity_scores,
                    'suggested_action': conflict.suggested_action,
                    'confidence_score': conflict.confidence_score,
                    'created_at': conflict.created_at.isoformat(),
                    'chunks': chunk_info
                })
            
            return conflicts_data
            
        except Exception as e:
            logger.error(f"Error getting active conflicts for bot {bot_id}: {e}")
            return []