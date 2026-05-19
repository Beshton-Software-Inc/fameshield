"""
Celery worker for content monitoring tasks.
"""
from typing import List
from datetime import datetime, timedelta
from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.workers.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.athlete import Athlete
from app.models.social_account import SocialAccount, MonitoringStatus
from app.models.content_item import ContentItem
from app.adapters.twitter_adapter import TwitterAdapter
from app.adapters.instagram_adapter import InstagramAdapter


class MonitoringTask(Task):
    """Base task for monitoring with adapters."""

    _twitter_adapter = None
    _instagram_adapter = None

    @property
    def twitter_adapter(self):
        """Lazy load Twitter adapter."""
        if self._twitter_adapter is None:
            self._twitter_adapter = TwitterAdapter()
        return self._twitter_adapter

    @property
    def instagram_adapter(self):
        """Lazy load Instagram adapter."""
        if self._instagram_adapter is None:
            self._instagram_adapter = InstagramAdapter()
        return self._instagram_adapter


@celery_app.task(base=MonitoringTask, bind=True, name="monitor_social_account")
def monitor_social_account(self, social_account_id: str):
    """
    Monitor a single social media account for new content.

    Args:
        social_account_id: UUID of social account to monitor
    """
    async def _monitor():
        async with AsyncSessionLocal() as db:
            try:
                # Get social account and athlete
                social_account = await db.get(SocialAccount, social_account_id)
                if not social_account:
                    print(f"Social account not found: {social_account_id}")
                    return None

                athlete = await db.get(Athlete, social_account.athlete_id)
                if not athlete or not athlete.monitoring_enabled:
                    print(f"Athlete not found or monitoring disabled: {social_account.athlete_id}")
                    return None

                # Get appropriate adapter
                if social_account.platform.value == "twitter":
                    adapter = self.twitter_adapter
                elif social_account.platform.value == "instagram":
                    adapter = self.instagram_adapter
                else:
                    print(f"Unsupported platform: {social_account.platform}")
                    return None

                # Get last monitored content ID for incremental polling
                last_content_query = select(ContentItem).where(
                    ContentItem.social_account_id == social_account.id
                ).order_by(ContentItem.discovered_at.desc()).limit(1)
                result = await db.execute(last_content_query)
                last_content = result.scalar_one_or_none()
                since_id = last_content.platform_content_id if last_content else None

                # Fetch new mentions
                try:
                    content_items = await adapter.fetch_mentions(
                        athlete_user_id=social_account.platform_user_id,
                        since_id=since_id,
                        max_results=100
                    )

                    print(f"Fetched {len(content_items)} new items for {social_account.platform} "
                          f"account {social_account.username}")

                    # Save content items to database
                    new_items = []
                    for item in content_items:
                        # Check for duplicates
                        existing = await db.execute(
                            select(ContentItem).where(
                                ContentItem.platform == item.platform,
                                ContentItem.platform_content_id == item.platform_content_id
                            )
                        )
                        if existing.scalar_one_or_none():
                            continue  # Skip duplicates

                        # Create content item
                        content_item = ContentItem(
                            athlete_id=athlete.id,
                            social_account_id=social_account.id,
                            platform=item.platform,
                            content_type=item.content_type,
                            platform_content_id=item.platform_content_id,
                            author_platform_id=item.author_platform_id,
                            author_username=item.author_username,
                            author_display_name=item.author_display_name,
                            author_profile_url=item.author_profile_url,
                            author_follower_count=item.author_follower_count,
                            content_text=item.content_text,
                            content_url=item.content_url,
                            media_urls=item.media_urls,
                            engagement_metrics=item.engagement_metrics,
                            published_at=item.published_at,
                            discovered_at=item.discovered_at
                        )
                        db.add(content_item)
                        new_items.append(content_item)

                    await db.commit()

                    # Refresh items to get IDs
                    for item in new_items:
                        await db.refresh(item)

                    # Update social account last monitored
                    social_account.last_monitored_at = datetime.utcnow()
                    social_account.monitoring_status = MonitoringStatus.ACTIVE
                    await db.commit()

                    # Queue classification for new items
                    from app.workers.classify_worker import classify_content_item
                    for item in new_items:
                        classify_content_item.delay(str(item.id), str(athlete.id))

                    return {
                        "social_account_id": str(social_account.id),
                        "platform": social_account.platform.value,
                        "new_items": len(new_items)
                    }

                except Exception as e:
                    print(f"Error fetching content from {social_account.platform}: {e}")
                    social_account.monitoring_status = MonitoringStatus.ERROR
                    await db.commit()
                    raise

            except Exception as e:
                print(f"Error monitoring social account {social_account_id}: {e}")
                raise

    return asyncio.run(_monitor())


