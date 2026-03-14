"""
LeadForge AI - Base Scraper Class
Provides common scraping functionality with proxy rotation, rate limiting, and retry logic
"""
import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from bs4 import BeautifulSoup
import requests


@dataclass
class ScraperConfig:
    """Configuration for scraper behavior"""
    concurrent_requests: int = 5
    delay_min: int = 1
    delay_max: int = 3
    max_retries: int = 3
    use_proxies: bool = True
    headless: bool = True


@dataclass
class ScrapedLead:
    """Represents a scraped lead"""
    business_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_size: Optional[str] = None
    estimated_revenue: Optional[str] = None
    source_url: Optional[str] = None
    source_name: str = "unknown"
    raw_data: Optional[Dict[str, Any]] = None


class ProxyRotator:
    """Manages proxy rotation for scraping"""

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]

    def __init__(self, proxy_list: Optional[List[str]] = None):
        """
        Initialize proxy rotator

        Args:
            proxy_list: List of proxy URLs in format "http://user:pass@host:port"
        """
        self.proxy_list = proxy_list or []
        self.current_index = 0

    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(self.USER_AGENTS)

    def get_proxy(self) -> Optional[str]:
        """Get next proxy in rotation"""
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxy_list)
        return proxy

    def add_proxy(self, proxy_url: str):
        """Add a proxy to the rotation"""
        if proxy_url not in self.proxy_list:
            self.proxy_list.append(proxy_url)


class RateLimiter:
    """Rate limiting for scraper requests"""

    def __init__(self, requests_per_minute: int = 30):
        """
        Initialize rate limiter

        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_minute = requests_per_minute
        self.request_times = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Wait if rate limit would be exceeded"""
        async with self.lock:
            now = time.time()
            # Remove old request times (>1 minute ago)
            self.request_times = [t for t in self.request_times if now - t < 60]

            if len(self.request_times) >= self.requests_per_minute:
                # Wait until we can make another request
                sleep_time = 60 - (now - self.request_times[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    self.request_times = []

            self.request_times.append(now)


class BaseScraper(ABC):
    """Base class for all scrapers"""

    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        proxy_rotator: Optional[ProxyRotator] = None
    ):
        """
        Initialize base scraper

        Args:
            config: Scraper configuration
            proxy_rotator: Proxy rotator instance
        """
        self.config = config or ScraperConfig()
        self.proxy_rotator = proxy_rotator or ProxyRotator()
        self.rate_limiter = RateLimiter(requests_per_minute=30)
        self.session: Optional[requests.Session] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def initialize_session(self):
        """Initialize HTTP session with proper headers"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.proxy_rotator.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

    async def initialize_browser(self):
        """Initialize Playwright browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.config.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )

        # Create context with random user agent
        self.context = await self.browser.new_context(
            user_agent=self.proxy_rotator.get_random_user_agent(),
            viewport={'width': 1920, 'height': 1080}
        )

    async def close(self):
        """Clean up resources"""
        if self.session:
            self.session.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(self.config.delay_min, self.config.delay_max)
        await asyncio.sleep(delay)

    async def fetch_page(
        self,
        url: str,
        method: str = "GET",
        **kwargs
    ) -> Optional[str]:
        """
        Fetch a page with retry logic

        Args:
            url: URL to fetch
            method: HTTP method
            **kwargs: Additional arguments for requests

        Returns:
            Page content as string or None if failed
        """
        if not self.session:
            await self.initialize_session()

        await self.rate_limiter.acquire()
        await self.random_delay()

        for attempt in range(self.config.max_retries):
            try:
                # Update user agent for each request
                self.session.headers.update({
                    'User-Agent': self.proxy_rotator.get_random_user_agent()
                })

                # Add proxy if available
                if self.config.use_proxies:
                    proxy = self.proxy_rotator.get_proxy()
                    if proxy:
                        kwargs['proxies'] = {'http': proxy, 'https': proxy}

                response = self.session.request(method, url, timeout=30, **kwargs)
                response.raise_for_status()
                return response.text

            except requests.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    print(f"Failed to fetch {url} after {self.config.max_retries} attempts: {e}")
                    return None
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return None

    async def fetch_page_playwright(self, url: str) -> Optional[Page]:
        """
        Fetch a page using Playwright (for JavaScript-heavy sites)

        Args:
            url: URL to fetch

        Returns:
            Page object or None if failed
        """
        if not self.context:
            await self.initialize_browser()

        await self.rate_limiter.acquire()
        await self.random_delay()

        try:
            page = await self.context.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            return page
        except Exception as e:
            print(f"Failed to fetch {url} with Playwright: {e}")
            return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content"""
        return BeautifulSoup(html, 'lxml')

    @abstractmethod
    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        **kwargs
    ) -> List[ScrapedLead]:
        """
        Search for leads

        Args:
            query: Search query
            location: Optional location filter
            **kwargs: Additional search parameters

        Returns:
            List of scraped leads
        """
        pass

    @abstractmethod
    def parse_lead(self, data: Any) -> ScrapedLead:
        """
        Parse raw data into a ScrapedLead

        Args:
            data: Raw data from scraping

        Returns:
            ScrapedLead object
        """
        pass

    async def scrape_with_limit(
        self,
        search_func,
        max_leads: int = 100,
        **kwargs
    ) -> List[ScrapedLead]:
        """
        Scrape with a limit on number of leads

        Args:
            search_func: Search function to call
            max_leads: Maximum number of leads to scrape
            **kwargs: Arguments to pass to search function

        Returns:
            List of scraped leads (up to max_leads)
        """
        leads = []
        try:
            async for lead in search_func(**kwargs):
                leads.append(lead)
                if len(leads) >= max_leads:
                    break
        except Exception as e:
            print(f"Error during scraping: {e}")

        return leads
