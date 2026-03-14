"""
LeadForge AI - Google Maps Scraper
Scrapes business listings from Google Maps
"""
import asyncio
from typing import List, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapedLead


class GoogleMapsScraper(BaseScraper):
    """Scraper for Google Maps business listings"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://www.google.com/maps/search/"

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        max_leads: int = 100
    ) -> List[ScrapedLead]:
        """
        Search Google Maps for businesses

        Args:
            query: Business type or keyword (e.g., "restaurants", "plumbers")
            location: City or region (e.g., "New York, NY")
            max_leads: Maximum number of leads to scrape

        Returns:
            List of ScrapedLead objects
        """
        search_query = query
        if location:
            search_query = f"{query} {location}"

        encoded_query = quote_plus(search_query)
        url = f"{self.base_url}{encoded_query}"

        print(f"Searching Google Maps for: {search_query}")

        leads = []
        try:
            page = await self.fetch_page_playwright(url)
            if not page:
                return leads

            # Wait for results to load
            await asyncio.sleep(3)

            # Scroll to load more results
            for _ in range(5):
                await page.keyboard.press('End')
                await asyncio.sleep(1)

            # Get all business listings
            listings = await page.query_selector_all('div[role="article"]')

            for listing in listings[:max_leads]:
                try:
                    lead = await self._parse_listing(listing)
                    if lead:
                        lead.source_name = "google_maps"
                        leads.append(lead)
                except Exception as e:
                    print(f"Error parsing listing: {e}")
                    continue

            await page.close()

        except Exception as e:
            print(f"Error searching Google Maps: {e}")

        return leads

    async def _parse_listing(self, listing) -> Optional[ScrapedLead]:
        """Parse a Google Maps listing into a ScrapedLead"""
        try:
            # Get business name
            name_elem = await listing.query_selector('a[role="heading"]')
            name = await name_elem.inner_text() if name_elem else "Unknown"

            # Get rating and reviews (for quality scoring)
            rating_elem = await listing.query_selector('span[aria-label*="stars"]')
            rating_text = await rating_elem.get_attribute('aria-label') if rating_elem else ""
            rating = float(rating_text.split()[0]) if rating_text else 0

            # Get address
            address_elem = await listing.query_selector('button[data-item-id*="address"]')
            address = await address_elem.get_attribute('aria-label') if address_elem else ""

            # Get phone
            phone_elem = await listing.query_selector('button[data-item-id*="phone:"]')
            phone = await phone_elem.get_attribute('aria-label') if phone_elem else ""
            if phone and phone.startswith("phone:"):
                phone = phone.replace("phone:", "").strip()

            # Get website
            website_elem = await listing.query_selector('a[data-item-id*="authority"]')
            website = await website_elem.get_attribute('href') if website_elem else ""

            # Parse city/state from address
            city, state = self._parse_location(address)

            # Estimate company size and revenue based on rating and presence
            company_size, estimated_revenue = self._estimate_metrics(rating, website)

            return ScrapedLead(
                business_name=name,
                phone=phone,
                website=website,
                city=city,
                state=state,
                company_size=company_size,
                estimated_revenue=estimated_revenue,
                source_url=website,
                raw_data={
                    "rating": rating,
                    "address": address
                }
            )

        except Exception as e:
            print(f"Error parsing listing: {e}")
            return None

    def _parse_location(self, address: str) -> tuple:
        """Parse city and state from address"""
        if not address:
            return None, None

        parts = address.split(',')
        if len(parts) >= 2:
            city = parts[-2].strip() if len(parts) > 1 else None
            state = parts[-1].strip().split()[0] if len(parts) > 0 else None
            return city, state

        return None, None

    def _estimate_metrics(self, rating: float, has_website: bool) -> tuple:
        """Estimate company size and revenue based on available data"""
        # Simple estimation logic - can be enhanced with ML
        if rating >= 4.5 and has_website:
            return "51-200", "$1M-$10M"
        elif rating >= 4.0:
            return "11-50", "$500K-$1M"
        elif rating >= 3.5:
            return "2-10", "$100K-$500K"
        else:
            return "1", "<$100K"

    def parse_lead(self, data: dict) -> ScrapedLead:
        """Parse dictionary data into ScrapedLead"""
        return ScrapedLead(
            business_name=data.get('name', ''),
            phone=data.get('phone'),
            website=data.get('website'),
            city=data.get('city'),
            state=data.get('state'),
            industry=data.get('industry'),
            source_url=data.get('source_url'),
            source_name="google_maps"
        )
