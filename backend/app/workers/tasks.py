"""
LeadForge AI - Celery Tasks
Background tasks for scraping, enrichment, and outreach
"""
from celery import shared_task
from datetime import datetime
import sys
import os

# Add scrapers and ai-services to path
sys.path.append('/app/scrapers')
sys.path.append('/app/ai-services')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import Lead, ScraperJob, Organization, LeadStatus, ScraperJobStatus


@shared_task(name='app.workers.tasks.scheduled_scrape_task')
def scheduled_scrape_task(source: str, query: str, location: str):
    """
    Scheduled scraping task
    Runs scraping based on schedule (Celery Beat)
    """
    print(f"Starting scheduled scrape: {source} - {query} in {location}")

    # Get organization (default to first org for scheduled tasks)
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        if not org:
            print("No organization found")
            return {"error": "No organization found"}

        # Import scraper here to avoid import issues
        if source == "google_maps":
            from scrapers.scrapers.google_maps_scraper import GoogleMapsScraper
            import asyncio

            async def run_scrape():
                scraper = GoogleMapsScraper()
                leads = await scraper.search(query=query, location=location, max_leads=100)
                return leads

            leads = asyncio.run(run_scrape())

        elif source == "yelp":
            from scrapers.scrapers.yelp_scraper import YelpScraper
            import asyncio

            async def run_scrape():
                scraper = YelpScraper()
                leads = await scraper.search(query=query, location=location, max_leads=100)
                return leads

            leads = asyncio.run(run_scrape())
        else:
            return {"error": f"Unknown source: {source}"}

        # Create scraper job record
        job = ScraperJob(
            organization_id=org.id,
            source=source,
            status=ScraperJobStatus.RUNNING,
            started_at=datetime.utcnow(),
            search_params={"query": query, "location": location}
        )
        db.add(job)
        db.commit()

        # Import leads to database
        imported = 0
        for lead_data in leads:
            # Check for duplicates
            existing = db.query(Lead).filter(
                Lead.organization_id == org.id,
                Lead.email == lead_data.email
            ).first() if lead_data.email else None

            if not existing:
                new_lead = Lead(
                    organization_id=org.id,
                    business_name=lead_data.business_name,
                    contact_name=lead_data.contact_name,
                    email=lead_data.email,
                    phone=lead_data.phone,
                    website=lead_data.website,
                    industry=lead_data.industry,
                    city=lead_data.city,
                    state=lead_data.state,
                    linkedin_url=lead_data.linkedin_url,
                    company_size=lead_data.company_size,
                    estimated_revenue=lead_data.estimated_revenue,
                    source_url=lead_data.source_url,
                    source_name=lead_data.source_name,
                    status=LeadStatus.SCRAPED
                )
                db.add(new_lead)
                imported += 1

        db.commit()

        # Update job
        job.leads_found = len(leads)
        job.leads_imported = imported
        job.status = ScraperJobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()

        result = {
            "source": source,
            "leads_found": len(leads),
            "leads_imported": imported,
            "job_id": job.id
        }

        print(f"Scrape completed: {result}")
        return result

    except Exception as e:
        print(f"Scrape failed: {e}")
        if job:
            job.status = ScraperJobStatus.FAILED
            job.completed_at = datetime.utcnow()
            db.commit()
        return {"error": str(e)}
    finally:
        db.close()


