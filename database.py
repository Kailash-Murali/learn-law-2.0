import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

class ConstitutionalLawDB:
    """SQLite database handler for constitutional law research system"""
    
    def __init__(self, db_path: str = "constitutional_law.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create user_requests table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    original_query TEXT NOT NULL,
                    query_summary TEXT NOT NULL,  -- JSON formatted
                    status TEXT NOT NULL DEFAULT 'pending'
                )
            ''')
            
            # Create research_results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS research_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    sources TEXT NOT NULL,  -- JSON formatted
                    case_laws TEXT NOT NULL,  -- JSON formatted
                    statutes TEXT NOT NULL,  -- JSON formatted
                    pending_cases TEXT NOT NULL,  -- JSON formatted
                    articles TEXT NOT NULL,  -- JSON formatted
                    research_timestamp DATETIME NOT NULL,
                    FOREIGN KEY (request_id) REFERENCES user_requests (id)
                )
            ''')
            
            # Create documentation_output table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documentation_output (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    output_json TEXT NOT NULL,  -- JSON formatted
                    creation_timestamp DATETIME NOT NULL,
                    FOREIGN KEY (request_id) REFERENCES user_requests (id)
                )
            ''')

            # Create trace_logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trace_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER,
                    agent TEXT NOT NULL,
                    phase TEXT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (request_id) REFERENCES user_requests (id)
                )
            ''')

            # Create artefact_snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS artefact_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER,
                    agent TEXT NOT NULL,
                    artefact_type TEXT NOT NULL,
                    content TEXT NOT NULL, -- This stores the wrapped_content from TraceLogger
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (request_id) REFERENCES user_requests (id)
                )
            ''')

            # Create decision_metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS decision_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER,
                    agent TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    rationale TEXT,
                    metadata TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (request_id) REFERENCES user_requests (id)
                )
            ''')
            
            conn.commit()
    
    def insert_user_request(self, user_id: str, original_query: str, 
                          query_summary: Dict[str, Any]) -> int:
        """Insert a new user request and return the request ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_requests 
                (user_id, timestamp, original_query, query_summary, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                datetime.now().isoformat(), # Store as ISO format string
                original_query,
                json.dumps(query_summary),
                'pending'
            ))
            return cursor.lastrowid
    
    def update_request_status(self, request_id: int, status: str):
        """Update the status of a request"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_requests SET status = ? WHERE id = ?
            ''', (status, request_id))
            conn.commit()
    
    def insert_research_results(self, request_id: int, research_data: Dict[str, Any]) -> int:
        """Insert research results for a request"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO research_results 
                (request_id, sources, case_laws, statutes, pending_cases, articles, research_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                request_id,
                json.dumps(research_data.get('sources', [])),
                json.dumps(research_data.get('case_laws', [])),
                json.dumps(research_data.get('statutes', [])),
                json.dumps(research_data.get('pending_cases', [])),
                json.dumps(research_data.get('articles', [])),
                datetime.now().isoformat() # Store as ISO format string
            ))
            return cursor.lastrowid
    
    def insert_documentation_output(self, request_id: int, output_json: Dict[str, Any]) -> int:
        """Insert documentation output for a request"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO documentation_output 
                (request_id, output_json, creation_timestamp)
                VALUES (?, ?, ?)
            ''', (
                request_id,
                json.dumps(output_json),
                datetime.now().isoformat() # Store as ISO format string
            ))
            return cursor.lastrowid
    
    def get_user_request(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a user request by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user_requests WHERE id = ?', (request_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['query_summary'] = json.loads(result['query_summary'])
                return result
            return None
    
    def get_research_results(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve research results by request ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM research_results WHERE request_id = ?', (request_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Parse JSON fields
                for field in ['sources', 'case_laws', 'statutes', 'pending_cases', 'articles']:
                    result[field] = json.loads(result[field])
                return result
            return None
    
    def get_documentation_output(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve documentation output by request ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM documentation_output WHERE request_id = ?', (request_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['output_json'] = json.loads(result['output_json'])
                return result
            return None

    def insert_trace_log(self, agent: str, event_type: str, payload: Dict[str, Any],
                         request_id: Optional[int] = None, phase: Optional[str] = None) -> int:
        """Insert a structured trace log entry"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trace_logs (request_id, agent, phase, event_type, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                request_id,
                agent,
                phase,
                event_type,
                json.dumps(payload, default=str),
                datetime.now().isoformat() # Store as ISO format string
            ))
            conn.commit()
            return cursor.lastrowid

    def insert_artefact_snapshot(self, agent: str, artefact_type: str, content: Dict[str, Any],
                                 request_id: Optional[int] = None) -> int:
        """Persist an artefact snapshot for explainability"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO artefact_snapshots (request_id, agent, artefact_type, content, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                request_id,
                agent,
                artefact_type,
                json.dumps(content, default=str), # This 'content' is the wrapped_content from TraceLogger
                datetime.now().isoformat() # Store as ISO format string
            ))
            conn.commit()
            return cursor.lastrowid

    def insert_decision_metadata(self, agent: str, decision_type: str, metadata: Dict[str, Any],
                                 request_id: Optional[int] = None, rationale: Optional[str] = None) -> int:
        """Persist decision metadata for traceability"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO decision_metadata (request_id, agent, decision_type, rationale, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                request_id,
                agent,
                decision_type,
                rationale,
                json.dumps(metadata, default=str),
                datetime.now().isoformat() # Store as ISO format string
            ))
            conn.commit()
            return cursor.lastrowid

    def get_combined_request_trace_data(self, request_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all trace events, decisions, and artefact snapshots for a given request_id,
        sorted chronologically by their logging/recording/capture timestamp.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            combined_data = []

            # Fetch trace logs
            cursor.execute('''
                SELECT id, request_id, agent, phase, event_type, payload, created_at 
                FROM trace_logs WHERE request_id = ?
            ''', (request_id,))
            for row in cursor.fetchall():
                entry = dict(row)
                entry['type'] = 'event'
                entry['logged_at'] = entry.pop('created_at') # Standardize timestamp key
                entry['payload'] = json.loads(entry['payload'])
                combined_data.append(entry)

            # Fetch artefact snapshots
            cursor.execute('''
                SELECT id, request_id, agent, artefact_type, content, created_at 
                FROM artefact_snapshots WHERE request_id = ?
            ''', (request_id,))
            for row in cursor.fetchall():
                entry = dict(row)
                entry['type'] = 'artefact'
                entry['captured_at'] = entry.pop('created_at') # Standardize timestamp key
                
                # The 'content' column contains the wrapped_content from TraceLogger
                wrapped_content = json.loads(entry.pop('content'))
                
                # Extract original content and provide a summary for the trace view
                entry['content_hash'] = wrapped_content.get('content_hash')
                entry['original_content'] = wrapped_content.get('content') # Keep full content for potential drill-down
                
                # Create a concise summary for the trace display
                content_summary_str = str(wrapped_content.get('content', {}))
                entry['content_summary'] = content_summary_str[:150] + ('...' if len(content_summary_str) > 150 else '')
                combined_data.append(entry)

            # Fetch decision metadata
            cursor.execute('''
                SELECT id, request_id, agent, decision_type, rationale, metadata, created_at 
                FROM decision_metadata WHERE request_id = ?
            ''', (request_id,))
            for row in cursor.fetchall():
                entry = dict(row)
                entry['type'] = 'decision'
                entry['recorded_at'] = entry.pop('created_at') # Standardize timestamp key
                entry['metadata'] = json.loads(entry['metadata'])
                combined_data.append(entry)
            
            # Sort all entries by their timestamp
            # We need to use the specific timestamp key for each type
            def get_sort_key(item):
                if item['type'] == 'event':
                    return item['logged_at']
                elif item['type'] == 'artefact':
                    return item['captured_at']
                elif item['type'] == 'decision':
                    return item['recorded_at']
                return "1970-01-01T00:00:00.000000" # Fallback for unexpected types

            combined_data.sort(key=get_sort_key)
            return combined_data

    def get_artefact_snapshots_for_request(self, request_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves summary details for all artefact snapshots for a given request_id.
        Each dictionary includes 'id', 'agent', 'artefact_type', 'captured_at', and a content_summary.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, request_id, agent, artefact_type, content, created_at 
                FROM artefact_snapshots WHERE request_id = ? ORDER BY created_at ASC
            ''', (request_id,))
            
            artefact_summaries = []
            for row in cursor.fetchall():
                entry = dict(row)
                
                # The 'content' column stores the wrapped_content from TraceLogger
                wrapped_content = json.loads(entry.pop('content'))
                
                # Extract relevant information
                entry['captured_at'] = entry.pop('created_at') # Rename for consistency
                
                # Create a concise summary of the actual content
                actual_content = wrapped_content.get('content', {})
                content_summary_str = str(actual_content)
                entry['content_summary'] = content_summary_str[:150] + ('...' if len(content_summary_str) > 150 else '')
                
                artefact_summaries.append(entry)
            
            return artefact_summaries

    def get_artefact_full_content_by_id(self, artefact_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves the full 'content' of an artefact snapshot by its ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, agent, artefact_type, content, created_at 
                FROM artefact_snapshots WHERE id = ?
            ''', (artefact_id,))
            row = cursor.fetchone()
            
            if row:
                entry = dict(row)
                
                # The 'content' column stores the wrapped_content from TraceLogger
                wrapped_content = json.loads(entry.pop('content'))
                
                # We want to return the actual 'content' part, not the wrapper
                result = {
                    'id': entry['id'],
                    'agent': entry['agent'],
                    'artefact_type': entry['artefact_type'],
                    'captured_at': entry['created_at'], # Use the database's creation time
                    'content': wrapped_content.get('content') # This is the actual artefact content
                }
                return result
            return None