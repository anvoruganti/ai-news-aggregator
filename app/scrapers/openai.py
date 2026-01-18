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
            # Try published_parsed first (most reliable)
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt = datetime(*entry.published_parsed[:6])
                dt = dt.replace(tzinfo=timezone.utc)
                return dt
            
            # Fallback to updated_parsed
            if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                dt = datetime(*entry.updated_parsed[:6])
                dt = dt.replace(tzinfo=timezone.utc)
                return dt
            
            # Try parsing published string directly using feedparser's parse function
            if hasattr(entry, 'published') and entry.published:
                try:
                    # Re-parse just the date string
                    temp_feed = feedparser.parse(f'<rss><channel><item><pubDate>{entry.published}</pubDate></item></channel></rss>')
                    if temp_feed.entries and hasattr(temp_feed.entries[0], 'published_parsed'):
                        parsed = temp_feed.entries[0].published_parsed
                        if parsed:
                            dt = datetime(*parsed[:6])
                            dt = dt.replace(tzinfo=timezone.utc)
                            return dt
                except Exception:
                    pass
            
            return None
        except Exception as e:
            # Log parsing errors for debugging
            print(f"Warning: Failed to parse date for entry: {e}")
            return None
    
    def get_articles(self, hours: int = 24, max_articles_without_date: int = 10) -> List[OpenAIArticle]:
        """
        Get articles from OpenAI RSS feed within the specified time window.
        
        Args:
            hours: Number of hours to look back (default: 24)
            max_articles_without_date: Maximum number of articles without dates to include
                                      (RSS feeds show recent first, so limit to avoid old articles)
            
        Returns:
            List of OpenAIArticle models within the time window
        """
        feed = self.fetch_rss_feed()
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        articles = []
        articles_without_date = []
        
        for entry in feed.entries:
            published_date = self._parse_published_date(entry)
            
            # Filter by time if published_date is available and valid
            if published_date:
                now = datetime.now(timezone.utc)
                # If date is more than 1 day in the future, it's likely incorrect - include it
                if published_date > now + timedelta(days=1):
                    # Future date, likely incorrect - treat as recent and include
                    pass
                elif published_date < cutoff_time:
                    # Old article, skip it
                    continue
            else:
                # No date available - RSS feeds typically show recent articles first
                # We'll collect these separately and limit them
                articles_without_date.append(entry)
                continue
            
            article = OpenAIArticle(
                title=entry.title,
                url=entry.link,
                published_date=published_date,
                description=getattr(entry, 'description', ''),
            )
            articles.append(article)
        
        # Add articles without dates (limit to most recent ones)
        for entry in articles_without_date[:max_articles_without_date]:
            article = OpenAIArticle(
                title=entry.title,
                url=entry.link,
                published_date=None,
                description=getattr(entry, 'description', ''),
            )
            articles.append(article)
        
        # Sort by published_date (most recent first)
        articles.sort(key=lambda x: x.published_date or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        
        return articles


if __name__ == "__main__":
    scraper = OpenAIScraper()
    hours_param = 48
    articles = scraper.get_articles(hours=hours_param)
    
    print(f"Found {len(articles)} articles in last {hours_param} hours:\n")
    for article in articles:
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")
        print(f"Published: {article.published_date}")
        print(f"Description: {article.description}...")
        print("-" * 60)
