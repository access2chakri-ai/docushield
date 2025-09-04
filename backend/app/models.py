"""
DocuShield Digital Twin Document Intelligence - Enhanced Database Models
Bronze → Silver → Gold architecture for enterprise document processing
"""
from sqlalchemy import Column, String, Text, DateTime, Float, JSON, Integer, Boolean, LargeBinary, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum
import uuid

Base = declarative_base()

# =============================================================================
# 🟤 BRONZE LAYER (Raw Ingest + Orchestration)
# =============================================================================

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    contracts = relationship("BronzeContract", back_populates="owner")

class BronzeContract(Base):
    __tablename__ = "bronze_contracts"
    
    contract_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256
    raw_bytes = Column(LargeBinary, nullable=True)  # LONGBLOB - maximum size supported by TiDB
    
    # Metadata
    owner_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    source = Column(String(50), default="upload")  # upload, google_drive, api
    source_metadata = Column(JSON, nullable=True)  # Google Drive ID, etc.
    status = Column(String(50), default="uploaded")  # uploaded, processing, completed, failed
    retry_count = Column(Integer, default=0)  # Track number of retry attempts
    last_retry_at = Column(DateTime, nullable=True)  # Track last retry timestamp
    max_retries = Column(Integer, default=3)  # Maximum allowed retries per document
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="contracts")
    text_raw = relationship("BronzeContractTextRaw", back_populates="contract", uselist=False)
    processing_runs = relationship("ProcessingRun", back_populates="contract")
    chunks = relationship("SilverChunk", back_populates="contract")
    clause_spans = relationship("SilverClauseSpan", back_populates="contract")
    scores = relationship("GoldContractScore", back_populates="contract", uselist=False)
    findings = relationship("GoldFinding", back_populates="contract")
    suggestions = relationship("GoldSuggestion", back_populates="contract")
    summaries = relationship("GoldSummary", back_populates="contract")
    alerts = relationship("Alert", back_populates="contract")

class BronzeContractTextRaw(Base):
    __tablename__ = "bronze_contract_text_raw"
    
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), primary_key=True)
    raw_text = Column(Text, nullable=False)  # LONGTEXT in TiDB
    parser_version = Column(String(50), nullable=False)
    text_hash = Column(String(64), nullable=False)  # SHA-256 of text
    language = Column(String(10), default="en")
    page_count = Column(Integer, nullable=True)
    extraction_metadata = Column(JSON, nullable=True)  # Parser-specific data
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    contract = relationship("BronzeContract", back_populates="text_raw")

class ProcessingRun(Base):
    __tablename__ = "processing_runs"
    
    run_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), nullable=False)
    pipeline_version = Column(String(50), nullable=False)
    trigger = Column(String(50), default="manual")  # manual, auto, retry
    status = Column(String(50), default="running")  # running, completed, failed, cancelled
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    contract = relationship("BronzeContract", back_populates="processing_runs")
    steps = relationship("ProcessingStep", back_populates="run")

class ProcessingStep(Base):
    __tablename__ = "processing_steps"
    
    step_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("processing_runs.run_id"), nullable=False)
    step_name = Column(String(100), nullable=False)  # extract_text, chunk, embed, tag, score, etc.
    step_order = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")  # pending, running, completed, failed, skipped
    error_message = Column(Text, nullable=True)
    step_metadata = Column(JSON, nullable=True)  # Step-specific data
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    run = relationship("ProcessingRun", back_populates="steps")

class SyncStateGdrive(Base):
    __tablename__ = "sync_state_gdrive"
    
    folder_id = Column(String(100), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    last_sync_token = Column(String(500), nullable=True)
    last_sync_time = Column(DateTime, nullable=True)
    sync_status = Column(String(50), default="active")  # active, paused, error
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# =============================================================================
# ⚪ SILVER LAYER (Clean + Enriched)
# =============================================================================

class SilverChunk(Base):
    __tablename__ = "silver_chunks"
    
    chunk_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_order = Column(Integer, nullable=False)
    
    # Text position
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)
    
    # Vector embedding for TiDB Vector Search
    embedding = Column(JSON, nullable=True)  # Store as JSON array (768 dimensions)
    embedding_model = Column(String(100), nullable=True)  # openai, jina, etc.
    
    # Metadata
    chunk_type = Column(String(50), default="text")  # text, table, header, footer
    language = Column(String(10), default="en")
    token_count = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    contract = relationship("BronzeContract", back_populates="chunks")
    
    # Regular indexes (vector index can be added later via TiDB Console)
    __table_args__ = (
        Index('idx_chunks_contract', 'contract_id'),
    )

class Token(Base):
    __tablename__ = "tokens"
    
    token_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), nullable=False)
    token_text = Column(String(100), nullable=False)
    token_type = Column(String(50), default="word")  # word, phrase, entity
    position = Column(Integer, nullable=False)
    frequency = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=func.now())
    
    # Indexes for hybrid search
    __table_args__ = (
        Index('idx_tokens_contract_text', 'contract_id', 'token_text'),
        Index('idx_tokens_text', 'token_text'),
    )

