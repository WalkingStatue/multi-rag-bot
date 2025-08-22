#!/usr/bin/env python3
"""
Test script to demonstrate smart RAG retrieval decisions.

This script shows how the new query classifier works to determine
when document retrieval is needed versus when the LLM can answer directly.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from services.query_classifier import QueryClassifier

def test_smart_retrieval():
    """Test the smart retrieval decision-making."""
    classifier = QueryClassifier()
    
    # Test queries that should NOT trigger retrieval
    non_retrieval_queries = [
        "Hello, how are you?",
        "What is artificial intelligence in general?",
        "Thanks for your help!",
        "Can you explain what machine learning is?",
        "What's the weather like?",
        "Tell me a joke",
        "Good morning!",
        "How do neural networks work in general?",
    ]
    
    # Test queries that SHOULD trigger retrieval
    retrieval_queries = [
        "What does the document say about pricing?",
        "According to the manual, how do I install this?", 
        "Can you find the specifications in the report?",
        "Summarize the key findings from the research paper",
        "What are the requirements mentioned in the document?",
        "Analyze the data shown in the uploaded files",
        "Compare the different approaches outlined in the guide",
        "What specific examples are provided in the documentation?",
    ]
    
    print("🤖 Smart RAG Retrieval Decision Test")
    print("=" * 60)
    
    print("\n📝 Queries that should NOT use retrieval:")
    print("-" * 40)
    for query in non_retrieval_queries:
        decision = classifier.classify_query(query, has_documents=True)
        status = "✓" if not decision.should_retrieve else "✗"
        print(f"{status} '{query}'")
        print(f"   Decision: {'SKIP' if not decision.should_retrieve else 'RETRIEVE'}")
        print(f"   Confidence: {decision.confidence:.2f}")
        print(f"   Type: {decision.query_type.value}")
        print(f"   Reasoning: {decision.reasoning}")
        print()
    
    print("\n📋 Queries that SHOULD use retrieval:")
    print("-" * 40)
    for query in retrieval_queries:
        decision = classifier.classify_query(query, has_documents=True)
        status = "✓" if decision.should_retrieve else "✗"
        print(f"{status} '{query}'")
        print(f"   Decision: {'RETRIEVE' if decision.should_retrieve else 'SKIP'}")
        print(f"   Confidence: {decision.confidence:.2f}")
        print(f"   Type: {decision.query_type.value}")
        print(f"   Reasoning: {decision.reasoning}")
        print()
    
    print("\n🔍 Testing with no documents available:")
    print("-" * 40)
    decision = classifier.classify_query("What does the document say about pricing?", has_documents=False)
    print(f"Query: 'What does the document say about pricing?'")
    print(f"Decision: {'RETRIEVE' if decision.should_retrieve else 'SKIP'}")
    print(f"Reasoning: {decision.reasoning}")
    print()

def test_conversation_context():
    """Test how conversation context affects retrieval decisions."""
    classifier = QueryClassifier()
    
    print("\n💬 Testing conversation context impact:")
    print("-" * 40)
    
    # Simulate a conversation history
    conversation_history = [
        {"role": "user", "content": "What does the document say about pricing?"},
        {"role": "assistant", "content": "According to the document, the pricing structure includes three tiers: Basic ($10/month), Pro ($25/month), and Enterprise ($100/month). Each tier offers different features and usage limits."},
        {"role": "user", "content": "What about the Enterprise features?"},
        {"role": "assistant", "content": "The Enterprise tier includes advanced analytics, priority support, custom integrations, and unlimited usage."}
    ]
    
    test_queries = [
        "Can you tell me more about that?",  # Follow-up after document context
        "What other details are available?",  # Vague follow-up
        "Thank you for that information",     # Gratitude
        "What's the weather like today?"      # Unrelated question
    ]
    
    for query in test_queries:
        decision = classifier.classify_query(
            query, 
            conversation_history=conversation_history, 
            has_documents=True
        )
        print(f"Query: '{query}'")
        print(f"Decision: {'RETRIEVE' if decision.should_retrieve else 'SKIP'}")
        print(f"Reasoning: {decision.reasoning}")
        print()

if __name__ == "__main__":
    test_smart_retrieval()
    test_conversation_context()
    
    print("\n🎉 Smart retrieval testing complete!")
    print("\nKey Benefits:")
    print("• Reduces unnecessary document retrieval for general questions")
    print("• Saves API costs and improves response speed")  
    print("• Maintains high-quality responses by using RAG only when needed")
    print("• Provides detailed reasoning for debugging and optimization")
