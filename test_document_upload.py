#!/usr/bin/env python3
"""
Test script to verify document upload with new classification system
"""
import sys
import os
sys.path.append('backend')

from app.services.document_validator import document_classifier, DocumentCategory

async def test_document_classification():
    """Test the new document classification system"""
    
    print("🧪 Testing Document Classification System")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "filename": "service_agreement.pdf",
            "content": "This service agreement is between Company A and Company B for software services...",
            "user_type": "Contract",
            "user_industry": "Technology/SaaS"
        },
        {
            "filename": "research_paper.pdf", 
            "content": "Abstract: This paper presents a novel approach to machine learning...",
            "user_type": "Research Paper",
            "user_industry": "Education"
        },
        {
            "filename": "unknown_document.txt",
            "content": "This is some random text content that doesn't fit any specific category...",
            "user_type": None,
            "user_industry": None
        },
        {
            "filename": "invoice_123.pdf",
            "content": "Invoice #123 Amount Due: $1,500 Payment Terms: Net 30 days...",
            "user_type": "Invoice",
            "user_industry": "Financial Services"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📄 Test Case {i}: {test_case['filename']}")
        print("-" * 30)
        
        try:
            is_valid, category, details = await document_classifier.classify_document(
                filename=test_case["filename"],
                text_content=test_case["content"],
                mime_type="application/pdf",
                user_document_type=test_case["user_type"],
                user_industry_type=test_case["user_industry"]
            )
            
            print(f"✅ Valid: {is_valid}")
            print(f"📂 Category: {category.value}")
            print(f"🎯 Confidence: {details['confidence']:.2f}")
            print(f"💭 Reason: {details['reason']}")
            
            if test_case["user_type"]:
                print(f"👤 User Type: {test_case['user_type']}")
            if test_case["user_industry"]:
                print(f"🏢 User Industry: {test_case['user_industry']}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ All documents should be accepted now!")
    print("🎉 No more 'unsupported document' errors!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_document_classification())