"""
LeadForge AI - Database Models
All SQLAlchemy models are defined here
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User roles"""
    ADMIN = "admin"
    USER = "user"
    AGENCY = "agency"


class LeadStatus(str, enum.Enum):
    """Lead status values"""
    SCRAPED = "scraped"
    NEW_LEAD = "new_lead"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL_SENT = "proposal_sent"
    CONVERTED = "converted"
    LOST = "lost"


class OutreachStatus(str, enum.Enum):
    """Outreach campaign status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class ScraperJobStatus(str, enum.Enum):
    """Scraper job status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# USERS & ORGANIZATIONS
# =============================================================================

class User(Base):
    """User accounts"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    stripe_customer_id = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="user", uselist=False)
    activities = relationship("Activity", back_populates="created_by_user")
    notes = relationship("Note", back_populates="created_by_user")


class Organization(Base):
    """Organizations (multi-tenancy)"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    plan = Column(String(50), default="free")  # free, starter, pro, enterprise
    settings = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="organization")
    leads = relationship("Lead", back_populates="organization")


# =============================================================================
# LEADS & CONTACTS
# =============================================================================

class Lead(Base):
    """Business leads"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    # Business information
    business_name = Column(String(255), nullable=False, index=True)
    contact_name = Column(String(255))
    email = Column(String(255), index=True)
    phone = Column(String(50))
    website = Column(String(500))
    industry = Column(String(100), index=True)
    city = Column(String(100), index=True)
    state = Column(String(100))
    country = Column(String(100), default="USA")
    linkedin_url = Column(String(500))
    company_size = Column(String(50))  # 1-10, 11-50, 51-200, 201-500, 500+
    estimated_revenue = Column(String(50))

    # Scraping metadata
    source_url = Column(String(500))
    source_name = Column(String(100))  # google_maps, yelp, linkedin, etc.
    scraped_date = Column(DateTime(timezone=True), server_default=func.now())

    # AI Scoring
    lead_score = Column(Integer, default=0, index=True)  # 0-100
    score_factors = Column(JSON, nullable=True)  # Store scoring breakdown

    # CRM
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.SCRAPED, index=True)
    pipeline_stage = Column(Integer, ForeignKey("pipeline_stages.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="leads")
    contacts = relationship("Contact", back_populates="lead", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="lead", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="lead", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="lead_tags", back_populates="leads")
    pipeline_stage_rel = relationship("PipelineStage", foreign_keys=[pipeline_stage])
    enrichment_cache = relationship("EnrichmentCache", back_populates="lead", uselist=False)
    outreach_logs = relationship("OutreachLog", back_populates="lead", cascade="all, delete-orphan")


class Contact(Base):
    """Individual contacts at a lead company"""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)

    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    role = Column(String(255))  # CEO, Marketing Manager, etc.
    is_decision_maker = Column(Boolean, default=False)
    linkedin_url = Column(String(500))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="contacts")


# =============================================================================
# CRM PIPELINE
# =============================================================================

class PipelineStage(Base):
    """Pipeline stages (Kanban columns)"""
    __tablename__ = "pipeline_stages"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(100), nullable=False)
    order = Column(Integer, default=0)
    color = Column(String(20), default="#6366f1")  # Hex color

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Activity(Base):
    """Activity log for leads"""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    type = Column(String(50), nullable=False)  # email, call, meeting, note, etc.
    title = Column(String(255))
    description = Column(Text)
    metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="activities")
    created_by_user = relationship("User", back_populates="activities")


class Note(Base):
    """Notes on leads"""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="notes")
    created_by_user = relationship("User", back_populates="notes")


class Tag(Base):
    """Tags for organizing leads"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(100), nullable=False, unique=True)
    color = Column(String(20), default="#6366f1")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    leads = relationship("Lead", secondary="lead_tags", back_populates="tags")


# Association table for many-to-many relationship
from sqlalchemy import Table
lead_tags = Table(
    'lead_tags',
    Base.metadata,
    Column('lead_id', Integer, ForeignKey('leads.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)


# =============================================================================
# OUTREACH
# =============================================================================

class OutreachCampaign(Base):
    """Outreach email campaigns"""
    __tablename__ = "outreach_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50))  # cold_email, follow_up, newsletter

    status = Column(SQLEnum(OutreachStatus), default=OutreachStatus.DRAFT)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sequences = relationship("OutreachSequence", back_populates="campaign", cascade="all, delete-orphan")
    logs = relationship("OutreachLog", back_populates="campaign", cascade="all, delete-orphan")


class OutreachSequence(Base):
    """Email sequences within campaigns"""
    __tablename__ = "outreach_sequences"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("outreach_campaigns.id"), nullable=False)

    order = Column(Integer, default=0)
    days_delay = Column(Integer, default=0)  # Days after previous email
    subject = Column(String(500), nullable=True)
    template = Column(Text, nullable=False)  # AI-generated email template

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaign = relationship("OutreachCampaign", back_populates="sequences")


class OutreachLog(Base):
    """Email send logs"""
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("outreach_campaigns.id"), nullable=False)
    sequence_id = Column(Integer, ForeignKey("outreach_sequences.id"), nullable=True)

    status = Column(String(50))  # sent, failed, opened, clicked, replied
    email_id = Column(String(255))  # External email ID

    subject = Column(String(500))
    body = Column(Text)

    sent_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    replied_at = Column(DateTime(timezone=True), nullable=True)

    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="outreach_logs")
    campaign = relationship("OutreachCampaign", back_populates="logs")


# =============================================================================
# ENRICHMENT CACHE
# =============================================================================

class EnrichmentCache(Base):
    """Cache for enriched lead data"""
    __tablename__ = "enrichment_cache"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, unique=True)

    data = Column(JSON, nullable=False)  # Enriched data
    email_validated = Column(Boolean, default=False)
    email_valid = Column(Boolean, nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="enrichment_cache")


# =============================================================================
# SCRAPER JOBS
# =============================================================================

class ScraperJob(Base):
    """Scraping job tracking"""
    __tablename__ = "scraper_jobs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    source = Column(String(100), nullable=False)  # google_maps, yelp, etc.
    status = Column(SQLEnum(ScraperJobStatus), default=ScraperJobStatus.PENDING)

    leads_found = Column(Integer, default=0)
    leads_imported = Column(Integer, default=0)
    errors = Column(Integer, default=0)

    search_params = Column(JSON, nullable=True)  # Search criteria used
    error_log = Column(JSON, nullable=True)  # List of errors

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
