"""Anthropic blog/news scraper service using RSS feeds."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import feedparser  # pyright: ignore[reportMissingImports]
import requests  # pyright: ignore[reportMissingImports,reportMissingModuleSource]
from pydantic import BaseModel, Field  # pyright: ignore[reportMissingImports]
from docling.document_converter import DocumentConverter
DOCLING_AVAILABLE = True

class AnthropicArticle(BaseModel):
    """Model for Anthropic blog article."""
    
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    published_date: Optional[datetime] = Field(None, description="Article publication date")
    description: str = Field(default="", description="Article description/excerpt")
    category: str = Field(default="", description="Article category (news, engineering, research)")
    source_feed: str = Field(default="", description="Source RSS feed name")
    markdown_content: Optional[str] = Field(None, description="Article content in Markdown format")


class AnthropicScraper:
    """Service to scrape Anthropic news/blog articles from multiple RSS feeds."""
    
    RSS_FEEDS = {
        "news": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
        "engineering": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml",
        "research": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
    }
    
    def __init__(self):
        """Initialize the Anthropic scraper."""
        self._docling_converter = None
        if DOCLING_AVAILABLE:
            try:
                # Initialize docling converter
                self._docling_converter = DocumentConverter()
            except Exception as e:
                print(f"Warning: Failed to initialize docling converter: {e}")
                self._docling_converter = None
    
    def fetch_rss_feed(self, feed_url: str) -> feedparser.FeedParserDict:
        """Fetch and parse a single RSS feed."""
        response = requests.get(feed_url, timeout=10)
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
    
    def get_articles(
        self, 
        hours: int = 24,
        feeds: Optional[List[str]] = None,
        max_articles_without_date: int = 10
    ) -> List[AnthropicArticle]:
        """
        Get articles from Anthropic RSS feeds within the specified time window.
        
        Args:
            hours: Number of hours to look back (default: 24)
            feeds: List of feed names to fetch from. If None, fetches from all feeds.
                   Options: 'news', 'engineering', 'research'
            max_articles_without_date: Maximum number of articles without dates to include
                                      (RSS feeds show recent first, so limit to avoid old articles)
            
        Returns:
            List of AnthropicArticle models within the time window, sorted by date
        """
        if feeds is None:
            feeds = list(self.RSS_FEEDS.keys())
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        all_articles = []
        articles_without_date = []
        
        for feed_name in feeds:
            if feed_name not in self.RSS_FEEDS:
                continue
            
            feed_url = self.RSS_FEEDS[feed_name]
            try:
                feed = self.fetch_rss_feed(feed_url)
                
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
                        articles_without_date.append((feed_name, entry))
                        continue
                    
                    # Extract category from entry if available
                    category = ""
                    if hasattr(entry, 'category'):
                        if isinstance(entry.category, list) and len(entry.category) > 0:
                            category = entry.category[0]
                        elif isinstance(entry.category, str):
                            category = entry.category
                    
                    article = AnthropicArticle(
                        title=entry.title,
                        url=entry.link,
                        published_date=published_date,
                        description=getattr(entry, 'description', ''),
                        category=category,
                        source_feed=feed_name,
                    )
                    all_articles.append(article)
            except Exception as e:
                # Log error but continue with other feeds
                print(f"Error fetching {feed_name} feed: {e}")
                continue
        
        # Add articles without dates (limit to most recent ones)
        for feed_name, entry in articles_without_date[:max_articles_without_date]:
            category = ""
            if hasattr(entry, 'category'):
                if isinstance(entry.category, list) and len(entry.category) > 0:
                    category = entry.category[0]
                elif isinstance(entry.category, str):
                    category = entry.category
            
            article = AnthropicArticle(
                title=entry.title,
                url=entry.link,
                published_date=None,
                description=getattr(entry, 'description', ''),
                category=category,
                source_feed=feed_name,
            )
            all_articles.append(article)
        
        # Remove duplicates based on URL (same article might appear in multiple feeds)
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)
        
        # Sort by published_date (most recent first)
        unique_articles.sort(
            key=lambda x: x.published_date or datetime.min.replace(tzinfo=timezone.utc), 
            reverse=True
        )
        
        return unique_articles
    
    def convert_article_to_markdown(self, article: AnthropicArticle) -> Optional[str]:
        """
        Convert an article's HTML content to Markdown using docling.
        
        Args:
            article: AnthropicArticle object with URL to convert
            
        Returns:
            Markdown content as string, or None if conversion fails
        """
        if not DOCLING_AVAILABLE or self._docling_converter is None:
            print("Warning: docling is not available. Cannot convert to markdown.")
            return None
        
        try:
            # Use docling to convert the URL to a document
            result = self._docling_converter.convert(article.url)
            
            # Use export_to_markdown method to get markdown content
            if hasattr(result, 'document') and result.document:
                markdown = result.document.export_to_markdown()
                return markdown
            else:
                print(f"Warning: docling conversion did not return a document for {article.url}")
                return None
                
        except Exception as e:
            print(f"Error converting article '{article.title}' to markdown: {e}")
            return None
    
    def get_articles_with_markdown(
        self,
        hours: int = 24,
        feeds: Optional[List[str]] = None,
        convert_to_markdown: bool = True
    ) -> List[AnthropicArticle]:
        """
        Get articles and optionally convert their content to Markdown.
        
        Args:
            hours: Number of hours to look back (default: 24)
            feeds: List of feed names to fetch from. If None, fetches from all feeds.
            convert_to_markdown: Whether to convert article content to markdown (default: True)
            
        Returns:
            List of AnthropicArticle models with markdown_content populated if conversion enabled
        """
        articles = self.get_articles(hours=hours, feeds=feeds)
        
        if convert_to_markdown:
            for article in articles:
                markdown = self.convert_article_to_markdown(article)
                if markdown:
                    article.markdown_content = markdown
        
        return articles


if __name__ == "__main__":
    scraper = AnthropicScraper()
    # articles = scraper.get_articles 
    articles = scraper.get_articles_with_markdown(hours=24)
    
    print(f"Found {len(articles)} articles in last 24 hours:\n")
    for article in articles:
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")
        print(f"Published: {article.published_date}")
        print(f"Category: {article.category}")
        print(f"Source Feed: {article.source_feed}")
        print(f"Description: {article.description[:150]}...")
        print("-" * 60)
