"""
Celery worker for content classification tasks.
"""
from typing import List
from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.workers.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.content_item import ContentItem
from app.models.athlete import Athlete
from app.models.classification import Classification
from app.services.classification_service import ClassificationService


class ClassificationTask(Task):
    """Base task for classification with database session."""

    _classification_service = None

    @property
    def classification_service(self):
        """Lazy load classification service."""
        if self._classification_service is None:
            self._classification_service = ClassificationService()
        return self._classification_service


@celery_app.task(base=ClassificationTask, bind=True, name="classify_content_item")
def classify_content_item(self, content_item_id: str, athlete_id: str):
    """
    Classify a single content item.

    Args:
        content_item_id: UUID of content to classify
        athlete_id: UUID of athlete
    """
    async def _classify():
        async with AsyncSessionLocal() as db:
            try:
                # Get content item and athlete
                content_item = await db.get(ContentItem, content_item_id)
                athlete = await db.get(Athlete, athlete_id)

                if not content_item or not athlete:
                    print(f"Content or athlete not found: {content_item_id}, {athlete_id}")
                    return None

                # Classify content
                classification = await self.classification_service.classify_content(
                    content_item, athlete, db
                )

                print(f"Classified content {content_item_id}: "
                      f"{classification.primary_category} (severity {classification.severity_level})")

                # If high severity, trigger evidence capture
                if classification.severity_level >= 3:
                    capture_evidence.delay(content_item_id, classification.id)

                # If requires immediate review, trigger escalation
                if classification.requires_immediate_review:
                    create_escalation.delay(classification.id)

                return str(classification.id)

            except Exception as e:
                print(f"Error classifying content {content_item_id}: {e}")
                raise

    return asyncio.run(_classify())


@celery_app.task(name="classify_batch")
def classify_batch(content_item_ids: List[str], athlete_id: str):
    """
    Classify multiple content items in batch.

    Args:
        content_item_ids: List of content item UUIDs
        athlete_id: UUID of athlete
    """
    results = []
    for content_id in content_item_ids:
        result = classify_content_item.delay(content_id, athlete_id)
        results.append(result.id)

    return results


@celery_app.task(base=ClassificationTask, bind=True, name="process_pending_content")
def process_pending_content(self):
    """
    Process all content items that haven't been classified yet.

    This runs periodically (every 5 minutes) via Celery Beat.
    """
    async def _process():
        async with AsyncSessionLocal() as db:
            try:
                # Find content items without classifications
                query = select(ContentItem).outerjoin(
                    Classification, ContentItem.id == Classification.content_item_id
                ).where(Classification.id.is_(None)).limit(100)  # Process 100 at a time

                result = await db.execute(query)
                unclassified_items = result.scalars().all()

                print(f"Found {len(unclassified_items)} unclassified content items")

                # Classify each item
                for content_item in unclassified_items:
                    classify_content_item.delay(
                        str(content_item.id),
                        str(content_item.athlete_id)
                    )

                return len(unclassified_items)

            except Exception as e:
                print(f"Error processing pending content: {e}")
                raise

    return asyncio.run(_process())


@celery_app.task(name="reclassify_content")
def reclassify_content(classification_id: str):
    """
    Re-run classification on existing content.

    Args:
        classification_id: UUID of classification to re-run
    """
    async def _reclassify():
        async with AsyncSessionLocal() as db:
            try:
                service = ClassificationService()
                classification = await service.reclassify_content(classification_id, db)

                print(f"Reclassified content: {classification.primary_category} "
                      f"(severity {classification.severity_level})")

                return str(classification.id)

            except Exception as e:
                print(f"Error reclassifying {classification_id}: {e}")
                raise

    return asyncio.run(_reclassify())


@celery_app.task(name="capture_evidence")
def capture_evidence(content_item_id: str, classification_id: str):
    """
    Capture evidence for a classified content item.

    Args:
        content_item_id: UUID of content
        classification_id: UUID of classification
    """
    async def _capture():
        async with AsyncSessionLocal() as db:
            try:
                from app.services.evidence_service import EvidenceService

                # Get content, classification, and athlete
                content_item = await db.get(ContentItem, content_item_id)
                classification = await db.get(Classification, classification_id)

                if not content_item or not classification:
                    print(f"Content or classification not found")
                    return None

                athlete = await db.get(Athlete, content_item.athlete_id)
                if not athlete:
                    print(f"Athlete not found")
                    return None

                # Capture evidence
                service = EvidenceService()
                evidence_records = await service.capture_evidence(
                    content_item, classification, athlete, db
                )

                print(f"Captured {len(evidence_records)} evidence items for content {content_item_id}")

                return {
                    "status": "completed",
                    "content_id": content_item_id,
                    "evidence_count": len(evidence_records),
                    "evidence_ids": [str(ev.id) for ev in evidence_records]
                }

            except Exception as e:
                print(f"Error capturing evidence for {content_item_id}: {e}")
                raise

    return asyncio.run(_capture())


@celery_app.task(name="create_escalation")
def create_escalation(classification_id: str):
    """
    Create an escalation for high-severity content.

    Args:
        classification_id: UUID of classification
    """
    # TODO: Implement escalation creation in Phase 3
    print(f"Escalation triggered for classification {classification_id}")
    return {"status": "pending", "classification_id": classification_id}


@celery_app.task(name="analyze_coordinated_attack")
def analyze_coordinated_attack(athlete_id: str, time_window_minutes: int = 60):
    """
    Analyze recent content for signs of coordinated attack.

    Args:
        athlete_id: UUID of athlete to analyze
        time_window_minutes: Time window to analyze (default 60 minutes)
    """
    # TODO: Implement coordinated attack analysis
    print(f"Coordinated attack analysis for athlete {athlete_id}")
    return {"status": "pending", "athlete_id": athlete_id}
