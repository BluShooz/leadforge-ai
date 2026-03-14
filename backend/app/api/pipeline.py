"""
LeadForge AI - Pipeline API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.dependencies import get_organization
from app.models import Lead, PipelineStage, Tag
from app.schemas import (
    PipelineStageCreate,
    PipelineStageUpdate,
    PipelineStageResponse,
    PipelineUpdateRequest
)


router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


@router.get("/stages", response_model=List[PipelineStageResponse])
async def get_pipeline_stages(
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get all pipeline stages for the organization
    """
    stages = db.query(PipelineStage).filter(
        PipelineStage.organization_id == organization.id
    ).order_by(PipelineStage.order).all()

    return [PipelineStageResponse.from_orm(stage) for stage in stages]


@router.post("/stages", response_model=PipelineStageResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline_stage(
    stage_data: PipelineStageCreate,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Create a new pipeline stage
    """
    new_stage = PipelineStage(
        organization_id=organization.id,
        **stage_data.dict()
    )
    db.add(new_stage)
    db.commit()
    db.refresh(new_stage)

    return PipelineStageResponse.from_orm(new_stage)


@router.put("/stages/{stage_id}", response_model=PipelineStageResponse)
async def update_pipeline_stage(
    stage_id: int,
    stage_data: PipelineStageUpdate,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Update a pipeline stage
    """
    stage = db.query(PipelineStage).filter(
        PipelineStage.id == stage_id,
        PipelineStage.organization_id == organization.id
    ).first()

    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline stage not found"
        )

    # Update fields
    update_data = stage_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stage, field, value)

    db.commit()
    db.refresh(stage)

    return PipelineStageResponse.from_orm(stage)


@router.delete("/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline_stage(
    stage_id: int,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Delete a pipeline stage
    """
    stage = db.query(PipelineStage).filter(
        PipelineStage.id == stage_id,
        PipelineStage.organization_id == organization.id
    ).first()

    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline stage not found"
        )

    # Check if any leads are in this stage
    leads_in_stage = db.query(Lead).filter(
        Lead.pipeline_stage == stage_id
    ).count()

    if leads_in_stage > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete stage with {leads_in_stage} leads. Move leads to another stage first."
        )

    db.delete(stage)
    db.commit()

    return None


@router.post("/move", response_model=dict)
async def move_lead_to_stage(
    update_data: PipelineUpdateRequest,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Move a lead to a different pipeline stage
    """
    # Verify lead belongs to organization
    lead = db.query(Lead).filter(
        Lead.id == update_data.lead_id,
        Lead.organization_id == organization.id
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )

    # Verify stage belongs to organization
    stage = db.query(PipelineStage).filter(
        PipelineStage.id == update_data.stage_id,
        PipelineStage.organization_id == organization.id
    ).first()

    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline stage not found"
        )

    # Update lead's stage
    lead.pipeline_stage = update_data.stage_id
    db.commit()

    return {
        "lead_id": lead.id,
        "stage_id": stage.id,
        "stage_name": stage.name,
        "message": f"Lead moved to {stage.name}"
    }


@router.get("/leads/{stage_id}", response_model=List[dict])
async def get_leads_in_stage(
    stage_id: int,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get all leads in a specific pipeline stage
    """
    # Verify stage belongs to organization
    stage = db.query(PipelineStage).filter(
        PipelineStage.id == stage_id,
        PipelineStage.organization_id == organization.id
    ).first()

    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline stage not found"
        )

    leads = db.query(Lead).filter(
        Lead.pipeline_stage == stage_id,
        Lead.organization_id == organization.id
    ).order_by(Lead.lead_score.desc(), Lead.created_at.desc()).all()

    return [
        {
            "id": lead.id,
            "business_name": lead.business_name,
            "contact_name": lead.contact_name,
            "email": lead.email,
            "lead_score": lead.lead_score,
            "status": lead.status,
            "industry": lead.industry,
            "city": lead.city
        }
        for lead in leads
    ]


@router.post("/initialize", response_model=List[PipelineStageResponse])
async def initialize_default_pipeline(
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Initialize default pipeline stages for a new organization
    """
    # Check if organization already has stages
    existing_stages = db.query(PipelineStage).filter(
        PipelineStage.organization_id == organization.id
    ).count()

    if existing_stages > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline already initialized"
        )

    # Create default stages
    default_stages = [
        {"name": "Scraped", "order": 0, "color": "#94a3b8"},
        {"name": "New Lead", "order": 1, "color": "#3b82f6"},
        {"name": "Contacted", "order": 2, "color": "#8b5cf6"},
        {"name": "Qualified", "order": 3, "color": "#f59e0b"},
        {"name": "Proposal Sent", "order": 4, "color": "#ef4444"},
        {"name": "Converted", "order": 5, "color": "#10b981"},
        {"name": "Lost", "order": 6, "color": "#6b7280"}
    ]

    created_stages = []
    for stage_data in default_stages:
        new_stage = PipelineStage(
            organization_id=organization.id,
            **stage_data
        )
        db.add(new_stage)
        created_stages.append(new_stage)

    db.commit()

    for stage in created_stages:
        db.refresh(stage)

    return [PipelineStageResponse.from_orm(stage) for stage in created_stages]
