import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
import enum
from app.db.database import Base

class WorkflowStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    input_prompt = Column(Text, nullable=False)
    status = Column(String(20), default=WorkflowStatus.PENDING, nullable=False)
    current_agent = Column(String(100), nullable=True)
    final_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    logs = relationship("AgentExecutionLog", back_populates="workflow", cascade="all, delete-orphan")

class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("workflow_executions.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    step_name = Column(String(100), nullable=False)
    thought_log = Column(Text, nullable=True)
    action_taken = Column(String(255), nullable=True)
    step_output = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    workflow = relationship("WorkflowExecution", back_populates="logs")
