from __future__ import annotations

import uuid
from datetime import datetime, time

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


EMBED_DIM = 384


class Base(DeclarativeBase):
    pass


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_chain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    chain_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hours_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sources: Mapped[list[BusinessSource]] = relationship("BusinessSource", back_populates="business")
    capabilities: Mapped[list[BusinessCapability]] = relationship(
        "BusinessCapability", back_populates="business"
    )
    hours: Mapped[list[BusinessHour]] = relationship("BusinessHour", back_populates="business")


class OntologyTerm(Base):
    __tablename__ = "ontology_terms"

    term: Mapped[str] = mapped_column(String(255), primary_key=True)
    parent_term: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("ontology_terms.term"), nullable=True
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False, default="seed")

    __table_args__ = (
        CheckConstraint("depth >= 0", name="ontology_terms_depth_non_negative"),
    )


class BusinessSource(Base):
    __tablename__ = "business_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    last_fetched: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship("Business", back_populates="sources")


class BusinessCapability(Base):
    __tablename__ = "business_capabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"))
    ontology_term: Mapped[str] = mapped_column(ForeignKey("ontology_terms.term", ondelete="CASCADE"))
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    semantic_similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ontology_matches: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    business: Mapped[Business] = relationship("Business", back_populates="capabilities")
    ontology: Mapped[OntologyTerm] = relationship("OntologyTerm")

    __table_args__ = (
        UniqueConstraint("business_id", "ontology_term", name="business_capabilities_unique_term_per_business"),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="business_capabilities_conf_range"),
    )


class BusinessHour(Base):
    __tablename__ = "business_hours"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    opens_at: Mapped[time] = mapped_column(Time, nullable=False)
    closes_at: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    business: Mapped[Business] = relationship("Business", back_populates="hours")

    __table_args__ = (
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="business_hours_day_range"),
    )
