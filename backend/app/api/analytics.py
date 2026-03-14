"""
LeadForge AI - Analytics API Routes
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List

from app.core.database import get_db
from app.api.dependencies import get_organization
from app.models import Lead, PipelineStage
from app.schemas import (
    AnalyticsSummary,
    AnalyticsResponse,
    LeadSourceStats,
    IndustryStats,
    LocationStats
)


router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get overall analytics summary

    Returns key metrics: leads scraped today, total leads, qualified leads,
    pipeline value, conversion rate, and priority leads count
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Leads scraped today
    leads_today = db.query(func.count(Lead.id)).filter(
        and_(
            Lead.organization_id == organization.id,
            Lead.created_at >= today
        )
    ).scalar() or 0

    # Total leads
    total_leads = db.query(func.count(Lead.id)).filter(
        Lead.organization_id == organization.id
    ).scalar() or 0

    # Qualified leads (score >= 80)
    qualified_leads = db.query(func.count(Lead.id)).filter(
        and_(
            Lead.organization_id == organization.id,
            Lead.lead_score >= 80
        )
    ).scalar() or 0

    # Converted leads
    converted_leads = db.query(func.count(Lead.id)).filter(
        and_(
            Lead.organization_id == organization.id,
            Lead.status == "converted"
        )
    ).scalar() or 0

    # Priority leads (score >= 80, not converted/lost)
    priority_leads = db.query(func.count(Lead.id)).filter(
        and_(
            Lead.organization_id == organization.id,
            Lead.lead_score >= 80,
            Lead.status.in_(["scraped", "new_lead", "contacted", "qualified"])
        )
    ).scalar() or 0

    # Pipeline value (estimated revenue for qualified leads)
    # This is a rough estimate since revenue is stored as string
    pipeline_value = 0.0  # Would need parsing logic for revenue strings

    # Conversion rate
    conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0.0

    return AnalyticsSummary(
        leads_scraped_today=leads_today,
        total_leads=total_leads,
        qualified_leads=qualified_leads,
        pipeline_value=pipeline_value,
        conversion_rate=round(conversion_rate, 2),
        priority_leads=priority_leads
    )


@router.get("", response_model=AnalyticsResponse)
async def get_full_analytics(
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get complete analytics data

    Includes summary, top sources, industries, locations, and breakdowns
    """
    # Get summary
    summary = await get_analytics_summary(db, organization)

    # Get top sources
    source_results = db.query(
        Lead.source_name,
        func.count(Lead.id)
    ).filter(
        and_(
            Lead.organization_id == organization.id,
            Lead.source_name.isnot(None)
        )
    ).group_by(Lead.source_name).order_by(
        func.count(Lead.id).desc()
    ).limit(10).all()

    total_for_sources = sum(count for _, count in source_results) or 1
    top_sources = [
        LeadSourceStats(
            source=source or "Unknown",
            count=count,
            percentage=round(count / total_for_sources * 100, 2)
        )
        for source, count in source_results
    ]

    # Get top industries
    industry_results = db.query(
        Lead.industry,
        func.count(Lead.id)
    ).filter(
        and_(
            Lead.organization_id == organization.id,
            Lead.industry.isnot(None)
        )
    ).group_by(Lead.industry).order_by(
        func.count(Lead.id).desc()
    ).limit(15).all()

    total_for_industries = sum(count for _, count in industry_results) or 1
    top_industries = [
        IndustryStats(
            industry=industry or "Unknown",
            count=count,
            percentage=round(count / total_for_industries * 100, 2)
        )
        for industry, count in industry_results
    ]

    # Get top locations
    location_results = db.query(
        Lead.city,
        Lead.state,
        func.count(Lead.id)
    ).filter(
        and_(
            Lead.organization_id == organization.id,
            Lead.city.isnot(None)
        )
    ).group_by(Lead.city, Lead.state).order_by(
        func.count(Lead.id).desc()
    ).limit(15).all()

    top_locations = [
        LocationStats(
            city=city or "Unknown",
            state=state or "",
            count=count
        )
        for city, state, count in location_results
    ]

    # Get leads by status
    status_results = db.query(
        Lead.status,
        func.count(Lead.id)
    ).filter(
        Lead.organization_id == organization.id
    ).group_by(Lead.status).all()

    leads_by_status = {status: count for status, count in status_results}

    # Get leads by pipeline stage
    stage_results = db.query(
        PipelineStage.name,
        func.count(Lead.id)
    ).outerjoin(
        Lead, Lead.pipeline_stage == PipelineStage.id
    ).filter(
        PipelineStage.organization_id == organization.id
    ).group_by(PipelineStage.name).all()

    leads_by_stage = {stage_name: count for stage_name, count in stage_results}

    return AnalyticsResponse(
        summary=summary,
        top_sources=top_sources,
        top_industries=top_industries,
        top_locations=top_locations,
        leads_by_status=leads_by_status,
        leads_by_stage=leads_by_stage
    )


@router.get("/trends/leads-by-day")
async def get_leads_trend(
    days: int = 30,
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get lead creation trend over time

    Returns daily lead counts for the specified number of days
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    results = db.query(
        func.date(Lead.created_at).label('date'),
        func.count(Lead.id).label('count')
    ).filter(
        and_(
            Lead.organization_id == organization.id,
            Lead.created_at >= start_date
        )
    ).group_by(
        func.date(Lead.created_at)
    ).order_by(
        func.date(Lead.created_at)
    ).all()

    return [
        {
            "date": str(date),
            "count": count
        }
        for date, count in results
    ]


@router.get("/trends/score-distribution")
async def get_score_distribution(
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get distribution of lead scores

    Returns counts for score ranges: 0-20, 21-40, 41-60, 61-80, 81-100
    """
    ranges = [
        (0, 20),
        (21, 40),
        (41, 60),
        (61, 80),
        (81, 100)
    ]

    distribution = []
    for min_score, max_score in ranges:
        count = db.query(func.count(Lead.id)).filter(
            and_(
                Lead.organization_id == organization.id,
                Lead.lead_score >= min_score,
                Lead.lead_score <= max_score
            )
        ).scalar() or 0

        distribution.append({
            "range": f"{min_score}-{max_score}",
            "count": count
        })

    return distribution


@router.get("/conversion-funnel")
async def get_conversion_funnel(
    db: Session = Depends(get_db),
    organization = Depends(get_organization)
):
    """
    Get conversion funnel data

    Shows how leads move through each status
    """
    status_order = [
        "scraped",
        "new_lead",
        "contacted",
        "qualified",
        "proposal_sent",
        "converted",
        "lost"
    ]

    results = db.query(
        Lead.status,
        func.count(Lead.id)
    ).filter(
        Lead.organization_id == organization.id
    ).group_by(Lead.status).all()

    status_counts = {status: count for status, count in results}

    funnel = []
    for status in status_order:
        funnel.append({
            "stage": status.replace("_", " ").title(),
            "count": status_counts.get(status, 0)
        })

    return funnel
