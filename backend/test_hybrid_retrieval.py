"""
Test file demonstrating the capabilities of the Intelligent Hybrid Retrieval System

This test file shows how the system seamlessly integrates LLM generations with
document retrieval using dynamic context-aware switching mechanisms.
"""

import asyncio
import uuid
import time
from typing import Dict, List, Any

# Import the hybrid retrieval components
from src.services.hybrid_retrieval_orchestrator import (
    HybridRetrievalOrchestrator,
    AdvancedQueryAnalyzer,
    AdaptiveRoutingStrategy,
    ResponseBlender,
    RetrievalMode,
    QueryIntent,
    InformationDensity,
    HybridResponse
)

from src.services.context_aware_cache_manager import (
    ContextAwareCacheManager,
    CacheStrategy
)

from src.services.hybrid_performance_monitor import (
    HybridPerformanceMonitor,
    HybridRetrievalConfig,
    MetricType,
    OptimizationGoal
)


class TestHybridRetrieval:
    """Test cases demonstrating hybrid retrieval capabilities."""
    
    def __init__(self):
        """Initialize test environment."""
        self.config = HybridRetrievalConfig()
        self.performance_monitor = HybridPerformanceMonitor(config=self.config)
        self.cache_manager = ContextAwareCacheManager(strategy=CacheStrategy.ADAPTIVE)
        
        # Mock services for testing
        self.db = None  # Would be actual database session
        self.vector_service = MockVectorService()
        self.llm_service = MockLLMService()
        self.embedding_service = MockEmbeddingService()
        
        # Initialize orchestrator
        self.orchestrator = HybridRetrievalOrchestrator(
            self.db,
            self.vector_service,
            self.llm_service,
            self.embedding_service
        )
    
    async def test_dynamic_routing(self):
        """Test dynamic context-aware routing based on query characteristics."""
        print("\n=== Testing Dynamic Context-Aware Routing ===\n")
        
        test_queries = [
            {
                "query": "Hello, how are you today?",
                "expected_mode": RetrievalMode.PURE_LLM,
                "description": "Conversational query - should use pure LLM"
            },
            {
                "query": "According to the documentation, what is the API rate limit?",
                "expected_mode": RetrievalMode.HYBRID_DOCUMENT_HEAVY,
                "description": "Document-specific query - should prioritize documents"
            },
            {
                "query": "Compare the performance of method A versus method B and recommend the best approach",
                "expected_mode": RetrievalMode.HYBRID_BALANCED,
                "description": "Analytical query - should balance LLM and documents"
            },
            {
                "query": "Create a marketing strategy for our new product launch",
                "expected_mode": RetrievalMode.HYBRID_LLM_HEAVY,
                "description": "Creative query - should prioritize LLM with document support"
            },
            {
                "query": "What are the latest updates in the system as of today?",
                "expected_mode": RetrievalMode.HYBRID_LLM_HEAVY,
                "description": "Temporal query - should use LLM for recent information"
            }
        ]
        
        analyzer = AdvancedQueryAnalyzer()
        router = AdaptiveRoutingStrategy()
        
        for test_case in test_queries:
            print(f"Query: '{test_case['query']}'")
            print(f"Description: {test_case['description']}")
            
            # Analyze query
            characteristics = analyzer.analyze_query(test_case["query"])
            
            print(f"  Intent: {characteristics.intent.value}")
            print(f"  Complexity: {characteristics.complexity_score:.2f}")
            print(f"  Specificity: {characteristics.specificity_score:.2f}")
            print(f"  Temporal relevance: {characteristics.temporal_relevance:.2f}")
            
            # Determine routing
            decision = router.determine_retrieval_strategy(
                characteristics, 
                available_documents=10,
                system_load=0.5
            )
            
            print(f"  Selected mode: {decision.mode.value}")
            print(f"  Confidence: {decision.confidence:.2f}")
            print(f"  Document weight: {decision.document_weight:.2f}")
            print(f"  LLM weight: {decision.llm_weight:.2f}")
            print(f"  Rationale: {decision.rationale}")
            print()
    
    async def test_intelligent_blending(self):
        """Test intelligent response blending strategies."""
        print("\n=== Testing Intelligent Response Blending ===\n")
        
        blender = ResponseBlender()
        
        # Test different blending scenarios
        scenarios = [
            {
                "name": "Document-heavy blend",
                "llm_response": "Based on my understanding, the process involves several steps.",
                "documents": [
                    {"text": "Step 1: Initialize the system with proper credentials", "score": 0.9},
                    {"text": "Step 2: Configure the parameters according to specifications", "score": 0.85},
                    {"text": "Step 3: Execute the process and monitor results", "score": 0.8}
                ],
                "mode": RetrievalMode.HYBRID_DOCUMENT_HEAVY,
                "synthesis_strategy": "weighted_combination"
            },
            {
                "name": "LLM-heavy blend",
                "llm_response": "The creative solution involves thinking outside the box and considering multiple perspectives that haven't been documented yet.",
                "documents": [
                    {"text": "Traditional approaches have focused on linear progression", "score": 0.6}
                ],
                "mode": RetrievalMode.HYBRID_LLM_HEAVY,
                "synthesis_strategy": "llm_enhanced_documents"
            },
            {
                "name": "Balanced blend",
                "llm_response": "The analysis shows three key factors affecting performance.",
                "documents": [
                    {"text": "Factor 1: System load impacts response time by 40%", "score": 0.85},
                    {"text": "Factor 2: Cache hit rate correlates with user satisfaction", "score": 0.8}
                ],
                "mode": RetrievalMode.HYBRID_BALANCED,
                "synthesis_strategy": "weighted_combination"
            }
        ]
        
        for scenario in scenarios:
            print(f"Scenario: {scenario['name']}")
            print(f"Mode: {scenario['mode'].value}")
            print(f"Strategy: {scenario['synthesis_strategy']}")
            
            # Create mock decision
            from src.services.hybrid_retrieval_orchestrator import RetrievalDecision
            decision = RetrievalDecision(
                mode=scenario['mode'],
                confidence=0.85,
                document_weight=0.7 if "document" in scenario['name'].lower() else 0.3,
                llm_weight=0.3 if "document" in scenario['name'].lower() else 0.7,
                retrieval_depth=len(scenario['documents']),
                synthesis_strategy=scenario['synthesis_strategy'],
                rationale="Test scenario"
            )
            
            # Blend responses
            result = await blender.blend_responses(
                scenario['llm_response'],
                scenario['documents'],
                decision,
                "Test query"
            )
            
            print(f"\nBlended Response:")
            print(f"  {result.content[:200]}...")
            print(f"  Information density: {result.information_density.name}")
            print(f"  Document contribution: {result.document_contribution:.2%}")
            print(f"  LLM contribution: {result.llm_contribution:.2%}")
            print()
    
    async def test_adaptive_performance_optimization(self):
        """Test adaptive performance optimization based on metrics."""
        print("\n=== Testing Adaptive Performance Optimization ===\n")
        
        # Initialize performance monitor
        await self.performance_monitor.initialize()
        
        # Simulate query performance metrics
        queries = [
            {"mode": "hybrid_balanced", "response_time": 1.2, "accuracy": 0.85, "cache_hit": False},
            {"mode": "pure_llm", "response_time": 0.5, "accuracy": 0.7, "cache_hit": True},
            {"mode": "hybrid_document_heavy", "response_time": 2.1, "accuracy": 0.92, "cache_hit": False},
            {"mode": "hybrid_llm_heavy", "response_time": 0.8, "accuracy": 0.78, "cache_hit": True},
            {"mode": "hybrid_balanced", "response_time": 1.5, "accuracy": 0.88, "cache_hit": False},
        ]
        
        # Record metrics
        for i, query in enumerate(queries):
            query_id = f"test_query_{i}"
            await self.performance_monitor.record_query_performance(
                query_id=query_id,
                bot_id="test_bot",
                user_id="test_user",
                mode_used=query["mode"],
                response_time=query["response_time"],
                confidence_score=query["accuracy"],
                cache_hit=query["cache_hit"],
                document_count=5 if "hybrid" in query["mode"] else 0
            )
        
        # Get performance analysis
        mode_performance = self.performance_monitor.get_mode_performance("1h")
        
        print("Mode Performance Analysis:")
        for mode, metrics in mode_performance.items():
            print(f"  {mode}:")
            print(f"    Avg response time: {metrics['avg_response_time']:.2f}s")
            print(f"    Avg accuracy: {metrics['avg_accuracy']:.2%}")
            print(f"    Usage count: {metrics['usage_count']}")
        
        # Test different optimization goals
        optimization_goals = [
            OptimizationGoal.MINIMIZE_LATENCY,
            OptimizationGoal.MAXIMIZE_ACCURACY,
            OptimizationGoal.BALANCE_PERFORMANCE
        ]
        
        for goal in optimization_goals:
            print(f"\nOptimizing for: {goal.value}")
            self.config.set("performance.optimization_goal", goal.value)
            
            optimizations = await self.performance_monitor.optimize_system_parameters()
            
            if optimizations:
                print("  Recommended optimizations:")
                for key, value in optimizations.items():
                    print(f"    {key}: {value}")
            else:
                print("  No optimizations needed")
    
    async def test_context_aware_caching(self):
        """Test context-aware caching with intelligent invalidation."""
        print("\n=== Testing Context-Aware Caching ===\n")
        
        await self.cache_manager.initialize()
        
        # Test cache operations
        test_cases = [
            {
                "query": "What is machine learning?",
                "context": {"intent": "factual", "domain": "technical", "complexity": 0.3},
                "response": "Machine learning is a subset of AI that enables systems to learn from data.",
                "expected_cache": True
            },
            {
                "query": "Hello there!",
                "context": {"intent": "conversational", "domain": "general", "complexity": 0.1},
                "response": "Hello! How can I help you today?",
                "expected_cache": False  # Conversational, shouldn't cache
            },
            {
                "query": "What are today's stock prices?",
                "context": {"intent": "factual", "domain": "finance", "complexity": 0.5, "temporal": 0.9},
                "response": "Current stock prices: AAPL $150, GOOGL $2800",
                "expected_cache": True  # But with short TTL due to temporal nature
            }
        ]
        
        for test in test_cases:
            print(f"\nQuery: '{test['query']}'")
            print(f"Context: {test['context']}")
            
            # Create mock response
            mock_response = MockHybridResponse(
                content=test['response'],
                confidence_score=0.85,
                mode_used=RetrievalMode.HYBRID_BALANCED
            )
            
            # Try to cache
            cached = await self.cache_manager.set(
                query=test['query'],
                bot_id="test_bot",
                user_id="test_user",
                response=mock_response,
                context=test['context'],
                query_characteristics={
                    "intent": test['context']['intent'],
                    "temporal_relevance": test['context'].get('temporal', 0.0)
                }
            )
            
            print(f"  Cached: {cached} (expected: {test['expected_cache']})")
            
            if cached:
                # Try to retrieve
                entry = await self.cache_manager.get(
                    query=test['query'],
                    bot_id="test_bot",
                    user_id="test_user",
                    context=test['context']
                )
                
                if entry:
                    print(f"  Retrieved from cache: '{entry.content[:50]}...'")
                    print(f"  TTL: {entry.ttl}s")
                    print(f"  Access count: {entry.access_count}")
        
        # Display cache statistics
        stats = self.cache_manager.get_statistics()
        print("\nCache Statistics:")
        print(f"  Hit rate: {stats['hit_rate']:.2%}")
        print(f"  Total hits: {stats['total_hits']}")
        print(f"  Total misses: {stats['total_misses']}")
        print(f"  Entry count: {stats['entry_count']}")
        print(f"  Cache size: {stats['cache_size_mb']:.2f} MB")
    
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow with all components."""
        print("\n=== Testing End-to-End Workflow ===\n")
        
        # Test query
        query = "Based on the documentation, what are the best practices for API design, and can you provide creative examples?"
        bot_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        print(f"Query: '{query}'")
        print(f"Bot ID: {bot_id}")
        print(f"User ID: {user_id}")
        
        # Process through orchestrator
        start_time = time.time()
        
        try:
            # This would normally process through the full system
            response = await self.orchestrator.process_query(
                query=query,
                bot_id=bot_id,
                user_id=user_id,
                conversation_history=[],
                user_profile={"expertise_level": 0.7}
            )
            
            processing_time = time.time() - start_time
            
            print(f"\nResponse:")
            print(f"  Content: {response.content[:300]}...")
            print(f"  Mode used: {response.mode_used.value}")
            print(f"  Sources: {response.sources_used}")
            print(f"  Confidence: {response.confidence_score:.2f}")
            print(f"  Information density: {response.information_density.name}")
            print(f"  Processing time: {processing_time:.2f}s")
            print(f"  Document contribution: {response.document_contribution:.2%}")
            print(f"  LLM contribution: {response.llm_contribution:.2%}")
            
            # Record performance
            await self.performance_monitor.record_query_performance(
                query_id=str(uuid.uuid4()),
                bot_id=str(bot_id),
                user_id=str(user_id),
                mode_used=response.mode_used.value,
                response_time=processing_time,
                confidence_score=response.confidence_score,
                cache_hit=False,
                document_count=len([s for s in response.sources_used if s != "LLM"])
            )
            
        except Exception as e:
            print(f"Error in end-to-end test: {e}")
        
        # Get dashboard metrics
        dashboard = self.performance_monitor.get_dashboard_metrics()
        
        print("\nDashboard Metrics:")
        print(f"  Current response time (mean): {dashboard['current_performance']['response_time']['mean']:.2f}s")
        print(f"  Current accuracy (mean): {dashboard['current_performance']['accuracy']['mean']:.2%}")
        print(f"  Active alerts: {len(dashboard['active_alerts'])}")
        
        if dashboard['optimization_history']:
            print(f"  Last optimization: {dashboard['optimization_history'][-1]['goal']}")


# Mock classes for testing
class MockVectorService:
    async def search_relevant_chunks(self, *args, **kwargs):
        return [
            {"text": "Mock document chunk 1", "score": 0.85, "id": "doc1"},
            {"text": "Mock document chunk 2", "score": 0.75, "id": "doc2"}
        ]

class MockLLMService:
    async def generate_response(self, *args, **kwargs):
        return "This is a mock LLM response for testing purposes."

class MockEmbeddingService:
    async def generate_embedding(self, *args, **kwargs):
        return [0.1] * 768  # Mock 768-dimensional embedding

class MockHybridResponse:
    def __init__(self, content, confidence_score, mode_used):
        self.content = content
        self.confidence_score = confidence_score
        self.mode_used = mode_used
        self.sources_used = ["LLM", "doc1", "doc2"]
        self.metadata = {}


async def main():
    """Run all tests."""
    print("=" * 80)
    print("INTELLIGENT HYBRID RETRIEVAL SYSTEM - TEST SUITE")
    print("=" * 80)
    
    tester = TestHybridRetrieval()
    
    # Run tests
    await tester.test_dynamic_routing()
    await tester.test_intelligent_blending()
    await tester.test_adaptive_performance_optimization()
    await tester.test_context_aware_caching()
    await tester.test_end_to_end_workflow()
    
    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETED")
    print("=" * 80)
    
    # Clean up
    await tester.performance_monitor.close()
    await tester.cache_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