class SilverClauseSpan(Base):
    __tablename__ = "silver_clause_spans"
    
    span_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), nullable=False)
    clause_type = Column(String(100), nullable=False)  # sla, renewal, termination, security, fees
    clause_name = Column(String(200), nullable=False)
    
    # Text position
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)
    snippet = Column(Text, nullable=False)  # Actual clause text
    
    # Analysis results
    confidence = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0
    attributes = Column(JSON, nullable=True)  # {"uptime": "99.9%", "penalty": "$1000"}
    risk_indicators = Column(JSON, nullable=True)  # Array of risk flags
    
    # Metadata
    extraction_method = Column(String(50), default="ai")  # ai, pattern, manual
    model_version = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    contract = relationship("BronzeContract", back_populates="clause_spans")
    findings = relationship("GoldFinding", back_populates="clause_span")
    suggestions = relationship("GoldSuggestion", back_populates="clause_span")

# =============================================================================
# 🟡 GOLD LAYER (Curated Outputs)
# =============================================================================

class GoldContractScore(Base):
    __tablename__ = "gold_contract_scores"
    
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), primary_key=True)
    overall_score = Column(Integer, nullable=False)  # 0-100
    risk_level = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # Category scores
    category_scores = Column(JSON, nullable=True)  # {"legal": 85, "financial": 70, "operational": 90}
    score_components = Column(JSON, nullable=True)  # Detailed scoring breakdown
    
    # Analysis metadata
    scoring_model_version = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, default=func.now())
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    contract = relationship("BronzeContract", back_populates="scores")

class GoldFinding(Base):
    __tablename__ = "gold_findings"
    
    finding_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), nullable=False)
    span_id = Column(String(36), ForeignKey("silver_clause_spans.span_id"), nullable=True)
    
    # Finding details
    finding_type = Column(String(100), nullable=False)  # liability_risk, unfavorable_terms, etc.
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Business impact
    impact_category = Column(String(50), nullable=True)  # financial, legal, operational, strategic
    estimated_impact = Column(JSON, nullable=True)  # {"cost": 10000, "probability": 0.3}
    
    # Metadata
    confidence = Column(Float, nullable=False, default=0.0)
    detection_method = Column(String(50), default="ai")  # ai, pattern, manual
    model_version = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    contract = relationship("BronzeContract", back_populates="findings")
    clause_span = relationship("SilverClauseSpan", back_populates="findings")

class GoldSuggestion(Base):
    __tablename__ = "gold_suggestions"
    
    suggestion_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), nullable=False)
    span_id = Column(String(36), ForeignKey("silver_clause_spans.span_id"), nullable=True)
    
    # Suggestion details
    suggestion_type = Column(String(100), nullable=False)  # renegotiate, add_clause, remove_clause
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    suggested_text = Column(Text, nullable=True)  # Proposed clause text
    
    # Lifecycle
    status = Column(String(50), default="open")  # open, accepted, dismissed, implemented
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    
    # Business justification
    business_rationale = Column(Text, nullable=True)
    estimated_benefit = Column(JSON, nullable=True)  # {"risk_reduction": 0.2, "cost_savings": 5000}
    
    # Metadata
    confidence = Column(Float, nullable=False, default=0.0)
    model_version = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    contract = relationship("BronzeContract", back_populates="suggestions")
    clause_span = relationship("SilverClauseSpan", back_populates="suggestions")

class GoldSummary(Base):
    __tablename__ = "gold_summaries"
    
    summary_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), nullable=False)
    summary_type = Column(String(50), nullable=False)  # executive, legal, technical, financial
    
    # Summary content
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    key_points = Column(JSON, nullable=True)  # Array of key takeaways
    
    # Metadata
    word_count = Column(Integer, nullable=True)
    model_version = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    contract = relationship("BronzeContract", back_populates="summaries")

class Alert(Base):
    __tablename__ = "alerts"
    
    alert_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), nullable=False)
    alert_type = Column(String(100), nullable=False)  # risk_detected, high_value, compliance_issue
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # Alert content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True)  # Alert-specific data
    
    # Delivery tracking
    channels = Column(JSON, nullable=True)  # ["slack", "email", "webhook"]
    delivery_status = Column(JSON, nullable=True)  # {"slack": true, "email": false}
    
    # Lifecycle
    status = Column(String(50), default="pending")  # pending, sent, delivered, failed, acknowledged
    acknowledged_by = Column(String(36), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    contract = relationship("BronzeContract", back_populates="alerts")

# =============================================================================
# ⚙️ CROSS-CUTTING / OPS
# =============================================================================

class LlmCall(Base):
    __tablename__ = "llm_calls"
    
    call_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), nullable=True)
    
    # Call details
    provider = Column(String(50), nullable=False)  # openai, jina, anthropic
    model = Column(String(100), nullable=False)  # gpt-4, text-embedding-3-small
    call_type = Column(String(50), nullable=False)  # embedding, completion, analysis
    
    # Usage tracking
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    estimated_cost = Column(Float, nullable=True)  # USD
    
    # Performance
    latency_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Context
    purpose = Column(String(100), nullable=True)  # clause_extraction, risk_analysis, summarization
    call_metadata = Column(JSON, nullable=True)  # Call-specific data
    
    created_at = Column(DateTime, default=func.now())

class DocumentAcl(Base):
    __tablename__ = "document_acl"
    
    acl_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("bronze_contracts.contract_id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    permission = Column(String(20), nullable=False)  # view, edit, admin
    
    granted_by = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    granted_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)


