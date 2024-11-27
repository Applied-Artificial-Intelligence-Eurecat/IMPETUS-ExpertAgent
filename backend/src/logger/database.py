# pylint: disable=C0103
"""
Module housing all the basic structure of a Log DB instance once loaded
in python language.
"""

from datetime import datetime

from typing import List
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, Float
from sqlalchemy.engine.row import Row
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

Base = declarative_base()


def serialize_orm_instance(entity: Row):
    """
    Given a sqlalchemy.engine.row, it dynamically parses it
    into a str JSONResponse friendly dict object.
    """
    serialized = {f: getattr(entity, f) for f in entity._fields}
    return {
        k: v if not isinstance(v, datetime) else str(v) for k, v in serialized.items()
    }


# pylint: disable=R0903
class AbstractLogModelORM(Base):
    """
    Abstract implementation of a Logger SQL table to store the main statistics
    and resources referring to a specific ML/DL run.

    Arguments:
        - status: -1: Error, 0: Finished, 1: Ongoing
    """

    __abstract__ = True

    id: Mapped[String] = mapped_column(String, primary_key=True, nullable=False)
    owner = Column(String, nullable=False, name="owner")
    status = Column(Integer, default=1, nullable=False, name="status")
    # pylint: disable=E1102
    start_time = Column(
        DateTime(timezone=False), default=func.now(), nullable=False, name="start_time"
    )
    end_time = Column(DateTime(timezone=False), nullable=True, name="end_time")

    def serialize(self) -> dict:
        """Serialize the ORM model instance to a dictionary."""
        serialized = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
        # Convert datetime to string
        for key, value in serialized.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
        return serialized


# pylint: disable=R0903
class LogModelORM(AbstractLogModelORM):
    """Base class for IAG-LLM application, prepared to deal with LLM activity regarding
    prompt providing, enhancement, and response creation. It attaches a new DB table
    with information regarding:
        - raw_query: RAW text provided by the user to the RAG system.
        - enhanced_query: Improved version of the RAW query provided by the
        PromptOptimizationTool.
        - response: Final response (with text improvements) provided by the LLM under
        usage.
        - embedding_tag: Name of the Encoder used to build the VectorDB of the RAG
        context.
        - llm_tag: Name of the LLM used to compute the response to the enhanced query.
        - log_error: If procedure ends up abruptly, this field can be used to report the
        main cause.

    Args:
        AbstractLogModelORM (ABC, Base): Base Logging Structure for the application.
    """

    __tablename__ = "prompt_logs"

    raw_query = Column(String, nullable=False, name="raw_query")
    response = Column(String, nullable=True, name="response")
    prompt_template = Column(String, nullable=True, name="prompt_template")
    embedding_tag = Column(String, nullable=True, name="embedding_tag")
    llm_tag = Column(String, nullable=True, name="llm_tag")
    enhanced_query = Column(String, nullable=True, name="enhanced_query")
    log_error = Column(String, nullable=True, name="log_error")
    feedback = Column(String, nullable=True, name="feedback")
    documents: Mapped[List["DocumentSnippetORM"]] = relationship(
        "DocumentSnippetORM", backref="log", cascade="all, delete-orphan", lazy="joined"
    )

    # LLM
    max_tokens = Column(Integer, default=0, nullable=True, name="max_tokens")
    n_batch = Column(Integer, default=0, nullable=True, name="n_batch")
    n_ctx = Column(Integer, default=0, nullable=True, name="n_ctx")
    top_k = Column(Integer, default=0, nullable=True, name="top_k")
    n_gpu_layers = Column(Integer, default=0, nullable=True, name="n_gpu_layers")

    repetition_penalty = Column(Float, default=0.0, nullable=True, name="repetition_penalty")
    temperature = Column(Float, default=0.0, nullable=True, name="temperature")
    top_p = Column(Float, default=0.0, nullable=True, name="top_p")

    # LLM timing
    load_time = Column(Float, default=0.0, nullable=True, name="load_time")
    sample_time = Column(Float, default=0.0, nullable=True, name="sample_time")
    eval_time = Column(Float, default=0.0, nullable=True, name="eval_time")
    total_time = Column(Float, default=0.0, nullable=True, name="total_time")

    sample_runs = Column(Integer, default=0, nullable=True, name="sample_runs")
    prompt_eval_tokens = Column(Integer, default=0, nullable=True, name="prompt_eval_tokens")
    eval_runs = Column(Integer, default=0, nullable=True, name="eval_runs")
    total_tokens = Column(Integer, default=0, nullable=True, name="total_tokens")



class DocumentSnippetORM(Base):
    """
    Base entity definition of Documents inside the IA-Gen platform.

    Args:
        Base (sqlalchemy.orm.declarative_base): Base entity definition for SQLAlchemy.
    """

    __tablename__ = "documents"

    id: Mapped[String] = mapped_column(String, primary_key=True, nullable=False)
    parent_id: Mapped[int] = mapped_column(ForeignKey("prompt_logs.id"))
    title: String = Column(String, nullable=True, name="title")
    content: Mapped[List[String]] = Column(String, nullable=True, name="content")
    href: String = Column(String, nullable=True, name="href")
    similarity: Float = Column(Float, nullable=True, name="similarity")
