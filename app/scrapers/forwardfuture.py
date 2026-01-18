"""ForwardFuture.ai (Matthew Berman) scraper service using sitemap.xml."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from xml.etree import ElementTree

import requests  # pyright: ignore[reportMissingImports,reportMissingModuleSource]
from pydantic import BaseModel, Field  # pyright: ignore[reportMissingImports]


class ForwardFutureArticle(BaseModel):
    """Model for ForwardFuture.ai article."""
    
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    published_date: Optional[datetime] = Field(None, description="Article publication date")
    description: str = Field(default="", description="Article description/excerpt")


class ForwardFutureScraper:
    """Service to scrape ForwardFuture.ai articles from sitemap.xml."""
    
    SITEMAP_URL = "https://www.forwardfuture.ai/sitemap.xml"
    
    def __init__(self):
        """Initialize the ForwardFuture scraper."""
        pass
    
    def fetch_sitemap(self) -> ElementTree.Element:
        """Fetch and parse the sitemap.xml."""
        response = requests.get(self.SITEMAP_URL, timeout=10)
        response.raise_for_status()
        return ElementTree.fromstring(response.content)
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from sitemap (format: YYYY-MM-DD)."""
        try:
            # Sitemap dates are typically YYYY-MM-DD
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract a readable title from the URL slug."""
        # URL format: https://www.forwardfuture.ai/p/article-slug
        if '/p/' in url:
            slug = url.split('/p/')[-1]
            # Convert slug to title (replace hyphens with spaces, capitalize)
            title = slug.replace('-', ' ').title()
            return title
        return url
    
    def get_articles(
        self,
        hours: int = 48,
        max_articles_without_date: int = 10
    ) -> List[ForwardFutureArticle]:
        """
        Get articles from ForwardFuture.ai sitemap within the specified time window.
        
        Args:
            hours: Number of hours to look back (default: 48)
            max_articles_without_date: Maximum number of articles without dates to include
            
        Returns:
            List of ForwardFutureArticle models within the time window, sorted by date
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        articles = []
        articles_without_date = []
        
        try:
            root = self.fetch_sitemap()
            
            # Parse sitemap namespace
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            for url_elem in root.findall('.//ns:url', namespace):
                loc_elem = url_elem.find('ns:loc', namespace)
                lastmod_elem = url_elem.find('ns:lastmod', namespace)
                
                if loc_elem is None:
                    continue
                
                url = loc_elem.text
                if not url:
                    continue
                
                # Only process article URLs (those with /p/ prefix)
                if '/p/' not in url:
                    continue
                
                # Parse date
                published_date = None
                if lastmod_elem is not None and lastmod_elem.text:
                    published_date = self._parse_date(lastmod_elem.text)
                
                # Filter by time if date is available
                if published_date:
                    now = datetime.now(timezone.utc)
                    # If date is more than 1 day in the future, it's likely incorrect - include it
                    if published_date > now + timedelta(days=1):
                        pass  # Include future dates
                    elif published_date < cutoff_time:
                        continue  # Skip old articles
                else:
                    # No date available - collect separately
                    articles_without_date.append((url, published_date))
                    continue
                
                # Extract title from URL
                title = self._extract_title_from_url(url)
                
                article = ForwardFutureArticle(
                    title=title,
                    url=url,
                    published_date=published_date,
                    description="",  # Can be enhanced later by fetching the page
                )
                articles.append(article)
            
            # Add articles without dates (limit to most recent ones)
            for url, _ in articles_without_date[:max_articles_without_date]:
                title = self._extract_title_from_url(url)
                article = ForwardFutureArticle(
                    title=title,
                    url=url,
                    published_date=None,
                    description="",
                )
                articles.append(article)
            
        except Exception as e:
            print(f"Error fetching ForwardFuture sitemap: {e}")
            return []
        
        # Sort by published_date (most recent first)
        articles.sort(
            key=lambda x: x.published_date or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )
        
        return articles


if __name__ == "__main__":
    scraper = ForwardFutureScraper()
    articles = scraper.get_articles(hours=75)
    
    print(f"Found {len(articles)} articles in last 48 hours:\n")
    for article in articles:
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")
        print(f"Published: {article.published_date}")
        print(f"Description: {article.description[:150]}...")
        print("-" * 60)
