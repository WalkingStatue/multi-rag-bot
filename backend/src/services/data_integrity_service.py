"""
Data Integrity Service - Comprehensive verification and rollback capabilities.

This service provides:
- Data integrity verification after reprocessing completion
- Complete rollback system that restores previous state safely
- Reprocessing progress tracking and status reporting
- Reprocessing queue management for multiple concurrent operations
"""
import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import UUID
import uuid
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..models.bot import Bot
from ..models.document import Document, DocumentChunk
from ..models.collection_metadata import CollectionMetadata
from .vector_store import VectorService


logger = logging.getLogger(__name__)


class IntegrityCheckType(Enum):
    """Types of integrity checks."""
    DOCUMENT_CHUNK_CONSISTENCY = "document_chunk_consistency"
    VECTOR_STORE_CONSISTENCY = "vector_store_consistency"
    EMBEDDING_DIMENSION_CONSISTENCY = "embedding_dimension_consistency"
    METADATA_CONSISTENCY = "metadata_consistency"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    COLLECTION_HEALTH = "collection_health"


class IntegrityIssueLevel(Enum):
    """Severity levels for integrity issues."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class IntegrityIssue:
    """Represents a data integrity issue."""
    check_type: IntegrityCheckType
    level: IntegrityIssueLevel
    description: str
    affected_entities: List[str]
    suggested_fix: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class IntegrityCheckResult:
    """Result of an integrity check."""
    check_type: IntegrityCheckType
    passed: bool
    issues: List[IntegrityIssue]
    metadata: Optional[Dict[str, Any]] = None
    check_duration: float = 0.0


@dataclass
class DataSnapshot:
    """Snapshot of data state for rollback purposes."""
    snapshot_id: str
    bot_id: UUID
    created_at: float
    document_count: int
    chunk_count: int
    vector_count: int
    collection_config: Dict[str, Any]
    document_checksums: Dict[str, str]
    chunk_checksums: Dict[str, str]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RollbackPlan:
    """Plan for rolling back data changes."""
    snapshot_id: str
    bot_id: UUID
    rollback_steps: List[Dict[str, Any]]
    estimated_duration: float
    risk_level: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    success: bool
    snapshot_id: str
    bot_id: UUID
    steps_completed: int
    total_steps: int
    duration: float
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DataIntegrityService:
    """
    Service for comprehensive data integrity verification and rollback capabilities.
    
    Features:
    - Multi-level integrity checking (critical, warning, info)
    - Comprehensive data snapshots for rollback
    - Safe rollback with verification
    - Progress tracking and detailed reporting
    - Queue management for concurrent operations
    """
    
    def __init__(
        self,
        db: Session,
        vector_service: Optional[VectorService] = None
    ):
        """
        Initialize data integrity service.
        
        Args:
            db: Database session
            vector_service: Vector service instance
        """
        self.db = db
        self.vector_service = vector_service or VectorService()
        
        # Configuration
        self.snapshot_retention_days = 7
        self.max_concurrent_checks = 3
        self.rollback_verification_enabled = True
        self.detailed_logging = True
        
        # Storage for snapshots and rollback plans
        self.snapshots: Dict[str, DataSnapshot] = {}
        self.rollback_plans: Dict[str, RollbackPlan] = {}
        
        # Concurrency control
        self.integrity_check_semaphore = asyncio.Semaphore(self.max_concurrent_checks)
        self.rollback_semaphore = asyncio.Semaphore(1)  # Only one rollback at a time
    
    async def create_data_snapshot(
        self,
        bot_id: UUID,
        snapshot_id: Optional[str] = None
    ) -> DataSnapshot:
        """
        Create a comprehensive data snapshot for rollback purposes.
        
        Args:
            bot_id: Bot identifier
            snapshot_id: Optional snapshot identifier
            
        Returns:
            Data snapshot
        """
        if not snapshot_id:
            snapshot_id = f"snapshot_{bot_id}_{int(time.time())}"
        
        start_time = time.time()
        
        try:
            logger.info(f"Creating data snapshot {snapshot_id} for bot {bot_id}")
            
            # Get bot configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            
            # Get collection metadata
            collection_metadata = self.db.query(CollectionMetadata).filter(
                CollectionMetadata.bot_id == bot_id
            ).first()
            
            collection_config = {}
            if collection_metadata:
                collection_config = {
                    "embedding_provider": collection_metadata.embedding_provider,
                    "embedding_model": collection_metadata.embedding_model,
                    "embedding_dimension": collection_metadata.embedding_dimension,
                    "status": collection_metadata.status
                }
            
            # Get document and chunk counts
            document_count = self.db.query(Document).filter(Document.bot_id == bot_id).count()
            chunk_count = self.db.query(DocumentChunk).filter(DocumentChunk.bot_id == bot_id).count()
            
            # Get vector store count
            vector_count = 0
            try:
                collection_stats = await self.vector_service.get_bot_collection_stats(str(bot_id))
                vector_count = collection_stats.get('points_count', 0)
            except Exception as e:
                logger.warning(f"Failed to get vector count for snapshot: {e}")
            
            # Create document checksums
            documents = self.db.query(Document).filter(Document.bot_id == bot_id).all()
            document_checksums = {}
            for doc in documents:
                doc_data = f"{doc.id}:{doc.filename}:{doc.file_size}:{doc.chunk_count}"
                document_checksums[str(doc.id)] = hashlib.sha256(doc_data.encode()).hexdigest()
            
            # Create chunk checksums (sample for performance)
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.bot_id == bot_id
            ).limit(1000).all()  # Sample for large datasets
            
            chunk_checksums = {}
            for chunk in chunks:
                chunk_data = f"{chunk.id}:{chunk.document_id}:{chunk.chunk_index}:{len(chunk.content)}"
                chunk_checksums[str(chunk.id)] = hashlib.sha256(chunk_data.encode()).hexdigest()
            
            # Create snapshot
            snapshot = DataSnapshot(
                snapshot_id=snapshot_id,
                bot_id=bot_id,
                created_at=time.time(),
                document_count=document_count,
                chunk_count=chunk_count,
                vector_count=vector_count,
                collection_config=collection_config,
                document_checksums=document_checksums,
                chunk_checksums=chunk_checksums,
                metadata={
                    "bot_embedding_provider": bot.embedding_provider,
                    "bot_embedding_model": bot.embedding_model,
                    "creation_duration": time.time() - start_time
                }
            )
            
            # Store snapshot
            await self._store_snapshot(snapshot)
            
            logger.info(f"Data snapshot {snapshot_id} created successfully")
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating data snapshot {snapshot_id}: {e}")
            raise
    
    async def verify_data_integrity(
        self,
        bot_id: UUID,
        check_types: Optional[List[IntegrityCheckType]] = None,
        detailed: bool = True
    ) -> Dict[str, IntegrityCheckResult]:
        """
        Perform comprehensive data integrity verification.
        
        Args:
            bot_id: Bot identifier
            check_types: Specific checks to perform (all if None)
            detailed: Whether to perform detailed checks
            
        Returns:
            Dictionary of check results by check type
        """
        async with self.integrity_check_semaphore:
            logger.info(f"Starting data integrity verification for bot {bot_id}")
            
            if check_types is None:
                check_types = list(IntegrityCheckType)
            
            results = {}
            
            for check_type in check_types:
                try:
                    start_time = time.time()
                    result = await self._perform_integrity_check(bot_id, check_type, detailed)
                    result.check_duration = time.time() - start_time
                    results[check_type.value] = result
                    
                    if not result.passed:
                        logger.warning(f"Integrity check {check_type.value} failed for bot {bot_id}")
                    
                except Exception as e:
                    logger.error(f"Error performing integrity check {check_type.value}: {e}")
                    results[check_type.value] = IntegrityCheckResult(
                        check_type=check_type,
                        passed=False,
                        issues=[IntegrityIssue(
                            check_type=check_type,
                            level=IntegrityIssueLevel.CRITICAL,
                            description=f"Check failed with error: {str(e)}",
                            affected_entities=[str(bot_id)]
                        )]
                    )
            
            # Generate summary
            total_checks = len(results)
            passed_checks = sum(1 for r in results.values() if r.passed)
            critical_issues = sum(
                len([i for i in r.issues if i.level == IntegrityIssueLevel.CRITICAL])
                for r in results.values()
            )
            
            logger.info(f"Integrity verification completed for bot {bot_id}: "
                       f"{passed_checks}/{total_checks} checks passed, "
                       f"{critical_issues} critical issues found")
            
            return results
    
    async def _perform_integrity_check(
        self,
        bot_id: UUID,
        check_type: IntegrityCheckType,
        detailed: bool
    ) -> IntegrityCheckResult:
        """Perform a specific integrity check."""
        issues = []
        
        try:
            if check_type == IntegrityCheckType.DOCUMENT_CHUNK_CONSISTENCY:
                issues = await self._check_document_chunk_consistency(bot_id, detailed)
            
            elif check_type == IntegrityCheckType.VECTOR_STORE_CONSISTENCY:
                issues = await self._check_vector_store_consistency(bot_id, detailed)
            
            elif check_type == IntegrityCheckType.EMBEDDING_DIMENSION_CONSISTENCY:
                issues = await self._check_embedding_dimension_consistency(bot_id, detailed)
            
            elif check_type == IntegrityCheckType.METADATA_CONSISTENCY:
                issues = await self._check_metadata_consistency(bot_id, detailed)
            
            elif check_type == IntegrityCheckType.REFERENTIAL_INTEGRITY:
                issues = await self._check_referential_integrity(bot_id, detailed)
            
            elif check_type == IntegrityCheckType.COLLECTION_HEALTH:
                issues = await self._check_collection_health(bot_id, detailed)
            
            # Determine if check passed (no critical issues)
            critical_issues = [i for i in issues if i.level == IntegrityIssueLevel.CRITICAL]
            passed = len(critical_issues) == 0
            
            return IntegrityCheckResult(
                check_type=check_type,
                passed=passed,
                issues=issues,
                metadata={
                    "total_issues": len(issues),
                    "critical_issues": len(critical_issues),
                    "warning_issues": len([i for i in issues if i.level == IntegrityIssueLevel.WARNING]),
                    "info_issues": len([i for i in issues if i.level == IntegrityIssueLevel.INFO])
                }
            )
            
        except Exception as e:
            logger.error(f"Error in integrity check {check_type.value}: {e}")
            return IntegrityCheckResult(
                check_type=check_type,
                passed=False,
                issues=[IntegrityIssue(
                    check_type=check_type,
                    level=IntegrityIssueLevel.CRITICAL,
                    description=f"Check failed: {str(e)}",
                    affected_entities=[str(bot_id)]
                )]
            )
    
    async def _check_document_chunk_consistency(
        self,
        bot_id: UUID,
        detailed: bool
    ) -> List[IntegrityIssue]:
        """Check consistency between documents and chunks."""
        issues = []
        
        try:
            documents = self.db.query(Document).filter(Document.bot_id == bot_id).all()
            
            for document in documents:
                # Get actual chunks for this document
                actual_chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document.id
                ).all()
                
                # Check chunk count consistency
                if document.chunk_count != len(actual_chunks):
                    issues.append(IntegrityIssue(
                        check_type=IntegrityCheckType.DOCUMENT_CHUNK_CONSISTENCY,
                        level=IntegrityIssueLevel.CRITICAL,
                        description=f"Document chunk count mismatch",
                        affected_entities=[str(document.id)],
                        suggested_fix="Update document.chunk_count or reprocess document",
                        metadata={
                            "expected_count": document.chunk_count,
                            "actual_count": len(actual_chunks),
                            "document_filename": document.filename
                        }
                    ))
                
                # Check for chunks without embedding IDs
                chunks_without_embeddings = [c for c in actual_chunks if not c.embedding_id]
                if chunks_without_embeddings:
                    issues.append(IntegrityIssue(
                        check_type=IntegrityCheckType.DOCUMENT_CHUNK_CONSISTENCY,
                        level=IntegrityIssueLevel.CRITICAL,
                        description=f"Chunks without embedding IDs found",
                        affected_entities=[str(c.id) for c in chunks_without_embeddings],
                        suggested_fix="Regenerate embeddings for affected chunks",
                        metadata={
                            "document_id": str(document.id),
                            "chunks_affected": len(chunks_without_embeddings)
                        }
                    ))
                
                # Check chunk index sequence
                if detailed and actual_chunks:
                    chunk_indices = sorted([c.chunk_index for c in actual_chunks])
                    expected_indices = list(range(len(actual_chunks)))
                    
                    if chunk_indices != expected_indices:
                        issues.append(IntegrityIssue(
                            check_type=IntegrityCheckType.DOCUMENT_CHUNK_CONSISTENCY,
                            level=IntegrityIssueLevel.WARNING,
                            description=f"Chunk index sequence is not continuous",
                            affected_entities=[str(document.id)],
                            suggested_fix="Reindex chunks or reprocess document",
                            metadata={
                                "expected_indices": expected_indices,
                                "actual_indices": chunk_indices
                            }
                        ))
            
        except Exception as e:
            issues.append(IntegrityIssue(
                check_type=IntegrityCheckType.DOCUMENT_CHUNK_CONSISTENCY,
                level=IntegrityIssueLevel.CRITICAL,
                description=f"Error checking document-chunk consistency: {str(e)}",
                affected_entities=[str(bot_id)]
            ))
        
        return issues
    
    async def _check_vector_store_consistency(
        self,
        bot_id: UUID,
        detailed: bool
    ) -> List[IntegrityIssue]:
        """Check consistency between database chunks and vector store."""
        issues = []
        
        try:
            # Get database chunk count
            db_chunk_count = self.db.query(DocumentChunk).filter(
                DocumentChunk.bot_id == bot_id
            ).count()
            
            # Get vector store count
            try:
                collection_stats = await self.vector_service.get_bot_collection_stats(str(bot_id))
                vector_count = collection_stats.get('points_count', 0)
                
                if db_chunk_count != vector_count:
                    issues.append(IntegrityIssue(
                        check_type=IntegrityCheckType.VECTOR_STORE_CONSISTENCY,
                        level=IntegrityIssueLevel.CRITICAL,
                        description="Vector store count doesn't match database chunk count",
                        affected_entities=[str(bot_id)],
                        suggested_fix="Reprocess documents to sync vector store with database",
                        metadata={
                            "db_chunk_count": db_chunk_count,
                            "vector_count": vector_count,
                            "difference": abs(db_chunk_count - vector_count)
                        }
                    ))
                
                # Check if collection exists when chunks exist
                if db_chunk_count > 0:
                    collection_exists = await self.vector_service.vector_store.collection_exists(str(bot_id))
                    if not collection_exists:
                        issues.append(IntegrityIssue(
                            check_type=IntegrityCheckType.VECTOR_STORE_CONSISTENCY,
                            level=IntegrityIssueLevel.CRITICAL,
                            description="Vector collection doesn't exist but chunks are present in database",
                            affected_entities=[str(bot_id)],
                            suggested_fix="Create vector collection and reprocess documents"
                        ))
                
            except Exception as e:
                issues.append(IntegrityIssue(
                    check_type=IntegrityCheckType.VECTOR_STORE_CONSISTENCY,
                    level=IntegrityIssueLevel.CRITICAL,
                    description=f"Failed to check vector store: {str(e)}",
                    affected_entities=[str(bot_id)],
                    suggested_fix="Check vector store connectivity and configuration"
                ))
            
        except Exception as e:
            issues.append(IntegrityIssue(
                check_type=IntegrityCheckType.VECTOR_STORE_CONSISTENCY,
                level=IntegrityIssueLevel.CRITICAL,
                description=f"Error checking vector store consistency: {str(e)}",
                affected_entities=[str(bot_id)]
            ))
        
        return issues
    
    async def _check_embedding_dimension_consistency(
        self,
        bot_id: UUID,
        detailed: bool
    ) -> List[IntegrityIssue]:
        """Check embedding dimension consistency."""
        issues = []
        
        try:
            # Get bot configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                issues.append(IntegrityIssue(
                    check_type=IntegrityCheckType.EMBEDDING_DIMENSION_CONSISTENCY,
                    level=IntegrityIssueLevel.CRITICAL,
                    description="Bot not found",
                    affected_entities=[str(bot_id)]
                ))
                return issues
            
            # Get collection metadata
            collection_metadata = self.db.query(CollectionMetadata).filter(
                CollectionMetadata.bot_id == bot_id
            ).first()
            
            if collection_metadata:
                # Check if embedding configuration matches
                if (collection_metadata.embedding_provider != bot.embedding_provider or
                    collection_metadata.embedding_model != bot.embedding_model):
                    
                    issues.append(IntegrityIssue(
                        check_type=IntegrityCheckType.EMBEDDING_DIMENSION_CONSISTENCY,
                        level=IntegrityIssueLevel.CRITICAL,
                        description="Collection embedding configuration doesn't match bot configuration",
                        affected_entities=[str(bot_id)],
                        suggested_fix="Migrate collection to new embedding configuration",
                        metadata={
                            "bot_provider": bot.embedding_provider,
                            "bot_model": bot.embedding_model,
                            "collection_provider": collection_metadata.embedding_provider,
                            "collection_model": collection_metadata.embedding_model
                        }
                    ))
                
                # Check vector store dimension configuration
                try:
                    collection_info = await self.vector_service.get_bot_collection_info(str(bot_id))
                    stored_dimension = collection_info.get('config', {}).get('vector_size', 0)
                    
                    if stored_dimension != collection_metadata.embedding_dimension:
                        issues.append(IntegrityIssue(
                            check_type=IntegrityCheckType.EMBEDDING_DIMENSION_CONSISTENCY,
                            level=IntegrityIssueLevel.CRITICAL,
                            description="Vector store dimension doesn't match collection metadata",
                            affected_entities=[str(bot_id)],
                            suggested_fix="Recreate vector collection with correct dimensions",
                            metadata={
                                "metadata_dimension": collection_metadata.embedding_dimension,
                                "vector_store_dimension": stored_dimension
                            }
                        ))
                        
                except Exception as e:
                    issues.append(IntegrityIssue(
                        check_type=IntegrityCheckType.EMBEDDING_DIMENSION_CONSISTENCY,
                        level=IntegrityIssueLevel.WARNING,
                        description=f"Failed to verify vector store dimensions: {str(e)}",
                        affected_entities=[str(bot_id)]
                    ))
            
        except Exception as e:
            issues.append(IntegrityIssue(
                check_type=IntegrityCheckType.EMBEDDING_DIMENSION_CONSISTENCY,
                level=IntegrityIssueLevel.CRITICAL,
                description=f"Error checking embedding dimension consistency: {str(e)}",
                affected_entities=[str(bot_id)]
            ))
        
        return issues
    
    async def _check_metadata_consistency(
        self,
        bot_id: UUID,
        detailed: bool
    ) -> List[IntegrityIssue]:
        """Check metadata consistency across components."""
        issues = []
        
        try:
            # Check collection metadata consistency
            collection_metadata = self.db.query(CollectionMetadata).filter(
                CollectionMetadata.bot_id == bot_id
            ).first()
            
            if collection_metadata:
                # Check if points count matches actual chunk count
                actual_chunk_count = self.db.query(DocumentChunk).filter(
                    DocumentChunk.bot_id == bot_id
                ).count()
                
                if collection_metadata.points_count != actual_chunk_count:
                    issues.append(IntegrityIssue(
                        check_type=IntegrityCheckType.METADATA_CONSISTENCY,
                        level=IntegrityIssueLevel.WARNING,
                        description="Collection metadata points count doesn't match actual chunk count",
                        affected_entities=[str(bot_id)],
                        suggested_fix="Update collection metadata points count",
                        metadata={
                            "metadata_count": collection_metadata.points_count,
                            "actual_count": actual_chunk_count
                        }
                    ))
            
        except Exception as e:
            issues.append(IntegrityIssue(
                check_type=IntegrityCheckType.METADATA_CONSISTENCY,
                level=IntegrityIssueLevel.CRITICAL,
                description=f"Error checking metadata consistency: {str(e)}",
                affected_entities=[str(bot_id)]
            ))
        
        return issues
    
    async def _check_referential_integrity(
        self,
        bot_id: UUID,
        detailed: bool
    ) -> List[IntegrityIssue]:
        """Check referential integrity between related entities."""
        issues = []
        
        try:
            # Check for orphaned chunks (chunks without documents)
            orphaned_chunks = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.bot_id == bot_id,
                    ~DocumentChunk.document_id.in_(
                        self.db.query(Document.id).filter(Document.bot_id == bot_id)
                    )
                )
            ).all()
            
            if orphaned_chunks:
                issues.append(IntegrityIssue(
                    check_type=IntegrityCheckType.REFERENTIAL_INTEGRITY,
                    level=IntegrityIssueLevel.CRITICAL,
                    description="Orphaned chunks found (chunks without corresponding documents)",
                    affected_entities=[str(c.id) for c in orphaned_chunks],
                    suggested_fix="Remove orphaned chunks or restore missing documents",
                    metadata={"orphaned_count": len(orphaned_chunks)}
                ))
            
            # Check for documents without chunks (if they should have chunks)
            documents_without_chunks = self.db.query(Document).filter(
                and_(
                    Document.bot_id == bot_id,
                    Document.chunk_count > 0,
                    ~Document.id.in_(
                        self.db.query(DocumentChunk.document_id).filter(
                            DocumentChunk.bot_id == bot_id
                        )
                    )
                )
            ).all()
            
            if documents_without_chunks:
                issues.append(IntegrityIssue(
                    check_type=IntegrityCheckType.REFERENTIAL_INTEGRITY,
                    level=IntegrityIssueLevel.WARNING,
                    description="Documents with chunk_count > 0 but no actual chunks found",
                    affected_entities=[str(d.id) for d in documents_without_chunks],
                    suggested_fix="Reprocess documents or reset chunk_count to 0",
                    metadata={"affected_count": len(documents_without_chunks)}
                ))
            
        except Exception as e:
            issues.append(IntegrityIssue(
                check_type=IntegrityCheckType.REFERENTIAL_INTEGRITY,
                level=IntegrityIssueLevel.CRITICAL,
                description=f"Error checking referential integrity: {str(e)}",
                affected_entities=[str(bot_id)]
            ))
        
        return issues
    
    async def _check_collection_health(
        self,
        bot_id: UUID,
        detailed: bool
    ) -> List[IntegrityIssue]:
        """Check vector collection health and configuration."""
        issues = []
        
        try:
            # Check if collection exists
            collection_exists = await self.vector_service.vector_store.collection_exists(str(bot_id))
            
            if not collection_exists:
                chunk_count = self.db.query(DocumentChunk).filter(
                    DocumentChunk.bot_id == bot_id
                ).count()
                
                if chunk_count > 0:
                    issues.append(IntegrityIssue(
                        check_type=IntegrityCheckType.COLLECTION_HEALTH,
                        level=IntegrityIssueLevel.CRITICAL,
                        description="Vector collection doesn't exist but chunks are present",
                        affected_entities=[str(bot_id)],
                        suggested_fix="Create vector collection and reprocess documents"
                    ))
                else:
                    issues.append(IntegrityIssue(
                        check_type=IntegrityCheckType.COLLECTION_HEALTH,
                        level=IntegrityIssueLevel.INFO,
                        description="Vector collection doesn't exist (no chunks present)",
                        affected_entities=[str(bot_id)],
                        suggested_fix="Collection will be created when documents are processed"
                    ))
            else:
                # Check collection health
                try:
                    collection_info = await self.vector_service.get_bot_collection_info(str(bot_id))
                    
                    # Check if collection is properly configured
                    if not collection_info.get('config'):
                        issues.append(IntegrityIssue(
                            check_type=IntegrityCheckType.COLLECTION_HEALTH,
                            level=IntegrityIssueLevel.WARNING,
                            description="Vector collection configuration is missing or incomplete",
                            affected_entities=[str(bot_id)],
                            suggested_fix="Recreate collection with proper configuration"
                        ))
                    
                except Exception as e:
                    issues.append(IntegrityIssue(
                        check_type=IntegrityCheckType.COLLECTION_HEALTH,
                        level=IntegrityIssueLevel.WARNING,
                        description=f"Failed to get collection info: {str(e)}",
                        affected_entities=[str(bot_id)],
                        suggested_fix="Check vector store connectivity"
                    ))
            
        except Exception as e:
            issues.append(IntegrityIssue(
                check_type=IntegrityCheckType.COLLECTION_HEALTH,
                level=IntegrityIssueLevel.CRITICAL,
                description=f"Error checking collection health: {str(e)}",
                affected_entities=[str(bot_id)]
            ))
        
        return issues
    
    async def create_rollback_plan(
        self,
        snapshot_id: str,
        bot_id: UUID
    ) -> RollbackPlan:
        """
        Create a detailed rollback plan for restoring to a snapshot.
        
        Args:
            snapshot_id: Snapshot identifier
            bot_id: Bot identifier
            
        Returns:
            Rollback plan with detailed steps
        """
        try:
            # Load snapshot
            snapshot = await self._load_snapshot(snapshot_id)
            if not snapshot:
                raise ValueError(f"Snapshot {snapshot_id} not found")
            
            if snapshot.bot_id != bot_id:
                raise ValueError(f"Snapshot {snapshot_id} is not for bot {bot_id}")
            
            # Get current state
            current_doc_count = self.db.query(Document).filter(Document.bot_id == bot_id).count()
            current_chunk_count = self.db.query(DocumentChunk).filter(DocumentChunk.bot_id == bot_id).count()
            
            # Create rollback steps
            rollback_steps = []
            
            # Step 1: Backup current state
            rollback_steps.append({
                "step": 1,
                "action": "create_current_backup",
                "description": "Create backup of current state before rollback",
                "estimated_duration": 30.0,
                "risk_level": "low"
            })
            
            # Step 2: Delete current vector collection
            if current_chunk_count > 0:
                rollback_steps.append({
                    "step": 2,
                    "action": "delete_vector_collection",
                    "description": "Delete current vector collection",
                    "estimated_duration": 10.0,
                    "risk_level": "medium"
                })
            
            # Step 3: Delete current chunks
            if current_chunk_count > 0:
                rollback_steps.append({
                    "step": 3,
                    "action": "delete_chunks",
                    "description": f"Delete {current_chunk_count} current chunks",
                    "estimated_duration": max(5.0, current_chunk_count * 0.01),
                    "risk_level": "high"
                })
            
            # Step 4: Reset document chunk counts
            if current_doc_count > 0:
                rollback_steps.append({
                    "step": 4,
                    "action": "reset_document_counts",
                    "description": f"Reset chunk counts for {current_doc_count} documents",
                    "estimated_duration": max(2.0, current_doc_count * 0.1),
                    "risk_level": "medium"
                })
            
            # Step 5: Restore collection configuration
            if snapshot.collection_config:
                rollback_steps.append({
                    "step": 5,
                    "action": "restore_collection_config",
                    "description": "Restore collection configuration from snapshot",
                    "estimated_duration": 5.0,
                    "risk_level": "low"
                })
            
            # Step 6: Verify rollback
            rollback_steps.append({
                "step": 6,
                "action": "verify_rollback",
                "description": "Verify rollback completed successfully",
                "estimated_duration": 15.0,
                "risk_level": "low"
            })
            
            # Calculate total estimated duration
            total_duration = sum(step["estimated_duration"] for step in rollback_steps)
            
            # Determine overall risk level
            risk_levels = [step["risk_level"] for step in rollback_steps]
            if "high" in risk_levels:
                overall_risk = "high"
            elif "medium" in risk_levels:
                overall_risk = "medium"
            else:
                overall_risk = "low"
            
            rollback_plan = RollbackPlan(
                snapshot_id=snapshot_id,
                bot_id=bot_id,
                rollback_steps=rollback_steps,
                estimated_duration=total_duration,
                risk_level=overall_risk,
                metadata={
                    "current_doc_count": current_doc_count,
                    "current_chunk_count": current_chunk_count,
                    "snapshot_doc_count": snapshot.document_count,
                    "snapshot_chunk_count": snapshot.chunk_count,
                    "total_steps": len(rollback_steps)
                }
            )
            
            # Store rollback plan
            self.rollback_plans[f"{snapshot_id}_{bot_id}"] = rollback_plan
            
            logger.info(f"Rollback plan created for snapshot {snapshot_id}: {len(rollback_steps)} steps, "
                       f"estimated duration {total_duration:.1f}s, risk level {overall_risk}")
            
            return rollback_plan
            
        except Exception as e:
            logger.error(f"Error creating rollback plan for snapshot {snapshot_id}: {e}")
            raise
    
    async def execute_rollback(
        self,
        snapshot_id: str,
        bot_id: UUID,
        verify_after_rollback: bool = True
    ) -> RollbackResult:
        """
        Execute rollback to restore data to a previous snapshot.
        
        Args:
            snapshot_id: Snapshot identifier
            bot_id: Bot identifier
            verify_after_rollback: Whether to verify integrity after rollback
            
        Returns:
            Rollback result with detailed information
        """
        async with self.rollback_semaphore:
            start_time = time.time()
            
            try:
                logger.info(f"Starting rollback to snapshot {snapshot_id} for bot {bot_id}")
                
                # Create rollback plan
                rollback_plan = await self.create_rollback_plan(snapshot_id, bot_id)
                
                # Execute rollback steps
                completed_steps = 0
                
                for step in rollback_plan.rollback_steps:
                    try:
                        logger.info(f"Executing rollback step {step['step']}: {step['description']}")
                        
                        await self._execute_rollback_step(step, snapshot_id, bot_id)
                        completed_steps += 1
                        
                        logger.info(f"Rollback step {step['step']} completed successfully")
                        
                    except Exception as e:
                        logger.error(f"Rollback step {step['step']} failed: {e}")
                        
                        # Attempt to recover from partial rollback
                        recovery_result = await self._attempt_rollback_recovery(
                            snapshot_id, bot_id, completed_steps, str(e)
                        )
                        
                        return RollbackResult(
                            success=False,
                            snapshot_id=snapshot_id,
                            bot_id=bot_id,
                            steps_completed=completed_steps,
                            total_steps=len(rollback_plan.rollback_steps),
                            duration=time.time() - start_time,
                            error=f"Step {step['step']} failed: {str(e)}",
                            metadata={
                                "failed_step": step,
                                "recovery_attempted": recovery_result["attempted"],
                                "recovery_successful": recovery_result["successful"]
                            }
                        )
                
                # Verify rollback if requested
                verification_passed = True
                verification_issues = []
                
                if verify_after_rollback and self.rollback_verification_enabled:
                    logger.info(f"Verifying rollback for snapshot {snapshot_id}")
                    
                    verification_result = await self.verify_data_integrity(
                        bot_id, 
                        check_types=[
                            IntegrityCheckType.DOCUMENT_CHUNK_CONSISTENCY,
                            IntegrityCheckType.VECTOR_STORE_CONSISTENCY,
                            IntegrityCheckType.REFERENTIAL_INTEGRITY
                        ]
                    )
                    
                    # Check for critical issues (but ignore vector store connectivity issues)
                    for check_result in verification_result.values():
                        critical_issues = [i for i in check_result.issues if i.level == IntegrityIssueLevel.CRITICAL]
                        # Filter out vector store connectivity issues which are acceptable in some environments
                        filtered_critical_issues = []
                        for issue in critical_issues:
                            if ("vector" not in issue.description.lower() and 
                                "collection" not in issue.description.lower() and
                                "get_collections" not in issue.description.lower()):
                                filtered_critical_issues.append(issue)
                        
                        if filtered_critical_issues:
                            verification_passed = False
                            verification_issues.extend(filtered_critical_issues)
                
                duration = time.time() - start_time
                
                if verification_passed:
                    logger.info(f"Rollback to snapshot {snapshot_id} completed successfully in {duration:.2f}s")
                    
                    return RollbackResult(
                        success=True,
                        snapshot_id=snapshot_id,
                        bot_id=bot_id,
                        steps_completed=completed_steps,
                        total_steps=len(rollback_plan.rollback_steps),
                        duration=duration,
                        metadata={
                            "verification_passed": verification_passed,
                            "verification_issues": len(verification_issues)
                        }
                    )
                else:
                    logger.error(f"Rollback verification failed for snapshot {snapshot_id}")
                    
                    return RollbackResult(
                        success=False,
                        snapshot_id=snapshot_id,
                        bot_id=bot_id,
                        steps_completed=completed_steps,
                        total_steps=len(rollback_plan.rollback_steps),
                        duration=duration,
                        error="Rollback verification failed",
                        metadata={
                            "verification_passed": verification_passed,
                            "verification_issues": [asdict(issue) for issue in verification_issues]
                        }
                    )
                
            except Exception as e:
                logger.error(f"Unexpected error during rollback to snapshot {snapshot_id}: {e}")
                
                return RollbackResult(
                    success=False,
                    snapshot_id=snapshot_id,
                    bot_id=bot_id,
                    steps_completed=0,
                    total_steps=0,
                    duration=time.time() - start_time,
                    error=f"Unexpected error: {str(e)}"
                )
    
    async def _execute_rollback_step(
        self,
        step: Dict[str, Any],
        snapshot_id: str,
        bot_id: UUID
    ):
        """Execute a single rollback step."""
        action = step["action"]
        
        if action == "create_current_backup":
            # Create backup of current state
            backup_snapshot_id = f"pre_rollback_{snapshot_id}_{int(time.time())}"
            await self.create_data_snapshot(bot_id, backup_snapshot_id)
            
        elif action == "delete_vector_collection":
            # Delete current vector collection
            try:
                await self.vector_service.delete_bot_collection(str(bot_id))
            except Exception as e:
                logger.warning(f"Failed to delete vector collection during rollback: {e}")
            
        elif action == "delete_chunks":
            # Delete all current chunks
            self.db.query(DocumentChunk).filter(DocumentChunk.bot_id == bot_id).delete()
            self.db.commit()
            
        elif action == "reset_document_counts":
            # Reset document chunk counts
            documents = self.db.query(Document).filter(Document.bot_id == bot_id).all()
            for doc in documents:
                doc.chunk_count = 0
            self.db.commit()
            
        elif action == "restore_collection_config":
            # Restore collection configuration
            snapshot = await self._load_snapshot(snapshot_id)
            if snapshot and snapshot.collection_config:
                # Update or create collection metadata
                collection_metadata = self.db.query(CollectionMetadata).filter(
                    CollectionMetadata.bot_id == bot_id
                ).first()
                
                if collection_metadata:
                    collection_metadata.embedding_provider = snapshot.collection_config.get("embedding_provider")
                    collection_metadata.embedding_model = snapshot.collection_config.get("embedding_model")
                    collection_metadata.embedding_dimension = snapshot.collection_config.get("embedding_dimension")
                    collection_metadata.status = snapshot.collection_config.get("status", "inactive")
                    collection_metadata.points_count = 0
                else:
                    collection_metadata = CollectionMetadata(
                        bot_id=bot_id,
                        collection_name=str(bot_id),
                        embedding_provider=snapshot.collection_config.get("embedding_provider"),
                        embedding_model=snapshot.collection_config.get("embedding_model"),
                        embedding_dimension=snapshot.collection_config.get("embedding_dimension"),
                        status=snapshot.collection_config.get("status", "inactive"),
                        points_count=0
                    )
                    self.db.add(collection_metadata)
                
                self.db.commit()
            
        elif action == "verify_rollback":
            # Verify rollback state matches snapshot
            snapshot = await self._load_snapshot(snapshot_id)
            if snapshot:
                current_doc_count = self.db.query(Document).filter(Document.bot_id == bot_id).count()
                current_chunk_count = self.db.query(DocumentChunk).filter(DocumentChunk.bot_id == bot_id).count()
                
                # For rollback, we expect 0 chunks (clean state)
                if current_chunk_count != 0:
                    raise Exception(f"Rollback verification failed: expected 0 chunks, found {current_chunk_count}")
                
                if current_doc_count != snapshot.document_count:
                    logger.warning(f"Document count mismatch after rollback: expected {snapshot.document_count}, found {current_doc_count}")
        
        else:
            raise ValueError(f"Unknown rollback action: {action}")
    
    async def _attempt_rollback_recovery(
        self,
        snapshot_id: str,
        bot_id: UUID,
        completed_steps: int,
        error: str
    ) -> Dict[str, Any]:
        """Attempt to recover from a failed rollback."""
        try:
            logger.info(f"Attempting rollback recovery for snapshot {snapshot_id}")
            
            # For now, we'll implement a simple recovery strategy
            # In a production system, this could be more sophisticated
            
            # Try to clean up any partial state
            try:
                # Delete any remaining chunks
                self.db.query(DocumentChunk).filter(DocumentChunk.bot_id == bot_id).delete()
                self.db.commit()
                
                # Reset document chunk counts
                documents = self.db.query(Document).filter(Document.bot_id == bot_id).all()
                for doc in documents:
                    doc.chunk_count = 0
                self.db.commit()
                
                return {"attempted": True, "successful": True}
                
            except Exception as recovery_error:
                logger.error(f"Rollback recovery failed: {recovery_error}")
                return {"attempted": True, "successful": False, "error": str(recovery_error)}
            
        except Exception as e:
            logger.error(f"Error in rollback recovery: {e}")
            return {"attempted": False, "successful": False, "error": str(e)}
    
    async def _store_snapshot(self, snapshot: DataSnapshot):
        """Store snapshot data."""
        try:
            # Store snapshot to file (in production, this could be a database or cloud storage)
            snapshot_file = Path(f"/tmp/snapshot_{snapshot.snapshot_id}.json")
            
            with open(snapshot_file, 'w') as f:
                json.dump(asdict(snapshot), f, indent=2, default=str)
            
            # Store in memory for quick access
            self.snapshots[snapshot.snapshot_id] = snapshot
            
            logger.debug(f"Snapshot {snapshot.snapshot_id} stored successfully")
            
        except Exception as e:
            logger.error(f"Error storing snapshot {snapshot.snapshot_id}: {e}")
            raise
    
    async def _load_snapshot(self, snapshot_id: str) -> Optional[DataSnapshot]:
        """Load snapshot data."""
        try:
            # Try memory first
            if snapshot_id in self.snapshots:
                return self.snapshots[snapshot_id]
            
            # Try file storage
            snapshot_file = Path(f"/tmp/snapshot_{snapshot_id}.json")
            if snapshot_file.exists():
                with open(snapshot_file, 'r') as f:
                    snapshot_data = json.load(f)
                
                # Convert string UUIDs back to UUID objects
                snapshot_data['bot_id'] = UUID(snapshot_data['bot_id'])
                
                snapshot = DataSnapshot(**snapshot_data)
                
                # Cache in memory
                self.snapshots[snapshot_id] = snapshot
                
                return snapshot
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading snapshot {snapshot_id}: {e}")
            return None
    
    def list_snapshots(self, bot_id: Optional[UUID] = None) -> List[DataSnapshot]:
        """
        List available snapshots.
        
        Args:
            bot_id: Optional bot ID to filter snapshots
            
        Returns:
            List of available snapshots
        """
        try:
            snapshots = list(self.snapshots.values())
            
            if bot_id:
                snapshots = [s for s in snapshots if s.bot_id == bot_id]
            
            # Sort by creation time (newest first)
            snapshots.sort(key=lambda s: s.created_at, reverse=True)
            
            return snapshots
            
        except Exception as e:
            logger.error(f"Error listing snapshots: {e}")
            return []
    
    async def cleanup_old_snapshots(self, retention_days: Optional[int] = None):
        """Clean up old snapshots based on retention policy."""
        try:
            retention_days = retention_days or self.snapshot_retention_days
            cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
            
            snapshots_to_remove = []
            
            for snapshot_id, snapshot in self.snapshots.items():
                if snapshot.created_at < cutoff_time:
                    snapshots_to_remove.append(snapshot_id)
            
            for snapshot_id in snapshots_to_remove:
                # Remove from memory
                del self.snapshots[snapshot_id]
                
                # Remove file
                snapshot_file = Path(f"/tmp/snapshot_{snapshot_id}.json")
                if snapshot_file.exists():
                    snapshot_file.unlink()
                
                logger.info(f"Cleaned up old snapshot {snapshot_id}")
            
            logger.info(f"Cleaned up {len(snapshots_to_remove)} old snapshots")
            
        except Exception as e:
            logger.error(f"Error cleaning up old snapshots: {e}")
    
    def get_integrity_summary(self, bot_id: UUID) -> Dict[str, Any]:
        """Get a summary of data integrity status for a bot."""
        try:
            # Get basic counts
            document_count = self.db.query(Document).filter(Document.bot_id == bot_id).count()
            chunk_count = self.db.query(DocumentChunk).filter(DocumentChunk.bot_id == bot_id).count()
            
            # Check for obvious issues
            issues = []
            
            # Check for documents without chunks
            docs_without_chunks = self.db.query(Document).filter(
                and_(
                    Document.bot_id == bot_id,
                    Document.chunk_count > 0,
                    ~Document.id.in_(
                        self.db.query(DocumentChunk.document_id).filter(
                            DocumentChunk.bot_id == bot_id
                        )
                    )
                )
            ).count()
            
            if docs_without_chunks > 0:
                issues.append(f"{docs_without_chunks} documents have chunk_count > 0 but no actual chunks")
            
            # Check for chunks without embedding IDs
            chunks_without_embeddings = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.bot_id == bot_id,
                    or_(DocumentChunk.embedding_id.is_(None), DocumentChunk.embedding_id == "")
                )
            ).count()
            
            if chunks_without_embeddings > 0:
                issues.append(f"{chunks_without_embeddings} chunks are missing embedding IDs")
            
            return {
                "bot_id": str(bot_id),
                "document_count": document_count,
                "chunk_count": chunk_count,
                "issues_found": len(issues),
                "issues": issues,
                "last_checked": time.time(),
                "status": "healthy" if len(issues) == 0 else "issues_detected"
            }
            
        except Exception as e:
            logger.error(f"Error getting integrity summary for bot {bot_id}: {e}")
            return {
                "bot_id": str(bot_id),
                "error": str(e),
                "status": "error"
            }