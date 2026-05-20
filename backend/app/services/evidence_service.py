"""
Evidence capture service for screenshots, HTML, and media preservation.
"""
import hashlib
import os
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright, Browser, Page
import boto3
from botocore.exceptions import ClientError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.content_item import ContentItem
from app.models.classification import Classification
from app.models.evidence import Evidence, EvidenceType
from app.models.athlete import Athlete


class EvidenceService:
    """Service for capturing and storing digital evidence."""

    def __init__(self):
        """Initialize evidence service with S3 client."""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        self.bucket = settings.aws_s3_bucket
        self.evidence_prefix = settings.aws_s3_evidence_prefix
        self._browser: Optional[Browser] = None

    async def capture_evidence(
        self,
        content_item: ContentItem,
        classification: Classification,
        athlete: Athlete,
        db: AsyncSession
    ) -> list[Evidence]:
        """
        Capture comprehensive evidence for a content item.

        Args:
            content_item: Content to capture evidence for
            classification: Classification of the content
            athlete: Athlete being protected
            db: Database session

        Returns:
            List of Evidence objects created
        """
        evidence_records = []

        try:
            # 1. Capture screenshot
            screenshot_evidence = await self._capture_screenshot(
                content_item, classification, athlete, db
            )
            if screenshot_evidence:
                evidence_records.append(screenshot_evidence)

            # 2. Capture raw HTML
            html_evidence = await self._capture_html(
                content_item, classification, athlete, db
            )
            if html_evidence:
                evidence_records.append(html_evidence)

            # 3. Save metadata
            metadata_evidence = await self._save_metadata(
                content_item, classification, athlete, db
            )
            if metadata_evidence:
                evidence_records.append(metadata_evidence)

            # 4. Download media files (if any)
            if content_item.media_urls:
                media_evidence = await self._download_media(
                    content_item, classification, athlete, db
                )
                evidence_records.extend(media_evidence)

            return evidence_records

        except Exception as e:
            print(f"Error capturing evidence for content {content_item.id}: {e}")
            return evidence_records

    async def _capture_screenshot(
        self,
        content_item: ContentItem,
        classification: Classification,
        athlete: Athlete,
        db: AsyncSession
    ) -> Optional[Evidence]:
        """Capture screenshot of content using Playwright."""
        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()

                # Navigate to content URL
                try:
                    await page.goto(content_item.content_url, wait_until='networkidle', timeout=30000)

                    # Wait a bit for dynamic content
                    await asyncio.sleep(2)

                    # Take screenshot
                    screenshot_bytes = await page.screenshot(full_page=True, type='png')

                    # Generate storage path
                    storage_path = self._generate_storage_path(
                        athlete.id,
                        content_item.id,
                        'screenshot.png'
                    )

                    # Upload to S3
                    self.s3_client.put_object(
                        Bucket=self.bucket,
                        Key=storage_path,
                        Body=screenshot_bytes,
                        ContentType='image/png',
                        Metadata={
                            'athlete_id': str(athlete.id),
                            'content_id': str(content_item.id),
                            'classification_id': str(classification.id),
                            'platform': content_item.platform,
                            'captured_at': datetime.utcnow().isoformat()
                        }
                    )

                    # Calculate checksum
                    checksum = hashlib.sha256(screenshot_bytes).hexdigest()

                    # Create evidence record
                    evidence = Evidence(
                        content_item_id=content_item.id,
                        classification_id=classification.id,
                        athlete_id=athlete.id,
                        evidence_type=EvidenceType.SCREENSHOT,
                        storage_path=storage_path,
                        file_size=len(screenshot_bytes),
                        mime_type='image/png',
                        checksum=checksum,
                        metadata={
                            'capture_timestamp': datetime.utcnow().isoformat(),
                            'capture_method': 'playwright_chromium',
                            'browser_info': {
                                'browser': 'chromium',
                                'headless': True
                            },
                            'viewport_size': {'width': 1920, 'height': 1080},
                            'url': content_item.content_url
                        }
                    )

                    # Add chain of custody entry
                    evidence.add_custody_entry(
                        actor_id='system',
                        actor_type='system',
                        action='created'
                    )

                    db.add(evidence)
                    await db.commit()
                    await db.refresh(evidence)

                    print(f"Screenshot captured for content {content_item.id}")
                    return evidence

                except Exception as e:
                    print(f"Error navigating to {content_item.content_url}: {e}")
                    return None
                finally:
                    await browser.close()

        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None

    async def _capture_html(
        self,
        content_item: ContentItem,
        classification: Classification,
        athlete: Athlete,
        db: AsyncSession
    ) -> Optional[Evidence]:
        """Capture raw HTML of content page."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                try:
                    await page.goto(content_item.content_url, wait_until='networkidle', timeout=30000)

                    # Get HTML content
                    html_content = await page.content()
                    html_bytes = html_content.encode('utf-8')

                    # Generate storage path
                    storage_path = self._generate_storage_path(
                        athlete.id,
                        content_item.id,
                        'raw.html'
                    )

                    # Upload to S3
                    self.s3_client.put_object(
                        Bucket=self.bucket,
                        Key=storage_path,
                        Body=html_bytes,
                        ContentType='text/html',
                        Metadata={
                            'athlete_id': str(athlete.id),
                            'content_id': str(content_item.id),
                            'classification_id': str(classification.id)
                        }
                    )

                    # Calculate checksum
                    checksum = hashlib.sha256(html_bytes).hexdigest()

                    # Create evidence record
                    evidence = Evidence(
                        content_item_id=content_item.id,
                        classification_id=classification.id,
                        athlete_id=athlete.id,
                        evidence_type=EvidenceType.RAW_HTML,
                        storage_path=storage_path,
                        file_size=len(html_bytes),
                        mime_type='text/html',
                        checksum=checksum,
                        metadata={
                            'capture_timestamp': datetime.utcnow().isoformat(),
                            'capture_method': 'playwright_chromium',
                            'url': content_item.content_url,
                            'size_bytes': len(html_bytes)
                        }
                    )

                    evidence.add_custody_entry(
                        actor_id='system',
                        actor_type='system',
                        action='created'
                    )

                    db.add(evidence)
                    await db.commit()
                    await db.refresh(evidence)

                    print(f"HTML captured for content {content_item.id}")
                    return evidence

                except Exception as e:
                    print(f"Error capturing HTML: {e}")
                    return None
                finally:
                    await browser.close()

        except Exception as e:
            print(f"Error in HTML capture: {e}")
            return None

    async def _save_metadata(
        self,
        content_item: ContentItem,
        classification: Classification,
        athlete: Athlete,
        db: AsyncSession
    ) -> Optional[Evidence]:
        """Save content metadata as JSON."""
        try:
            import json

            # Compile metadata
            metadata_obj = {
                'content_item': {
                    'id': str(content_item.id),
                    'platform': content_item.platform,
                    'content_type': content_item.content_type.value,
                    'platform_content_id': content_item.platform_content_id,
                    'content_text': content_item.content_text,
                    'content_url': content_item.content_url,
                    'media_urls': content_item.media_urls,
                    'published_at': content_item.published_at.isoformat(),
                    'discovered_at': content_item.discovered_at.isoformat(),
                    'engagement_metrics': content_item.engagement_metrics
                },
                'author': {
                    'platform_id': content_item.author_platform_id,
                    'username': content_item.author_username,
                    'display_name': content_item.author_display_name,
                    'profile_url': content_item.author_profile_url,
                    'follower_count': content_item.author_follower_count
                },
                'classification': {
                    'id': str(classification.id),
                    'primary_category': classification.primary_category.value,
                    'secondary_categories': classification.secondary_categories,
                    'severity_level': classification.severity_level,
                    'confidence_score': classification.confidence_score,
                    'reasoning': classification.reasoning,
                    'key_evidence': classification.key_evidence,
                    'detected_entities': classification.detected_entities,
                    'model_used': classification.model_used
                },
                'athlete': {
                    'id': str(athlete.id),
                    'name': athlete.full_name,
                    'sport': athlete.sport,
                    'age': athlete.age
                },
                'capture_info': {
                    'captured_at': datetime.utcnow().isoformat(),
                    'version': '1.0'
                }
            }

            metadata_json = json.dumps(metadata_obj, indent=2)
            metadata_bytes = metadata_json.encode('utf-8')

            # Generate storage path
            storage_path = self._generate_storage_path(
                athlete.id,
                content_item.id,
                'metadata.json'
            )

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=storage_path,
                Body=metadata_bytes,
                ContentType='application/json',
                Metadata={
                    'athlete_id': str(athlete.id),
                    'content_id': str(content_item.id)
                }
            )

            # Calculate checksum
            checksum = hashlib.sha256(metadata_bytes).hexdigest()

            # Create evidence record
            evidence = Evidence(
                content_item_id=content_item.id,
                classification_id=classification.id,
                athlete_id=athlete.id,
                evidence_type=EvidenceType.METADATA,
                storage_path=storage_path,
                file_size=len(metadata_bytes),
                mime_type='application/json',
                checksum=checksum,
                metadata={
                    'capture_timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0'
                }
            )

            evidence.add_custody_entry(
                actor_id='system',
                actor_type='system',
                action='created'
            )

            db.add(evidence)
            await db.commit()
            await db.refresh(evidence)

            print(f"Metadata saved for content {content_item.id}")
            return evidence

        except Exception as e:
            print(f"Error saving metadata: {e}")
            return None

    async def _download_media(
        self,
        content_item: ContentItem,
        classification: Classification,
        athlete: Athlete,
        db: AsyncSession
    ) -> list[Evidence]:
        """Download media files from content."""
        evidence_records = []

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                for idx, media_url in enumerate(content_item.media_urls[:5]):  # Limit to 5 files
                    try:
                        response = await client.get(media_url)
                        response.raise_for_status()

                        media_bytes = response.content
                        content_type = response.headers.get('content-type', 'application/octet-stream')

                        # Determine file extension
                        ext = Path(media_url).suffix or self._guess_extension(content_type)

                        # Generate storage path
                        storage_path = self._generate_storage_path(
                            athlete.id,
                            content_item.id,
                            f'media_{idx}{ext}'
                        )

                        # Upload to S3
                        self.s3_client.put_object(
                            Bucket=self.bucket,
                            Key=storage_path,
                            Body=media_bytes,
                            ContentType=content_type,
                            Metadata={
                                'athlete_id': str(athlete.id),
                                'content_id': str(content_item.id),
                                'source_url': media_url
                            }
                        )

                        # Calculate checksum
                        checksum = hashlib.sha256(media_bytes).hexdigest()

                        # Create evidence record
                        evidence = Evidence(
                            content_item_id=content_item.id,
                            classification_id=classification.id,
                            athlete_id=athlete.id,
                            evidence_type=EvidenceType.VIDEO if 'video' in content_type else EvidenceType.SCREENSHOT,
                            storage_path=storage_path,
                            file_size=len(media_bytes),
                            mime_type=content_type,
                            checksum=checksum,
                            metadata={
                                'capture_timestamp': datetime.utcnow().isoformat(),
                                'source_url': media_url,
                                'index': idx
                            }
                        )

                        evidence.add_custody_entry(
                            actor_id='system',
                            actor_type='system',
                            action='created'
                        )

                        db.add(evidence)
                        evidence_records.append(evidence)

                    except Exception as e:
                        print(f"Error downloading media from {media_url}: {e}")
                        continue

                if evidence_records:
                    await db.commit()
                    for ev in evidence_records:
                        await db.refresh(ev)

        except Exception as e:
            print(f"Error downloading media: {e}")

        return evidence_records

    def _generate_storage_path(self, athlete_id: str, content_id: str, filename: str) -> str:
        """Generate S3 storage path for evidence."""
        now = datetime.utcnow()
        return f"{self.evidence_prefix}{athlete_id}/{now.year}/{now.month:02d}/{content_id}/{filename}"

    def _guess_extension(self, content_type: str) -> str:
        """Guess file extension from content type."""
        mapping = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/webm': '.webm',
            'video/quicktime': '.mov'
        }
        return mapping.get(content_type, '.bin')

    async def get_presigned_url(self, storage_path: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for evidence access.

        Args:
            storage_path: S3 key
            expiration: URL expiration in seconds (default 1 hour)

        Returns:
            Presigned URL or None if error
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': storage_path},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return None

    async def update_evidence_custody(
        self,
        evidence: Evidence,
        actor_id: str,
        actor_type: str,
        action: str,
        ip_address: Optional[str] = None,
        db: AsyncSession = None
    ) -> None:
        """
        Add entry to evidence chain of custody.

        Args:
            evidence: Evidence object
            actor_id: ID of actor (user, system, etc.)
            actor_type: Type of actor
            action: Action performed
            ip_address: Optional IP address
            db: Database session
        """
        evidence.add_custody_entry(actor_id, actor_type, action, ip_address)

        if db:
            await db.commit()
            await db.refresh(evidence)
