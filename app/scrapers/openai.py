"""OpenAI blog/news scraper service using RSS feed."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import feedparser  # pyright: ignore[reportMissingImports]
import requests  # pyright: ignore[reportMissingImports,reportMissingModuleSource]
from pydantic import BaseModel, Field  # pyright: ignore[reportMissingImports]


class OpenAIArticle(BaseModel):
    """Model for OpenAI blog article."""
    
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    published_date: Optional[datetime] = Field(None, description="Article publication date")
    description: str = Field(default="", description="Article description/excerpt")


class OpenAIScraper:
    """Service to scrape OpenAI news/blog articles from RSS feed."""
    
    RSS_FEED_URL = "https://openai.com/news/rss.xml"
    
    def __init__(self):
        """Initialize the OpenAI scraper."""
        pass
    
    def fetch_rss_feed(self) -> feedparser.FeedParserDict:
        """Fetch and parse the RSS feed."""
        response = requests.get(self.RSS_FEED_URL, timeout=10)
        response.raise_for_status()
        return feedparser.parse(response.content)
    
    def _parse_published_date(self, entry) -> Optional[datetime]:
        """Parse published date from RSS feed entry."""
        try:
            # feedparser provides published_parsed as a struct_time
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                # Convert struct_time to datetime
                dt = datetime(*entry.published_parsed[:6])
                # RSS dates are typically in GMT/UTC
                dt = dt.replace(tzinfo=timezone.utc)
                return dt
            return None
        except Exception:
            return None
    
    def get_articles(self, hours: int = 24) -> List[OpenAIArticle]:
        """
        Get articles from OpenAI RSS feed within the specified time window.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            List of OpenAIArticle models within the time window
        """
        feed = self.fetch_rss_feed()
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # print(feed.entries[0])
        
        articles = []
        for entry in feed.entries:
            published_date = self._parse_published_date(entry)
            
            # Filter by time if published_date is available
            if published_date and published_date < cutoff_time:
                continue
            
            article = OpenAIArticle(
                title=entry.title,
                url=entry.link,
                published_date=published_date,
                description=getattr(entry, 'description', ''),
            )
            articles.append(article)
        
        # Sort by published_date (most recent first)
        articles.sort(key=lambda x: x.published_date or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        
        return articles


if __name__ == "__main__":
    scraper = OpenAIScraper()
    articles = scraper.get_articles(hours=24)
    
    print(f"Found {len(articles)} articles in last 24 hours:\n")
    for article in articles:
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")
        print(f"Published: {article.published_date}")
        print(f"Description: {article.description[:150]}...")
        print("-" * 60)