@shared_task(name='app.workers.tasks.enrich_pending_leads')
def enrich_pending_leads():
    """
    Enrich leads that haven't been enriched yet
    """
    print("Starting lead enrichment task")

    db = SessionLocal()
    try:
        # Get leads without enrichment
        leads = db.query(Lead).filter(
            Lead.status == LeadStatus.SCRAPED,
            Lead.lead_score == 0
        ).limit(50).all()

        if not leads:
            return {"message": "No leads to enrich"}

        # Import enrichment service
        from ai_services.app.enrichment import LeadEnricher
        from ai_services.app.scoring import LeadScorer
        import asyncio

        enricher = LeadEnricher()
        scorer = LeadScorer()

        enriched_count = 0
        for lead in leads:
            try:
                # Build lead data dict
                lead_data = {
                    'business_name': lead.business_name,
                    'email': lead.email,
                    'phone': lead.phone,
                    'website': lead.website,
                    'industry': lead.industry,
                    'city': lead.city,
                    'state': lead.state,
                    'linkedin_url': lead.linkedin_url,
                    'company_size': lead.company_size
                }

                # Enrich
                async def do_enrichment():
                    return await enricher.enrich_lead(lead_data)

                enriched = asyncio.run(do_enrichment())

                # Score
                async def do_scoring():
                    return await scorer.score_lead(lead_data)

                score, breakdown = asyncio.run(do_scoring())

                # Update lead
                lead.lead_score = score
                lead.score_factors = breakdown

                if enriched.email_valid is False:
                    # Mark as low quality
                    lead.lead_score = max(0, lead.lead_score - 30)

                if lead.lead_score >= 80:
                    lead.status = LeadStatus.NEW_LEAD

                enriched_count += 1

            except Exception as e:
                print(f"Error enriching lead {lead.id}: {e}")

        db.commit()

        result = {
            "leads_processed": len(leads),
            "leads_enriched": enriched_count
        }

        print(f"Enrichment completed: {result}")
        return result

    except Exception as e:
        print(f"Enrichment failed: {e}")
        return {"error": str(e)}
    finally:
        db.close()


@shared_task(name='app.workers.tasks.send_pending_outreach')
def send_pending_outreach():
    """
    Send pending outreach emails
    """
    print("Starting outreach send task")

    db = SessionLocal()
    try:
        # This would query pending outreach logs and send emails
        # For now, it's a placeholder

        return {"message": "Outreach task not yet implemented"}

    except Exception as e:
        print(f"Outreach failed: {e}")
        return {"error": str(e)}
    finally:
        db.close()


@shared_task(name='app.workers.tasks.manual_scrape')
def manual_scrape(
    organization_id: int,
    source: str,
    query: str,
    location: str,
    max_leads: int = 100
):
    """
    Manual scrape triggered by user
    """
    print(f"Starting manual scrape: {source} - {query} in {location}")

    db = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            return {"error": "Organization not found"}

        # Import and run scraper
        if source == "google_maps":
            from scrapers.scrapers.google_maps_scraper import GoogleMapsScraper
            import asyncio

            async def run_scrape():
                scraper = GoogleMapsScraper()
                return await scraper.search(query=query, location=location, max_leads=max_leads)

            leads = asyncio.run(run_scrape())

        elif source == "yelp":
            from scrapers.scrapers.yelp_scraper import YelpScraper
            import asyncio

            async def run_scrape():
                scraper = YelpScraper()
                return await scraper.search(query=query, location=location, max_leads=max_leads)

            leads = asyncio.run(run_scrape())
        else:
            return {"error": f"Unknown source: {source}"}

        # Create job record
        job = ScraperJob(
            organization_id=org.id,
            source=source,
            status=ScraperJobStatus.RUNNING,
            started_at=datetime.utcnow(),
            search_params={"query": query, "location": location}
        )
        db.add(job)
        db.commit()

        # Import leads
        imported = 0
        for lead_data in leads:
            existing = db.query(Lead).filter(
                Lead.organization_id == org.id,
                Lead.email == lead_data.email
            ).first() if lead_data.email else None

            if not existing:
                new_lead = Lead(
                    organization_id=org.id,
                    business_name=lead_data.business_name,
                    contact_name=lead_data.contact_name,
                    email=lead_data.email,
                    phone=lead_data.phone,
                    website=lead_data.website,
                    industry=lead_data.industry,
                    city=lead_data.city,
                    state=lead_data.state,
                    linkedin_url=lead_data.linkedin_url,
                    company_size=lead_data.company_size,
                    estimated_revenue=lead_data.estimated_revenue,
                    source_url=lead_data.source_url,
                    source_name=lead_data.source_name,
                    status=LeadStatus.SCRAPED
                )
                db.add(new_lead)
                imported += 1

        db.commit()

        # Update job
        job.leads_found = len(leads)
        job.leads_imported = imported
        job.status = ScraperJobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()

        return {
            "source": source,
            "leads_found": len(leads),
            "leads_imported": imported,
            "job_id": job.id
        }

    except Exception as e:
        print(f"Manual scrape failed: {e}")
        return {"error": str(e)}
    finally:
        db.close()
