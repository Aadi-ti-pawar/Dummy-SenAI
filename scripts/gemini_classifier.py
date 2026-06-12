"""
SenAI Gemini API Integration
LLM-based email classification with reasoning
"""

import json
import google.generativeai as genai
from backend.config import settings

# Configure Gemini from environment variables.
genai.configure(api_key=settings.gemini_api_key)
MODEL_NAME = settings.gemini_model

# System prompt for email classification
SYSTEM_PROMPT = """You are an expert customer support AI classifier for SenAI CRM platform.

Analyze the following customer email and provide classification in JSON format.

REQUIRED OUTPUT (valid JSON only):
{
    "category": "category_name",
    "urgency": "urgency_level",
    "sentiment": "sentiment_value",
    "sentiment_score": score_float,
    "confidence": confidence_float,
    "is_spam": boolean,
    "is_security_alert": boolean,
    "is_legal_threat": boolean,
    "is_gdpr_request": boolean,
    "reasoning": "brief_explanation"
}

CLASSIFICATION RULES:

Categories (choose ONE):
- "Bug Report": Customer reports a defect or malfunction
- "Feature Request": Customer requests new functionality
- "Billing": Questions about pricing, invoices, payments
- "Compliance": Data privacy, GDPR, compliance questions
- "Legal": Legal threats, disputes, liability claims
- "Inquiry": General questions about product/service
- "Complaint": Customer dissatisfaction, poor experience
- "Other": Doesn't fit above categories

Urgency (choose ONE):
- "Critical": System down, data loss, legal threat, revenue impact
- "High": Feature broken, customer unhappy, needs urgent fix
- "Medium": Important but can wait 24h
- "Low": General inquiry, feature request

Sentiment (choose ONE):
- "Positive": Customer happy, complimentary, grateful
- "Neutral": Factual, no emotional tone
- "Negative": Unhappy, frustrated, angry, disappointed

Sentiment Score: Float -1.0 (very negative) to +1.0 (very positive)

Confidence: Float 0.0 (uncertain) to 1.0 (very certain)
- >0.90: Very confident
- 0.70-0.90: Confident
- <0.70: Uncertain (escalate to human)

Flags:
- is_spam: True if promotional content, unsolicited offer, etc.
- is_security_alert: True if mentions breach, hack, stolen credentials, malware
- is_legal_threat: True if mentions lawsuit, attorney, court, damages
- is_gdpr_request: True if mentions GDPR, data portability, right to be forgotten

OUTPUT MUST BE VALID JSON ONLY. No markdown, no explanations outside JSON.
"""


def classify_email_with_gemini(email_data):
    """Classify email using Gemini API with streaming"""
    
    try:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        # Prepare email text
        email_text = f"""
Subject: {email_data.get('subject', 'No subject')}

From: {email_data.get('sender', 'Unknown')}
Timestamp: {email_data.get('timestamp', 'Unknown')}

Body:
{email_data.get('body', 'No body')}
"""
        
        # Call Gemini with streaming
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = f"{SYSTEM_PROMPT}\n\nEMAIL TO CLASSIFY:\n{email_text}"
        
        response = model.generate_content(
            prompt,
            stream=False,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # Lower temperature for more consistent classification
                max_output_tokens=1024
            )
        )
        
        # Extract and parse JSON response
        response_text = response.text.strip()
        
        # Find JSON in response (sometimes Gemini adds text before/after)
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            classification = json.loads(json_str)
        else:
            raise ValueError("No valid JSON found in response")
        
        return {
            'success': True,
            'classification': classification,
            'raw_response': response_text
        }
    
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return {
            'success': False,
            'error': str(e),
            'raw_response': None
        }


def test_gemini_classification():
    """Test Gemini classification with sample emails"""
    
    print("\n" + "="*60)
    print("TESTING GEMINI API CLASSIFICATION")
    print("="*60)
    
    test_emails = [
        {
            'message_id': 'test_001',
            'sender': 'customer@example.com',
            'subject': 'Urgent: Payment declined on Enterprise plan',
            'body': """Hi SenAI team,

I've been trying to renew my Enterprise subscription but our payment keeps getting declined. 
This is impacting our business and we need this resolved TODAY.

The error message isn't helpful. Can someone call me at +1-555-0123?

Thanks,
John"""
        },
        {
            'message_id': 'test_002',
            'sender': 'spammer@badsite.com',
            'subject': 'Click HERE to boost your SenAI performance by 500%!',
            'body': """LIMITED TIME OFFER!

Dear SenAI User,

We've discovered a secret technique that will make your AI 500% faster.
Prince Hareem of Nigeria wants to partner with you. Act now!

CLICK HERE NOW: [malicious_link]

Only $99/month!"""
        },
        {
            'message_id': 'test_003',
            'sender': 'legal@bigcorp.com',
            'subject': 'LEGAL NOTICE: Data Breach Liability Claim',
            'body': """Dear SenAI,

We have been hacked and believe the breach originated from your platform.
Our legal team is preparing a lawsuit for damages exceeding $2M.

Expect communication from our attorneys within 48 hours.

Regards,
BigCorp Legal Department"""
        },
        {
            'message_id': 'test_004',
            'sender': 'alice@techstartup.io',
            'subject': 'Feature Request: Bulk Email Import',
            'body': """Hi team,

We love SenAI! Quick question - can you add bulk email import via CSV?

This would help us onboard our customer support data much faster.

Thanks!
Alice"""
        }
    ]
    
    for email in test_emails:
        print(f"\n📧 Testing: {email['subject']}")
        print(f"   From: {email['sender']}")
        
        result = classify_email_with_gemini(email)
        
        if result['success']:
            classification = result['classification']
            print(f"   ✓ Classification successful")
            print(f"     • Category: {classification.get('category', 'N/A')}")
            print(f"     • Urgency: {classification.get('urgency', 'N/A')}")
            print(f"     • Sentiment: {classification.get('sentiment', 'N/A')} ({classification.get('sentiment_score', 0):.2f})")
            print(f"     • Confidence: {classification.get('confidence', 0):.2%}")
            print(f"     • Spam: {classification.get('is_spam', False)}")
            print(f"     • Security Alert: {classification.get('is_security_alert', False)}")
            print(f"     • Legal Threat: {classification.get('is_legal_threat', False)}")
            print(f"     • GDPR Request: {classification.get('is_gdpr_request', False)}")
            print(f"     • Reasoning: {classification.get('reasoning', 'N/A')}")
        else:
            print(f"   ✗ Classification failed: {result['error']}")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60)


def classify_batch_emails(emails_list):
    """Classify multiple emails (for batch processing)"""
    
    print(f"\n🔄 Classifying {len(emails_list)} emails...")
    
    results = []
    for i, email in enumerate(emails_list, 1):
        result = classify_email_with_gemini(email)
        results.append({
            'email_id': email.get('message_id'),
            'sender': email.get('sender'),
            **result
        })
        
        if i % 5 == 0:
            print(f"   ✓ Processed {i}/{len(emails_list)} emails")
    
    return results


if __name__ == "__main__":
    print("\n🚀 SenAI Gemini API Integration")
    
    # Test API connection
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        print("✓ Gemini API connected successfully")
    except Exception as e:
        print(f"❌ Gemini API connection failed: {e}")
        exit(1)
    
    # Run classification tests
    test_gemini_classification()
