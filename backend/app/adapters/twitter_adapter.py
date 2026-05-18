"""
Twitter/X API v2 adapter for content monitoring and takedown.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx

from app.adapters.base_adapter import BasePlatformAdapter, ContentItem, TakedownResult
from app.config import settings


class TwitterAdapter(BasePlatformAdapter):
    """Twitter API v2 integration."""

    def __init__(self):
        """Initialize Twitter adapter with credentials from settings."""
        super().__init__(
            api_key=settings.twitter_api_key,
            api_secret=settings.twitter_api_secret
        )
        self.bearer_token = settings.twitter_bearer_token
        self.base_url = "https://api.twitter.com/2"

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for Twitter API."""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }

    async def fetch_mentions(
        self,
        athlete_user_id: str,
        since_id: Optional[str] = None,
        max_results: int = 100
    ) -> List[ContentItem]:
        """
        Fetch mentions of the athlete using Twitter API v2.

        Endpoint: GET /2/users/:id/mentions
        """
        endpoint = f"{self.base_url}/users/{athlete_user_id}/mentions"

        params = {
            "max_results": min(max_results, 100),  # Twitter API limit
            "tweet.fields": "created_at,public_metrics,author_id,entities",
            "expansions": "author_id,attachments.media_keys",
            "user.fields": "username,name,public_metrics,verified",
            "media.fields": "url,preview_image_url"
        }

        if since_id:
            params["since_id"] = since_id

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self._get_headers(),
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                return self._parse_tweets(data)

            except httpx.HTTPStatusError as e:
                print(f"Twitter API error: {e.response.status_code} - {e.response.text}")
                return []
            except Exception as e:
                print(f"Error fetching Twitter mentions: {e}")
                return []

    async def fetch_comments(
        self,
        post_id: str,
        max_results: int = 100
    ) -> List[ContentItem]:
        """
        Fetch replies to a specific tweet.

        Uses search endpoint to find replies.
        """
        endpoint = f"{self.base_url}/tweets/search/recent"

        params = {
            "query": f"conversation_id:{post_id}",
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,author_id,conversation_id",
            "expansions": "author_id",
            "user.fields": "username,name,public_metrics,verified"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self._get_headers(),
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                return self._parse_tweets(data)

            except httpx.HTTPStatusError as e:
                print(f"Twitter API error: {e.response.status_code} - {e.response.text}")
                return []
            except Exception as e:
                print(f"Error fetching Twitter comments: {e}")
                return []

    async def fetch_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user profile information.

        Endpoint: GET /2/users/:id
        """
        endpoint = f"{self.base_url}/users/{user_id}"

        params = {
            "user.fields": "created_at,description,public_metrics,verified,profile_image_url"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self._get_headers(),
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                user = data.get("data", {})
                return {
                    "platform_user_id": user.get("id"),
                    "username": user.get("username"),
                    "display_name": user.get("name"),
                    "bio": user.get("description"),
                    "follower_count": user.get("public_metrics", {}).get("followers_count", 0),
                    "verified": user.get("verified", False),
                    "profile_image_url": user.get("profile_image_url"),
                    "created_at": user.get("created_at")
                }

            except Exception as e:
                print(f"Error fetching Twitter profile: {e}")
                return {}

    async def submit_takedown(
        self,
        content_ids: List[str],
        reason: str,
        evidence: Optional[Dict[str, Any]] = None
    ) -> TakedownResult:
        """
        Submit abuse report to Twitter.

        Note: Twitter doesn't have a public API for reporting.
        This would need to use web scraping or manual submission.
        """
        # TODO: Implement Twitter abuse reporting
        # Options:
        # 1. Use web automation (Playwright) to submit via web form
        # 2. Use Twitter's internal reporting API (if available)
        # 3. Generate report for manual submission

        return TakedownResult(
            success=False,
            reference_id=None,
            message="Twitter takedown submission not yet implemented. Generate report for manual submission."
        )

    def _parse_tweets(self, data: Dict[str, Any]) -> List[ContentItem]:
        """Parse Twitter API response into ContentItem objects."""
        tweets = data.get("data", [])
        users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}
        media = {m["media_key"]: m for m in data.get("includes", {}).get("media", [])}

        content_items = []

        for tweet in tweets:
            author_id = tweet.get("author_id")
            author = users.get(author_id, {})

            # Get media URLs
            media_keys = []
            if tweet.get("attachments"):
                media_keys = tweet["attachments"].get("media_keys", [])

            media_urls = [
                media[key].get("url") or media[key].get("preview_image_url", "")
                for key in media_keys
                if key in media
            ]

            content_item = ContentItem(
                platform="twitter",
                platform_content_id=tweet["id"],
                content_type="mention" if "conversation_id" not in tweet else "comment",
                author_platform_id=author_id,
                author_username=author.get("username", "unknown"),
                author_display_name=author.get("name", "Unknown"),
                author_profile_url=f"https://twitter.com/{author.get('username', '')}",
                author_follower_count=author.get("public_metrics", {}).get("followers_count", 0),
                content_text=tweet.get("text"),
                content_url=f"https://twitter.com/i/web/status/{tweet['id']}",
                media_urls=media_urls,
                engagement_metrics={
                    "likes": tweet.get("public_metrics", {}).get("like_count", 0),
                    "retweets": tweet.get("public_metrics", {}).get("retweet_count", 0),
                    "replies": tweet.get("public_metrics", {}).get("reply_count", 0),
                    "impressions": tweet.get("public_metrics", {}).get("impression_count", 0)
                },
                published_at=datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
            )

            content_items.append(content_item)

        return content_items
