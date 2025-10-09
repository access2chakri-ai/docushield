"""
Privacy Audit Utility
Scans codebase for potential privacy violations and PII exposure risks
Helps ensure compliance with GDPR, HIPAA, SOX, and other privacy regulations
"""
import os
import re
import ast
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ViolationType(Enum):
    """Types of privacy violations"""
    DIRECT_LLM_CALL = "direct_llm_call"
    RAW_CONTENT_EXPOSURE = "raw_content_exposure"
    PII_IN_LOGS = "pii_in_logs"
    UNENCRYPTED_STORAGE = "unencrypted_storage"
    EXTERNAL_API_CALL = "external_api_call"
    MISSING_REDACTION = "missing_redaction"
    HARDCODED_SECRETS = "hardcoded_secrets"

class Severity(Enum):
    """Severity levels for violations"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class PrivacyViolation:
    """Represents a privacy violation found in code"""
    violation_type: ViolationType
    severity: Severity
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str
    confidence: float

class PrivacyAuditor:
    """
    Audits codebase for privacy violations and PII exposure risks
    """
    
    def __init__(self):
        self.violations = []
        
        # Patterns that indicate potential privacy violations
        self.violation_patterns = {
            ViolationType.DIRECT_LLM_CALL: [
                (r'llm_factory\.generate_completion\(', 0.9, "Direct LLM factory call without privacy protection"),
                (r'openai\.', 0.8, "Direct OpenAI API call"),
                (r'anthropic\.', 0.8, "Direct Anthropic API call"),
                (r'genai\.', 0.8, "Direct Gemini API call"),
                (r'groq\.', 0.8, "Direct Groq API call"),
            ],
            ViolationType.RAW_CONTENT_EXPOSURE: [
                (r'\.raw_text', 0.9, "Raw document text access"),
                (r'contract\.text', 0.8, "Contract text access"),
                (r'document_content', 0.7, "Document content variable"),
                (r'original_text', 0.7, "Original text variable"),
            ],
            ViolationType.PII_IN_LOGS: [
                (r'logger\.(info|debug|warning|error).*\{.*\}', 0.6, "Potential PII in log formatting"),
                (r'print\(.*text.*\)', 0.7, "Print statement with text content"),
                (r'console\.log', 0.6, "Console logging (if JS)"),
            ],
            ViolationType.EXTERNAL_API_CALL: [
                (r'requests\.(get|post)', 0.8, "HTTP request to external API"),
                (r'httpx\.(get|post)', 0.8, "HTTPX request to external API"),
                (r'urllib\.request', 0.7, "URL request to external service"),
            ],
            ViolationType.HARDCODED_SECRETS: [
                (r'api_key\s*=\s*["\'][^"\']+["\']', 0.9, "Hardcoded API key"),
                (r'password\s*=\s*["\'][^"\']+["\']', 0.9, "Hardcoded password"),
                (r'secret\s*=\s*["\'][^"\']+["\']', 0.9, "Hardcoded secret"),
                (r'token\s*=\s*["\'][^"\']+["\']', 0.8, "Hardcoded token"),
            ]
        }
        
        # Safe patterns that indicate proper privacy protection
        self.safe_patterns = [
            r'privacy_safe_llm\.',
            r'ensure_privacy_safe_content\(',
            r'redact_pii\(',
            r'create_safe_analysis_prompt\(',
            r'PrivacySafeLLMService',
        ]
        
        # Files to exclude from audit
        self.excluded_files = {
            'privacy_safe_processing.py',
            'privacy_safe_llm.py',
            'privacy_audit.py',
            '__pycache__',
            '.git',
            'node_modules',
            'venv',
            '.env'
        }
    
    def audit_directory(self, directory_path: str) -> List[PrivacyViolation]:
        """Audit entire directory for privacy violations"""
        self.violations = []
        
        logger.info(f"🔍 Starting privacy audit of {directory_path}")
        
        for root, dirs, files in os.walk(directory_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.excluded_files]
            
            for file in files:
                if any(excluded in file for excluded in self.excluded_files):
                    continue
                
                if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):
                    file_path = os.path.join(root, file)
                    self._audit_file(file_path)
        
        logger.info(f"🔍 Privacy audit complete: {len(self.violations)} violations found")
        return self.violations
    
    def _audit_file(self, file_path: str) -> None:
        """Audit a single file for privacy violations"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check each line for violations
            for line_num, line in enumerate(lines, 1):
                self._check_line_for_violations(file_path, line_num, line, content)
                
        except Exception as e:
            logger.warning(f"Could not audit file {file_path}: {e}")
    
    def _check_line_for_violations(self, file_path: str, line_num: int, line: str, full_content: str) -> None:
        """Check a single line for privacy violations"""
        line_stripped = line.strip()
        
        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith('#') or line_stripped.startswith('//'):
            return
        
        # Check if line uses safe patterns
        uses_safe_pattern = any(re.search(pattern, line) for pattern in self.safe_patterns)
        
        # Check for violation patterns
        for violation_type, patterns in self.violation_patterns.items():
            for pattern, confidence, description in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Reduce severity if safe patterns are also present
                    if uses_safe_pattern:
                        confidence *= 0.5  # Reduce confidence if safe patterns detected
                        severity = Severity.LOW
                    else:
                        severity = self._determine_severity(violation_type, confidence)
                    
                    # Skip low-confidence violations with safe patterns
                    if confidence < 0.3:
                        continue
                    
                    violation = PrivacyViolation(
                        violation_type=violation_type,
                        severity=severity,
                        file_path=file_path,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        description=description,
                        recommendation=self._get_recommendation(violation_type),
                        confidence=confidence
                    )
                    
                    self.violations.append(violation)
    
    def _determine_severity(self, violation_type: ViolationType, confidence: float) -> Severity:
        """Determine severity based on violation type and confidence"""
        if violation_type in [ViolationType.DIRECT_LLM_CALL, ViolationType.RAW_CONTENT_EXPOSURE]:
            if confidence > 0.8:
                return Severity.CRITICAL
            elif confidence > 0.6:
                return Severity.HIGH
            else:
                return Severity.MEDIUM
        elif violation_type == ViolationType.HARDCODED_SECRETS:
            return Severity.CRITICAL
        elif violation_type == ViolationType.EXTERNAL_API_CALL:
            if confidence > 0.7:
                return Severity.HIGH
            else:
                return Severity.MEDIUM
        else:
            return Severity.MEDIUM
    
    def _get_recommendation(self, violation_type: ViolationType) -> str:
        """Get recommendation for fixing violation"""
        recommendations = {
            ViolationType.DIRECT_LLM_CALL: "Use PrivacySafeLLMService instead of direct LLM factory calls",
            ViolationType.RAW_CONTENT_EXPOSURE: "Use privacy_processor.redact_pii() before processing content",
            ViolationType.PII_IN_LOGS: "Avoid logging raw content; use sanitized summaries instead",
            ViolationType.EXTERNAL_API_CALL: "Ensure content is redacted before external API calls",
            ViolationType.HARDCODED_SECRETS: "Move secrets to environment variables or secure vault",
            ViolationType.UNENCRYPTED_STORAGE: "Use encrypted storage for sensitive data",
            ViolationType.MISSING_REDACTION: "Add PII redaction before processing"
        }
        return recommendations.get(violation_type, "Review for privacy compliance")
    
    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate privacy audit report"""
        # Group violations by severity
        by_severity = {}
        for violation in self.violations:
            severity = violation.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(violation)
        
        # Group violations by type
        by_type = {}
        for violation in self.violations:
            vtype = violation.violation_type.value
            if vtype not in by_type:
                by_type[vtype] = []
            by_type[vtype].append(violation)
        
        # Group violations by file
        by_file = {}
        for violation in self.violations:
            file_path = violation.file_path
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(violation)
        
        report = {
            "audit_timestamp": datetime.now().isoformat(),
            "total_violations": len(self.violations),
            "summary": {
                "critical": len(by_severity.get("critical", [])),
                "high": len(by_severity.get("high", [])),
                "medium": len(by_severity.get("medium", [])),
                "low": len(by_severity.get("low", [])),
                "info": len(by_severity.get("info", []))
            },
            "by_type": {vtype: len(violations) for vtype, violations in by_type.items()},
            "by_file": {file_path: len(violations) for file_path, violations in by_file.items()},
            "violations": [
                {
                    "type": v.violation_type.value,
                    "severity": v.severity.value,
                    "file": v.file_path,
                    "line": v.line_number,
                    "code": v.code_snippet,
                    "description": v.description,
                    "recommendation": v.recommendation,
                    "confidence": v.confidence
                }
                for v in sorted(self.violations, key=lambda x: (x.severity.value, x.confidence), reverse=True)
            ]
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"📄 Privacy audit report saved to {output_file}")
        
        return report
    
    def print_summary(self) -> None:
        """Print audit summary to console"""
        if not self.violations:
            print("✅ No privacy violations found!")
            return
        
        print(f"\n🔍 Privacy Audit Summary")
        print(f"{'='*50}")
        print(f"Total violations: {len(self.violations)}")
        
        # Count by severity
        severity_counts = {}
        for violation in self.violations:
            severity = violation.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        for severity in ["critical", "high", "medium", "low", "info"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                emoji = {"critical": "🚨", "high": "⚠️", "medium": "⚡", "low": "💡", "info": "ℹ️"}
                print(f"{emoji.get(severity, '•')} {severity.upper()}: {count}")
        
        print(f"\n🔥 Top Issues:")
        critical_and_high = [v for v in self.violations if v.severity in [Severity.CRITICAL, Severity.HIGH]]
        for i, violation in enumerate(sorted(critical_and_high, key=lambda x: x.confidence, reverse=True)[:5], 1):
            print(f"{i}. {violation.file_path}:{violation.line_number}")
            print(f"   {violation.description}")
            print(f"   Code: {violation.code_snippet[:80]}...")
            print(f"   Fix: {violation.recommendation}")
            print()

def audit_docushield_backend(output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to audit DocuShield backend
    """
    auditor = PrivacyAuditor()
    
    # Get backend directory
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # Run audit
    violations = auditor.audit_directory(backend_dir)
    
    # Generate report
    report = auditor.generate_report(output_file)
    
    # Print summary
    auditor.print_summary()
    
    return report

if __name__ == "__main__":
    # Run audit when script is executed directly
    report = audit_docushield_backend("privacy_audit_report.json")
    
    if report["total_violations"] > 0:
        print(f"\n📄 Full report saved to privacy_audit_report.json")
        exit(1)  # Exit with error code if violations found
    else:
        print("✅ No privacy violations detected!")
        exit(0)