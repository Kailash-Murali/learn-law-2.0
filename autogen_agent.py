"""
AutoGen-based Legal Research Multi-Agent System

This module implements the legal research workflow using AutoGen
for agent coordination, with Groq as the LLM backend.

Enhanced with XAI (Explainable AI) capabilities for transparency.
"""

from typing import Dict, List, Any, Optional
import json
import asyncio
from datetime import datetime
from groq import Groq
from config import Config
from database import ConstitutionalLawDB
from trace_logger import TraceLogger

# Initialize Groq client
groq_client = Groq(api_key=Config.GROQ_API_KEY)

# Initialize database and trace logger
db = ConstitutionalLawDB()
trace_logger = TraceLogger(db)


class LegalAgent:
    """Base class for legal research agents with XAI traceability"""
    
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.request_id: Optional[int] = None
        self.reasoning_steps: List[Dict[str, Any]] = []
    
    def set_request_id(self, request_id: int):
        """Set the request ID for traceability"""
        self.request_id = request_id
    
    def log_reasoning_step(self, step: str, details: Dict[str, Any]):
        """Log a reasoning step for XAI transparency"""
        step_entry = {
            "agent": self.name,
            "step": step,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.reasoning_steps.append(step_entry)
        
        # Log to trace logger if request_id is set
        if self.request_id:
            trace_logger.record_decision(
                request_id=self.request_id,
                agent=self.name,
                decision_point=step,
                chosen_path=details.get("action", "unknown"),
                alternatives=[details.get("alternatives", "N/A")],
                rationale=details.get("rationale", "Not specified"),
                metadata=details
            )
    
    def call_llm(self, prompt: str, log_reasoning: bool = True) -> str:
        """Call Groq LLM with XAI logging"""
        
        if log_reasoning:
            self.log_reasoning_step(
                "llm_call_initiated",
                {
                    "action": "calling_llm",
                    "prompt_length": len(prompt),
                    "rationale": f"Agent {self.name} requires LLM assistance"
                }
            )
        
        try:
            response = groq_client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            
            # Log the response for traceability
            if self.request_id:
                trace_logger.snapshot_artefact(
                    request_id=self.request_id,
                    artefact_type=f"{self.name}_llm_response",
                    content=result,
                    agent=self.name,
                    metadata={"model": Config.GROQ_MODEL}
                )
            
            if log_reasoning:
                self.log_reasoning_step(
                    "llm_response_received",
                    {
                        "action": "response_processed",
                        "response_length": len(result),
                        "rationale": "LLM provided response successfully"
                    }
                )
            
            return result
        except Exception as e:
            if log_reasoning:
                self.log_reasoning_step(
                    "llm_error",
                    {
                        "action": "error_occurred",
                        "error": str(e),
                        "rationale": "LLM call failed"
                    }
                )
            return f"Error: {str(e)}"
    
    def get_reasoning_trace(self) -> List[Dict[str, Any]]:
        """Get the reasoning trace for this agent"""
        return self.reasoning_steps.copy()
    
    def clear_reasoning_trace(self):
        """Clear the reasoning trace"""
        self.reasoning_steps = []


class UIAgent(LegalAgent):
    """Parses and structures user queries with XAI transparency"""
    
    def __init__(self):
        super().__init__(
            name="UIAgent",
            system_prompt="""You are a legal query parser. Your job is to:
1. Understand the user's legal research query
2. Extract key topics, jurisdictions, and keywords
3. Return a structured JSON response

Always respond with valid JSON in this format:
{
    "topic": "main legal topic",
    "jurisdiction": "India" or specific state,
    "keywords": ["keyword1", "keyword2"],
    "document_types": ["case_law", "statutes", "articles"],
    "time_period": "any specific time constraints"
}"""
        )
    
    def parse(self, query: str) -> Dict[str, Any]:
        """Parse user query into structured format with XAI logging"""
        print(f"📝 {self.name}: Parsing query...")
        
        # Log reasoning step
        self.log_reasoning_step(
            "query_analysis_started",
            {
                "action": "analyzing_user_query",
                "query_length": len(query),
                "rationale": "Need to extract structured information from natural language query",
                "alternatives": "Could use regex-based extraction or direct keyword matching"
            }
        )
        
        response = self.call_llm(f"Parse this legal research query:\n\n{query}")
        
        try:
            # Try to extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
            else:
                json_str = response
            
            result = json.loads(json_str)
            
            # Log successful parsing
            self.log_reasoning_step(
                "query_parsed_successfully",
                {
                    "action": "json_extraction_success",
                    "extracted_topic": result.get("topic", ""),
                    "keyword_count": len(result.get("keywords", [])),
                    "rationale": "Successfully extracted structured query information"
                }
            )
            
            return result
        except Exception as e:
            # Log parsing failure
            self.log_reasoning_step(
                "query_parsing_fallback",
                {
                    "action": "using_default_structure",
                    "error": str(e),
                    "rationale": "JSON parsing failed, using fallback extraction method"
                }
            )
            
            # Return default structure if parsing fails
            return {
                "topic": query,
                "jurisdiction": "India",
                "keywords": query.split()[:5],
                "document_types": ["case_law", "statutes"],
                "time_period": "all"
            }


class ResearchAgent(LegalAgent):
    """Conducts legal research with XAI transparency"""
    
    def __init__(self):
        super().__init__(
            name="ResearchAgent",
            system_prompt="""You are an expert legal researcher specializing in Indian Constitutional Law.
Your job is to:
1. Find relevant case laws, statutes, and legal principles
2. Provide accurate citations
3. Summarize key holdings and principles

Always provide well-researched, accurate legal information with proper citations."""
        )
    
    def research(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct legal research based on parsed query with XAI logging"""
        print(f"🔍 {self.name}: Conducting research...")
        
        # Log research strategy selection
        self.log_reasoning_step(
            "research_strategy_selection",
            {
                "action": "selecting_research_approach",
                "topic": parsed_query.get("topic", ""),
                "jurisdiction": parsed_query.get("jurisdiction", "India"),
                "rationale": "Choosing appropriate research methodology based on query characteristics",
                "alternatives": "Could use different databases, API sources, or search strategies"
            }
        )
        
        prompt = f"""
Research the following legal topic:

Topic: {parsed_query.get('topic', '')}
Jurisdiction: {parsed_query.get('jurisdiction', 'India')}
Keywords: {', '.join(parsed_query.get('keywords', []))}

Provide:
1. Relevant constitutional articles/provisions
2. Key case laws with citations (case name, year, court)
3. Important legal principles established
4. Any relevant statutes

Format your response as detailed legal research."""

        response = self.call_llm(prompt)
        
        # Log research completion
        self.log_reasoning_step(
            "research_completed",
            {
                "action": "research_results_compiled",
                "response_length": len(response),
                "sources_used": ["Indian Kanoon", "Supreme Court Judgments", "Constitutional Provisions"],
                "rationale": "Research completed using constitutional law knowledge base"
            }
        )
        
        return {
            "query_info": parsed_query,
            "research_content": response,
            "sources": ["Indian Kanoon", "Supreme Court Judgments", "Constitutional Provisions"],
            "status": "completed",
            "reasoning_trace": self.get_reasoning_trace()
        }


class DocumentationAgent(LegalAgent):
    """Generates legal documentation and reports with XAI transparency"""
    
    def __init__(self):
        super().__init__(
            name="DocumentationAgent",
            system_prompt="""You are a legal documentation specialist.
Your job is to:
1. Create professional legal research reports
2. Organize information clearly with proper sections
3. Provide executive summaries and recommendations

Format all reports professionally with clear headings and structure."""
        )
    
    def generate_report(self, query: str, research: Dict[str, Any]) -> Dict[str, Any]:
        """Generate documentation from research results with XAI logging"""
        print(f"📄 {self.name}: Generating report...")
        
        # Log report structure decision
        self.log_reasoning_step(
            "report_structure_selection",
            {
                "action": "selecting_report_format",
                "sections": ["Executive Summary", "Legal Background", "Case Laws", "Analysis", "Conclusion", "Recommendations"],
                "rationale": "Standard legal research report format provides comprehensive coverage",
                "alternatives": "Could use brief memo format, Q&A format, or annotated bibliography"
            }
        )
        
        prompt = f"""
Create a professional legal research report based on:

Original Query: {query}

Research Findings:
{research.get('research_content', '')}

Generate a report with these sections:
1. EXECUTIVE SUMMARY (2-3 paragraphs)
2. LEGAL BACKGROUND
3. RELEVANT CASE LAWS
4. ANALYSIS
5. CONCLUSION
6. RECOMMENDATIONS (bullet points)

Make it professional and well-structured."""

        response = self.call_llm(prompt)
        
        # Extract recommendations
        recommendations = []
        if "RECOMMENDATIONS" in response:
            rec_section = response.split("RECOMMENDATIONS")[1]
            lines = rec_section.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith(("•", "-", "*", "1", "2", "3")):
                    recommendations.append(line.lstrip("•-*0123456789. "))
        
        # Log documentation completion
        self.log_reasoning_step(
            "documentation_completed",
            {
                "action": "report_generated",
                "report_length": len(response),
                "recommendations_count": len(recommendations),
                "rationale": "Comprehensive legal report generated with all required sections"
            }
        )
        
        return {
            "full_report": response,
            "executive_summary": response.split("LEGAL BACKGROUND")[0].replace("EXECUTIVE SUMMARY", "").strip() if "LEGAL BACKGROUND" in response else response[:500],
            "recommendations": recommendations[:5],
            "status": "completed",
            "reasoning_trace": self.get_reasoning_trace()
        }


class Coordinator:
    """Coordinates the multi-agent workflow with XAI traceability"""
    
    def __init__(self):
        self.ui_agent = UIAgent()
        self.research_agent = ResearchAgent()
        self.documentation_agent = DocumentationAgent()
        self.workflow_trace: List[Dict[str, Any]] = []
    
    def _log_workflow_step(self, step: str, agent: str, details: Dict[str, Any]):
        """Log a workflow step for XAI transparency"""
        self.workflow_trace.append({
            "step": step,
            "agent": agent,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def run(self, query: str, enable_xai: bool = False) -> Dict[str, Any]:
        """Run the complete research workflow with optional XAI explanation"""
        print("\n" + "=" * 60)
        print("🏛️  Legal Research Multi-Agent System")
        if enable_xai:
            print("🔬 XAI Mode: Enabled")
        print("=" * 60)
        print(f"\nQuery: {query}\n")
        
        # Clear previous traces
        self.workflow_trace = []
        self.ui_agent.clear_reasoning_trace()
        self.research_agent.clear_reasoning_trace()
        self.documentation_agent.clear_reasoning_trace()
        
        # Create request in trace logger for traceability
        request_id = None
        try:
            request_id = trace_logger.create_request(query)
            self.ui_agent.set_request_id(request_id)
            self.research_agent.set_request_id(request_id)
            self.documentation_agent.set_request_id(request_id)
        except Exception:
            pass
        
        result = {
            "query": query,
            "parsed_query": {},
            "research": {},
            "documentation": {},
            "status": "started",
            "error": None,
            "request_id": request_id,
            "workflow_trace": [],
            "agent_reasoning_traces": {}
        }
        
        try:
            # Step 1: Parse Query
            self._log_workflow_step("query_parsing", "UIAgent", {"query": query})
            if request_id:
                trace_logger.log_event(request_id, "UIAgent", "query_parsing", {"query": query})
            
            result["parsed_query"] = self.ui_agent.parse(query)
            print(f"✅ Query parsed: {result['parsed_query'].get('topic', query)}\n")
            
            # Step 2: Conduct Research
            self._log_workflow_step("research_execution", "ResearchAgent", 
                                   {"topic": result["parsed_query"].get("topic", "")})
            if request_id:
                trace_logger.log_event(request_id, "ResearchAgent", "research_started", 
                                      {"parsed_query": result["parsed_query"]})
            
            result["research"] = self.research_agent.research(result["parsed_query"])
            print(f"✅ Research completed\n")
            
            # Step 3: Generate Documentation
            self._log_workflow_step("documentation_generation", "DocumentationAgent",
                                   {"research_available": True})
            if request_id:
                trace_logger.log_event(request_id, "DocumentationAgent", "documentation_started", {})
            
            result["documentation"] = self.documentation_agent.generate_report(
                query, 
                result["research"]
            )
            print(f"✅ Documentation generated\n")
            
            result["status"] = "completed"
            
            # Collect reasoning traces
            result["workflow_trace"] = self.workflow_trace
            result["agent_reasoning_traces"] = {
                "UIAgent": self.ui_agent.get_reasoning_trace(),
                "ResearchAgent": self.research_agent.get_reasoning_trace(),
                "DocumentationAgent": self.documentation_agent.get_reasoning_trace()
            }
            
            # Log completion
            if request_id:
                trace_logger.log_event(request_id, "Coordinator", "workflow_completed", 
                                      {"status": "success"})
            
            # Generate XAI explanation if enabled (using advanced_xai module)
            if enable_xai:
                try:
                    from advanced_xai import generate_advanced_xai_explanation
                    print("🔬 Generating Advanced XAI Explanation...")
                    explanation, formatted_report = generate_advanced_xai_explanation(query, result)
                    result["xai_explanation"] = explanation
                    result["xai_report_formatted"] = formatted_report
                except ImportError as e:
                    print(f"⚠️ Advanced XAI module not available: {e}")
                except Exception as e:
                    print(f"⚠️ XAI explanation generation failed: {e}")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            print(f"❌ Error: {e}\n")
            
            if request_id:
                trace_logger.log_event(request_id, "Coordinator", "workflow_failed", 
                                      {"error": str(e)})
        
        return result
    
    def get_full_trace(self, request_id: int) -> Dict[str, Any]:
        """Get the full trace for a request from the database"""
        return trace_logger.get_full_request_trace(request_id)


class AutoGenLegalResearch:
    """Main interface for the legal research system with XAI support"""
    
    def __init__(self, enable_xai: bool = False):
        self.coordinator = Coordinator()
        self.enable_xai = enable_xai
    
    def run_research(self, query: str) -> Dict[str, Any]:
        """Run research and return results"""
        return self.coordinator.run(query, enable_xai=self.enable_xai)
    
    def run_research_with_xai(self, query: str) -> Dict[str, Any]:
        """Run research with XAI explanation enabled"""
        return self.coordinator.run(query, enable_xai=True)
    
    def parse_query(self, query: str) -> Dict[str, Any]:
        """Parse query only"""
        return self.coordinator.ui_agent.parse(query)
    
    def conduct_research(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct research only"""
        return self.coordinator.research_agent.research(parsed_query)
    
    def generate_documentation(self, query: str, parsed_query: Dict, research: Dict) -> Dict[str, Any]:
        """Generate documentation only"""
        return self.coordinator.documentation_agent.generate_report(query, research)
    
    def get_trace(self, request_id: int) -> Dict[str, Any]:
        """Get the full trace for a completed request"""
        return self.coordinator.get_full_trace(request_id)


def run_autogen_research(query: str, enable_xai: bool = False) -> Dict[str, Any]:
    """Convenience function to run research with optional XAI"""
    system = AutoGenLegalResearch(enable_xai=enable_xai)
    return system.run_research(query)


if __name__ == "__main__":
    import sys
    
    # Test the system with XAI
    query = "What are the fundamental rights under Article 21 of Indian Constitution?"
    
    # Check for --xai flag
    enable_xai = "--xai" in sys.argv
    
    result = run_autogen_research(query, enable_xai=enable_xai)
    
    print("\n" + "=" * 60)
    print(f"Status: {result['status']}")
    print("=" * 60)
    
    if result["documentation"]:
        print("\n📋 EXECUTIVE SUMMARY:\n")
        print(result["documentation"].get("executive_summary", "N/A"))
        
        print("\n📌 RECOMMENDATIONS:\n")
        for rec in result["documentation"].get("recommendations", []):
            print(f"  • {rec}")
    
    # Print XAI report if enabled
    if enable_xai and "xai_report_formatted" in result:
        print(result["xai_report_formatted"])
    
    # Print reasoning trace summary
    if result.get("agent_reasoning_traces"):
        print("\n" + "=" * 60)
        print("📊 AGENT REASONING SUMMARY")
        print("=" * 60)
        for agent, trace in result["agent_reasoning_traces"].items():
            print(f"\n{agent}: {len(trace)} reasoning steps")
            for step in trace[:2]:  # Show first 2 steps
                print(f"  - {step.get('step', 'N/A')}: {step.get('details', {}).get('action', 'N/A')}")
    
    if result["error"]:
        print(f"\n❌ Error: {result['error']}")