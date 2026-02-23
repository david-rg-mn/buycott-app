import uuid
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
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
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
    google_place_id: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    formatted_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hours_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    primary_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    business_model: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    google_last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    google_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="places_api",
        server_default=text("'places_api'"),
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Chicago")
    specialty_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    canonical_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    source_documents: Mapped[list["SourceDocument"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    evidence_packets: Mapped[list["EvidencePacket"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    menu_items: Mapped[list["MenuItem"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    capability_profiles: Mapped[list["CapabilityProfile"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    global_footprint: Mapped["GlobalFootprint | None"] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    vertical_slices: Mapped[list["VerticalSlice"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    evidence_index_terms: Mapped[list["EvidenceIndexTerm"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    micrograph: Mapped["BusinessMicrograph | None"] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    verified_claims: Mapped[list["VerifiedClaim"]] = relationship(
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


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __table_args__ = (UniqueConstraint("business_id", "source_url", "content_hash", name="uq_source_document"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    etag: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship(back_populates="source_documents")


class EvidencePacket(Base):
    __tablename__ = "evidence_packets"
    __table_args__ = (
        UniqueConstraint("business_id", "claim_hash", "source_url", name="uq_evidence_packet_claim"),
        CheckConstraint("extraction_confidence >= 0 AND extraction_confidence <= 1", name="ck_evidence_extraction"),
        CheckConstraint("credibility_score >= 0 AND credibility_score <= 100", name="ck_evidence_credibility"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    sanitized_claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    credibility_score: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship(back_populates="evidence_packets")


class MenuItem(Base):
    __tablename__ = "menu_items"
    __table_args__ = (
        UniqueConstraint("business_id", "claim_hash", name="uq_menu_item_claim"),
        CheckConstraint("extraction_confidence >= 0 AND extraction_confidence <= 1", name="ck_menu_extraction"),
        CheckConstraint("credibility_score >= 0 AND credibility_score <= 100", name="ck_menu_credibility"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    section: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    dietary_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    credibility_score: Mapped[float] = mapped_column(Float, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship(back_populates="menu_items")


class CapabilityProfile(Base):
    __tablename__ = "capabilities"
    __table_args__ = (
        UniqueConstraint("business_id", "capability_type", "canonical_text", name="uq_capability_profile"),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="ck_capability_profile_confidence"),
        CheckConstraint("evidence_score >= 0 AND evidence_score <= 100", name="ck_capability_profile_evidence"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    capability_type: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_items: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_claim_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    canonical_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship(back_populates="capability_profiles")


class OntologyNode(Base):
    __tablename__ = "ontology_nodes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    canonical_term: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ontology_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    synonyms: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="seed")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


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


class GlobalFootprint(Base):
    __tablename__ = "global_footprints"
    __table_args__ = (CheckConstraint("coverage_score >= 0 AND coverage_score <= 1", name="ck_global_footprint_coverage"),)

    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    feature_vector: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    feature_flags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    coverage_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship(back_populates="global_footprint")


class VerticalSlice(Base):
    __tablename__ = "vertical_slices"
    __table_args__ = (UniqueConstraint("business_id", "slice_key", name="uq_vertical_slice"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    slice_key: Mapped[str] = mapped_column(String(96), nullable=False)
    category_weights: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    slice_terms: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship(back_populates="vertical_slices")


class EvidenceIndexTerm(Base):
    __tablename__ = "evidence_index_terms"
    __table_args__ = (
        UniqueConstraint("business_id", "term", "claim_id", "source_kind", name="uq_evidence_index_term"),
        CheckConstraint("weight >= 0 AND weight <= 1", name="ck_evidence_index_weight"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    term: Mapped[str] = mapped_column(Text, nullable=False)
    claim_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_ref: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship(back_populates="evidence_index_terms")


class BusinessMicrograph(Base):
    __tablename__ = "business_micrographs"

    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    graph_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    business: Mapped[Business] = relationship(back_populates="micrograph")


class VerifiedClaim(Base):
    __tablename__ = "verified_claims"
    __table_args__ = (
        UniqueConstraint("business_id", "claim_id", name="uq_verified_claim"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_verified_claim_confidence"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_id: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    audit_chain: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    business: Mapped[Business] = relationship(back_populates="verified_claims")


class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"

    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    expansion_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    db_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    ranking_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())


class GoogleApiUsageLog(Base):
    __tablename__ = "google_api_usage_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    requests_made: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False)
