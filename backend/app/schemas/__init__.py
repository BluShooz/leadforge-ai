"""
LeadForge AI - Pydantic Schemas
Request and response validation schemas
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# =============================================================================
# AUTHENTICATION SCHEMAS
# =============================================================================

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# =============================================================================
# LEAD SCHEMAS
# =============================================================================

class LeadBase(BaseModel):
    business_name: str
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_size: Optional[str] = None
    estimated_revenue: Optional[str] = None


class LeadCreate(LeadBase):
    source_url: Optional[str] = None
    source_name: Optional[str] = None


class LeadUpdate(BaseModel):
    business_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_size: Optional[str] = None
    estimated_revenue: Optional[str] = None
    status: Optional[str] = None
    lead_score: Optional[int] = None
    pipeline_stage: Optional[int] = None


class LeadResponse(LeadBase):
    id: int
    organization_id: int
    status: str
    lead_score: int
    pipeline_stage: Optional[int] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    scraped_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    leads: List[LeadResponse]
    total: int
    page: int
    per_page: int


# =============================================================================
# PIPELINE SCHEMAS
# =============================================================================

class PipelineStageCreate(BaseModel):
    name: str
    order: int = 0
    color: str = "#6366f1"


class PipelineStageUpdate(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None
    color: Optional[str] = None


class PipelineStageResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    order: int
    color: str
    created_at: datetime

    class Config:
        from_attributes = True


class PipelineUpdateRequest(BaseModel):
    lead_id: int
    stage_id: int


# =============================================================================
# ACTIVITY & NOTE SCHEMAS
# =============================================================================

class ActivityCreate(BaseModel):
    lead_id: int
    type: str
    title: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ActivityResponse(BaseModel):
    id: int
    lead_id: int
    created_by: int
    type: str
    title: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NoteCreate(BaseModel):
    lead_id: int
    content: str


class NoteUpdate(BaseModel):
    content: str


class NoteResponse(BaseModel):
    id: int
    lead_id: int
    created_by: int
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# OUTREACH SCHEMAS
# =============================================================================

class OutreachSequenceCreate(BaseModel):
    order: int = 0
    days_delay: int = 0
    subject: Optional[str] = None
    template: str


class OutreachSequenceResponse(BaseModel):
    id: int
    campaign_id: int
    order: int
    days_delay: int
    subject: Optional[str] = None
    template: str
    created_at: datetime

    class Config:
        from_attributes = True


class OutreachCampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    sequences: List[OutreachSequenceCreate] = []


class OutreachCampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class OutreachCampaignResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    description: Optional[str] = None
    type: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    sequences: List[OutreachSequenceResponse] = []

    class Config:
        from_attributes = True


class SendOutreachRequest(BaseModel):
    lead_id: int
    campaign_id: int


# =============================================================================
# SCRAPER SCHEMAS
# =============================================================================

class ScraperJobCreate(BaseModel):
    source: str  # google_maps, yelp, linkedin, etc.
    search_params: Optional[Dict[str, Any]] = None


class ScraperJobResponse(BaseModel):
    id: int
    organization_id: int
    source: str
    status: str
    leads_found: int
    leads_imported: int
    errors: int
    search_params: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# ANALYTICS SCHEMAS
# =============================================================================

class AnalyticsSummary(BaseModel):
    leads_scraped_today: int
    total_leads: int
    qualified_leads: int  # score >= 80
    pipeline_value: float  # Sum of estimated_revenue for qualified leads
    conversion_rate: float  # Converted / Total
    priority_leads: int  # Score >= 80, status <= qualified


class LeadSourceStats(BaseModel):
    source: str
    count: int
    percentage: float


class IndustryStats(BaseModel):
    industry: str
    count: int
    percentage: float


class LocationStats(BaseModel):
    city: str
    state: str
    count: int


class AnalyticsResponse(BaseModel):
    summary: AnalyticsSummary
    top_sources: List[LeadSourceStats]
    top_industries: List[IndustryStats]
    top_locations: List[LocationStats]
    leads_by_status: Dict[str, int]
    leads_by_stage: Dict[str, int]


# =============================================================================
# TAG SCHEMAS
# =============================================================================

class TagCreate(BaseModel):
    name: str
    color: str = "#6366f1"


class TagResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    color: str
    created_at: datetime

    class Config:
        from_attributes = True


class AddTagsRequest(BaseModel):
    lead_id: int
    tag_ids: List[int]
