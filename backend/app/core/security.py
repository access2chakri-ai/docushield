"""
Security utilities and middleware for DocuShield
"""
import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, UploadFile
from fastapi.security import HTTPBearer
import logging

logger = logging.getLogger(__name__)

# Try to import magic with fallback
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logger.warning("python-magic not available, file type detection will use filename extensions only")

# Security configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_MIME_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'text/plain',
    'text/markdown'
]

ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.txt', '.md']

# Malicious file patterns
MALICIOUS_PATTERNS = [
    b'<script',
    b'javascript:',
    b'vbscript:',
    b'onload=',
    b'onerror=',
    b'<?php',
    b'<%',
    b'exec(',
    b'eval(',
    b'system(',
    b'shell_exec'
]

security = HTTPBearer()

class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename for security"""
        if not filename:
            return False
        
        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\x00']
        if any(char in filename for char in dangerous_chars):
            return False
        
        # Check extension
        extension = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if extension not in ALLOWED_EXTENSIONS:
            return False
        
        return True
    
    @staticmethod
    def validate_file_content(content: bytes, filename: str) -> bool:
        """Validate file content for malicious patterns"""
        try:
            # Check file size
            if len(content) > MAX_FILE_SIZE:
                logger.warning(f"File {filename} exceeds size limit: {len(content)} bytes")
                return False
            
            # Get file extension
            extension = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
            
            # For binary files (PDF, DOCX), skip content pattern matching as it can cause false positives
            if extension in ['.pdf', '.docx', '.doc']:
                logger.debug(f"Skipping content pattern validation for binary file: {filename}")
                # Only do basic checks for binary files
                if b'<script' in content[:1000] or b'javascript:' in content[:1000]:
                    logger.warning(f"Suspicious script content detected in binary file {filename}")
                    return False
            else:
                # For text files, do full pattern matching
                content_lower = content.lower()
                for pattern in MALICIOUS_PATTERNS:
                    if pattern in content_lower:
                        logger.warning(f"Malicious pattern detected in file {filename}: {pattern}")
                        return False
            
            # Validate MIME type using python-magic if available
            if MAGIC_AVAILABLE:
                try:
                    mime_type = magic.from_buffer(content, mime=True)
                    if mime_type not in ALLOWED_MIME_TYPES:
                        logger.warning(f"Invalid MIME type for file {filename}: {mime_type}")
                        return False
                except Exception as e:
                    logger.warning(f"Magic library error: {e}, falling back to basic validation")
            else:
                # Fallback to basic validation if python-magic not available
                logger.debug("python-magic not available, using basic file validation")
            
            return True
            
        except Exception as e:
            logger.error(f"File content validation failed: {e}")
            return False
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """Sanitize text input"""
        if not text:
            return ""
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        
        # Remove potentially dangerous characters
        text = re.sub(r'[<>"\'\x00-\x1f\x7f-\x9f]', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def validate_upload_file(file: UploadFile) -> None:
        """Comprehensive file upload validation"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Validate filename
        if not SecurityValidator.validate_filename(file.filename):
            raise HTTPException(
                status_code=400, 
                detail="Invalid filename. Only PDF, DOCX, TXT, and MD files are allowed."
            )
        
        # Validate content type
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Only PDF, DOCX, TXT, and MD files are allowed."
            )
    
    @staticmethod
    def generate_secure_filename(original_filename: str, user_id: str) -> str:
        """Generate a secure filename"""
        # Extract extension
        extension = '.' + original_filename.split('.')[-1].lower() if '.' in original_filename else ''
        
        # Create hash of original filename + user_id + timestamp
        hash_input = f"{original_filename}_{user_id}_{datetime.now().isoformat()}"
        file_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        
        # Create secure filename
        secure_name = f"doc_{file_hash}{extension}"
        return secure_name

# Rate limiting (simple in-memory implementation)
class RateLimiter:
    """Simple rate limiter for API endpoints"""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key: str, max_requests: int = 100, window_seconds: int = 3600) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.now()
        
        # Clean old entries
        cutoff = now - timedelta(seconds=window_seconds)
        self.requests = {k: v for k, v in self.requests.items() if v[-1] > cutoff}
        
        # Check current requests
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests for this key
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > cutoff]
        
        # Check if under limit
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True

# Global instances
security_validator = SecurityValidator()
rate_limiter = RateLimiter()