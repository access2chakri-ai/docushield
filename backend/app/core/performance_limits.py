"""
Performance limits and safeguards for DocuShield
Prevents the application from getting stuck or overwhelmed
"""

# File upload limits
MAX_FILE_SIZE_MB = 50  # Maximum file size in MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Document processing limits
MAX_TEXT_LENGTH = 500000  # Maximum characters in extracted text
MAX_CHUNKS_PER_DOCUMENT = 200  # Maximum number of chunks to create
MAX_PROCESSING_TIME_SECONDS = 600  # 10 minutes maximum processing time
CHUNK_SIZE = 1000  # Characters per chunk
MAX_EMBEDDINGS_PER_BATCH = 50  # Batch size for embedding generation

# User quotas
MAX_DOCUMENTS_PER_USER = 100  # Maximum documents per user
MAX_DAILY_UPLOADS = 20  # Maximum uploads per user per day
MAX_CONCURRENT_PROCESSING = 3  # Maximum concurrent processing jobs per user

# API rate limits
MAX_REQUESTS_PER_MINUTE = 60  # API requests per minute per user
MAX_CHAT_MESSAGES_PER_HOUR = 100  # Chat messages per hour per user

# LLM limits
MAX_LLM_PROMPT_LENGTH = 50000  # Maximum prompt length for LLM calls
MAX_LLM_CALLS_PER_DOCUMENT = 20  # Maximum LLM calls per document processing
LLM_TIMEOUT_SECONDS = 120  # 2 minutes timeout for LLM calls

# Supported file types
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.md'}
SUPPORTED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'text/plain',
    'text/markdown',
    'application/octet-stream'  # For some valid files
}

# Document content validation
MIN_DOCUMENT_SIZE_BYTES = 100  # Minimum file size
MIN_TEXT_LENGTH = 50  # Minimum text content length

# Business document keywords (for content validation)
BUSINESS_DOCUMENT_KEYWORDS = [
    'contract', 'agreement', 'terms', 'conditions', 'policy', 'document',
    'shall', 'party', 'service', 'payment', 'liability', 'clause',
    'provision', 'section', 'article', 'whereas', 'therefore', 'hereby',
    'invoice', 'receipt', 'purchase', 'order', 'statement', 'report',
    'memo', 'memorandum', 'letter', 'correspondence', 'proposal',
    'specification', 'requirement', 'guideline', 'procedure', 'manual'
]

# Error messages
ERROR_MESSAGES = {
    'file_too_large': f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB for optimal processing performance.",
    'unsupported_type': "Unsupported file type. DocuShield supports PDF, Word, and Text documents for analysis.",
    'file_too_small': "File appears to be empty or too small. Please upload a document with actual content.",
    'content_too_short': "Document content is too short. Please upload documents with substantial text content for analysis.",
    'quota_exceeded': f"Document limit reached. You can upload up to {MAX_DOCUMENTS_PER_USER} documents.",
    'processing_timeout': f"Document processing timed out after {MAX_PROCESSING_TIME_SECONDS//60} minutes. The document may be too complex or large.",
    'rate_limit_exceeded': "Too many requests. Please wait before uploading more documents.",
    'unsupported_content': "This file doesn't appear to be a business document suitable for DocuShield analysis."
}

def validate_file_size(size_bytes: int) -> bool:
    """Validate file size is within limits"""
    return MIN_DOCUMENT_SIZE_BYTES <= size_bytes <= MAX_FILE_SIZE_BYTES

def validate_file_extension(filename: str) -> bool:
    """Validate file extension is supported"""
    if '.' not in filename:
        return False
    extension = '.' + filename.lower().split('.')[-1]
    return extension in SUPPORTED_EXTENSIONS

def validate_mime_type(mime_type: str) -> bool:
    """Validate MIME type is supported"""
    return mime_type in SUPPORTED_MIME_TYPES

def validate_text_content(text: str) -> tuple[bool, str]:
    """
    Validate text content for business document context
    Returns (is_valid, error_message)
    """
    if len(text.strip()) < MIN_TEXT_LENGTH:
        return False, ERROR_MESSAGES['content_too_short']
    
    # Check for business document indicators
    text_lower = text.lower()
    has_business_keywords = any(keyword in text_lower for keyword in BUSINESS_DOCUMENT_KEYWORDS)
    
    if not has_business_keywords:
        return False, ERROR_MESSAGES['unsupported_content']
    
    return True, ""

def get_processing_limits() -> dict:
    """Get all processing limits as a dictionary"""
    return {
        'max_file_size_mb': MAX_FILE_SIZE_MB,
        'max_text_length': MAX_TEXT_LENGTH,
        'max_chunks': MAX_CHUNKS_PER_DOCUMENT,
        'max_processing_time': MAX_PROCESSING_TIME_SECONDS,
        'chunk_size': CHUNK_SIZE,
        'max_embeddings_batch': MAX_EMBEDDINGS_PER_BATCH,
        'max_documents_per_user': MAX_DOCUMENTS_PER_USER,
        'supported_extensions': list(SUPPORTED_EXTENSIONS),
        'supported_mime_types': list(SUPPORTED_MIME_TYPES)
    }
