"""
Simplified database models for TiDB integration
"""
from sqlalchemy import Column, String, Text, DateTime, Float, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    file_type = Column(String(50), nullable=False)
    dataset_id = Column(String(36), nullable=False, default="default")
    
    # Vector embedding for TiDB Vector Search
    embedding = Column(JSON, nullable=True)  # Store as JSON array
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query = Column(Text, nullable=False)
    dataset_id = Column(String(36), nullable=False)
    
    # Multi-step workflow results
    retrieval_results = Column(JSON, nullable=True)  # Retrieved documents
    llm_analysis = Column(JSON, nullable=True)       # LLM analysis
    final_answer = Column(Text, nullable=True)       # Final response
    external_actions = Column(JSON, nullable=True)   # External API calls
    
    # Metadata
    total_steps = Column(Integer, default=0)
    execution_time = Column(Float, nullable=True)
    status = Column(String(50), default="running")  # running, completed, failed
    
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
