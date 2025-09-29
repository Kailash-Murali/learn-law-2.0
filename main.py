import asyncio
import json
import logging
import sys
from typing import Optional

from config import Config
from main_agent import MainAgent
from exceptions import ConstitutionalLawException

class ConstitutionalLawCLI:
    """Command Line Interface for Constitutional Law Research Agent System"""
    
    def __init__(self):
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize main agent
        try:
            self.config = Config()
            self.main_agent = MainAgent(self.config)
            self.logger.info("Constitutional Law Research System initialized")
        except Exception as e:
            self.logger.error(f"Initialization failed: {str(e)}")
            sys.exit(1)
    
    async def run_interactive_mode(self):
        """Run the CLI in interactive mode"""
        print("=" * 60)
        print("Constitutional Law Research Agent System")
        print("=" * 60)
        print("Type 'help' for available commands, 'quit' to exit")
        print()
        
        user_id = "cli_user"  # Simple user ID for CLI mode
        
        while True:
            try:
                command = input("ConLaw> ").strip()
                
                if command.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                elif command.lower() in ['help', 'h']:
                    self._show_help()
                
                elif command.lower().startswith('status '):
                    request_id = int(command.split()[1])
                    await self._show_status(request_id)
                
                elif command.lower().startswith('result '):
                    request_id = int(command.split()[1])
                    await self._show_result(request_id)
                
                elif command.lower() == 'clear':
                    print("\n" * 50)  # Clear screen
                
                elif command.strip():
                    # Treat as research query
                    await self._process_query(user_id, command)
                
                else:
                    print("Please enter a command or research query.")
            
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except ValueError as e:
                print(f"Error: Invalid input format - {str(e)}")
            except Exception as e:
                self.logger.error(f"Command error: {str(e)}")
                print(f"An error occurred: {str(e)}")
    
    async def _process_query(self, user_id: str, query: str):
        """Process a research query"""
        print(f"\nProcessing query: '{query}'")
        print("This may take a moment...")
        
        try:
            # Process the request
            result = await self.main_agent.process_request(user_id, query)
            
            print(f"\n✓ Research completed! Request ID: {result['request_id']}")
            print(f"Status: {result['status']}")
            
            # Show summary
            summary = result['processing_summary']
            print(f"\nResearch Summary:")
            print(f"  • Cases found: {summary['total_cases_found']}")
            print(f"  • Statutes found: {summary['total_statutes_found']}")
            print(f"  • Articles found: {summary['total_articles_found']}")
            print(f"  • Sources searched: {summary['research_sources']}")
            
            # Show key findings
            if result['documentation']:
                doc = result['documentation']
                print(f"\nExecutive Summary:")
                print(f"  {doc.get('executive_summary', 'Not available')[:200]}...")
                
                if doc.get('case_law_review'):
                    print(f"\nKey Cases:")
                    for case in doc['case_law_review'][:3]:
                        print(f"  • {case.get('case_name', 'Unknown')}")
            
            print(f"\nUse 'result {result['request_id']}' to see full documentation")
            
        except ConstitutionalLawException as e:
            print(f"Research failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            print(f"An unexpected error occurred: {str(e)}")
    
    async def _show_status(self, request_id: int):
        """Show status of a request"""
        try:
            status = self.main_agent.get_request_status(request_id)
            if not status:
                print(f"Request {request_id} not found")
                return
            
            print(f"\nRequest {request_id} Status:")
            print(f"  Status: {status['status']}")
            print(f"  Topic: {status['research_topic']}")
            print(f"  Submitted: {status['timestamp']}")
            
            if 'research_summary' in status:
                rs = status['research_summary']
                print(f"  Research: {rs['cases_found']} cases, {rs['statutes_found']} statutes")
            
            if status.get('documentation_available'):
                print(f"  Documentation: Available")
        
        except Exception as e:
            print(f"Error retrieving status: {str(e)}")
    
    async def _show_result(self, request_id: int):
        """Show full results for a request"""
        try:
            documentation = self.main_agent.get_completed_documentation(request_id)
            if not documentation:
                print(f"No documentation found for request {request_id}")
                return
            
            print(f"\n" + "="*60)
            print(f"CONSTITUTIONAL LAW RESEARCH RESULTS - Request {request_id}")
            print("="*60)
            
            # Executive Summary
            print(f"\nEXECUTIVE SUMMARY")
            print("-" * 20)
            print(documentation.get('executive_summary', 'Not available'))
            
            # Legal Analysis
            print(f"\nLEGAL ANALYSIS")
            print("-" * 15)
            print(documentation.get('legal_analysis', 'Not available'))
            
            # Case Law Review
            if documentation.get('case_law_review'):
                print(f"\nCASE LAW REVIEW")
                print("-" * 16)
                for case in documentation['case_law_review']:
                    print(f"• {case.get('case_name', 'Unknown Case')}")
                    print(f"  Citation: {case.get('citation', 'N/A')}")
                    print(f"  Holding: {case.get('key_holding', 'N/A')}")
                    print()
            
            # Statutory Provisions
            if documentation.get('statutory_provisions'):
                print(f"STATUTORY PROVISIONS")
                print("-" * 20)
                for statute in documentation['statutory_provisions']:
                    print(f"• {statute.get('provision', 'Unknown')}")
                    print(f"  Application: {statute.get('application', 'N/A')}")
                    print()
            
            # Recommendations
            if documentation.get('recommendations'):
                print(f"RECOMMENDATIONS")
                print("-" * 15)
                for i, rec in enumerate(documentation['recommendations'], 1):
                    print(f"{i}. {rec}")
                print()
        
        except Exception as e:
            print(f"Error retrieving results: {str(e)}")
    
    def _show_help(self):
        """Show help information"""
        print("\nAvailable Commands:")
        print("  help, h              - Show this help message")
        print("  status <request_id>  - Show status of a research request")
        print("  result <request_id>  - Show full results of a completed request")
        print("  clear               - Clear the screen")
        print("  quit, exit, q       - Exit the program")
        print("\nTo start a research query, simply type your constitutional law question.")
        print("Examples:")
        print("  • What is the current status of affirmative action in education?")
        print("  • How has the Equal Protection Clause been interpreted recently?")
        print("  • What are the limits on executive power during emergencies?")
        print()

async def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Command line mode with query as argument
        cli = ConstitutionalLawCLI()
        query = " ".join(sys.argv[1:])
        await cli._process_query("cli_user", query)
    else:
        # Interactive mode
        cli = ConstitutionalLawCLI()
        await cli.run_interactive_mode()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)
