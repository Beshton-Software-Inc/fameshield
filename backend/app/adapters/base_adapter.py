"""
Base adapter class for social media platform integrations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ContentItem(BaseModel):
    """Standardized content item from any platform."""
    platform: str
    platform_content_id: str
    content_type: str  # post, comment, mention, video, etc.
    author_platform_id: str
    author_username: str
    author_display_name: str
    author_profile_url: str
    author_follower_count: int
    content_text: Optional[str]
    content_url: str
    media_urls: List[str] = []
    engagement_metrics: Dict[str, int] = {}
    published_at: datetime
    discovered_at: datetime = datetime.utcnow()


class TakedownResult(BaseModel):
    """Result of a takedown submission."""
    success: bool
    reference_id: Optional[str]
    message: str
    submitted_at: datetime = datetime.utcnow()


class BasePlatformAdapter(ABC):
    """
    Base class for all social media platform adapters.

    Each platform (Twitter, Instagram, TikTok, YouTube) implements this interface.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize adapter with API credentials."""
        self.api_key = api_key
        self.api_secret = api_secret
        self.platform_name: str = self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    async def fetch_mentions(
        self,
        athlete_user_id: str,
        since_id: Optional[str] = None,
        max_results: int = 100
    ) -> List[ContentItem]:
        """
        Fetch mentions of the athlete.

        Args:
            athlete_user_id: Platform-specific user ID
            since_id: Fetch only content after this ID (for incremental polling)
            max_results: Maximum number of items to fetch

        Returns:
            List of ContentItem objects
        """
        pass

    @abstractmethod
    async def fetch_comments(
        self,
        post_id: str,
        max_results: int = 100
    ) -> List[ContentItem]:
        """
        Fetch comments on a specific post.

        Args:
            post_id: Platform-specific post ID
            max_results: Maximum number of comments to fetch

        Returns:
            List of ContentItem objects (comments)
        """
        pass

    @abstractmethod
    async def fetch_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user profile information.

        Args:
            user_id: Platform-specific user ID

        Returns:
            Dictionary with user profile data
        """
        pass

    @abstractmethod
    async def submit_takedown(
        self,
        content_ids: List[str],
        reason: str,
        evidence: Optional[Dict[str, Any]] = None
    ) -> TakedownResult:
        """
        Submit a takedown/abuse report to the platform.

        Args:
            content_ids: List of platform-specific content IDs to report
            reason: Reason for takedown (abuse type)
            evidence: Additional evidence data

        Returns:
            TakedownResult with submission status
        """
        pass

    async def check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.

        Returns:
            True if request is allowed, False if rate limited
        """
        # Default implementation - override in subclasses
        return True

    def get_platform_name(self) -> str:
        """Get the platform name."""
        return self.platform_name
