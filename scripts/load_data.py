"""
SenAI CRM Intelligence Platform - Data Loader
Loads email-data-advanced.json into PostgreSQL database
"""

import json
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
import os

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'crm_ai',
    'user': 'postgres',
    'password': 'postgres'  # Change this to your PostgreSQL password
}

# File path
JSON_FILE = r'c:\Users\Aditi\OneDrive\Desktop\Dummy-SenAI\Dummy-SenAI\email-data-advanced.json'


def load_email_data(json_file):
    """Load email data from JSON file"""
    print(f"Loading data from {json_file}...")
    with open(json_file, 'r') as f:
        data = json.load(f)
    print(f"✓ Loaded {len(data)} emails")
    return data


def extract_unique_contacts(emails):
    """Extract unique contacts (senders) from emails"""
    contacts = {}
    for email in emails:
        sender = email['sender']
        if sender not in contacts:
            contacts[sender] = {
                'email': sender,
                'name': extract_name_from_email(sender),
                'company': extract_company_from_email(sender),
                'status': 'Active',
                'account_value': 0.00,
                'churn_risk_score': 0.00,
            }
    return list(contacts.values())


def extract_name_from_email(email):
    """Extract name from email address"""
    name_part = email.split('@')[0]
    return name_part.replace('.', ' ').title()


def extract_company_from_email(email):
    """Extract company from email domain"""
    domain = email.split('@')[1]
    company = domain.split('.')[0]
    return company.replace('-', ' ').title()


def classify_email(email_body, subject):
    """Basic heuristic classification"""
    body_lower = email_body.lower()
    subject_lower = subject.lower()
    
    # Urgency detection
    urgency_keywords = ['urgent', 'p0', 'critical', 'emergency', 'immediately', 'asap']
    urgency = 'Low'
    for keyword in urgency_keywords:
        if keyword in subject_lower or keyword in body_lower:
            if keyword in ['urgent', 'p0', 'critical', 'emergency']:
                urgency = 'Critical'
            elif keyword in ['immediately', 'asap']:
                urgency = 'High'
            break
    
    # Spam detection
    spam_keywords = ['boost', 'seo', 'click here', 'limited offer', 'prince', 'inheritance']
    is_spam = any(keyword in body_lower for keyword in spam_keywords)
    
    # Category detection
    category = 'Other'
    if 'refund' in subject_lower or 'refund' in body_lower:
        category = 'Billing'
    elif 'bug' in subject_lower or 'crash' in body_lower or 'error' in body_lower:
        category = 'Bug Report'
    elif 'feature' in subject_lower or 'request' in body_lower:
        category = 'Feature Request'
    elif 'hipaa' in body_lower or 'compliance' in subject_lower or 'gdpr' in body_lower:
        category = 'Compliance'
    elif 'legal' in subject_lower or 'cease' in body_lower or 'lawsuit' in body_lower:
        category = 'Legal'
    elif 'data' in subject_lower and 'export' in body_lower:
        category = 'Compliance'
    elif is_spam:
        category = 'Spam'
    else:
        category = 'Inquiry'
    
    # Sentiment detection (basic)
    negative_words = ['hate', 'terrible', 'broken', 'angry', 'worst', 'horrible', 'useless']
    positive_words = ['love', 'great', 'excellent', 'perfect', 'amazing', 'wonderful']
    
    sentiment = 'Neutral'
    sentiment_score = 0.0
    
    neg_count = sum(1 for word in negative_words if word in body_lower)
    pos_count = sum(1 for word in positive_words if word in body_lower)
    
    if neg_count > pos_count:
        sentiment = 'Negative'
        sentiment_score = -min(1.0, neg_count * 0.3)
    elif pos_count > neg_count:
        sentiment = 'Positive'
        sentiment_score = min(1.0, pos_count * 0.3)
    
    return {
        'category': category,
        'urgency': urgency,
        'sentiment': sentiment,
        'sentiment_score': sentiment_score,
        'is_spam': is_spam,
        'confidence': 0.75
    }


def insert_contacts(conn, contacts):
    """Insert contacts into database"""
    print(f"\nInserting {len(contacts)} contacts...")
    
    with conn.cursor() as cur:
        sql = """
            INSERT INTO contacts (email, name, company, status, account_value, churn_risk_score)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """
        
        data = [
            (c['email'], c['name'], c['company'], c['status'], c['account_value'], c['churn_risk_score'])
            for c in contacts
        ]
        
        execute_batch(cur, sql, data, page_size=100)
        conn.commit()
        print(f"✓ Inserted {len(contacts)} contacts")


