"""
Constitutional Law Research System - Integrated Main Entry Point
Uses AutoGen multi-agent system + Advanced XAI
"""

import argparse
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConstitutionalLawCLI:
    """Command-line interface for Constitutional Law Research with AutoGen + XAI."""
    
    def __init__(self, enable_xai: bool = True):
        self.enable_xai = enable_xai
        self.research_system = None
        
    def initialize(self):
        """Initialize the AutoGen research system."""
        try:
            from autogen_agent import AutoGenLegalResearch
            self.research_system = AutoGenLegalResearch(enable_xai=self.enable_xai)
            
            if self.enable_xai:
                print("[XAI] Advanced XAI Engine enabled (SHAP, LIME, Counterfactuals)")
            
            print("[System] AutoGen Multi-Agent System initialized")
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            print(f"[Error] Failed to initialize: {e}")
            return False
    
    def process_query(self, query: str) -> dict:
        """Process a legal research query."""
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}\n")
        
        try:
            # Process with AutoGen (includes XAI if enabled)
            if self.enable_xai:
                result = self.research_system.run_research_with_xai(query)
            else:
                result = self.research_system.run_research(query)
            
            return result
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    def display_result(self, result: dict):
        """Display the research result."""
        if result.get("error"):
            print(f"\n[Error] {result['error']}")
            return
        
        print("\n" + "="*70)
        print("📄 LEGAL RESEARCH REPORT")
        print("="*70)
        
        # Display full documentation if available
        doc = result.get("documentation", {})
        if doc:
            # Show full report
            full_report = doc.get("full_report", "")
            if full_report:
                print("\n" + full_report)
            else:
                # Fallback to executive summary
                print("\n📋 EXECUTIVE SUMMARY:\n")
                print(doc.get("executive_summary", "N/A"))
                
                print("\n📌 RECOMMENDATIONS:\n")
                for rec in doc.get("recommendations", []):
                    print(f"  • {rec}")
        else:
            # Show research content if no documentation
            research_content = result.get("research", {}).get("research_content", "No response generated")
            print("\n📚 RESEARCH FINDINGS:\n")
            print(research_content)
        
        # Show XAI report if available
        if result.get("xai_report_formatted"):
            print(result["xai_report_formatted"])
        
        # Show reasoning summary (brief)
        if result.get("agent_reasoning_traces"):
            print("\n" + "-"*70)
            print("📊 AGENT ACTIVITY SUMMARY")
            print("-"*70)
            for agent, trace in result["agent_reasoning_traces"].items():
                print(f"  {agent}: {len(trace)} steps completed")
    
    def interactive_mode(self):
        """Run interactive query mode."""
        print("\n" + "="*60)
        print("CONSTITUTIONAL LAW RESEARCH SYSTEM")
        print("AutoGen Multi-Agent + Advanced XAI")
        print("="*60)
        print("\nCommands: 'quit' to exit, 'help' for info")
        print("-"*60)
        
        while True:
            try:
                query = input("\nEnter your legal query: ").strip()
                
                if not query:
                    continue
                elif query.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                elif query.lower() == 'help':
                    self.show_help()
                    continue
                
                result = self.process_query(query)
                self.display_result(result)
                
            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n[Error] {e}")
    
    def show_help(self):
        """Show help information."""
        print("""
Available Commands:
  - Type any legal question to research
  - 'quit' or 'exit' - Exit the program
  - 'help' - Show this message

Example Queries:
  - What is Article 14 of the Indian Constitution?
  - Explain the Right to Equality
  - What are Fundamental Rights?
  - Explain judicial review in India

XAI Features (enabled by default):
  - SHAP: Feature importance analysis
  - LIME: Local interpretable explanations
  - Counterfactuals: Alternative scenarios
  - Uncertainty Quantification: Confidence bounds
  - Integrated Gradients: Attribution analysis

Use --no-xai flag to disable XAI explanations.
        """)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Constitutional Law Research System with AutoGen + Advanced XAI"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Direct query (optional, runs interactive mode if not provided)"
    )
    parser.add_argument(
        "--no-xai",
        action="store_true",
        help="Disable XAI explanations (XAI is enabled by default)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize CLI - XAI enabled by default, use --no-xai to disable
    cli = ConstitutionalLawCLI(enable_xai=not args.no_xai)
    
    if not cli.initialize():
        print("[Error] Failed to initialize system. Check your API keys.")
        sys.exit(1)
    
    # Run query or interactive mode
    if args.query:
        result = cli.process_query(args.query)
        cli.display_result(result)
    else:
        cli.interactive_mode()


if __name__ == "__main__":
    main()
