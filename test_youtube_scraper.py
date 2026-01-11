"""Test script for YouTube scraper functionality."""

from app.scrapers.youtube import YouTubeScraper
from datetime import datetime


def test_youtube_scraper():
    """Test the YouTube scraper with example channels."""
    
    scraper = YouTubeScraper()
    
    # Test channels - you can replace these with your own
    # Example: OpenAI's YouTube channel
    test_channels = [
        "https://www.youtube.com/@Firstpost"
        # "UCXZCJLdBC09xxGZ6gcdrc6A",
        # "UCNq1VRNOpaQoh5cHdcEmirA"  # OpenAI channel ID (example)
        # "ETJSn8wk2kjahavY8-_yIg"  #  Dave channel ID (example)
        # You can also test with:
        # "https://www.youtube.com/channel/UCr0l3VfK2jS3sfz8kXz_9Fw"
        # "@OpenAI" (if you want to test handle resolution)
    ]
    
    print("=" * 60)
    print("Testing YouTube Scraper")
    print("=" * 60)
    
    for channel in test_channels:
        print(f"\n📺 Testing channel: {channel}")
        print("-" * 60)
        
        # Test channel ID extraction
        channel_id = scraper.extract_channel_id(channel)
        print(f"Extracted Channel ID: {channel_id}")
        
        if not channel_id:
            print("❌ Could not extract channel ID. Skipping...")
            continue
        
        # Test RSS feed URL
        rss_url = scraper.get_rss_feed_url(channel_id)
        print(f"RSS Feed URL: {rss_url}")
        
        # Fetch videos
        print("\nFetching videos from RSS feed...")
        videos = scraper.fetch_videos_from_rss(channel_id)
        print(f"Total videos found: {len(videos)}")
        
        if videos:
            print("\nLatest 5 videos:")
            for i, video in enumerate(videos[:5], 1):
                print(f"\n{i}. {video['title']}")
                print(f"   Link: {video['link']}")
                print(f"   Video ID: {video['video_id']}")
                print(f"   Published: {video['published_date']}")
                print(f"   Description: {video['description'][:100]}...")
        
        # Test time filtering (last 24 hours)
        print("\n" + "=" * 60)
        print("Testing time filtering (last 24 hours)...")
        print("=" * 60)
        recent_videos = scraper.filter_videos_by_time(videos, hours=24)
        print(f"Videos in last 24 hours: {len(recent_videos)}")
        
        if recent_videos:
            print("\nRecent videos:")
            for i, video in enumerate(recent_videos[:3], 1):
                print(f"\n{i}. {video['title']}")
                print(f"   Published: {video['published_date']}")
                print(f"   Link: {video['link']}")
        
        # Test transcript fetching (on first recent video if available)
        if recent_videos:
            print("\n" + "=" * 60)
            print("Testing transcript extraction...")
            print("=" * 60)
            test_video = recent_videos[0]
            video_id = test_video.get('video_id')
            
            if video_id:
                print(f"Fetching transcript for: {test_video['title']}")
                print(f"Video ID: {video_id}")
                
                transcript = scraper.get_video_transcript(video_id)
                if transcript:
                    print(f"\n✅ Transcript retrieved ({len(transcript)} characters)")
                    print(f"Preview: {transcript[:200]}...")
                else:
                    print("\n❌ Transcript not available for this video")
        
        # Test complete workflow
        print("\n" + "=" * 60)
        print("Testing complete workflow (get_latest_videos)...")
        print("=" * 60)
        latest_videos = scraper.get_latest_videos(
            channel, 
            hours=24, 
            include_transcripts=True
        )
        print(f"Latest videos with transcripts: {len(latest_videos)}")
        
        if latest_videos:
            for i, video in enumerate(latest_videos[:2], 1):
                print(f"\n{i}. {video['title']}")
                print(f"   Has transcript: {'Yes' if video.get('transcript') else 'No'}")
                if video.get('transcript'):
                    print(f"   Transcript length: {len(video['transcript'])} characters")


if __name__ == "__main__":
    test_youtube_scraper()


