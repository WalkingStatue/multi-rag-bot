"""
Deduplication audit trail service for tracking deduplication decisions.
Implements requirement 10.4 for task 11.1.
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from sqlalchemy.dialects.postgresql import insert

from ..core.database import get_db
from ..models.activity import ActivityLog
from ..services.chunk_deduplication_service import DeduplicationDecision

logger = logging.getLogger(__name__)


@dataclass
class AuditTrailEntry:
    """Audit trail entry for deduplication operations."""
    id: str
    bot_id: UUID
    operation_type: str  # 'deduplication', 'merge', 'preserve'
    timestamp: datetime
    decision_id: str
    affected_chunks: List[UUID]
    similarity_score: float
    action_taken: str
    reason: str
    metadata: Dict[str, Any]
    user_id: Optional[UUID] = None


@dataclass
class AuditQueryResult:
    """Result of audit trail query."""
    entries: List[AuditTrailEntry]
    total_count: int
    has_more: bool


class DeduplicationAuditService:
    """
    Service for tracking and querying deduplication audit trails.
    Maintains comprehensive records of all deduplication decisions.
    """
    
    def __init__(self, db: Session):
        """
        Initialize deduplication audit service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def record_deduplication_decision(
        self,
        bot_id: UUID,
        decision: DeduplicationDecision,
        user_id: Optional[UUID] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a deduplication decision in the audit trail.
        
        Args:
            bot_id: Bot identifier
            decision: Deduplication decision to record
            user_id: Optional user who initiated the operation
            additional_metadata: Optional additional metadata
            
        Returns:
            Audit entry ID
        """
        try:
            # Prepare audit metadata
            audit_metadata = {
                'decision_details': {
                    'primary_chunk_id': str(decision.primary_chunk_id),
                    'duplicate_chunk_ids': [str(cid) for cid in decision.duplicate_chunk_ids],
                    'similarity_score': decision.similarity_score,
                    'preserved_metadata': decision.preserved_metadata,
                    'source_attribution': decision.source_attribution
                },
                'operation_context': {
                    'timestamp': decision.timestamp.isoformat(),
                    'decision_id': decision.decision_id,
                    'action': decision.action,
                    'reason': decision.reason
                }
            }
            
            # Add additional metadata if provided
            if additional_metadata:
                audit_metadata['additional_context'] = additional_metadata
            
            # Create activity log entry
            activity_log = ActivityLog(
                bot_id=bot_id,
                user_id=user_id,
                action=f"deduplication_{decision.action}",
                details={
                    'operation_type': 'chunk_deduplication',
                    'decision_id': decision.decision_id,
                    'affected_chunks': len(decision.duplicate_chunk_ids) + 1,
                    'similarity_score': decision.similarity_score,
                    'action_taken': decision.action,
                    'reason': decision.reason,
                    'audit_metadata': audit_metadata
                }
            )
            
            self.db.add(activity_log)
            self.db.flush()
            
            logger.info(
                f"Recorded deduplication decision {decision.decision_id} "
                f"for bot {bot_id} in audit trail"
            )
            
            return str(activity_log.id)
            
        except Exception as e:
            logger.error(f"Error recording deduplication decision: {e}")
            raise
    
    async def record_batch_deduplication(
        self,
        bot_id: UUID,
        decisions: List[DeduplicationDecision],
        user_id: Optional[UUID] = None,
        batch_metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Record multiple deduplication decisions as a batch operation.
        
        Args:
            bot_id: Bot identifier
            decisions: List of deduplication decisions
            user_id: Optional user who initiated the operation
            batch_metadata: Optional batch operation metadata
            
        Returns:
            List of audit entry IDs
        """
        try:
            audit_ids = []
            
            # Record batch operation summary
            batch_summary = {
                'total_decisions': len(decisions),
                'actions_summary': {},
                'similarity_stats': {
                    'min_score': min(d.similarity_score for d in decisions) if decisions else 0,
                    'max_score': max(d.similarity_score for d in decisions) if decisions else 0,
                    'avg_score': sum(d.similarity_score for d in decisions) / len(decisions) if decisions else 0
                },
                'batch_timestamp': datetime.utcnow().isoformat()
            }
            
            # Count actions
            for decision in decisions:
                action = decision.action
                batch_summary['actions_summary'][action] = batch_summary['actions_summary'].get(action, 0) + 1
            
            # Add batch metadata if provided
            if batch_metadata:
                batch_summary['batch_context'] = batch_metadata
            
            # Record batch summary
            batch_log = ActivityLog(
                bot_id=bot_id,
                user_id=user_id,
                action="deduplication_batch",
                details={
                    'operation_type': 'batch_deduplication',
                    'batch_summary': batch_summary
                }
            )
            
            self.db.add(batch_log)
            self.db.flush()
            audit_ids.append(str(batch_log.id))
            
            # Record individual decisions
            for decision in decisions:
                decision_metadata = {
                    'batch_id': str(batch_log.id),
                    'batch_size': len(decisions)
                }
                
                audit_id = await self.record_deduplication_decision(
                    bot_id=bot_id,
                    decision=decision,
                    user_id=user_id,
                    additional_metadata=decision_metadata
                )
                audit_ids.append(audit_id)
            
            logger.info(
                f"Recorded batch deduplication with {len(decisions)} decisions "
                f"for bot {bot_id}"
            )
            
            return audit_ids
            
        except Exception as e:
            logger.error(f"Error recording batch deduplication: {e}")
            raise
    
    async def query_audit_trail(
        self,
        bot_id: UUID,
        operation_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> AuditQueryResult:
        """
        Query deduplication audit trail with filtering options.
        
        Args:
            bot_id: Bot identifier
            operation_type: Optional operation type filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            AuditQueryResult with matching entries
        """
        try:
            # Build base query
            query = self.db.query(ActivityLog).filter(
                and_(
                    ActivityLog.bot_id == bot_id,
                    ActivityLog.action.like('deduplication_%')
                )
            )
            
            # Apply filters
            if operation_type:
                query = query.filter(ActivityLog.action == f"deduplication_{operation_type}")
            
            if start_date:
                query = query.filter(ActivityLog.created_at >= start_date)
            
            if end_date:
                query = query.filter(ActivityLog.created_at <= end_date)
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination and ordering
            entries_query = query.order_by(desc(ActivityLog.created_at)).offset(offset).limit(limit)
            activity_logs = entries_query.all()
            
            # Convert to audit trail entries
            entries = []
            for log in activity_logs:
                details = log.details or {}
                audit_metadata = details.get('audit_metadata', {})
                decision_details = audit_metadata.get('decision_details', {})
                
                entry = AuditTrailEntry(
                    id=str(log.id),
                    bot_id=log.bot_id,
                    operation_type=details.get('operation_type', 'unknown'),
                    timestamp=log.created_at,
                    decision_id=details.get('decision_id', ''),
                    affected_chunks=[
                        UUID(cid) for cid in decision_details.get('duplicate_chunk_ids', [])
                    ] + ([UUID(decision_details['primary_chunk_id'])] 
                         if decision_details.get('primary_chunk_id') else []),
                    similarity_score=details.get('similarity_score', 0.0),
                    action_taken=details.get('action_taken', ''),
                    reason=details.get('reason', ''),
                    metadata=audit_metadata,
                    user_id=log.user_id
                )
                entries.append(entry)
            
            result = AuditQueryResult(
                entries=entries,
                total_count=total_count,
                has_more=(offset + len(entries)) < total_count
            )
            
            logger.debug(
                f"Retrieved {len(entries)} audit trail entries for bot {bot_id}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error querying audit trail for bot {bot_id}: {e}")
            return AuditQueryResult(entries=[], total_count=0, has_more=False)
    
    async def get_chunk_deduplication_history(
        self,
        chunk_id: UUID,
        bot_id: UUID
    ) -> List[AuditTrailEntry]:
        """
        Get deduplication history for a specific chunk.
        
        Args:
            chunk_id: Chunk identifier
            bot_id: Bot identifier
            
        Returns:
            List of audit trail entries involving the chunk
        """
        try:
            # Query activity logs that mention this chunk
            query = self.db.query(ActivityLog).filter(
                and_(
                    ActivityLog.bot_id == bot_id,
                    ActivityLog.action.like('deduplication_%'),
                    or_(
                        ActivityLog.details.op('->>')('audit_metadata').op('->>')('decision_details').op('->>')('primary_chunk_id') == str(chunk_id),
                        ActivityLog.details.op('->>')('audit_metadata').op('->>')('decision_details').op('->>')('duplicate_chunk_ids').op('@>')(f'["{str(chunk_id)}"]')
                    )
                )
            ).order_by(desc(ActivityLog.created_at))
            
            activity_logs = query.all()
            
            # Convert to audit trail entries
            entries = []
            for log in activity_logs:
                details = log.details or {}
                audit_metadata = details.get('audit_metadata', {})
                decision_details = audit_metadata.get('decision_details', {})
                
                entry = AuditTrailEntry(
                    id=str(log.id),
                    bot_id=log.bot_id,
                    operation_type=details.get('operation_type', 'unknown'),
                    timestamp=log.created_at,
                    decision_id=details.get('decision_id', ''),
                    affected_chunks=[
                        UUID(cid) for cid in decision_details.get('duplicate_chunk_ids', [])
                    ] + ([UUID(decision_details['primary_chunk_id'])] 
                         if decision_details.get('primary_chunk_id') else []),
                    similarity_score=details.get('similarity_score', 0.0),
                    action_taken=details.get('action_taken', ''),
                    reason=details.get('reason', ''),
                    metadata=audit_metadata,
                    user_id=log.user_id
                )
                entries.append(entry)
            
            logger.debug(
                f"Retrieved {len(entries)} deduplication history entries for chunk {chunk_id}"
            )
            
            return entries
            
        except Exception as e:
            logger.error(f"Error getting chunk deduplication history for {chunk_id}: {e}")
            return []
    
    async def get_deduplication_statistics(
        self,
        bot_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get deduplication statistics for a bot over a time period.
        
        Args:
            bot_id: Bot identifier
            days: Number of days to analyze
            
        Returns:
            Statistics about deduplication operations
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Query deduplication activities
            query = self.db.query(ActivityLog).filter(
                and_(
                    ActivityLog.bot_id == bot_id,
                    ActivityLog.action.like('deduplication_%'),
                    ActivityLog.created_at >= start_date
                )
            )
            
            activities = query.all()
            
            # Analyze statistics
            stats = {
                'period_days': days,
                'total_operations': len(activities),
                'operations_by_type': {},
                'chunks_affected': 0,
                'similarity_scores': [],
                'recent_operations': [],
                'efficiency_metrics': {}
            }
            
            for activity in activities:
                details = activity.details or {}
                action = activity.action.replace('deduplication_', '')
                
                # Count operations by type
                stats['operations_by_type'][action] = stats['operations_by_type'].get(action, 0) + 1
                
                # Count affected chunks
                affected_chunks = details.get('affected_chunks', 0)
                stats['chunks_affected'] += affected_chunks
                
                # Collect similarity scores
                similarity_score = details.get('similarity_score', 0)
                if similarity_score > 0:
                    stats['similarity_scores'].append(similarity_score)
                
                # Add to recent operations (last 10)
                if len(stats['recent_operations']) < 10:
                    stats['recent_operations'].append({
                        'timestamp': activity.created_at.isoformat(),
                        'action': action,
                        'affected_chunks': affected_chunks,
                        'similarity_score': similarity_score,
                        'reason': details.get('reason', '')
                    })
            
            # Calculate efficiency metrics
            if stats['similarity_scores']:
                stats['efficiency_metrics'] = {
                    'avg_similarity_score': sum(stats['similarity_scores']) / len(stats['similarity_scores']),
                    'min_similarity_score': min(stats['similarity_scores']),
                    'max_similarity_score': max(stats['similarity_scores']),
                    'high_confidence_operations': len([s for s in stats['similarity_scores'] if s >= 0.95]),
                    'medium_confidence_operations': len([s for s in stats['similarity_scores'] if 0.85 <= s < 0.95]),
                    'low_confidence_operations': len([s for s in stats['similarity_scores'] if s < 0.85])
                }
            
            # Sort recent operations by timestamp (newest first)
            stats['recent_operations'].sort(key=lambda x: x['timestamp'], reverse=True)
            
            logger.debug(
                f"Generated deduplication statistics for bot {bot_id} "
                f"over {days} days: {stats['total_operations']} operations"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting deduplication statistics for bot {bot_id}: {e}")
            return {'error': str(e)}
    
    async def export_audit_trail(
        self,
        bot_id: UUID,
        format: str = 'json',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Export audit trail data for analysis or compliance.
        
        Args:
            bot_id: Bot identifier
            format: Export format ('json', 'csv')
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Exported audit trail data
        """
        try:
            # Get all audit trail entries
            result = await self.query_audit_trail(
                bot_id=bot_id,
                start_date=start_date,
                end_date=end_date,
                limit=10000  # Large limit for export
            )
            
            if format == 'json':
                export_data = {
                    'export_metadata': {
                        'bot_id': str(bot_id),
                        'export_timestamp': datetime.utcnow().isoformat(),
                        'total_entries': result.total_count,
                        'date_range': {
                            'start': start_date.isoformat() if start_date else None,
                            'end': end_date.isoformat() if end_date else None
                        }
                    },
                    'audit_entries': [
                        {
                            'id': entry.id,
                            'timestamp': entry.timestamp.isoformat(),
                            'operation_type': entry.operation_type,
                            'decision_id': entry.decision_id,
                            'affected_chunks': [str(cid) for cid in entry.affected_chunks],
                            'similarity_score': entry.similarity_score,
                            'action_taken': entry.action_taken,
                            'reason': entry.reason,
                            'user_id': str(entry.user_id) if entry.user_id else None,
                            'metadata': entry.metadata
                        }
                        for entry in result.entries
                    ]
                }
                
                return export_data
            
            elif format == 'csv':
                # Convert to CSV-friendly format
                csv_data = []
                for entry in result.entries:
                    csv_row = {
                        'id': entry.id,
                        'timestamp': entry.timestamp.isoformat(),
                        'operation_type': entry.operation_type,
                        'decision_id': entry.decision_id,
                        'affected_chunks_count': len(entry.affected_chunks),
                        'similarity_score': entry.similarity_score,
                        'action_taken': entry.action_taken,
                        'reason': entry.reason,
                        'user_id': str(entry.user_id) if entry.user_id else ''
                    }
                    csv_data.append(csv_row)
                
                return {
                    'format': 'csv',
                    'data': csv_data,
                    'total_entries': result.total_count
                }
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting audit trail for bot {bot_id}: {e}")
            return {'error': str(e)}
    
    async def cleanup_old_audit_entries(
        self,
        bot_id: UUID,
        retention_days: int = 365
    ) -> Dict[str, Any]:
        """
        Clean up old audit trail entries based on retention policy.
        
        Args:
            bot_id: Bot identifier
            retention_days: Number of days to retain audit entries
            
        Returns:
            Cleanup operation results
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Count entries to be deleted
            count_query = self.db.query(func.count(ActivityLog.id)).filter(
                and_(
                    ActivityLog.bot_id == bot_id,
                    ActivityLog.action.like('deduplication_%'),
                    ActivityLog.created_at < cutoff_date
                )
            )
            
            entries_to_delete = count_query.scalar()
            
            if entries_to_delete > 0:
                # Delete old entries
                delete_query = self.db.query(ActivityLog).filter(
                    and_(
                        ActivityLog.bot_id == bot_id,
                        ActivityLog.action.like('deduplication_%'),
                        ActivityLog.created_at < cutoff_date
                    )
                )
                
                delete_query.delete(synchronize_session=False)
                self.db.commit()
                
                logger.info(
                    f"Cleaned up {entries_to_delete} old audit entries for bot {bot_id} "
                    f"older than {retention_days} days"
                )
            
            return {
                'success': True,
                'entries_deleted': entries_to_delete,
                'cutoff_date': cutoff_date.isoformat(),
                'retention_days': retention_days
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up audit entries for bot {bot_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'entries_deleted': 0
            }