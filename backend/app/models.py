from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    is_chain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    chain_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    hours_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Chicago")
    specialty_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    sources: Mapped[list["BusinessSource"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    capabilities: Mapped[list["BusinessCapability"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class BusinessSource(Base):
    __tablename__ = "business_sources"
    __table_args__ = (UniqueConstraint("business_id", "source_type", "source_url", name="uq_business_source"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_fetched: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship(back_populates="sources")


class OntologyTerm(Base):
    __tablename__ = "ontology_terms"
    __table_args__ = (CheckConstraint("depth >= 0", name="ck_ontology_depth"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    term: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    parent_term: Mapped[str | None] = mapped_column(ForeignKey("ontology_terms.term", ondelete="SET NULL"), nullable=True)
    depth: Mapped[int] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="seed")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BusinessCapability(Base):
    __tablename__ = "business_capabilities"
    __table_args__ = (
        UniqueConstraint("business_id", "ontology_term", name="uq_business_capability"),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="ck_capability_confidence"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ontology_term: Mapped[str] = mapped_column(
        Text,
        ForeignKey("ontology_terms.term", ondelete="CASCADE"),
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship(back_populates="capabilities")
