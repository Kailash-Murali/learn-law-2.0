import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Optional, Any, Dict

# Assuming these are available in your project structure
from config import Config
from main_agent import MainAgent
from exceptions import ConstitutionalLawException
from database import ConstitutionalLawDB # Assuming this is available for TraceLogger
from trace_logger import TraceLogger # Assuming your TraceLogger is in tracelogger.py

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
            # Ensure MainAgent initializes and exposes the TraceLogger
            self.main_agent = MainAgent(self.config) 
            self.trace_logger: TraceLogger = self.main_agent.trace_logger
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
                
                elif command.lower().startswith('trace '):
                    request_id = int(command.split()[1])
                    await self._show_trace(request_id)

                elif command.lower().startswith('artefacts '):
                    request_id = int(command.split()[1])
                    await self._list_artefacts(request_id)

                elif command.lower().startswith('artefact_content '):
                    artefact_id = int(command.split()[1])
                    await self._show_artefact_content(artefact_id)
                
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
            except (ValueError, IndexError) as e:
                print(f"Error: Invalid input format. Please check the command and arguments. ({e})")
            except Exception as e:
                self.logger.error(f"Command error: {str(e)}")
                print(f"An unexpected error occurred: {str(e)}")
    
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
            print(f"Use 'trace {result['request_id']}' to view the processing trace.") # Added trace instruction
            
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
            
            # Optionally, add a brief summary of trace data
            # This would require a lightweight query to trace_logger (e.g., count events/decisions)
            # For simplicity, we'll just point to the trace command for now.
            print(f"\nFor detailed processing trace, use 'trace {request_id}'")
        
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

    async def _show_trace(self, request_id: int):
        """Show the chronological trace of events, decisions, and artefacts for a request."""
        print(f"\n" + "="*60)
        print(f"PROCESSING TRACE FOR REQUEST {request_id}")
        print("="*60)
        
        try:
            trace_data = self.trace_logger.get_full_request_trace(request_id)
            if not trace_data:
                print(f"No trace data found for request {request_id}.")
                return

            for entry in trace_data:
                timestamp = (
                    entry.get('logged_at') or 
                    entry.get('recorded_at') or 
                    entry.get('captured_at')
                )
                agent = entry.get('agent', 'N/A')
                entry_type = entry['type'].upper()

                print(f"\n[{timestamp}] AGENT: {agent} | TYPE: {entry_type}")
                print("-" * 80)

                if entry_type == 'EVENT':
                    event_type = entry.get('event_type', 'N/A')
                    phase = entry.get('phase', 'N/A')
                    print(f"  Event Type: {event_type}")
                    print(f"  Phase: {phase}")
                    print(f"  Payload (excerpt): {json.dumps(entry.get('payload', {}), indent=2, default=str)[:500]}...") # Limit output
                elif entry_type == 'DECISION':
                    decision_type = entry.get('decision_type', 'N/A')
                    rationale = entry.get('rationale', 'No rationale provided')
                    print(f"  Decision Type: {decision_type}")
                    print(f"  Rationale: {rationale}")
                    print(f"  Metadata: {json.dumps(entry.get('metadata', {}), indent=2, default=str)}")
                elif entry_type == 'ARTEFACT':
                    artefact_type = entry.get('artefact_type', 'N/A')
                    artefact_id = entry.get('id', 'N/A')
                    print(f"  Artefact Type: {artefact_type}")
                    print(f"  Artefact ID: {artefact_id}")
                    # Display a summary or just indicate it's available
                    print(f"  Content Summary: {str(entry.get('content_summary', 'Not available'))[:100]}...")
                    print(f"  Use 'artefact_content {artefact_id}' to view full content.")

        except Exception as e:
            print(f"Error retrieving trace for request {request_id}: {str(e)}")

    async def _list_artefacts(self, request_id: int):
        """Lists all artefact snapshots for a given request_id."""
        print(f"\n" + "="*60)
        print(f"ARTEFACTS FOR REQUEST {request_id}")
        print("="*60)

        try:
            artefacts = self.trace_logger.get_artefact_snapshots_for_request(request_id)
            if not artefacts:
                print(f"No artefacts found for request {request_id}.")
                return
            
            for artefact in artefacts:
                artefact_id = artefact.get('id', 'N/A')
                artefact_type = artefact.get('artefact_type', 'N/A')
                agent = artefact.get('agent', 'N/A')
                captured_at = artefact.get('captured_at', 'N/A')
                
                print(f"\nID: {artefact_id}")
                print(f"  Type: {artefact_type}")
                print(f"  Agent: {agent}")
                print(f"  Captured At: {captured_at}")
                # Provide a snippet if available, or just indicate it's viewable
                # Assuming 'content_summary' is part of the returned artefact dict
                if 'content_summary' in artefact:
                    print(f"  Summary: {str(artefact['content_summary'])[:150]}...")
                print(f"  To view full content: artefact_content {artefact_id}")

        except Exception as e:
            print(f"Error listing artefacts for request {request_id}: {str(e)}")

    async def _show_artefact_content(self, artefact_id: int):
        """Displays the full content of a specific artefact by ID."""
        print(f"\n" + "="*60)
        print(f"ARTEFACT CONTENT FOR ID {artefact_id}")
        print("="*60)

        try:
            artefact_data = self.trace_logger.get_artefact_content_by_id(artefact_id)
            if not artefact_data:
                print(f"Artefact with ID {artefact_id} not found.")
                return
            
            print(f"Agent: {artefact_data.get('agent', 'N/A')}")
            print(f"Type: {artefact_data.get('artefact_type', 'N/A')}")
            print(f"Captured At: {artefact_data.get('captured_at', 'N/A')}")
            print("\nFull Content:")
            print(json.dumps(artefact_data.get('content', {}), indent=2, default=str))

        except Exception as e:
            print(f"Error retrieving content for artefact {artefact_id}: {str(e)}")
    
    def _show_help(self):
        """Show help information"""
        print("\nAvailable Commands:")
        print("  help, h               - Show this help message")
        print("  status <request_id>   - Show status of a research request")
        print("  result <request_id>   - Show full results of a completed request")
        print("  trace <request_id>    - Show detailed chronological trace of processing steps")
        print("  artefacts <request_id> - List all intermediate data snapshots for a request")
        print("  artefact_content <id> - Show the full content of a specific artefact by its ID")
        print("  clear                 - Clear the screen")
        print("  quit, exit, q         - Exit the program")
        print("\nTo start a research query, simply type your constitutional law question.")
        print("Examples:")
        print("  • What is the current status of affirmative action in education?")
        print("  • How has the Equal Protection Clause been interpreted recently?")
        print("  • What are the limits on executive power during emergencies?")
        print()

async def main():
    """Main entry point"""
    # Fix for asyncio.run() being called multiple times in interactive mode,
    # or when an event loop is already running.
    # asyncio.run() should ideally be called once.
    # If the CLI enters an interactive loop, the loop should already be running.
    # For a simple command-line query, it's fine.

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
        # asyncio.run() creates and manages the event loop for the entire program execution [3, 6, 8, 9, 10].
        # It should typically be called only once as the main entry point [3, 9, 10].
        # If the CLI is purely interactive, `asyncio.run` encompasses the entire `run_interactive_mode`.
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)