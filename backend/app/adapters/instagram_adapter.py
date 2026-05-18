"""
Instagram Graph API adapter for content monitoring.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx

from app.adapters.base_adapter import BasePlatformAdapter, ContentItem, TakedownResult
from app.config import settings


class InstagramAdapter(BasePlatformAdapter):
    """
    Instagram Graph API integration.

    Note: Instagram API has significant limitations:
    - Requires Business/Creator accounts
    - Can only access athlete's own posts and comments on those posts
    - Cannot access mentions or DMs
    - Mentions require scraping or webhooks
    """

    def __init__(self):
        """Initialize Instagram adapter with credentials from settings."""
        super().__init__(
            api_key=settings.instagram_app_id,
            api_secret=settings.instagram_app_secret
        )
        self.base_url = "https://graph.instagram.com"

    async def fetch_mentions(
        self,
        athlete_user_id: str,
        since_id: Optional[str] = None,
        max_results: int = 100
    ) -> List[ContentItem]:
        """
        Fetch mentions of the athlete.

        WARNING: Instagram Graph API does not support fetching mentions directly.
        Options:
        1. Use webhooks to receive mention notifications
        2. Use web scraping (Apify/Playwright)
        3. Use Instagram Basic Display API (limited)

        This is a placeholder that returns empty list.
        """
        # TODO: Implement Instagram mention monitoring via:
        # - Instagram Graph API webhooks
        # - Web scraping with Apify or Playwright
        print("Instagram mentions require webhooks or web scraping - not yet implemented")
        return []

    async def fetch_comments(
        self,
        post_id: str,
        max_results: int = 100
    ) -> List[ContentItem]:
        """
        Fetch comments on a specific Instagram post.

        Endpoint: GET /{media-id}/comments
        """
        endpoint = f"{self.base_url}/{post_id}/comments"

        params = {
            "fields": "id,text,username,timestamp,like_count,replies",
            "limit": min(max_results, 100)
        }

        # Note: access_token should be passed per request
        # This is a simplified version - in production, get token from SocialAccount model
        access_token = self._get_access_token(post_id)
        if not access_token:
            print("No access token available for Instagram post")
            return []

        params["access_token"] = access_token

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                return self._parse_comments(data, post_id)

            except httpx.HTTPStatusError as e:
                print(f"Instagram API error: {e.response.status_code} - {e.response.text}")
                return []
            except Exception as e:
                print(f"Error fetching Instagram comments: {e}")
                return []

    async def fetch_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch Instagram user profile.

        Endpoint: GET /{user-id}
        """
        endpoint = f"{self.base_url}/{user_id}"

        params = {
            "fields": "id,username,account_type,media_count,followers_count,follows_count",
        }

        access_token = self._get_access_token(user_id)
        if not access_token:
            print("No access token available for Instagram user")
            return {}

        params["access_token"] = access_token

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                user = response.json()

                return {
                    "platform_user_id": user.get("id"),
                    "username": user.get("username"),
                    "display_name": user.get("username"),  # Instagram doesn't have separate display name
                    "follower_count": user.get("followers_count", 0),
                    "account_type": user.get("account_type"),
                }

            except Exception as e:
                print(f"Error fetching Instagram profile: {e}")
                return {}

    async def submit_takedown(
        self,
        content_ids: List[str],
        reason: str,
        evidence: Optional[Dict[str, Any]] = None
    ) -> TakedownResult:
        """
        Submit abuse report to Instagram.

        Instagram doesn't have a public reporting API.
        Must use web form or partner API.
        """
        # TODO: Implement Instagram abuse reporting
        # Options:
        # 1. Use web automation to submit via Instagram web interface
        # 2. Use Instagram Partner Program API (if available)
        # 3. Generate report for manual submission

        return TakedownResult(
            success=False,
            reference_id=None,
            message="Instagram takedown submission not yet implemented. Generate report for manual submission."
        )

    def _get_access_token(self, resource_id: str) -> Optional[str]:
        """
        Get access token for a specific resource.

        In production, this should fetch the token from the SocialAccount model
        associated with the athlete.
        """
        # TODO: Implement token retrieval from database
        # For now, return None as placeholder
        return None

    def _parse_comments(self, data: Dict[str, Any], post_id: str) -> List[ContentItem]:
        """Parse Instagram API response into ContentItem objects."""
        comments = data.get("data", [])
        content_items = []

        for comment in comments:
            content_item = ContentItem(
                platform="instagram",
                platform_content_id=comment["id"],
                content_type="comment",
                author_platform_id=comment.get("from", {}).get("id", "unknown"),
                author_username=comment.get("username", "unknown"),
                author_display_name=comment.get("username", "Unknown"),
                author_profile_url=f"https://instagram.com/{comment.get('username', '')}",
                author_follower_count=0,  # Not available in comments endpoint
                content_text=comment.get("text"),
                content_url=f"https://instagram.com/p/{post_id}",  # Link to post
                media_urls=[],
                engagement_metrics={
                    "likes": comment.get("like_count", 0),
                },
                published_at=datetime.fromisoformat(comment["timestamp"].replace("Z", "+00:00"))
            )

            content_items.append(content_item)

        return content_items