def insert_threads(conn, emails):
    """Insert threads into database"""
    threads = {}
    for email in emails:
        thread_id = email['thread_id']
        if thread_id not in threads:
            threads[thread_id] = {
                'thread_id': thread_id,
                'subject': email['subject'],
                'sender_email': email['sender'],
                'timestamp': email['timestamp'],
            }
    
    print(f"\nInserting {len(threads)} threads...")
    
    with conn.cursor() as cur:
        sql = """
            INSERT INTO threads (thread_id, subject, sender_email, first_seen_at, status)
            VALUES (%s, %s, %s, %s, 'Open')
            ON CONFLICT (thread_id) DO NOTHING
        """
        
        data = [
            (t['thread_id'], t['subject'], t['sender_email'], t['timestamp'])
            for t in threads.values()
        ]
        
        execute_batch(cur, sql, data, page_size=100)
        conn.commit()
        print(f"✓ Inserted {len(threads)} threads")


def get_thread_uuid(conn, thread_id):
    """Get thread UUID from thread_id"""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM threads WHERE thread_id = %s", (thread_id,))
        result = cur.fetchone()
        return result[0] if result else None


def insert_emails(conn, emails):
    """Insert emails into database"""
    print(f"\nInserting {len(emails)} emails...")
    
    with conn.cursor() as cur:
        # Get thread IDs mapping
        cur.execute("SELECT id, thread_id FROM threads")
        threads = {row[1]: row[0] for row in cur.fetchall()}
    
    with conn.cursor() as cur:
        sql = """
            INSERT INTO emails 
            (thread_id, message_id, sender, subject, body, timestamp, 
             category, urgency, sentiment, sentiment_score, confidence, 
             requires_human, status, is_spam, is_security_alert, is_legal_threat)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (message_id) DO NOTHING
        """
        
        data = []
        for email in emails:
            classification = classify_email(email['body'], email['subject'])
            thread_uuid = threads.get(email['thread_id'])
            
            # Determine flags
            is_security = 'security' in email['subject'].lower() or 'ransomware' in email['body'].lower()
            is_legal = 'cease' in email['body'].lower() or 'legal' in email['subject'].lower()
            requires_human = (
                classification['confidence'] < 0.70 or
                classification['urgency'] == 'Critical' or
                is_legal or
                is_security
            )
            
            data.append((
                thread_uuid,
                email['message_id'],
                email['sender'],
                email['subject'],
                email['body'],
                email['timestamp'],
                classification['category'],
                classification['urgency'],
                classification['sentiment'],
                classification['sentiment_score'],
                classification['confidence'],
                requires_human,
                'Received',
                classification['is_spam'],
                is_security,
                is_legal
            ))
        
        execute_batch(cur, sql, data, page_size=100)
        conn.commit()
        print(f"✓ Inserted {len(emails)} emails")


def print_summary(conn):
    """Print data summary"""
    print("\n" + "="*60)
    print("DATA INSERTION SUMMARY")
    print("="*60)
    
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM contacts")
        print(f"✓ Contacts: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM threads")
        print(f"✓ Threads: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM emails")
        print(f"✓ Emails: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM emails WHERE is_spam = TRUE")
        print(f"✓ Spam emails: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM emails WHERE urgency = 'Critical'")
        print(f"✓ Critical emails: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM emails WHERE requires_human = TRUE")
        print(f"✓ Emails requiring human review: {cur.fetchone()[0]}")
        
        cur.execute("""
            SELECT category, COUNT(*) 
            FROM emails 
            WHERE category != 'Spam'
            GROUP BY category 
            ORDER BY COUNT(*) DESC
        """)
        print("\nEmail categories:")
        for category, count in cur.fetchall():
            print(f"  • {category}: {count}")


def main():
    """Main execution"""
    print("="*60)
    print("SenAI CRM - Email Data Loader")
    print("="*60)
    
    # Load JSON
    emails = load_email_data(JSON_FILE)
    
    # Extract contacts
    contacts = extract_unique_contacts(emails)
    print(f"✓ Extracted {len(contacts)} unique contacts")
    
    # Connect to database
    print(f"\nConnecting to database: {DB_CONFIG['database']}...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check that crm_ai database exists")
        print("3. Verify the password in DB_CONFIG")
        return
    
    try:
        # Insert data
        insert_contacts(conn, contacts)
        insert_threads(conn, emails)
        insert_emails(conn, emails)
        
        # Print summary
        print_summary(conn)
        
        print("\n" + "="*60)
        print("✓ DATA INSERTION COMPLETE!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Error during insertion: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == '__main__':
    main()
