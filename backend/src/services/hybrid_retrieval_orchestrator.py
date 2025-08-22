"""
Hybrid Retrieval Orchestrator - Intelligent Document Retrieval with Dynamic Context-Aware Switching

This module implements an advanced retrieval system that seamlessly integrates LLM generations
with document retrieval, eliminating the binary limitation of pure LLM or document-only responses.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import numpy as np
from collections import deque

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class RetrievalMode(Enum):
    """Modes of retrieval operation with granular control."""
    PURE_LLM = "pure_llm"  # No document retrieval
    DOCUMENT_ONLY = "document_only"  # Pure document retrieval
    HYBRID_BALANCED = "hybrid_balanced"  # Balanced mix
    HYBRID_LLM_HEAVY = "hybrid_llm_heavy"  # More LLM, less documents
    HYBRID_DOCUMENT_HEAVY = "hybrid_document_heavy"  # More documents, less LLM
    ADAPTIVE = "adaptive"  # System decides based on context
    CONTEXTUAL_ENHANCEMENT = "contextual_enhancement"  # LLM enhances retrieved docs
    FALLBACK_CASCADE = "fallback_cascade"  # Try multiple strategies in sequence


class QueryIntent(Enum):
    """Detected query intents for routing decisions."""
    FACTUAL_LOOKUP = "factual_lookup"
    ANALYTICAL_REASONING = "analytical_reasoning"
    CREATIVE_GENERATION = "creative_generation"
    CONVERSATIONAL = "conversational"
    CLARIFICATION = "clarification"
    SUMMARIZATION = "summarization"
    COMPARISON = "comparison"
    RECOMMENDATION = "recommendation"
    TECHNICAL_EXPLANATION = "technical_explanation"
    FOLLOW_UP = "follow_up"


class InformationDensity(Enum):
    """Information density levels for content analysis."""
    VERY_LOW = 0.0
    LOW = 0.25
    MEDIUM = 0.5
    HIGH = 0.75
    VERY_HIGH = 1.0


@dataclass
class QueryCharacteristics:
    """Comprehensive query characteristics for routing decisions."""
    complexity_score: float  # 0.0 to 1.0
    specificity_score: float  # 0.0 to 1.0
    temporal_relevance: float  # 0.0 to 1.0 (how time-sensitive)
    domain_specificity: float  # 0.0 to 1.0
    intent: QueryIntent
    requires_factual_accuracy: bool
    requires_creative_synthesis: bool
    conversation_depth: int  # Number of previous exchanges
    user_expertise_level: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalDecision:
    """Detailed retrieval decision with rationale."""
    mode: RetrievalMode
    confidence: float  # 0.0 to 1.0
    document_weight: float  # 0.0 to 1.0 (weight given to documents)
    llm_weight: float  # 0.0 to 1.0 (weight given to LLM)
    retrieval_depth: int  # Number of documents to retrieve
    synthesis_strategy: str  # How to combine sources
    rationale: str
    fallback_modes: List[RetrievalMode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HybridResponse:
    """Response from hybrid retrieval system."""
    content: str
    mode_used: RetrievalMode
    sources_used: List[str]  # Document IDs or "LLM"
    confidence_score: float
    information_density: InformationDensity
    processing_time: float
    document_contribution: float  # Percentage from documents
    llm_contribution: float  # Percentage from LLM
    metadata: Dict[str, Any]


@dataclass
class PerformanceMetrics:
    """Performance metrics for strategy optimization."""
    response_quality: float  # 0.0 to 1.0
    user_satisfaction: float  # 0.0 to 1.0
    information_accuracy: float  # 0.0 to 1.0
    response_time: float  # seconds
    cost_efficiency: float  # 0.0 to 1.0
    mode_effectiveness: Dict[RetrievalMode, float]


class AdvancedQueryAnalyzer:
    """Advanced query analysis for intelligent routing decisions."""
    
    def __init__(self):
        """Initialize the advanced query analyzer."""
        self.intent_patterns = self._initialize_intent_patterns()
        self.complexity_indicators = self._initialize_complexity_indicators()
        self.domain_keywords = self._initialize_domain_keywords()
        
    def _initialize_intent_patterns(self) -> Dict[QueryIntent, List[str]]:
        """Initialize intent detection patterns."""
        return {
            QueryIntent.FACTUAL_LOOKUP: [
                "what is", "when did", "where is", "who is", "define",
                "tell me about", "explain what", "list", "name"
            ],
            QueryIntent.ANALYTICAL_REASONING: [
                "why", "how does", "analyze", "evaluate", "assess",
                "what causes", "implications of", "impact of", "reason for"
            ],
            QueryIntent.CREATIVE_GENERATION: [
                "create", "generate", "write", "compose", "design",
                "imagine", "suggest creative", "come up with", "invent"
            ],
            QueryIntent.CONVERSATIONAL: [
                "hello", "hi", "thanks", "okay", "yes", "no",
                "can you", "please", "could you", "would you"
            ],
            QueryIntent.CLARIFICATION: [
                "what do you mean", "can you clarify", "explain further",
                "I don't understand", "be more specific", "elaborate"
            ],
            QueryIntent.SUMMARIZATION: [
                "summarize", "summary", "key points", "main ideas",
                "overview", "brief", "tldr", "in short", "bottom line"
            ],
            QueryIntent.COMPARISON: [
                "compare", "difference between", "versus", "vs",
                "similarities", "contrast", "better than", "pros and cons"
            ],
            QueryIntent.RECOMMENDATION: [
                "recommend", "suggest", "best", "should I", "advice",
                "which one", "optimal", "preferred", "top choice"
            ],
            QueryIntent.TECHNICAL_EXPLANATION: [
                "how to", "steps to", "procedure", "method", "technique",
                "implementation", "configure", "setup", "install"
            ],
            QueryIntent.FOLLOW_UP: [
                "also", "additionally", "furthermore", "what about",
                "how about", "and", "related to", "follow up", "more about"
            ]
        }
    
    def _initialize_complexity_indicators(self) -> Dict[str, float]:
        """Initialize complexity scoring indicators."""
        return {
            "multi_part_question": 0.3,
            "nested_clauses": 0.2,
            "technical_terms": 0.2,
            "abstract_concepts": 0.15,
            "conditional_logic": 0.15,
            "temporal_references": 0.1,
            "quantitative_analysis": 0.1,
            "causal_relationships": 0.15
        }
    
    def _initialize_domain_keywords(self) -> Dict[str, List[str]]:
        """Initialize domain-specific keyword detection."""
        return {
            "technical": ["algorithm", "system", "process", "architecture", "implementation"],
            "business": ["revenue", "strategy", "market", "customer", "competitive"],
            "scientific": ["hypothesis", "experiment", "data", "analysis", "research"],
            "legal": ["contract", "regulation", "compliance", "liability", "jurisdiction"],
            "medical": ["diagnosis", "treatment", "symptoms", "patient", "clinical"]
        }
    
    def analyze_query(
        self,
        query: str,
        conversation_history: List[Dict[str, str]] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> QueryCharacteristics:
        """
        Perform comprehensive query analysis.
        
        Args:
            query: The user query
            conversation_history: Previous conversation messages
            user_profile: User expertise and preferences
            
        Returns:
            QueryCharacteristics with detailed analysis
        """
        query_lower = query.lower().strip()
        
        # Detect intent
        intent = self._detect_intent(query_lower)
        
        # Calculate complexity
        complexity_score = self._calculate_complexity(query_lower)
        
        # Calculate specificity
        specificity_score = self._calculate_specificity(query_lower)
        
        # Assess temporal relevance
        temporal_relevance = self._assess_temporal_relevance(query_lower)
        
        # Determine domain specificity
        domain_specificity = self._determine_domain_specificity(query_lower)
        
        # Check factual accuracy requirements
        requires_factual = self._requires_factual_accuracy(query_lower, intent)
        
        # Check creative synthesis requirements
        requires_creative = self._requires_creative_synthesis(intent)
        
        # Calculate conversation depth
        conversation_depth = len(conversation_history) if conversation_history else 0
        
        # Estimate user expertise
        user_expertise = self._estimate_user_expertise(
            query_lower, user_profile, conversation_history
        )
        
        return QueryCharacteristics(
            complexity_score=complexity_score,
            specificity_score=specificity_score,
            temporal_relevance=temporal_relevance,
            domain_specificity=domain_specificity,
            intent=intent,
            requires_factual_accuracy=requires_factual,
            requires_creative_synthesis=requires_creative,
            conversation_depth=conversation_depth,
            user_expertise_level=user_expertise,
            metadata={
                "query_length": len(query),
                "word_count": len(query.split()),
                "has_technical_terms": self._has_technical_terms(query_lower)
            }
        )
    
    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect the primary intent of the query."""
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query)
            intent_scores[intent] = score
        
        # Return intent with highest score, default to FACTUAL_LOOKUP
        if not intent_scores or max(intent_scores.values()) == 0:
            return QueryIntent.FACTUAL_LOOKUP
        
        return max(intent_scores.items(), key=lambda x: x[1])[0]
    
    def _calculate_complexity(self, query: str) -> float:
        """Calculate query complexity score."""
        complexity = 0.0
        
        # Check for multi-part questions
        if any(indicator in query for indicator in ["and", "also", "additionally", "?"]):
            complexity += self.complexity_indicators["multi_part_question"]
        
        # Check for nested clauses
        if any(word in query for word in ["which", "that", "where", "when", "who"]):
            complexity += self.complexity_indicators["nested_clauses"]
        
        # Check for technical terms
        if self._has_technical_terms(query):
            complexity += self.complexity_indicators["technical_terms"]
        
        # Check for conditional logic
        if any(word in query for word in ["if", "when", "unless", "provided", "assuming"]):
            complexity += self.complexity_indicators["conditional_logic"]
        
        # Check for temporal references
        if any(word in query for word in ["before", "after", "during", "since", "until"]):
            complexity += self.complexity_indicators["temporal_references"]
        
        # Normalize to 0-1 range
        return min(complexity, 1.0)
    
    def _calculate_specificity(self, query: str) -> float:
        """Calculate how specific the query is."""
        specificity_indicators = 0
        
        # Check for specific names, numbers, dates
        import re
        
        # Numbers
        if re.search(r'\d+', query):
            specificity_indicators += 1
        
        # Quoted text
        if '"' in query or "'" in query:
            specificity_indicators += 1
        
        # Proper nouns (simple heuristic - words starting with capital)
        words = query.split()
        if any(word[0].isupper() for word in words if word):
            specificity_indicators += 1
        
        # Specific determiners
        if any(det in query for det in ["this", "that", "these", "those", "specific"]):
            specificity_indicators += 1
        
        # Long query suggests more specificity
        if len(words) > 10:
            specificity_indicators += 1
        
        return min(specificity_indicators / 5.0, 1.0)
    
    def _assess_temporal_relevance(self, query: str) -> float:
        """Assess how time-sensitive the query is."""
        temporal_keywords = [
            "current", "latest", "recent", "today", "now", "updated",
            "2024", "2023", "this year", "this month", "real-time"
        ]
        
        temporal_count = sum(1 for keyword in temporal_keywords if keyword in query)
        return min(temporal_count / 3.0, 1.0)
    
    def _determine_domain_specificity(self, query: str) -> float:
        """Determine how domain-specific the query is."""
        domain_matches = 0
        total_keywords = 0
        
        for domain, keywords in self.domain_keywords.items():
            for keyword in keywords:
                total_keywords += 1
                if keyword in query:
                    domain_matches += 1
        
        if total_keywords == 0:
            return 0.0
        
        return min(domain_matches / 5.0, 1.0)
    
    def _requires_factual_accuracy(self, query: str, intent: QueryIntent) -> bool:
        """Determine if the query requires high factual accuracy."""
        factual_intents = [
            QueryIntent.FACTUAL_LOOKUP,
            QueryIntent.TECHNICAL_EXPLANATION,
            QueryIntent.COMPARISON
        ]
        
        if intent in factual_intents:
            return True
        
        factual_keywords = [
            "accurate", "exact", "precise", "correct", "fact",
            "true", "false", "verify", "confirm", "data"
        ]
        
        return any(keyword in query for keyword in factual_keywords)
    
    def _requires_creative_synthesis(self, intent: QueryIntent) -> bool:
        """Determine if the query requires creative synthesis."""
        creative_intents = [
            QueryIntent.CREATIVE_GENERATION,
            QueryIntent.RECOMMENDATION,
            QueryIntent.ANALYTICAL_REASONING
        ]
        
        return intent in creative_intents
    
    def _has_technical_terms(self, query: str) -> bool:
        """Check if query contains technical terms."""
        technical_indicators = [
            "api", "algorithm", "database", "framework", "protocol",
            "implementation", "architecture", "system", "configuration"
        ]
        
        return any(term in query for term in technical_indicators)
    
    def _estimate_user_expertise(
        self,
        query: str,
        user_profile: Optional[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> float:
        """Estimate user expertise level."""
        if user_profile and "expertise_level" in user_profile:
            return user_profile["expertise_level"]
        
        # Estimate based on query complexity and vocabulary
        expertise_score = 0.0
        
        # Technical vocabulary suggests higher expertise
        if self._has_technical_terms(query):
            expertise_score += 0.3
        
        # Longer, more complex queries suggest expertise
        if len(query.split()) > 15:
            expertise_score += 0.2
        
        # Specific references suggest expertise
        if self._calculate_specificity(query) > 0.5:
            expertise_score += 0.2
        
        # Advanced question patterns
        advanced_patterns = ["implications", "architecture", "optimize", "trade-offs"]
        if any(pattern in query for pattern in advanced_patterns):
            expertise_score += 0.3
        
        return min(expertise_score, 1.0)


class AdaptiveRoutingStrategy:
    """Adaptive routing strategy for optimal retrieval decisions."""
    
    def __init__(self, learning_rate: float = 0.1):
        """
        Initialize adaptive routing strategy.
        
        Args:
            learning_rate: Rate of adaptation based on feedback
        """
        self.learning_rate = learning_rate
        self.performance_history = deque(maxlen=1000)
        self.mode_weights = self._initialize_mode_weights()
        self.strategy_rules = self._initialize_strategy_rules()
        
    def _initialize_mode_weights(self) -> Dict[RetrievalMode, float]:
        """Initialize default weights for retrieval modes."""
        return {
            RetrievalMode.PURE_LLM: 1.0,
            RetrievalMode.DOCUMENT_ONLY: 1.0,
            RetrievalMode.HYBRID_BALANCED: 1.5,
            RetrievalMode.HYBRID_LLM_HEAVY: 1.3,
            RetrievalMode.HYBRID_DOCUMENT_HEAVY: 1.3,
            RetrievalMode.ADAPTIVE: 1.0,
            RetrievalMode.CONTEXTUAL_ENHANCEMENT: 1.2,
            RetrievalMode.FALLBACK_CASCADE: 0.8
        }
    
    def _initialize_strategy_rules(self) -> List[Dict[str, Any]]:
        """Initialize routing strategy rules."""
        return [
            {
                "condition": lambda c: c.intent == QueryIntent.FACTUAL_LOOKUP and c.requires_factual_accuracy,
                "mode": RetrievalMode.HYBRID_DOCUMENT_HEAVY,
                "confidence": 0.9
            },
            {
                "condition": lambda c: c.intent == QueryIntent.CREATIVE_GENERATION,
                "mode": RetrievalMode.HYBRID_LLM_HEAVY,
                "confidence": 0.85
            },
            {
                "condition": lambda c: c.complexity_score > 0.7 and c.domain_specificity > 0.5,
                "mode": RetrievalMode.HYBRID_BALANCED,
                "confidence": 0.8
            },
            {
                "condition": lambda c: c.intent == QueryIntent.CONVERSATIONAL and c.conversation_depth < 2,
                "mode": RetrievalMode.PURE_LLM,
                "confidence": 0.9
            },
            {
                "condition": lambda c: c.intent == QueryIntent.SUMMARIZATION,
                "mode": RetrievalMode.CONTEXTUAL_ENHANCEMENT,
                "confidence": 0.85
            },
            {
                "condition": lambda c: c.temporal_relevance > 0.7,
                "mode": RetrievalMode.HYBRID_LLM_HEAVY,
                "confidence": 0.75
            },
            {
                "condition": lambda c: c.specificity_score > 0.8,
                "mode": RetrievalMode.HYBRID_DOCUMENT_HEAVY,
                "confidence": 0.8
            }
        ]
    
    def determine_retrieval_strategy(
        self,
        characteristics: QueryCharacteristics,
        available_documents: int,
        system_load: float = 0.5
    ) -> RetrievalDecision:
        """
        Determine optimal retrieval strategy based on query characteristics.
        
        Args:
            characteristics: Analyzed query characteristics
            available_documents: Number of available documents
            system_load: Current system load (0.0 to 1.0)
            
        Returns:
            RetrievalDecision with optimal strategy
        """
        # Apply rules-based routing first
        for rule in self.strategy_rules:
            if rule["condition"](characteristics):
                mode = rule["mode"]
                confidence = rule["confidence"]
                
                # Adjust for available documents
                if available_documents == 0 and mode != RetrievalMode.PURE_LLM:
                    mode = RetrievalMode.PURE_LLM
                    confidence *= 0.7
                
                return self._create_decision(
                    mode, confidence, characteristics, available_documents
                )
        
        # Default adaptive strategy
        return self._adaptive_decision(characteristics, available_documents, system_load)
    
    def _create_decision(
        self,
        mode: RetrievalMode,
        confidence: float,
        characteristics: QueryCharacteristics,
        available_documents: int
    ) -> RetrievalDecision:
        """Create a retrieval decision."""
        # Calculate weights based on mode
        doc_weight, llm_weight = self._calculate_weights(mode)
        
        # Determine retrieval depth
        retrieval_depth = self._determine_retrieval_depth(
            mode, characteristics, available_documents
        )
        
        # Determine synthesis strategy
        synthesis_strategy = self._determine_synthesis_strategy(mode, characteristics)
        
        # Generate rationale
        rationale = self._generate_rationale(mode, characteristics)
        
        # Determine fallback modes
        fallback_modes = self._determine_fallbacks(mode)
        
        return RetrievalDecision(
            mode=mode,
            confidence=confidence,
            document_weight=doc_weight,
            llm_weight=llm_weight,
            retrieval_depth=retrieval_depth,
            synthesis_strategy=synthesis_strategy,
            rationale=rationale,
            fallback_modes=fallback_modes,
            metadata={
                "characteristics": characteristics,
                "available_documents": available_documents
            }
        )
    
    def _calculate_weights(self, mode: RetrievalMode) -> Tuple[float, float]:
        """Calculate document and LLM weights for a mode."""
        weights = {
            RetrievalMode.PURE_LLM: (0.0, 1.0),
            RetrievalMode.DOCUMENT_ONLY: (1.0, 0.0),
            RetrievalMode.HYBRID_BALANCED: (0.5, 0.5),
            RetrievalMode.HYBRID_LLM_HEAVY: (0.3, 0.7),
            RetrievalMode.HYBRID_DOCUMENT_HEAVY: (0.7, 0.3),
            RetrievalMode.ADAPTIVE: (0.5, 0.5),  # Will be adjusted
            RetrievalMode.CONTEXTUAL_ENHANCEMENT: (0.6, 0.4),
            RetrievalMode.FALLBACK_CASCADE: (0.4, 0.6)
        }
        
        return weights.get(mode, (0.5, 0.5))
    
    def _determine_retrieval_depth(
        self,
        mode: RetrievalMode,
        characteristics: QueryCharacteristics,
        available_documents: int
    ) -> int:
        """Determine how many documents to retrieve."""
        if mode == RetrievalMode.PURE_LLM:
            return 0
        
        if mode == RetrievalMode.DOCUMENT_ONLY:
            return min(10, available_documents)
        
        # Base depth on complexity and specificity
        base_depth = 5
        
        if characteristics.complexity_score > 0.7:
            base_depth += 3
        
        if characteristics.specificity_score > 0.7:
            base_depth -= 2
        
        if mode == RetrievalMode.HYBRID_DOCUMENT_HEAVY:
            base_depth += 2
        elif mode == RetrievalMode.HYBRID_LLM_HEAVY:
            base_depth -= 2
        
        return max(1, min(base_depth, available_documents))
    
    def _determine_synthesis_strategy(
        self,
        mode: RetrievalMode,
        characteristics: QueryCharacteristics
    ) -> str:
        """Determine how to synthesize information."""
        if mode == RetrievalMode.PURE_LLM:
            return "llm_generation"
        
        if mode == RetrievalMode.DOCUMENT_ONLY:
            return "document_extraction"
        
        if mode == RetrievalMode.CONTEXTUAL_ENHANCEMENT:
            return "llm_enhanced_documents"
        
        if characteristics.intent == QueryIntent.SUMMARIZATION:
            return "extractive_summarization"
        
        if characteristics.intent == QueryIntent.COMPARISON:
            return "comparative_synthesis"
        
        if characteristics.requires_creative_synthesis:
            return "creative_blending"
        
        return "weighted_combination"
    
    def _generate_rationale(
        self,
        mode: RetrievalMode,
        characteristics: QueryCharacteristics
    ) -> str:
        """Generate human-readable rationale for the decision."""
        rationale_parts = []
        
        rationale_parts.append(f"Selected {mode.value} mode")
        
        if characteristics.complexity_score > 0.7:
            rationale_parts.append("due to high query complexity")
        
        if characteristics.requires_factual_accuracy:
            rationale_parts.append("requiring factual accuracy from documents")
        
        if characteristics.requires_creative_synthesis:
            rationale_parts.append("requiring creative synthesis from LLM")
        
        if characteristics.domain_specificity > 0.5:
            rationale_parts.append(f"with domain-specific content (score: {characteristics.domain_specificity:.2f})")
        
        return "; ".join(rationale_parts)
    
    def _determine_fallbacks(self, primary_mode: RetrievalMode) -> List[RetrievalMode]:
        """Determine fallback modes if primary fails."""
        fallback_map = {
            RetrievalMode.HYBRID_BALANCED: [
                RetrievalMode.HYBRID_LLM_HEAVY,
                RetrievalMode.PURE_LLM
            ],
            RetrievalMode.HYBRID_DOCUMENT_HEAVY: [
                RetrievalMode.HYBRID_BALANCED,
                RetrievalMode.DOCUMENT_ONLY
            ],
            RetrievalMode.HYBRID_LLM_HEAVY: [
                RetrievalMode.PURE_LLM,
                RetrievalMode.HYBRID_BALANCED
            ],
            RetrievalMode.DOCUMENT_ONLY: [
                RetrievalMode.HYBRID_DOCUMENT_HEAVY,
                RetrievalMode.HYBRID_BALANCED
            ],
            RetrievalMode.CONTEXTUAL_ENHANCEMENT: [
                RetrievalMode.HYBRID_BALANCED,
                RetrievalMode.PURE_LLM
            ]
        }
        
        return fallback_map.get(primary_mode, [RetrievalMode.PURE_LLM])
    
    def _adaptive_decision(
        self,
        characteristics: QueryCharacteristics,
        available_documents: int,
        system_load: float
    ) -> RetrievalDecision:
        """Make adaptive decision based on learned weights and system state."""
        # Score each mode based on characteristics and history
        mode_scores = {}
        
        for mode, weight in self.mode_weights.items():
            score = weight
            
            # Adjust for document availability
            if available_documents == 0 and mode != RetrievalMode.PURE_LLM:
                score *= 0.1
            
            # Adjust for system load
            if system_load > 0.8:
                # Prefer lighter modes under high load
                if mode in [RetrievalMode.PURE_LLM, RetrievalMode.DOCUMENT_ONLY]:
                    score *= 1.2
            
            # Adjust based on characteristics
            if characteristics.requires_factual_accuracy:
                if mode in [RetrievalMode.DOCUMENT_ONLY, RetrievalMode.HYBRID_DOCUMENT_HEAVY]:
                    score *= 1.3
            
            if characteristics.requires_creative_synthesis:
                if mode in [RetrievalMode.PURE_LLM, RetrievalMode.HYBRID_LLM_HEAVY]:
                    score *= 1.3
            
            mode_scores[mode] = score
        
        # Select mode with highest score
        best_mode = max(mode_scores.items(), key=lambda x: x[1])[0]
        confidence = min(mode_scores[best_mode] / sum(mode_scores.values()) * 2, 1.0)
        
        return self._create_decision(
            best_mode, confidence, characteristics, available_documents
        )
    
    def update_weights(self, mode: RetrievalMode, performance: float):
        """
        Update mode weights based on performance feedback.
        
        Args:
            mode: The mode that was used
            performance: Performance score (0.0 to 1.0)
        """
        current_weight = self.mode_weights[mode]
        
        # Simple exponential moving average update
        self.mode_weights[mode] = (
            (1 - self.learning_rate) * current_weight +
            self.learning_rate * performance * 2  # Scale performance
        )
        
        # Record for analysis
        self.performance_history.append({
            "mode": mode,
            "performance": performance,
            "timestamp": time.time()
        })


class ResponseBlender:
    """Intelligent response blending for seamless integration."""
    
    def __init__(self):
        """Initialize response blender."""
        self.blending_strategies = self._initialize_strategies()
        
    def _initialize_strategies(self) -> Dict[str, callable]:
        """Initialize blending strategies."""
        return {
            "weighted_combination": self._weighted_combination,
            "llm_enhanced_documents": self._llm_enhanced_documents,
            "document_extraction": self._document_extraction,
            "extractive_summarization": self._extractive_summarization,
            "comparative_synthesis": self._comparative_synthesis,
            "creative_blending": self._creative_blending,
            "llm_generation": self._llm_generation
        }
    
    async def blend_responses(
        self,
        llm_response: Optional[str],
        document_chunks: List[Dict[str, Any]],
        decision: RetrievalDecision,
        query: str
    ) -> HybridResponse:
        """
        Blend LLM and document responses based on decision.
        
        Args:
            llm_response: Response from LLM
            document_chunks: Retrieved document chunks
            decision: Retrieval decision
            query: Original query
            
        Returns:
            HybridResponse with blended content
        """
        start_time = time.time()
        
        # Get blending strategy
        strategy_func = self.blending_strategies.get(
            decision.synthesis_strategy,
            self._weighted_combination
        )
        
        # Apply blending strategy
        blended_content = await strategy_func(
            llm_response, document_chunks, decision, query
        )
        
        # Calculate contributions
        doc_contribution, llm_contribution = self._calculate_contributions(
            blended_content, llm_response, document_chunks
        )
        
        # Assess information density
        info_density = self._assess_information_density(blended_content)
        
        # Determine sources used
        sources = self._determine_sources(llm_response, document_chunks)
        
        processing_time = time.time() - start_time
        
        return HybridResponse(
            content=blended_content,
            mode_used=decision.mode,
            sources_used=sources,
            confidence_score=decision.confidence,
            information_density=info_density,
            processing_time=processing_time,
            document_contribution=doc_contribution,
            llm_contribution=llm_contribution,
            metadata={
                "synthesis_strategy": decision.synthesis_strategy,
                "document_count": len(document_chunks),
                "query_length": len(query)
            }
        )
    
    async def _weighted_combination(
        self,
        llm_response: Optional[str],
        document_chunks: List[Dict[str, Any]],
        decision: RetrievalDecision,
        query: str
    ) -> str:
        """Combine responses using weighted approach."""
        if not llm_response and not document_chunks:
            return "Unable to generate response."
        
        if not document_chunks:
            return llm_response or ""
        
        if not llm_response:
            return self._format_document_response(document_chunks)
        
        # Extract key information from documents
        doc_info = self._extract_key_information(document_chunks)
        
        # Blend based on weights
        if decision.document_weight > 0.7:
            # Document-heavy: Use documents as primary, LLM for coherence
            return self._document_focused_blend(doc_info, llm_response)
        elif decision.llm_weight > 0.7:
            # LLM-heavy: Use LLM as primary, documents for support
            return self._llm_focused_blend(llm_response, doc_info)
        else:
            # Balanced: Interweave both sources
            return self._balanced_blend(llm_response, doc_info)
    
    async def _llm_enhanced_documents(
        self,
        llm_response: Optional[str],
        document_chunks: List[Dict[str, Any]],
        decision: RetrievalDecision,
        query: str
    ) -> str:
        """Use LLM to enhance and explain document content."""
        if not document_chunks:
            return llm_response or "No relevant documents found."
        
        doc_content = self._format_document_response(document_chunks)
        
        if llm_response:
            # Combine LLM interpretation with document facts
            enhanced = f"{llm_response}\n\n**Supporting Information:**\n{doc_content}"
        else:
            enhanced = doc_content
        
        return enhanced
    
    async def _document_extraction(
        self,
        llm_response: Optional[str],
        document_chunks: List[Dict[str, Any]],
        decision: RetrievalDecision,
        query: str
    ) -> str:
        """Pure document extraction without LLM synthesis."""
        if not document_chunks:
            return "No relevant documents found."
        
        return self._format_document_response(document_chunks)
    
    async def _extractive_summarization(
        self,
        llm_response: Optional[str],
        document_chunks: List[Dict[str, Any]],
        decision: RetrievalDecision,
        query: str
    ) -> str:
        """Create extractive summary from documents with optional LLM enhancement."""
        if not document_chunks:
            return llm_response or "No documents to summarize."
        
        # Extract key sentences from documents
        key_sentences = self._extract_key_sentences(document_chunks)
        
        summary = "Summary of relevant information:\n\n"
        for i, sentence in enumerate(key_sentences[:5], 1):
            summary += f"{i}. {sentence}\n"
        
        if llm_response:
            summary += f"\n**Analysis:** {llm_response}"
        
        return summary
    
    async def _comparative_synthesis(
        self,
        llm_response: Optional[str],
        document_chunks: List[Dict[str, Any]],
        decision: RetrievalDecision,
        query: str
    ) -> str:
        """Synthesize comparative analysis from multiple sources."""
        if not document_chunks:
            return llm_response or "No documents for comparison."
        
        # Group documents by perspective/source
        grouped = self._group_by_source(document_chunks)
        
        comparison = "Comparative Analysis:\n\n"
        
        for source, chunks in grouped.items():
            key_points = self._extract_key_points(chunks)
            comparison += f"**{source}:**\n"
            for point in key_points[:3]:
                comparison += f"• {point}\n"
            comparison += "\n"
        
        if llm_response:
            comparison += f"**Synthesis:** {llm_response}"
        
        return comparison
    
    async def _creative_blending(
        self,
        llm_response: Optional[str],
        document_chunks: List[Dict[str, Any]],
        decision: RetrievalDecision,
        query: str
    ) -> str:
        """Creative blending of LLM and document content."""
        if not llm_response:
            return self._format_document_response(document_chunks) if document_chunks else ""
        
        if not document_chunks:
            return llm_response
        
        # Extract facts from documents
        facts = self._extract_facts(document_chunks)
        
        # Creatively integrate facts into LLM response
        enhanced_response = llm_response
        
        # Add factual support where appropriate
        if facts:
            enhanced_response += "\n\n**Key Facts:**\n"
            for fact in facts[:3]:
                enhanced_response += f"• {fact}\n"
        
        return enhanced_response
    
    async def _llm_generation(
        self,
        llm_response: Optional[str],
        document_chunks: List[Dict[str, Any]],
        decision: RetrievalDecision,
        query: str
    ) -> str:
        """Pure LLM generation without document support."""
        return llm_response or "Unable to generate response."
    
    def _extract_key_information(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Extract key information from document chunks."""
        key_info = []
        
        for chunk in chunks[:5]:  # Limit to top 5 chunks
            text = chunk.get("text", "")
            # Simple extraction - in production, use NLP techniques
            sentences = text.split(".")
            for sentence in sentences:
                if len(sentence.strip()) > 20:  # Filter short sentences
                    key_info.append(sentence.strip() + ".")
                    if len(key_info) >= 5:
                        break
        
        return key_info
    
    def _document_focused_blend(self, doc_info: List[str], llm_response: str) -> str:
        """Create document-focused blend."""
        response = "Based on the available documents:\n\n"
        
        for info in doc_info[:3]:
            response += f"• {info}\n"
        
        if llm_response:
            response += f"\n{llm_response}"
        
        return response
    
    def _llm_focused_blend(self, llm_response: str, doc_info: List[str]) -> str:
        """Create LLM-focused blend."""
        response = llm_response
        
        if doc_info:
            response += "\n\n**Additional Context from Documents:**\n"
            for info in doc_info[:2]:
                response += f"• {info}\n"
        
        return response
    
    def _balanced_blend(self, llm_response: str, doc_info: List[str]) -> str:
        """Create balanced blend of both sources."""
        # Split LLM response into paragraphs
        llm_parts = llm_response.split("\n\n")
        
        response = ""
        
        # Interweave LLM and document content
        for i, part in enumerate(llm_parts):
            response += part
            
            if i < len(doc_info):
                response += f"\n\n[From documents: {doc_info[i]}]\n\n"
        
        # Add remaining document info if any
        for remaining in doc_info[len(llm_parts):]:
            response += f"\n• {remaining}"
        
        return response
    
    def _format_document_response(self, chunks: List[Dict[str, Any]]) -> str:
        """Format document chunks into readable response."""
        if not chunks:
            return ""
        
        response = "Relevant information from documents:\n\n"
        
        for i, chunk in enumerate(chunks[:5], 1):
            text = chunk.get("text", "").strip()
            if text:
                response += f"{i}. {text[:500]}...\n\n" if len(text) > 500 else f"{i}. {text}\n\n"
        
        return response.strip()
    
    def _extract_key_sentences(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Extract key sentences from chunks."""
        sentences = []
        
        for chunk in chunks:
            text = chunk.get("text", "")
            chunk_sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
            sentences.extend(chunk_sentences[:2])  # Take top 2 from each chunk
        
        return sentences[:10]  # Return top 10 overall
    
    def _group_by_source(self, chunks: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Group chunks by their source document."""
        grouped = {}
        
        for chunk in chunks:
            source = chunk.get("metadata", {}).get("document_id", "Unknown")
            if source not in grouped:
                grouped[source] = []
            grouped[source].append(chunk)
        
        return grouped
    
    def _extract_key_points(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Extract key points from chunks."""
        points = []
        
        for chunk in chunks:
            text = chunk.get("text", "")
            # Simple extraction - look for bullet points or numbered items
            lines = text.split("\n")
            for line in lines:
                if line.strip().startswith(("•", "-", "*", "1", "2", "3")):
                    points.append(line.strip())
        
        return points[:5]
    
    def _extract_facts(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Extract factual statements from chunks."""
        facts = []
        
        for chunk in chunks:
            text = chunk.get("text", "")
            sentences = text.split(".")
            
            for sentence in sentences:
                # Simple heuristic for facts - contains numbers or specific terms
                if any(char.isdigit() for char in sentence) or any(
                    term in sentence.lower() for term in ["is", "are", "was", "were", "defined as"]
                ):
                    facts.append(sentence.strip() + ".")
        
        return facts[:5]
    
    def _calculate_contributions(
        self,
        blended: str,
        llm_response: Optional[str],
        chunks: List[Dict[str, Any]]
    ) -> Tuple[float, float]:
        """Calculate relative contributions of documents and LLM."""
        if not blended:
            return 0.0, 0.0
        
        total_length = len(blended)
        
        # Simple heuristic - check overlap
        doc_contribution = 0.0
        llm_contribution = 0.0
        
        if chunks:
            doc_text = " ".join(chunk.get("text", "") for chunk in chunks)
            # Check word overlap
            doc_words = set(doc_text.lower().split())
            blended_words = set(blended.lower().split())
            doc_overlap = len(doc_words & blended_words) / len(blended_words) if blended_words else 0
            doc_contribution = min(doc_overlap * 1.5, 1.0)  # Scale up
        
        if llm_response:
            llm_words = set(llm_response.lower().split())
            blended_words = set(blended.lower().split())
            llm_overlap = len(llm_words & blended_words) / len(blended_words) if blended_words else 0
            llm_contribution = min(llm_overlap * 1.5, 1.0)  # Scale up
        
        # Normalize
        total = doc_contribution + llm_contribution
        if total > 0:
            doc_contribution /= total
            llm_contribution /= total
        
        return doc_contribution, llm_contribution
    
    def _assess_information_density(self, content: str) -> InformationDensity:
        """Assess information density of content."""
        if not content:
            return InformationDensity.VERY_LOW
        
        # Simple heuristics
        word_count = len(content.split())
        
        # Check for specific indicators
        has_numbers = any(char.isdigit() for char in content)
        has_lists = any(marker in content for marker in ["•", "-", "1.", "2."])
        has_technical = any(
            term in content.lower() 
            for term in ["algorithm", "system", "process", "method", "technique"]
        )
        
        density_score = 0.0
        
        if word_count > 200:
            density_score += 0.3
        if has_numbers:
            density_score += 0.2
        if has_lists:
            density_score += 0.2
        if has_technical:
            density_score += 0.3
        
        if density_score >= 0.8:
            return InformationDensity.VERY_HIGH
        elif density_score >= 0.6:
            return InformationDensity.HIGH
        elif density_score >= 0.4:
            return InformationDensity.MEDIUM
        elif density_score >= 0.2:
            return InformationDensity.LOW
        else:
            return InformationDensity.VERY_LOW
    
    def _determine_sources(
        self,
        llm_response: Optional[str],
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """Determine which sources were used."""
        sources = []
        
        if llm_response:
            sources.append("LLM")
        
        for chunk in chunks:
            doc_id = chunk.get("metadata", {}).get("document_id", "Unknown")
            if doc_id not in sources:
                sources.append(doc_id)
        
        return sources


class HybridRetrievalOrchestrator:
    """
    Main orchestrator for hybrid retrieval system.
    Coordinates all components for seamless LLM-document integration.
    """
    
    def __init__(
        self,
        db: Session,
        vector_service: Any,
        llm_service: Any,
        embedding_service: Any
    ):
        """
        Initialize the hybrid retrieval orchestrator.
        
        Args:
            db: Database session
            vector_service: Vector store service
            llm_service: LLM service
            embedding_service: Embedding service
        """
        self.db = db
        self.vector_service = vector_service
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        
        # Initialize components
        self.query_analyzer = AdvancedQueryAnalyzer()
        self.routing_strategy = AdaptiveRoutingStrategy()
        self.response_blender = ResponseBlender()
        
        # Performance tracking
        self.performance_metrics = []
        
        # Configuration
        self.config = {
            "enable_adaptive_learning": True,
            "enable_fallback": True,
            "max_retrieval_time": 10.0,  # seconds
            "enable_caching": True
        }
    
    async def process_query(
        self,
        query: str,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> HybridResponse:
        """
        Process query through hybrid retrieval system.
        
        Args:
            query: User query
            bot_id: Bot identifier
            user_id: User identifier
            conversation_history: Previous conversation
            user_profile: User profile information
            
        Returns:
            HybridResponse with intelligently blended content
        """
        start_time = time.time()
        
        try:
            # Step 1: Analyze query characteristics
            characteristics = self.query_analyzer.analyze_query(
                query, conversation_history, user_profile
            )
            
            logger.info(f"Query analysis: intent={characteristics.intent.value}, "
                       f"complexity={characteristics.complexity_score:.2f}")
            
            # Step 2: Check document availability
            available_documents = await self._get_available_documents(bot_id)
            
            # Step 3: Determine retrieval strategy
            system_load = await self._get_system_load()
            decision = self.routing_strategy.determine_retrieval_strategy(
                characteristics, available_documents, system_load
            )
            
            logger.info(f"Retrieval decision: mode={decision.mode.value}, "
                       f"confidence={decision.confidence:.2f}")
            
            # Step 4: Execute retrieval strategy
            llm_response, document_chunks = await self._execute_retrieval(
                query, bot_id, user_id, decision, characteristics
            )
            
            # Step 5: Blend responses
            hybrid_response = await self.response_blender.blend_responses(
                llm_response, document_chunks, decision, query
            )
            
            # Step 6: Track performance
            if self.config["enable_adaptive_learning"]:
                await self._track_performance(decision, hybrid_response, start_time)
            
            return hybrid_response
            
        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            
            # Fallback to pure LLM if enabled
            if self.config["enable_fallback"]:
                return await self._fallback_response(query, bot_id, user_id, str(e))
            
            raise
    
    async def _get_available_documents(self, bot_id: uuid.UUID) -> int:
        """Get count of available documents for bot."""
        try:
            from ..models.document import Document
            count = self.db.query(Document).filter(Document.bot_id == bot_id).count()
            return count
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0
    
    async def _get_system_load(self) -> float:
        """Get current system load (simplified)."""
        # In production, this would check actual system metrics
        return 0.5
    
    async def _execute_retrieval(
        self,
        query: str,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        decision: RetrievalDecision,
        characteristics: QueryCharacteristics
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """Execute the retrieval strategy."""
        llm_response = None
        document_chunks = []
        
        # Handle different retrieval modes
        if decision.mode == RetrievalMode.PURE_LLM:
            llm_response = await self._get_llm_response(query, bot_id, user_id)
            
        elif decision.mode == RetrievalMode.DOCUMENT_ONLY:
            document_chunks = await self._retrieve_documents(
                query, bot_id, user_id, decision.retrieval_depth
            )
            
        elif decision.mode in [
            RetrievalMode.HYBRID_BALANCED,
            RetrievalMode.HYBRID_LLM_HEAVY,
            RetrievalMode.HYBRID_DOCUMENT_HEAVY,
            RetrievalMode.CONTEXTUAL_ENHANCEMENT
        ]:
            # Parallel retrieval for efficiency
            llm_task = self._get_llm_response(query, bot_id, user_id)
            doc_task = self._retrieve_documents(
                query, bot_id, user_id, decision.retrieval_depth
            )
            
            llm_response, document_chunks = await asyncio.gather(
                llm_task, doc_task, return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(llm_response, Exception):
                logger.error(f"LLM retrieval error: {llm_response}")
                llm_response = None
            
            if isinstance(document_chunks, Exception):
                logger.error(f"Document retrieval error: {document_chunks}")
                document_chunks = []
                
        elif decision.mode == RetrievalMode.FALLBACK_CASCADE:
            # Try modes in sequence
            for fallback_mode in [decision.mode] + decision.fallback_modes:
                try:
                    if fallback_mode in [RetrievalMode.PURE_LLM, RetrievalMode.HYBRID_LLM_HEAVY]:
                        llm_response = await self._get_llm_response(query, bot_id, user_id)
                        if llm_response:
                            break
                    else:
                        document_chunks = await self._retrieve_documents(
                            query, bot_id, user_id, decision.retrieval_depth
                        )
                        if document_chunks:
                            break
                except Exception as e:
                    logger.warning(f"Fallback mode {fallback_mode} failed: {e}")
                    continue
        
        return llm_response, document_chunks
    
    async def _get_llm_response(
        self,
        query: str,
        bot_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[str]:
        """Get response from LLM."""
        try:
            # This would integrate with your existing LLM service
            # Simplified for demonstration
            return f"LLM response to: {query}"
        except Exception as e:
            logger.error(f"LLM response error: {e}")
            return None
    
    async def _retrieve_documents(
        self,
        query: str,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents."""
        try:
            # This would integrate with your existing vector service
            # Simplified for demonstration
            return []
        except Exception as e:
            logger.error(f"Document retrieval error: {e}")
            return []
    
    async def _track_performance(
        self,
        decision: RetrievalDecision,
        response: HybridResponse,
        start_time: float
    ):
        """Track performance metrics for adaptive learning."""
        processing_time = time.time() - start_time
        
        # Simple performance estimation (would use actual metrics in production)
        performance_score = 0.7  # Base score
        
        # Adjust based on response characteristics
        if response.confidence_score > 0.8:
            performance_score += 0.1
        
        if processing_time < 2.0:
            performance_score += 0.1
        
        if response.information_density in [InformationDensity.HIGH, InformationDensity.VERY_HIGH]:
            performance_score += 0.1
        
        performance_score = min(performance_score, 1.0)
        
        # Update routing strategy weights
        self.routing_strategy.update_weights(decision.mode, performance_score)
        
        # Store metrics
        self.performance_metrics.append({
            "mode": decision.mode,
            "performance": performance_score,
            "processing_time": processing_time,
            "timestamp": time.time()
        })
    
    async def _fallback_response(
        self,
        query: str,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        error: str
    ) -> HybridResponse:
        """Generate fallback response."""
        return HybridResponse(
            content=f"I'll do my best to help with your query: {query}",
            mode_used=RetrievalMode.PURE_LLM,
            sources_used=["LLM"],
            confidence_score=0.5,
            information_density=InformationDensity.LOW,
            processing_time=0.0,
            document_contribution=0.0,
            llm_contribution=1.0,
            metadata={"fallback": True, "error": error}
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring."""
        if not self.performance_metrics:
            return {"status": "no_data"}
        
        # Calculate aggregates
        mode_performances = {}
        for metric in self.performance_metrics:
            mode = metric["mode"]
            if mode not in mode_performances:
                mode_performances[mode] = []
            mode_performances[mode].append(metric["performance"])
        
        summary = {
            "total_queries": len(self.performance_metrics),
            "average_performance": np.mean([m["performance"] for m in self.performance_metrics]),
            "average_processing_time": np.mean([m["processing_time"] for m in self.performance_metrics]),
            "mode_effectiveness": {
                mode.value: np.mean(scores)
                for mode, scores in mode_performances.items()
            }
        }
        
        return summary