@celery_app.task(name="monitor_athlete")
def monitor_athlete(athlete_id: str):
    """
    Monitor all social accounts for a specific athlete.

    Args:
        athlete_id: UUID of athlete to monitor
    """
    async def _monitor():
        async with AsyncSessionLocal() as db:
            try:
                # Get athlete's social accounts
                query = select(SocialAccount).where(
                    SocialAccount.athlete_id == athlete_id,
                    SocialAccount.monitoring_status == MonitoringStatus.ACTIVE
                )
                result = await db.execute(query)
                social_accounts = result.scalars().all()

                print(f"Monitoring {len(social_accounts)} accounts for athlete {athlete_id}")

                # Monitor each account
                results = []
                for account in social_accounts:
                    result = monitor_social_account.delay(str(account.id))
                    results.append(result.id)

                return results

            except Exception as e:
                print(f"Error monitoring athlete {athlete_id}: {e}")
                raise

    return asyncio.run(_monitor())


@celery_app.task(name="monitor_all_active_athletes")
def monitor_all_active_athletes():
    """
    Monitor all athletes with monitoring enabled.

    This runs periodically (every 15 minutes) via Celery Beat.
    """
    async def _monitor_all():
        async with AsyncSessionLocal() as db:
            try:
                # Get all athletes with monitoring enabled
                query = select(Athlete).where(Athlete.monitoring_enabled == True)
                result = await db.execute(query)
                athletes = result.scalars().all()

                print(f"Monitoring {len(athletes)} active athletes")

                # Queue monitoring for each athlete
                results = []
                for athlete in athletes:
                    result = monitor_athlete.delay(str(athlete.id))
                    results.append(result.id)

                # Update last monitored timestamp
                for athlete in athletes:
                    athlete.last_monitored_at = datetime.utcnow()
                await db.commit()

                return {
                    "athletes_monitored": len(athletes),
                    "tasks_queued": len(results)
                }

            except Exception as e:
                print(f"Error monitoring all athletes: {e}")
                raise

    return asyncio.run(_monitor_all())


@celery_app.task(name="cleanup_old_data")
def cleanup_old_data():
    """
    Clean up old data based on retention policies.

    Runs daily at 2 AM via Celery Beat.
    """
    async def _cleanup():
        async with AsyncSessionLocal() as db:
            try:
                # Delete content older than 2 years (as per privacy policy)
                cutoff_date = datetime.utcnow() - timedelta(days=730)

                # Note: Evidence is retained for 7 years, only content metadata is deleted
                result = await db.execute(
                    select(ContentItem).where(ContentItem.discovered_at < cutoff_date)
                )
                old_content = result.scalars().all()

                for item in old_content:
                    await db.delete(item)

                await db.commit()

                print(f"Cleaned up {len(old_content)} old content items")

                return {"items_deleted": len(old_content)}

            except Exception as e:
                print(f"Error cleaning up old data: {e}")
                raise

    return asyncio.run(_cleanup())


@celery_app.task(name="trigger_immediate_monitoring")
def trigger_immediate_monitoring(athlete_id: str):
    """
    Trigger immediate monitoring for an athlete (outside regular schedule).

    Args:
        athlete_id: UUID of athlete
    """
    return monitor_athlete.delay(athlete_id)
