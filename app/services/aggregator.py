"""Main aggregator service that collects content from all sources."""

from datetime import datetime
from typing import List, Dict, Any

from app.scrapers.youtube import YouTubeScraper, ChannelVideo
from app.scrapers.anthropic import AnthropicScraper, AnthropicArticle
from app.scrapers.openai import OpenAIScraper, OpenAIArticle
from app.scrapers.forwardfuture import ForwardFutureScraper, ForwardFutureArticle
from config.youtube_channels import YOUTUBE_CHANNELS


class NewsAggregator:
    """Main service that aggregates content from all sources."""
    
    def __init__(self, hours: int = 48):
        """
        Initialize the news aggregator.
        
        Args:
            hours: Number of hours to look back for content (default: 48)
        """
        self.hours = hours
        self.youtube_scraper = YouTubeScraper()
        self.anthropic_scraper = AnthropicScraper()
        self.openai_scraper = OpenAIScraper()
        self.forwardfuture_scraper = ForwardFutureScraper()
    
    def collect_all_content(self) -> Dict[str, Any]:
        """
        Collect content from all sources.
        
        Returns:
            Dictionary containing all collected content:
            {
                'youtube_videos': List[ChannelVideo],
                'anthropic_articles': List[AnthropicArticle],
                'openai_articles': List[OpenAIArticle],
                'forwardfuture_articles': List[ForwardFutureArticle],
                'timestamp': datetime
            }
        """
        print(f"Collecting content from last {self.hours} hours...")
        
        results = {
            'youtube_videos': [],
            'anthropic_articles': [],
            'openai_articles': [],
            'forwardfuture_articles': [],
            'timestamp': datetime.now(),
        }
        
        # Collect YouTube videos
        if YOUTUBE_CHANNELS:
            print(f"\nFetching videos from {len(YOUTUBE_CHANNELS)} YouTube channel(s)...")
            for channel in YOUTUBE_CHANNELS:
                try:
                    videos = self.youtube_scraper.get_latest_videos(
                        channel_identifier=channel,
                        hours=self.hours,
                        include_transcripts=False  # Set to True if you want transcripts
                    )
                    results['youtube_videos'].extend(videos)
                    print(f"  ✓ Found {len(videos)} videos from {channel}")
                except Exception as e:
                    print(f"  ✗ Error fetching from {channel}: {e}")
        else:
            print("No YouTube channels configured.")
        
        # Collect Anthropic articles
        print("\nFetching Anthropic articles...")
        try:
            anthropic_articles = self.anthropic_scraper.get_articles(hours=self.hours)
            results['anthropic_articles'] = anthropic_articles
            print(f"  ✓ Found {len(anthropic_articles)} Anthropic articles")
        except Exception as e:
            print(f"  ✗ Error fetching Anthropic articles: {e}")
        
        # Collect OpenAI articles
        print("\nFetching OpenAI articles...")
        try:
            openai_articles = self.openai_scraper.get_articles(hours=self.hours)
            results['openai_articles'] = openai_articles
            print(f"  ✓ Found {len(openai_articles)} OpenAI articles")
        except Exception as e:
            print(f"  ✗ Error fetching OpenAI articles: {e}")
        
        # Collect ForwardFuture articles
        print("\nFetching ForwardFuture articles...")
        try:
            forwardfuture_articles = self.forwardfuture_scraper.get_articles(hours=self.hours)
            results['forwardfuture_articles'] = forwardfuture_articles
            print(f"  ✓ Found {len(forwardfuture_articles)} ForwardFuture articles")
        except Exception as e:
            print(f"  ✗ Error fetching ForwardFuture articles: {e}")
        
        # Summary
        total_items = (
            len(results['youtube_videos']) +
            len(results['anthropic_articles']) +
            len(results['openai_articles']) +
            len(results['forwardfuture_articles'])
        )
        print(f"\n{'='*60}")
        print(f"Total items collected: {total_items}")
        print(f"  - YouTube videos: {len(results['youtube_videos'])}")
        print(f"  - Anthropic articles: {len(results['anthropic_articles'])}")
        print(f"  - OpenAI articles: {len(results['openai_articles'])}")
        print(f"  - ForwardFuture articles: {len(results['forwardfuture_articles'])}")
        print(f"{'='*60}")
        
        return results


def run_aggregator(hours: int = 48) -> Dict[str, Any]:
    """
    Convenience function to run the aggregator.
    
    Args:
        hours: Number of hours to look back (default: 48)
        
    Returns:
        Dictionary with all collected content
    """
    aggregator = NewsAggregator(hours=hours)
    return aggregator.collect_all_content()


if __name__ == "__main__":
    # Example usage
    results = run_aggregator(hours=48)
    
    # Print some details
    print("\n" + "="*60)
    print("Sample Content:")
    print("="*60)
    
    if results['youtube_videos']:
        print(f"\nYouTube Videos ({len(results['youtube_videos'])}):")
        for video in results['youtube_videos'][:3]:
            print(f"  - {video.title}")
    
    if results['anthropic_articles']:
        print(f"\nAnthropic Articles ({len(results['anthropic_articles'])}):")
        for article in results['anthropic_articles'][:3]:
            print(f"  - {article.title}")
    
    if results['openai_articles']:
        print(f"\nOpenAI Articles ({len(results['openai_articles'])}):")
        for article in results['openai_articles'][:3]:
            print(f"  - {article.title}")
    
    if results['forwardfuture_articles']:
        print(f"\nForwardFuture Articles ({len(results['forwardfuture_articles'])}):")
        for article in results['forwardfuture_articles'][:3]:
            print(f"  - {article.title}")