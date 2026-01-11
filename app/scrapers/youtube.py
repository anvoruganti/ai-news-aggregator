"""YouTube scraper service for fetching videos from RSS feeds and extracting transcripts."""

import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

import feedparser  # pyright: ignore[reportMissingImports]
import requests  # pyright: ignore[reportMissingImports,reportMissingModuleSource]
from pydantic import BaseModel, Field  # pyright: ignore[reportMissingImports]
from youtube_transcript_api import (  # pyright: ignore[reportMissingImports]
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)


class Transcript(BaseModel):
    """Model for video transcript."""
    
    text: str = Field(..., description="The transcript text content")


class ChannelVideo(BaseModel):
    """Model for YouTube channel video."""
    
    title: str = Field(..., description="Video title")
    link: str = Field(..., description="Video URL")
    video_id: Optional[str] = Field(None, description="YouTube video ID")
    published_date: Optional[datetime] = Field(None, description="Video publication date")
    description: str = Field(default="", description="Video description")
    channel_id: str = Field(..., description="YouTube channel ID")
    transcript: Optional[Transcript] = Field(None, description="Video transcript if available")


class YouTubeScraper:
    """Service to scrape YouTube channels via RSS feeds and extract video transcripts."""

    RSS_FEED_BASE_URL = "https://www.youtube.com/feeds/videos.xml?channel_id="

    def __init__(self):
        """Initialize the YouTube scraper."""
        pass

    def extract_channel_id(self, channel_identifier: str) -> Optional[str]:
        """
        Extract channel ID from various input formats.
        
        Supports:
        - Direct channel ID: "UCxxxxxxxxxxxxxxxxxxxxxxxxxx"
        - Channel URL: "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxxxxxx"
        - Custom handle URL: "https://www.youtube.com/@ChannelName"
        - Custom handle: "@ChannelName"
        
        Args:
            channel_identifier: Channel ID, URL, or handle
            
        Returns:
            Channel ID string or None if extraction fails
        """
        # If it's already a channel ID (starts with UC and is 24 chars)
        if re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_identifier):
            return channel_identifier
        
        # If it's a channel URL
        if 'youtube.com/channel/' in channel_identifier:
            match = re.search(r'/channel/([a-zA-Z0-9_-]+)', channel_identifier)
            if match:
                return match.group(1)
        
        # If it's a custom handle URL or handle
        if '@' in channel_identifier:
            # For custom handles, we need to resolve them to channel ID
            # This requires fetching the page or using YouTube Data API
            # For now, we'll try to extract from URL or return None
            if 'youtube.com/@' in channel_identifier:
                handle = re.search(r'@([a-zA-Z0-9_-]+)', channel_identifier).group(1)
            else:
                handle = channel_identifier.lstrip('@')
            
            # Try to resolve handle to channel ID via page scraping
            return self._resolve_handle_to_channel_id(handle)
        
        return None

    def _resolve_handle_to_channel_id(self, handle: str) -> Optional[str]:
        """
        Resolve a YouTube handle to channel ID by scraping the channel page.
        
        Args:
            handle: YouTube handle (without @)
            
        Returns:
            Channel ID or None if resolution fails
        """
        try:
            url = f"https://www.youtube.com/@{handle}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Look for channel ID in the page source
            # YouTube embeds the channel ID in various places in the HTML
            match = re.search(r'"channelId":"([^"]+)"', response.text)
            if match:
                return match.group(1)
            
            # Alternative pattern
            match = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/([^"]+)"', response.text)
            if match:
                return match.group(1)
                
        except Exception as e:
            print(f"Error resolving handle {handle} to channel ID: {e}")
        
        return None

    def get_rss_feed_url(self, channel_id: str) -> str:
        """
        Construct RSS feed URL from channel ID.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            RSS feed URL
        """
        return f"{self.RSS_FEED_BASE_URL}{channel_id}"

    def fetch_videos_from_rss(self, channel_id: str) -> List[ChannelVideo]:
        """
        Fetch videos from YouTube RSS feed for a given channel.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            List of ChannelVideo models with title, link, video_id, published_date, description
        """
        rss_url = self.get_rss_feed_url(channel_id)
        
        try:
            # Fetch RSS feed using requests first to validate response
            response = requests.get(rss_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Check if we got valid XML/RSS content
            content_type = response.headers.get('Content-Type', '').lower()
            if 'xml' not in content_type and 'rss' not in content_type and 'atom' not in content_type:
                # Still try to parse, as some feeds don't set content-type correctly
                pass
            
            # Parse the RSS feed content
            feed = feedparser.parse(response.content)
            
            # Check for parsing errors
            if feed.bozo:
                error_msg = str(feed.bozo_exception) if feed.bozo_exception else "Unknown parsing error"
                # Some bozo errors are non-fatal (like missing DTD), check if we have entries
                if not feed.entries:
                    raise Exception(f"RSS feed parsing error: {error_msg}")
            
            # Check if feed has entries
            if not feed.entries:
                print(f"No videos found in RSS feed for channel {channel_id}")
                return []
            
            videos = []
            for entry in feed.entries:
                # Extract video ID from link or yt_videoid
                video_id = None
                if hasattr(entry, 'yt_videoid'):
                    video_id = entry.yt_videoid
                else:
                    # Extract from link: https://www.youtube.com/watch?v=VIDEO_ID
                    match = re.search(r'[?&]v=([a-zA-Z0-9_-]+)', entry.link)
                    if match:
                        video_id = match.group(1)
                
                video = ChannelVideo(
                    title=entry.title,
                    link=entry.link,
                    video_id=video_id,
                    published_date=self._parse_published_date(entry.published),
                    description=getattr(entry, 'summary', ''),
                    channel_id=channel_id,
                    transcript=None,
                )
                videos.append(video)
            
            return videos
            
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error fetching RSS feed for channel {channel_id}: {e}")
            print(f"URL: {rss_url}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Request error fetching RSS feed for channel {channel_id}: {e}")
            return []
        except Exception as e:
            print(f"Error fetching RSS feed for channel {channel_id}: {e}")
            return []

    def _parse_published_date(self, date_string: str) -> Optional[datetime]:
        """
        Parse published date string to datetime object.
        
        Args:
            date_string: Date string from RSS feed (can be struct_time or string)
            
        Returns:
            Timezone-aware datetime object in UTC or None if parsing fails
        """
        try:
            # feedparser provides parsed time as a time.struct_time
            # Check if it's a struct_time object
            if hasattr(date_string, 'timetuple'):
                # feedparser's parsed dates are timezone-aware
                # Convert to UTC datetime
                dt = datetime(*date_string.timetuple()[:6])
                # If the struct_time has timezone info, use it
                if hasattr(date_string, 'tzinfo') and date_string.tzinfo:
                    dt = dt.replace(tzinfo=date_string.tzinfo)
                    return dt.astimezone(timezone.utc)
                # Otherwise, assume UTC
                return dt.replace(tzinfo=timezone.utc)
            
            # Try parsing as string
            try:
                dt = datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %Z')
                # If no timezone info, assume UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                # Try ISO format
                dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                return dt.astimezone(timezone.utc)
        except Exception:
            return None

    def filter_videos_by_time(
        self, 
        videos: List[ChannelVideo], 
        hours: int = 24
    ) -> List[ChannelVideo]:
        """
        Filter videos published within the last N hours.
        
        Args:
            videos: List of ChannelVideo models
            hours: Number of hours to look back (default: 24)
            
        Returns:
            Filtered list of ChannelVideo models
        """
        # Use timezone-aware UTC datetime
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        filtered = []
        for video in videos:
            published_date = video.published_date
            if published_date:
                # Ensure published_date is timezone-aware
                if published_date.tzinfo is None:
                    # Assume UTC if naive
                    published_date = published_date.replace(tzinfo=timezone.utc)
                else:
                    # Convert to UTC if timezone-aware
                    published_date = published_date.astimezone(timezone.utc)
                
                if published_date >= cutoff_time:
                    filtered.append(video)
        
        return filtered

    def get_video_transcript(self, video_id: str, languages: Optional[List[str]] = None) -> Optional[Transcript]:
        """
        Get transcript for a YouTube video.
        
        Args:
            video_id: YouTube video ID
            languages: Preferred languages (default: ['en'] for English)
            
        Returns:
            Transcript model or None if transcript not available
        """
        if languages is None:
            languages = ['en']
        
        try:
            # Create API instance and get list of available transcripts
            yt_api = YouTubeTranscriptApi()
            transcript_list = yt_api.list(video_id)
            
            # Try to get transcript in preferred language
            transcript_obj = None
            for lang in languages:
                try:
                    transcript_obj = transcript_list.find_transcript([lang])
                    break
                except Exception:
                    continue
            
            # If no preferred language found, try to get any manually created transcript
            if transcript_obj is None:
                try:
                    transcript_obj = transcript_list.find_manually_created_transcript(languages)
                except Exception:
                    # If no manually created transcript, get the first available (auto-generated)
                    try:
                        transcript_obj = transcript_list.find_generated_transcript(languages)
                    except Exception:
                        # Last resort: get any available transcript
                        available_transcripts = list(transcript_list)
                        if available_transcripts:
                            transcript_obj = available_transcripts[0]
            
            if transcript_obj is None:
                print(f"No transcript available for video {video_id}")
                return None
            
            # Fetch the actual transcript
            transcript_data = transcript_obj.fetch()
            
            # Combine all text segments (transcript_data contains FetchedTranscriptSnippet objects)
            transcript_text = ' '.join([item.text for item in transcript_data])
            
            return Transcript(text=transcript_text)
            
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            print(f"Transcript not available for video {video_id}: {e}")
            return None
        except Exception as e:
            print(f"Error fetching transcript for video {video_id}: {e}")
            return None

    def get_latest_videos(
        self, 
        channel_identifier: str, 
        hours: int = 24,
        include_transcripts: bool = True
    ) -> List[ChannelVideo]:
        """
        Get latest videos from a channel within the specified time window.
        
        Args:
            channel_identifier: Channel ID, URL, or handle
            hours: Number of hours to look back (default: 24)
            include_transcripts: Whether to fetch transcripts (default: True)
            
        Returns:
            List of ChannelVideo models with all metadata and optionally transcripts
        """
        # Extract channel ID
        channel_id = self.extract_channel_id(channel_identifier)
        if not channel_id:
            print(f"Could not extract channel ID from: {channel_identifier}")
            return []
        
        # Fetch all videos from RSS
        videos = self.fetch_videos_from_rss(channel_id)
        
        # Filter by time
        recent_videos = self.filter_videos_by_time(videos, hours=hours)
        
        # Optionally fetch transcripts
        if include_transcripts:
            updated_videos = []
            for video in recent_videos:
                if video.video_id:
                    transcript = self.get_video_transcript(video.video_id)
                    # Update video with transcript using model_copy
                    updated_video = video.model_copy(update={'transcript': transcript})
                    updated_videos.append(updated_video)
                else:
                    updated_videos.append(video)
            return updated_videos
        
        return recent_videos


if __name__ == "__main__":
    scraper = YouTubeScraper()
    # latest_videos = scraper.get_latest_videos("https://www.youtube.com/@Firstpost")
    latest_videos = scraper.get_latest_videos("https://www.youtube.com/@daveebbelaar")
    for video in latest_videos:
        print(f"Video: {video.title}")
        if video.transcript:
            print(f"Transcript: {video.transcript.text[:200]}...")
        else:
            print("Transcript: Not available")
        print(f"Published: {video.published_date}")
        print(f"Link: {video.link}")
        print(f"Video ID: {video.video_id}")
        print(f"Channel ID: {video.channel_id}")
        print(f"Description: {video.description[:100]}...")
        print("-" * 60)

    print(f"Total videos: {len(latest_videos)}")    
