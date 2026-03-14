"""
LeadForge AI - Leads API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional

from app.core.database import get_db
from app.api.dependencies import get_current_user_id, get_organization
from app.models import Lead, Tag, Organization
from app.schemas import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
    AddTagsRequest
)


router = APIRouter(prefix="/api/leads", tags=["Leads"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreate,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Create a new lead

    Creates a lead in the user's organization
    """
    new_lead = Lead(
        organization_id=organization.id,
        **lead_data.dict(exclude_unset=True)
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)

    return LeadResponse.from_orm(new_lead)


@router.get("", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    industry: Optional[str] = None,
    city: Optional[str] = None,
    min_score: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    List leads with pagination and filtering

    Supports filtering by status, industry, location, score, and text search
    """
    query = db.query(Lead).filter(
        Lead.organization_id == organization.id
    )

    # Apply filters
    if status:
        query = query.filter(Lead.status == status)
    if industry:
        query = query.filter(Lead.industry == industry)
    if city:
        query = query.filter(Lead.city == city)
    if min_score is not None:
        query = query.filter(Lead.lead_score >= min_score)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Lead.business_name.ilike(search_pattern),
                Lead.contact_name.ilike(search_pattern),
                Lead.email.ilike(search_pattern)
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * per_page
    leads = query.order_by(Lead.created_at.desc()).offset(offset).limit(per_page).all()

    return LeadListResponse(
        leads=[LeadResponse.from_orm(lead) for lead in leads],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get a specific lead by ID
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )

    return LeadResponse.from_orm(lead)


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    lead_data: LeadUpdate,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Update a lead
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )

    # Update fields
    update_data = lead_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)

    return LeadResponse.from_orm(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Delete a lead
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )

    db.delete(lead)
    db.commit()

    return None


@router.post("/{lead_id}/tags", response_model=LeadResponse)
async def add_tags_to_lead(
    lead_id: int,
    tag_data: AddTagsRequest,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Add tags to a lead
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )

    # Get tags
    tags = db.query(Tag).filter(
        Tag.id.in_(tag_data.tag_ids),
        Tag.organization_id == organization.id
    ).all()

    # Add tags to lead
    for tag in tags:
        if tag not in lead.tags:
            lead.tags.append(tag)

    db.commit()
    db.refresh(lead)

    return LeadResponse.from_orm(lead)


@router.delete("/{lead_id}/tags/{tag_id}", response_model=LeadResponse)
async def remove_tag_from_lead(
    lead_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Remove a tag from a lead
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )

    tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.organization_id == organization.id
    ).first()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    if tag in lead.tags:
        lead.tags.remove(tag)
        db.commit()

    db.refresh(lead)
    return LeadResponse.from_orm(lead)


@router.get("/stats/by-status", response_model=dict)
async def get_leads_by_status(
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get lead counts grouped by status
    """
    results = db.query(
        Lead.status,
        func.count(Lead.id)
    ).filter(
        Lead.organization_id == organization.id
    ).group_by(Lead.status).all()

    return {status: count for status, count in results}


@router.get("/stats/by-source", response_model=List[dict])
async def get_leads_by_source(
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get lead counts grouped by source
    """
    results = db.query(
        Lead.source_name,
        func.count(Lead.id)
    ).filter(
        Lead.organization_id == organization.id,
        Lead.source_name.isnot(None)
    ).group_by(Lead.source_name).order_by(func.count(Lead.id).desc()).all()

    return [{"source": source, "count": count} for source, count in results]


@router.get("/stats/by-industry", response_model=List[dict])
async def get_leads_by_industry(
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get lead counts grouped by industry
    """
    results = db.query(
        Lead.industry,
        func.count(Lead.id)
    ).filter(
        Lead.organization_id == organization.id,
        Lead.industry.isnot(None)
    ).group_by(Lead.industry).order_by(func.count(Lead.id).desc()).limit(20).all()

    return [{"industry": industry, "count": count} for industry, count in results]
