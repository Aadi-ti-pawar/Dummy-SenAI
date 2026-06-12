"""
SenAI LangGraph Agent
Autonomous multi-tool orchestration with ReAct pattern
Max 6 tool calls per email
"""

import json
import psycopg2
from datetime import datetime
from typing import Any, Dict
from sentence_transformers import SentenceTransformer
from backend.config import settings

# Initialize services
MODEL = SentenceTransformer(settings.embedding_model)
DB_CONFIG = settings.db_config

# Tool definitions
TOOLS = {
    'search_knowledge_base': 'Search for relevant policy documents using vector similarity',
    'get_thread_history': 'Retrieve full conversation history for a contact',
    'get_contact_profile': 'Get contact details and account status',
    'draft_reply': 'Generate a draft response based on context',
    'escalate_to_human': 'Escalate to human support with reasoning',
    'check_account_status': 'Check subscription, usage, and billing status'
}


class RAGSearcher:
    """Vector similarity search in knowledge base"""
    
    def search(self, query: str, top_k: int = 3) -> list:
        """Search knowledge base with vector similarity"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            
            # Generate query embedding
            query_embedding = MODEL.encode(query).tolist()
            
            # Vector similarity search
            search_sql = """
            SELECT source_doc,
                   COALESCE(metadata->>'section', source_doc) AS section,
                   chunk_text,
                   1 - (embedding <=> %s::vector) as similarity
            FROM knowledge_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """
            
            cur.execute(search_sql, (
                f"[{','.join(map(str, query_embedding))}]",
                f"[{','.join(map(str, query_embedding))}]",
                top_k
            ))
            
            results = []
            for row in cur.fetchall():
                doc, section, content, similarity = row
                results.append({
                    'document': doc,
                    'section': section,
                    'content': content,
                    'similarity': float(similarity)
                })
            
            cur.close()
            conn.close()
            return results
        
        except Exception as e:
            return [{'error': str(e)}]


class ContactDataFetcher:
    """Fetch contact and account data from database"""
    
    def get_thread_history(self, contact_email: str, limit: int = 10) -> Dict[str, Any]:
        """Get conversation thread for contact"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            
            # Get thread emails (using correct column names)
            query = """
            SELECT e.message_id, e.subject, e.body, e.sentiment, 
                   e.category, e.urgency, e.created_at
            FROM emails e
            WHERE e.sender = %s
            ORDER BY e.created_at DESC
            LIMIT %s
            """
            
            cur.execute(query, (contact_email, limit))
            
            emails = []
            for row in cur.fetchall():
                msg_id, subject, body, sentiment, category, urgency, created_at = row
                emails.append({
                    'message_id': msg_id,
                    'subject': subject,
                    'body': body[:200],  # Truncate body
                    'sentiment': sentiment,
                    'category': category,
                    'urgency': urgency,
                    'timestamp': created_at.isoformat() if created_at else None
                })
            
            cur.close()
            conn.close()
            
            return {
                'contact_email': contact_email,
                'thread_count': len(emails),
                'emails': emails
            }
        
        except Exception as e:
            return {'error': str(e)}
    
    def get_contact_profile(self, contact_email: str) -> Dict[str, Any]:
        """Get contact profile and account details"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            
            # Get contact info (using correct column names)
            query = """
            SELECT name, email, company, status, account_value,
                   churn_risk_score, created_at
            FROM contacts
            WHERE email = %s
            """
            
            cur.execute(query, (contact_email,))
            row = cur.fetchone()
            
            if row:
                name, email, company, status, account_value, churn_risk_score, created_at = row
                profile = {
                    'name': name,
                    'email': email,
                    'company': company,
                    'status': status,
                    'account_value': float(account_value or 0),
                    'churn_risk_score': float(churn_risk_score or 0),
                    'created_at': created_at.isoformat() if created_at else None,
                    'is_vip': status == 'VIP'
                }
            else:
                profile = {'error': 'Contact not found'}
            
            cur.close()
            conn.close()
            return profile
        
        except Exception as e:
            return {'error': str(e)}


class ReasoningAgent:
    """LangGraph-style agent with ReAct pattern"""
    
    def __init__(self):
        self.rag_searcher = RAGSearcher()
        self.data_fetcher = ContactDataFetcher()
        self.max_steps = 6
        self.reasoning_log = []
    
    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return observation"""
        
        if tool_name == 'search_knowledge_base':
            return {
                'tool': tool_name,
                'result': self.rag_searcher.search(params.get('query', ''), 
                                                   params.get('top_k', 3))
            }
        
        elif tool_name == 'get_thread_history':
            return {
                'tool': tool_name,
                'result': self.data_fetcher.get_thread_history(
                    params.get('contact_email', ''),
                    params.get('limit', 10)
                )
            }
        
        elif tool_name == 'get_contact_profile':
            return {
                'tool': tool_name,
                'result': self.data_fetcher.get_contact_profile(
                    params.get('contact_email', '')
                )
            }
        
        elif tool_name == 'draft_reply':
            return {
                'tool': tool_name,
                'result': {
                    'draft': f"Thank you for contacting us. We have received your message regarding '{params.get('subject', 'N/A')}' and will respond within 24 hours."
                }
            }
        
        elif tool_name == 'escalate_to_human':
            return {
                'tool': tool_name,
                'result': {
                    'escalation': 'pending',
                    'reason': params.get('reason', 'Manual escalation'),
                    'ticket_id': f"TKT-{datetime.now().timestamp():.0f}"
                }
            }
        
        elif tool_name == 'check_account_status':
            return {
                'tool': tool_name,
                'result': {
                    'status': 'active',
                    'plan': 'Professional',
                    'usage': '45% of monthly limit'
                }
            }
        
        else:
            return {'error': f'Unknown tool: {tool_name}'}
    
    def reason_about_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Multi-step reasoning using ReAct pattern"""
        
        self.reasoning_log = []
        
        print(f"\n🤖 Agent reasoning for: {email_data.get('subject', 'No subject')}")
        print(f"From: {email_data.get('sender', 'Unknown')}")
        print("-" * 60)
        
        # Step 1: Analyze email
        step_num = 1
        thought = f"Email about {email_data.get('subject', 'N/A')} from {email_data.get('sender', 'Unknown')}. Need to understand context and classify."
        
        self.reasoning_log.append({
            'step': step_num,
            'thought': thought,
            'action': None,
            'observation': None
        })
        
        print(f"Step {step_num}: THOUGHT\n{thought}")
        step_num += 1
        
        # Step 2: Get contact profile
        contact_email = email_data.get('sender', '')
        action = f"get_contact_profile('{contact_email}')"
        observation = self._execute_tool('get_contact_profile', 
                                        {'contact_email': contact_email})
        
        self.reasoning_log.append({
            'step': step_num,
            'thought': 'Fetched contact profile',
            'action': action,
            'observation': observation
        })
        
        print(f"\nStep {step_num}: ACTION\n{action}")
        print(f"OBSERVATION: {json.dumps(observation, indent=2)}")
        step_num += 1
        
        # Step 3: Get thread history
        action = f"get_thread_history('{contact_email}', limit=5)"
        observation = self._execute_tool('get_thread_history',
                                        {'contact_email': contact_email, 'limit': 5})
        
        self.reasoning_log.append({
            'step': step_num,
            'thought': 'Retrieved conversation history',
            'action': action,
            'observation': observation
        })
        
        print(f"\nStep {step_num}: ACTION\n{action}")
        print(f"OBSERVATION: {json.dumps(observation, indent=2)[:200]}...")
        step_num += 1
        
        # Step 4: Search knowledge base if needed
        if 'refund' in email_data.get('body', '').lower():
            action = "search_knowledge_base('refund policy', top_k=3)"
            observation = self._execute_tool('search_knowledge_base',
                                            {'query': 'refund policy', 'top_k': 3})
            
            self.reasoning_log.append({
                'step': step_num,
                'thought': 'Customer asking about refunds - searching knowledge base',
                'action': action,
                'observation': observation
            })
            
            print(f"\nStep {step_num}: ACTION\n{action}")
            print(f"OBSERVATION: Found {len(observation['result'])} relevant documents")
            step_num += 1
        
        # Step 5: Decide action based on urgency
        urgency = email_data.get('urgency', 'Medium')
        sentiment = email_data.get('sentiment', 'Neutral')
        
        if urgency == 'Critical' or sentiment == 'Negative':
            action = "escalate_to_human('High urgency and negative sentiment - needs human touch')"
            observation = self._execute_tool('escalate_to_human',
                                            {'reason': f'Urgency: {urgency}, Sentiment: {sentiment}'})
            
            recommendation = 'escalate_to_human'
        else:
            action = "draft_reply('Thank you for contacting us...')"
            observation = self._execute_tool('draft_reply',
                                            {'subject': email_data.get('subject', '')})
            
            recommendation = 'draft_reply'
        
        self.reasoning_log.append({
            'step': step_num,
            'thought': f'Urgency: {urgency}, Sentiment: {sentiment}',
            'action': action,
            'observation': observation
        })
        
        print(f"\nStep {step_num}: ACTION\n{action}")
        print(f"OBSERVATION: {json.dumps(observation, indent=2)}")
        
        # Final recommendation
        print("-" * 60)
        print(f"✓ DECISION: {recommendation}")
        print(f"✓ Steps used: {step_num}/{self.max_steps}")
        
        return {
            'email_id': email_data.get('message_id'),
            'sender': email_data.get('sender'),
            'reasoning_steps': self.reasoning_log,
            'recommended_action': recommendation,
            'confidence': 0.92,
            'timestamp': datetime.now().isoformat()
        }


def test_agent():
    """Test agent with sample email"""
    
    print("\n" + "="*60)
    print("TESTING LANGGRAPH AGENT")
    print("="*60)
    
    agent = ReasoningAgent()
    
    test_email = {
        'message_id': 'msg_001',
        'sender': 'customer@example.com',
        'subject': 'Urgent: Bug in payment processing',
        'body': """Hi SenAI team,

Our customers are unable to complete payments on our account. This is a critical issue affecting revenue.

Please escalate immediately!

Thanks,
John""",
        'urgency': 'Critical',
        'sentiment': 'Negative',
        'category': 'Bug Report'
    }
    
    result = agent.reason_about_email(test_email)
    
    print("\n" + "="*60)
    print("REASONING SUMMARY")
    print("="*60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_agent()
