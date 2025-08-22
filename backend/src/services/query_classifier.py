"""
Query classifier service to determine when RAG retrieval is needed.

This service analyzes user queries to intelligently decide whether document
retrieval is necessary or if the LLM can answer directly from its knowledge.
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries that help determine retrieval necessity."""
    DOCUMENT_SPECIFIC = "document_specific"  # Needs document retrieval
    GENERAL_KNOWLEDGE = "general_knowledge"  # Can answer without docs
    CONVERSATIONAL = "conversational"  # Chat/greeting, no docs needed
    FOLLOW_UP = "follow_up"  # May need docs based on context
    ANALYTICAL = "analytical"  # Likely needs docs for analysis
    FACTUAL = "factual"  # May or may not need docs


@dataclass
class RetrievalDecision:
    """Decision about whether to retrieve documents."""
    should_retrieve: bool
    confidence: float  # 0.0 to 1.0
    query_type: QueryType
    reasoning: str
    metadata: Dict[str, Any]


class QueryClassifier:
    """Intelligent query classifier for RAG retrieval decisions."""
    
    def __init__(self):
        """Initialize the query classifier with patterns and rules."""
        self.setup_patterns()
        self.setup_keywords()
        
    def setup_patterns(self):
        """Setup regex patterns for different query types."""
        self.patterns = {
            # Document-specific patterns - high retrieval probability
            'document_reference': [
                r'(?i)\b(?:according to|based on|in the|from the|what does.*say)\b.*\b(?:document|file|paper|report|manual|guide)\b',
                r'(?i)\b(?:document|file|report|manual|guide)\b.*\b(?:states|says|mentions|contains|describes)\b',
                r'(?i)\bwhat.*(?:document|file|report|manual|guide)\b',
                r'(?i)\b(?:quote|cite|reference|excerpt)\b.*from',
                r'(?i)\bfind.*in.*(?:document|file|report|manual|guide)\b'
            ],
            
            # General knowledge patterns - low retrieval probability  
            'general_knowledge': [
                r'(?i)\b(?:what is|what are|define|explain|tell me about)\b.*\b(?:general|common|basic|typical|usually|normally)\b',
                r'(?i)\b(?:how do|how does|how can|why do|why does)\b.*\b(?:in general|typically|usually|commonly)\b',
                r'(?i)\b(?:general|basic|common|typical|standard|universal|widespread)\b.*\b(?:concept|principle|idea|approach|method)\b'
            ],
            
            # Conversational patterns - very low retrieval probability
            'conversational': [
                r'(?i)\b(?:hello|hi|hey|good morning|good afternoon|good evening|greetings)\b',
                r'(?i)\b(?:how are you|how\'s it going|what\'s up|how do you do)\b',
                r'(?i)\b(?:thank you|thanks|appreciate|grateful)\b',
                r'(?i)\b(?:goodbye|bye|see you|farewell|talk to you later)\b',
                r'(?i)\b(?:please|could you|would you|can you help)\b.*\b(?:with|me)\b',
                r'(?i)\b(?:sorry|excuse me|pardon|my apologies)\b'
            ],
            
            # Analytical patterns - high retrieval probability
            'analytical': [
                r'(?i)\b(?:analyze|compare|contrast|evaluate|assess|examine)\b',
                r'(?i)\b(?:what are the differences|similarities|pros and cons|advantages and disadvantages)\b',
                r'(?i)\b(?:summarize|summary|overview|key points|main ideas)\b',
                r'(?i)\b(?:trend|pattern|insight|finding|conclusion|recommendation)\b.*\b(?:from|in|based on)\b'
            ],
            
            # Specific question patterns - medium to high retrieval probability
            'specific_inquiry': [
                r'(?i)\bwhat\s+(?:is|are|was|were|does|do|did)\b.*\b(?:specific|exactly|precisely|particularly)\b',
                r'(?i)\b(?:list|provide|give me|show me|tell me)\b.*\b(?:details|specifics|examples|cases)\b',
                r'(?i)\b(?:how many|how much|when|where|who|which)\b.*\b(?:in|from|according to)\b'
            ]
        }
    
    def setup_keywords(self):
        """Setup keyword lists for different categories."""
        self.keywords = {
            # Keywords that suggest document retrieval is needed
            'document_indicators': {
                'high_confidence': [
                    'document', 'file', 'report', 'manual', 'guide', 'paper', 'study',
                    'specification', 'procedure', 'policy', 'contract', 'agreement',
                    'according to', 'based on', 'mentioned in', 'states that', 'says that'
                ],
                'medium_confidence': [
                    'data', 'information', 'details', 'specifics', 'examples', 'cases',
                    'requirements', 'guidelines', 'instructions', 'steps', 'process'
                ]
            },
            
            # Keywords that suggest general knowledge response
            'general_knowledge_indicators': [
                'general', 'common', 'basic', 'typical', 'standard', 'universal',
                'what is', 'what are', 'define', 'explain', 'concept', 'principle',
                'how does', 'why does', 'theory', 'meaning', 'definition'
            ],
            
            # Conversational keywords
            'conversational_indicators': [
                'hello', 'hi', 'hey', 'thanks', 'thank you', 'please', 'help me',
                'can you', 'would you', 'could you', 'sorry', 'excuse me'
            ],
            
            # Analytical keywords
            'analytical_indicators': [
                'analyze', 'compare', 'contrast', 'evaluate', 'assess', 'examine',
                'summarize', 'overview', 'key points', 'main ideas', 'insights',
                'trends', 'patterns', 'conclusions', 'recommendations'
            ]
        }
    
    def classify_query(
        self, 
        query: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None,
        has_documents: bool = True
    ) -> RetrievalDecision:
        """
        Classify a query and decide whether document retrieval is needed.
        
        Args:
            query: The user's query
            conversation_history: Recent conversation context
            has_documents: Whether the bot has documents uploaded
            
        Returns:
            RetrievalDecision with retrieval recommendation and reasoning
        """
        # If no documents available, never retrieve
        if not has_documents:
            return RetrievalDecision(
                should_retrieve=False,
                confidence=1.0,
                query_type=QueryType.GENERAL_KNOWLEDGE,
                reasoning="No documents available for retrieval",
                metadata={"has_documents": False}
            )
        
        # Analyze query characteristics
        query_lower = query.lower().strip()
        
        # Check for empty or very short queries
        if len(query_lower) < 3:
            return RetrievalDecision(
                should_retrieve=False,
                confidence=0.9,
                query_type=QueryType.CONVERSATIONAL,
                reasoning="Query too short to warrant document retrieval",
                metadata={"query_length": len(query_lower)}
            )
        
        # Pattern-based analysis
        pattern_scores = self._analyze_patterns(query_lower)
        
        # Keyword-based analysis
        keyword_scores = self._analyze_keywords(query_lower)
        
        # Contextual analysis
        context_score = self._analyze_context(query_lower, conversation_history)
        
        # Combine scores and make decision
        decision = self._make_retrieval_decision(
            query, pattern_scores, keyword_scores, context_score
        )
        
        return decision
    
    def _analyze_patterns(self, query: str) -> Dict[str, float]:
        """Analyze query using regex patterns."""
        scores = {}
        
        for category, patterns in self.patterns.items():
            score = 0.0
            matches = []
            
            for pattern in patterns:
                if re.search(pattern, query):
                    score += 1.0
                    matches.append(pattern)
            
            # Normalize score
            if patterns:
                score = min(score / len(patterns), 1.0)
            
            scores[category] = {
                'score': score,
                'matches': matches
            }
        
        return scores
    
    def _analyze_keywords(self, query: str) -> Dict[str, float]:
        """Analyze query using keyword matching."""
        scores = {}
        
        # Document indicators (promote retrieval)
        doc_score = 0.0
        doc_matches = []
        
        for keyword in self.keywords['document_indicators']['high_confidence']:
            if keyword.lower() in query:
                doc_score += 2.0
                doc_matches.append(keyword)
        
        for keyword in self.keywords['document_indicators']['medium_confidence']:
            if keyword.lower() in query:
                doc_score += 1.0
                doc_matches.append(keyword)
        
        scores['document_indicators'] = {
            'score': min(doc_score / 10.0, 1.0),  # Normalize
            'matches': doc_matches
        }
        
        # General knowledge indicators (reduce retrieval)
        gen_score = 0.0
        gen_matches = []
        
        for keyword in self.keywords['general_knowledge_indicators']:
            if keyword.lower() in query:
                gen_score += 1.0
                gen_matches.append(keyword)
        
        scores['general_knowledge'] = {
            'score': min(gen_score / 5.0, 1.0),  # Normalize
            'matches': gen_matches
        }
        
        # Conversational indicators (reduce retrieval)
        conv_score = 0.0
        conv_matches = []
        
        for keyword in self.keywords['conversational_indicators']:
            if keyword.lower() in query:
                conv_score += 1.0
                conv_matches.append(keyword)
        
        scores['conversational'] = {
            'score': min(conv_score / 3.0, 1.0),  # Normalize
            'matches': conv_matches
        }
        
        # Analytical indicators (promote retrieval)
        anal_score = 0.0
        anal_matches = []
        
        for keyword in self.keywords['analytical_indicators']:
            if keyword.lower() in query:
                anal_score += 1.0
                anal_matches.append(keyword)
        
        scores['analytical'] = {
            'score': min(anal_score / 5.0, 1.0),  # Normalize
            'matches': anal_matches
        }
        
        return scores
    
    def _analyze_context(
        self, 
        query: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Analyze conversational context to inform retrieval decision."""
        context = {
            'is_follow_up': False,
            'previous_rag_used': False,
            'conversation_length': 0,
            'recent_topics': []
        }
        
        if not conversation_history:
            return context
        
        context['conversation_length'] = len(conversation_history)
        
        # Check if this seems like a follow-up question
        follow_up_indicators = [
            'and', 'also', 'what about', 'how about', 'can you tell me more',
            'elaborate', 'explain further', 'more details', 'additionally'
        ]
        
        for indicator in follow_up_indicators:
            if indicator in query.lower():
                context['is_follow_up'] = True
                break
        
        # Check recent conversation for RAG usage (simplified)
        if len(conversation_history) > 0:
            recent_messages = conversation_history[-3:]  # Last 3 messages
            for msg in recent_messages:
                content = msg.get('content', '').lower()
                # Simple heuristic: if recent messages are long, might have used RAG
                if len(content) > 200:
                    context['previous_rag_used'] = True
        
        return context
    
    def _make_retrieval_decision(
        self,
        original_query: str,
        pattern_scores: Dict[str, Any],
        keyword_scores: Dict[str, Any], 
        context_score: Dict[str, Any]
    ) -> RetrievalDecision:
        """Make the final retrieval decision based on all analysis."""
        
        # Calculate retrieval probability
        retrieval_score = 0.0
        reasoning_parts = []
        metadata = {
            'pattern_scores': pattern_scores,
            'keyword_scores': keyword_scores,
            'context_score': context_score
        }
        
        # Pattern contributions
        if pattern_scores.get('document_reference', {}).get('score', 0) > 0:
            retrieval_score += 0.4
            reasoning_parts.append("query references documents")
        
        if pattern_scores.get('analytical', {}).get('score', 0) > 0:
            retrieval_score += 0.3
            reasoning_parts.append("analytical query detected")
        
        if pattern_scores.get('specific_inquiry', {}).get('score', 0) > 0:
            retrieval_score += 0.2
            reasoning_parts.append("specific information requested")
        
        # Keyword contributions
        doc_keyword_score = keyword_scores.get('document_indicators', {}).get('score', 0)
        if doc_keyword_score > 0:
            retrieval_score += doc_keyword_score * 0.3
            reasoning_parts.append(f"document keywords present (strength: {doc_keyword_score:.2f})")
        
        analytical_keyword_score = keyword_scores.get('analytical', {}).get('score', 0)
        if analytical_keyword_score > 0:
            retrieval_score += analytical_keyword_score * 0.2
            reasoning_parts.append(f"analytical keywords present (strength: {analytical_keyword_score:.2f})")
        
        # Negative contributions (reduce retrieval score)
        conv_score = keyword_scores.get('conversational', {}).get('score', 0)
        if conv_score > 0:
            retrieval_score -= conv_score * 0.3
            reasoning_parts.append(f"conversational query (strength: {conv_score:.2f})")
        
        gen_knowledge_score = keyword_scores.get('general_knowledge', {}).get('score', 0)
        if gen_knowledge_score > 0:
            retrieval_score -= gen_knowledge_score * 0.2
            reasoning_parts.append(f"general knowledge query (strength: {gen_knowledge_score:.2f})")
        
        # Context contributions
        if context_score.get('is_follow_up'):
            if context_score.get('previous_rag_used'):
                retrieval_score += 0.1
                reasoning_parts.append("follow-up to RAG-assisted response")
            else:
                retrieval_score -= 0.1
                reasoning_parts.append("follow-up to non-RAG response")
        
        # Ensure score is within bounds
        retrieval_score = max(0.0, min(1.0, retrieval_score))
        
        # Make decision based on threshold
        RETRIEVAL_THRESHOLD = 0.3  # Adjustable threshold
        should_retrieve = retrieval_score >= RETRIEVAL_THRESHOLD
        
        # Determine query type
        query_type = self._determine_query_type(pattern_scores, keyword_scores)
        
        # Build reasoning
        if not reasoning_parts:
            reasoning = "default scoring applied"
        else:
            reasoning = "; ".join(reasoning_parts)
        
        reasoning = f"Score: {retrieval_score:.2f} (threshold: {RETRIEVAL_THRESHOLD}) - {reasoning}"
        
        return RetrievalDecision(
            should_retrieve=should_retrieve,
            confidence=abs(retrieval_score - RETRIEVAL_THRESHOLD) + 0.5,  # Higher confidence when far from threshold
            query_type=query_type,
            reasoning=reasoning,
            metadata=metadata
        )
    
    def _determine_query_type(
        self, 
        pattern_scores: Dict[str, Any], 
        keyword_scores: Dict[str, Any]
    ) -> QueryType:
        """Determine the primary type of the query."""
        
        # Check pattern scores
        if pattern_scores.get('conversational', {}).get('score', 0) > 0:
            return QueryType.CONVERSATIONAL
        
        if pattern_scores.get('document_reference', {}).get('score', 0) > 0:
            return QueryType.DOCUMENT_SPECIFIC
        
        if pattern_scores.get('analytical', {}).get('score', 0) > 0:
            return QueryType.ANALYTICAL
        
        if pattern_scores.get('general_knowledge', {}).get('score', 0) > 0:
            return QueryType.GENERAL_KNOWLEDGE
        
        # Check keyword scores
        if keyword_scores.get('document_indicators', {}).get('score', 0) > 0.5:
            return QueryType.DOCUMENT_SPECIFIC
        
        if keyword_scores.get('conversational', {}).get('score', 0) > 0.5:
            return QueryType.CONVERSATIONAL
        
        if keyword_scores.get('analytical', {}).get('score', 0) > 0.5:
            return QueryType.ANALYTICAL
        
        if keyword_scores.get('general_knowledge', {}).get('score', 0) > 0.5:
            return QueryType.GENERAL_KNOWLEDGE
        
        # Default
        return QueryType.FACTUAL
    
    def get_retrieval_suggestion(self, query: str, has_documents: bool = True) -> str:
        """Get a human-readable suggestion about retrieval for debugging."""
        decision = self.classify_query(query, has_documents=has_documents)
        
        if decision.should_retrieve:
            return f"RETRIEVE - {decision.reasoning} (confidence: {decision.confidence:.2f})"
        else:
            return f"SKIP - {decision.reasoning} (confidence: {decision.confidence:.2f})"
