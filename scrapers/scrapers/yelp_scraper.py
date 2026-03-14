"""
LeadForge AI - Yelp Scraper
Scrapes business listings from Yelp
"""
import asyncio
from typing import List, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapedLead


class YelpScraper(BaseScraper):
    """Scraper for Yelp business listings"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://www.yelp.com/search"

    async def search(
        self,
        query: str,
        location: str,
        max_leads: int = 100
    ) -> List[ScrapedLead]:
        """
        Search Yelp for businesses

        Args:
            query: Business type or keyword (e.g., "restaurants", "plumbers")
            location: City or region (e.g., "New York, NY")
            max_leads: Maximum number of leads to scrape

        Returns:
            List of ScrapedLead objects
        """
        params = {
            'find_desc': query,
            'find_loc': location
        }

        print(f"Searching Yelp for: {query} in {location}")

        leads = []
        try:
            page = await self.fetch_page_playwright(
                f"{self.base_url}?find_desc={quote_plus(query)}&find_loc={quote_plus(location)}"
            )

            if not page:
                return leads

            # Wait for results to load
            await asyncio.sleep(3)

            # Scroll to load more results
            for _ in range(5):
                await page.keyboard.press('End')
                await asyncio.sleep(1)

            # Get all business listings
            listings = await page.query_selector_all('[data-testid="serp-ia-card"]')

            for listing in listings[:max_leads]:
                try:
                    lead = await self._parse_listing(listing)
                    if lead:
                        lead.source_name = "yelp"
                        lead.city = location
                        leads.append(lead)
                except Exception as e:
                    print(f"Error parsing listing: {e}")
                    continue

            await page.close()

        except Exception as e:
            print(f"Error searching Yelp: {e}")

        return leads

    async def _parse_listing(self, listing) -> Optional[ScrapedLead]:
        """Parse a Yelp listing into a ScrapedLead"""
        try:
            # Get business name
            name_elem = await listing.query_selector('h3 a')
            name = await name_elem.inner_text() if name_elem else "Unknown"

            # Get rating
            rating_elem = await listing.query_selector('[aria-label*="star rating"]')
            rating_text = await rating_elem.get_attribute('aria-label') if rating_elem else ""
            rating = float(rating_text.split()[0]) if rating_text else 0

            # Get review count
            review_elem = await listing.query_selector('[data-font-weight="semibold"]')
            review_count_text = await review_elem.inner_text() if review_elem else "0"

            # Get address
            address_elem = await listing.query_selector('p[class*="address"]')
            address = await address_elem.inner_text() if address_elem else ""

            # Get phone
            phone_elem = await listing.query_selector('p[class*="phone"]')
            phone = await phone_elem.inner_text() if phone_elem else ""

            # Get website
            link_elem = await listing.query_selector('h3 a')
            website = f"https://www.yelp.com{await link_elem.get_attribute('href')}" if link_elem else ""

            # Parse city/state from address
            city, state = self._parse_location(address)

            # Estimate company size and revenue
            company_size, estimated_revenue = self._estimate_metrics(
                rating,
                review_count_text,
                bool(address and phone)
            )

            # Detect industry from category
            industry = await self._detect_industry(listing)

            return ScrapedLead(
                business_name=name,
                phone=phone,
                website=website,
                industry=industry,
                city=city,
                state=state,
                company_size=company_size,
                estimated_revenue=estimated_revenue,
                source_url=website,
                raw_data={
                    "rating": rating,
                    "review_count": review_count_text,
                    "address": address
                }
            )

        except Exception as e:
            print(f"Error parsing Yelp listing: {e}")
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

    def _estimate_metrics(self, rating: float, review_count: str, established: bool) -> tuple:
        """Estimate company size and revenue"""
        # Parse review count
        try:
            count = int(review_count.replace('reviews', '').replace('review', '').strip())
        except:
            count = 0

        if rating >= 4.5 and count >= 100 and established:
            return "51-200", "$1M-$10M"
        elif rating >= 4.0 and count >= 50:
            return "11-50", "$500K-$1M"
        elif rating >= 3.5 and count >= 20:
            return "2-10", "$100K-$500K"
        else:
            return "1", "<$100K"

    async def _detect_industry(self, listing) -> Optional[str]:
        """Detect industry from category tags"""
        try:
            category_elems = await listing.query_selector_all('a[aria-label*="Category"]')
            if category_elems:
                categories = []
                for elem in category_elems[:3]:
                    text = await elem.inner_text()
                    categories.append(text)
                return ', '.join(categories) if categories else None
        except:
            pass
        return None

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
            source_name="yelp"
        )
