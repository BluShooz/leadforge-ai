"""
LeadForge AI - Lead Enrichment Service
Enriches leads with additional data, email validation, and insights
"""
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import re
import httpx

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


@dataclass
class EnrichedLead:
    """Enriched lead data"""
    lead_data: Dict[str, Any]
    email_valid: Optional[bool] = None
    email_disposable: bool = False
    website_active: bool = False
    social_media: Dict[str, str] = None
    technologies: List[str] = None
    business_description: str = ""
    confidence_score: float = 0.0

    def __post_init__(self):
        if self.social_media is None:
            self.social_media = {}
        if self.technologies is None:
            self.technologies = []


class LeadEnricher:
    """Lead enrichment service"""

    def __init__(
        self,
        neverbounce_api_key: Optional[str] = None,
        timeout: int = 10
    ):
        """
        Initialize lead enricher

        Args:
            neverbounce_api_key: API key for NeverBounce email validation
            timeout: Request timeout in seconds
        """
        self.neverbounce_api_key = neverbounce_api_key
        self.timeout = timeout
        self.http_client = None

    async def __aenter__(self):
        self.http_client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.http_client:
            await self.http_client.aclose()

    async def enrich_lead(self, lead: Dict[str, Any]) -> EnrichedLead:
        """
        Enrich a single lead with additional data

        Args:
            lead: Lead data dictionary

        Returns:
            EnrichedLead object with additional data
        """
        enriched = EnrichedLead(lead_data=lead)

        # Email validation
        if lead.get('email'):
            await self._validate_email(enriched)

        # Website analysis
        if lead.get('website'):
            await self._analyze_website(enriched)

        # Social media discovery
        await self._discover_social_media(enriched)

        # Technology detection
        if lead.get('website'):
            await self._detect_technologies(enriched)

        # Calculate confidence score
        enriched.confidence_score = self._calculate_confidence(enriched)

        return enriched

    async def _validate_email(self, enriched: EnrichedLead):
        """Validate email address"""
        email = enriched.lead_data.get('email', '')

        # Basic format validation
        if not self._is_valid_email_format(email):
            enriched.email_valid = False
            return

        # Check for disposable email domains
        disposable_domains = [
            'tempmail.com', 'guerrillamail.com', 'mailinator.com',
            '10minutemail.com', 'throwaway.email'
        ]
        domain = email.split('@')[1].lower()
        enriched.email_disposable = any(d in domain for d in disposable_domains)

        # Use NeverBounce API if key available
        if self.neverbounce_api_key and not enriched.email_disposable:
            try:
                response = await self.http_client.get(
                    f"https://api.neverbounce.com/v4/single/check",
                    params={
                        'key': self.neverbounce_api_key,
                        'email': email
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    enriched.email_valid = data.get('result') == 'valid'
            except Exception as e:
                print(f"NeverBounce validation failed: {e}")
                enriched.email_valid = None
        else:
            enriched.email_valid = True

    async def _analyze_website(self, enriched: EnrichedLead):
        """Analyze website for business information"""
        website = enriched.lead_data.get('website', '')

        try:
            response = await self.http_client.get(website, follow_redirects=True)
            enriched.website_active = response.status_code == 200

            if enriched.website_active and BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'lxml')

                # Extract meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    enriched.business_description = meta_desc.get('content', '')

                # Extract business description from first paragraph if no meta description
                if not enriched.business_description:
                    first_p = soup.find('p')
                    if first_p:
                        text = first_p.get_text().strip()
                        if len(text) > 50 and len(text) < 500:
                            enriched.business_description = text

        except Exception as e:
            print(f"Website analysis failed: {e}")
            enriched.website_active = False

    async def _discover_social_media(self, enriched: EnrichedLead):
        """Discover social media profiles"""
        business_name = enriched.lead_data.get('business_name', '')
        city = enriched.lead_data.get('city', '')

        # Generate likely social media URLs
        # LinkedIn
        linkedin = enriched.lead_data.get('linkedin_url')
        if linkedin:
            enriched.social_media['linkedin'] = linkedin

        # Facebook (guess URL)
        if business_name:
            fb_slug = business_name.lower().replace(' ', '-').replace("'", '')
            enriched.social_media['facebook'] = f"https://facebook.com/{fb_slug}"

        # Instagram (guess URL)
        if business_name:
            ig_slug = business_name.lower().replace(' ', '').replace("'", '')
            enriched.social_media['instagram'] = f"https://instagram.com/{ig_slug}"

    async def _detect_technologies(self, enriched: EnrichedLead):
        """Detect technologies used on website"""
        website = enriched.lead_data.get('website', '')

        try:
            response = await self.http_client.get(website, follow_redirects=True)

            if response.status_code == 200 and BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'lxml')
                html = str(soup).lower()

                # Detect common technologies
                tech_signatures = {
                    'WordPress': 'wp-content',
                    'Shopify': 'shopify',
                    'Squarespace': 'squarespace',
                    'Wix': 'wix',
                    'React': 'react',
                    'Vue.js': 'vue',
                    'Angular': 'angular',
                    'jQuery': 'jquery',
                    'Bootstrap': 'bootstrap',
                    'TailwindCSS': 'tailwind',
                    'Google Analytics': 'ga(',
                    'Google Tag Manager': 'gtm.js',
                    'Facebook Pixel': 'fbevents',
                    'Hotjar': 'hotjar',
                }

                for tech, signature in tech_signatures.items():
                    if signature in html:
                        enriched.technologies.append(tech)

        except Exception as e:
            print(f"Technology detection failed: {e}")

    def _calculate_confidence(self, enriched: EnrichedLead) -> float:
        """Calculate confidence score for enriched data"""
        score = 0.0

        # Email validation
        if enriched.email_valid is True:
            score += 0.3
        elif enriched.email_valid is False:
            score -= 0.2

        # Disposable email penalty
        if enriched.email_disposable:
            score -= 0.1

        # Website active
        if enriched.website_active:
            score += 0.3

        # Has social media
        score += min(len(enriched.social_media) * 0.1, 0.2)

        # Has business description
        if enriched.business_description:
            score += 0.1

        # Has technologies detected
        if enriched.technologies:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _is_valid_email_format(self, email: str) -> bool:
        """Basic email format validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


async def enrich_leads_batch(
    leads: List[Dict[str, Any]],
    neverbounce_api_key: Optional[str] = None,
    concurrency: int = 5
) -> List[EnrichedLead]:
    """
    Enrich multiple leads in batch with concurrency control

    Args:
        leads: List of lead dictionaries
        neverbounce_api_key: API key for email validation
        concurrency: Number of concurrent enrichment operations

    Returns:
        List of EnrichedLead objects
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def enrich_with_semaphore(lead: Dict[str, Any]) -> EnrichedLead:
        async with semaphore:
            async with LeadEnricher(neverbounce_api_key) as enricher:
                return await enricher.enrich_lead(lead)

    tasks = [enrich_with_semaphore(lead) for lead in leads]
    return await asyncio.gather(*tasks)


def duplicate_detection(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect and remove duplicate leads

    Args:
        leads: List of lead dictionaries

    Returns:
        List of unique leads
    """
    seen = set()
    unique_leads = []

    for lead in leads:
        # Create fingerprint from email, website, and business name
        fingerprint = (
            lead.get('email', '').lower(),
            lead.get('website', '').lower(),
            lead.get('business_name', '').lower(),
            lead.get('phone', '')
        )

        if fingerprint not in seen:
            seen.add(fingerprint)
            unique_leads.append(lead)

    return unique_leads
