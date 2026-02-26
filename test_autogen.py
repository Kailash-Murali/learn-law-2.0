"""
Test script for AutoGen Legal Research System

This script tests the AutoGen-based multi-agent coordination
separately from the main application.
"""

from autogen_agent import AutoGenLegalResearch, run_autogen_research
import json


def test_individual_agents():
    """Test each agent separately"""
    print("\n" + "=" * 60)
    print("🧪 Testing Individual Agents")
    print("=" * 60)
    
    system = AutoGenLegalResearch()
    
    # Test 1: UI Agent
    print("\n1️⃣ Testing UI Agent (Query Parser)...")
    query = "What is the right to privacy under Indian Constitution?"
    parsed = system.parse_query(query)
    print(f"   Input: {query}")
    print(f"   Output: {json.dumps(parsed, indent=2)}")
    
    # Test 2: Research Agent
    print("\n2️⃣ Testing Research Agent...")
    research = system.conduct_research(parsed)
    print(f"   Cases found: {len(research.get('case_laws', []))}")
    print(f"   Statutes found: {len(research.get('statutes', []))}")
    
    # Test 3: Documentation Agent
    print("\n3️⃣ Testing Documentation Agent...")
    doc = system.generate_documentation(query, parsed, research)
    summary = doc.get('executive_summary', '')
    print(f"   Summary length: {len(summary)} chars")
    print(f"   Recommendations: {len(doc.get('recommendations', []))}")
    
    return True


def test_full_workflow():
    """Test the complete research workflow"""
    print("\n" + "=" * 60)
    print("🔄 Testing Full Research Workflow")
    print("=" * 60)
    
    test_queries = [
        "What are fundamental rights under Article 21?",
        "Explain the doctrine of basic structure",
        "Right to education as a fundamental right"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test {i}: {query[:50]}... ---\n")
        
        result = run_autogen_research(query)
        
        print(f"Status: {result['status']}")
        
        if result['status'] == 'completed':
            print("✅ Test passed!")
            
            # Show brief summary
            if result['documentation']:
                summary = result['documentation'].get('executive_summary', '')
                if summary:
                    print(f"Summary preview: {summary[:200]}...")
        else:
            print(f"❌ Test failed: {result.get('error', 'Unknown error')}")
        
        # Only run first test if we're in mock mode
        if not result.get('documentation'):
            print("(Running in mock mode - limited testing)")
            break
    
    return True


def test_error_handling():
    """Test error handling"""
    print("\n" + "=" * 60)
    print("🛡️ Testing Error Handling")
    print("=" * 60)
    
    system = AutoGenLegalResearch()
    
    # Test with empty query
    print("\n1️⃣ Testing with empty query...")
    result = system.run_research("")
    print(f"   Status: {result['status']}")
    
    # Test with very long query
    print("\n2️⃣ Testing with long query...")
    long_query = "legal rights " * 100
    result = system.run_research(long_query[:500])
    print(f"   Status: {result['status']}")
    
    return True


def interactive_test():
    """Interactive testing mode"""
    print("\n" + "=" * 60)
    print("🎮 Interactive Testing Mode")
    print("=" * 60)
    print("\nType your legal research query (or 'quit' to exit):\n")
    
    while True:
        query = input("Query: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not query:
            print("Please enter a query.\n")
            continue
        
        print("\n🔍 Processing...\n")
        result = run_autogen_research(query)
        
        print("\n" + "-" * 40)
        print(f"Status: {result['status']}")
        
        if result['documentation']:
            print("\n📋 REPORT:\n")
            doc = result['documentation']
            
            if doc.get('executive_summary'):
                print("Executive Summary:")
                print(doc['executive_summary'])
            
            if doc.get('recommendations'):
                print("\nRecommendations:")
                for rec in doc['recommendations']:
                    print(f"  • {rec}")
        
        if result['error']:
            print(f"\n❌ Error: {result['error']}")
        
        print("\n" + "-" * 40 + "\n")


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("🏛️  AutoGen Legal Research - Test Suite")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "interactive":
            interactive_test()
        elif mode == "agents":
            test_individual_agents()
        elif mode == "workflow":
            test_full_workflow()
        elif mode == "errors":
            test_error_handling()
        else:
            print(f"Unknown mode: {mode}")
            print("Available modes: interactive, agents, workflow, errors")
    else:
        # Run all tests
        print("\nRunning all tests...\n")
        
        test_individual_agents()
        test_full_workflow()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        print("\nTo run interactive mode: python test_autogen.py interactive")
