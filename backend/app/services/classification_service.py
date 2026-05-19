"""
Classification service for content abuse detection using Claude API.
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.content_item import ContentItem
from app.models.classification import Classification, ClassificationCategory, ClassificationStatus
from app.models.athlete import Athlete
from app.prompts.classification_prompt import get_classification_prompt


class ClassificationService:
    """Service for classifying content using Claude API."""

    def __init__(self):
        """Initialize classification service with Claude client."""
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens

    async def classify_content(
        self,
        content_item: ContentItem,
        athlete: Athlete,
        db: AsyncSession
    ) -> Classification:
        """
        Classify a content item for abuse detection.

        Args:
            content_item: The content to classify
            athlete: The athlete being protected
            db: Database session

        Returns:
            Classification object with results
        """
        # Calculate author account age (placeholder - would need actual data)
        account_age_days = 365  # Default to 1 year

        # Get classification from Claude
        prompt = get_classification_prompt(
            content_text=content_item.content_text or "",
            author_username=content_item.author_username,
            author_follower_count=content_item.author_follower_count,
            account_age_days=account_age_days,
            athlete_name=athlete.full_name,
            athlete_sport=athlete.sport,
            athlete_age=athlete.age,
            athlete_gender="female" if athlete.settings.get("gender") == "female" else "male",
            recent_context=""
        )

        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse response
            response_text = response.content[0].text
            classification_data = self._parse_classification_response(response_text)

            # Calculate adjusted severity
            adjusted_severity = self._calculate_severity(
                classification_data,
                athlete,
                content_item
            )

            # Create classification record
            classification = Classification(
                content_item_id=content_item.id,
                athlete_id=athlete.id,
                primary_category=ClassificationCategory(classification_data["primary_category"]),
                secondary_categories=classification_data.get("secondary_categories", []),
                severity_level=adjusted_severity,
                confidence_score=classification_data["confidence_score"],
                reasoning=classification_data["reasoning"],
                key_evidence=classification_data.get("key_evidence", []),
                detected_entities=classification_data.get("detected_entities", {}),
                model_used=self.model,
                recommended_action=classification_data.get("recommended_action", "monitor"),
                status=ClassificationStatus.PENDING
            )

            db.add(classification)
            await db.commit()
            await db.refresh(classification)

            return classification

        except anthropic.APIError as e:
            print(f"Claude API error: {e}")
            # Create a fallback classification for errors
            return await self._create_error_classification(content_item, athlete, db, str(e))
        except Exception as e:
            print(f"Classification error: {e}")
            return await self._create_error_classification(content_item, athlete, db, str(e))

    def _parse_classification_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude API response into structured classification data.

        Args:
            response_text: Raw response from Claude

        Returns:
            Dictionary with classification data
        """
        try:
            # Try to extract JSON from response
            # Claude sometimes wraps JSON in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # Try to find JSON object
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]

            data = json.loads(json_text)

            # Validate required fields
            required_fields = ["primary_category", "severity_level", "confidence_score", "reasoning"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            return data

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse classification response: {e}")
            # Return a safe default
            return {
                "primary_category": "normal_criticism",
                "severity_level": 1,
                "confidence_score": 0.5,
                "reasoning": f"Failed to parse response: {str(e)}",
                "key_evidence": [],
                "recommended_action": "monitor"
            }

    def _calculate_severity(
        self,
        classification_data: Dict[str, Any],
        athlete: Athlete,
        content_item: ContentItem
    ) -> int:
        """
        Calculate adjusted severity level based on context.

        Args:
            classification_data: Raw classification from Claude
            athlete: Athlete being protected
            content_item: Content being classified

        Returns:
            Adjusted severity level (1-5)
        """
        base_severity = classification_data["severity_level"]
        confidence = classification_data["confidence_score"]

        # Start with base severity
        severity = base_severity

        # Adjustment 1: Youth athletes get +1 severity
        if athlete.is_youth:
            severity = min(severity + 1, 5)

        # Adjustment 2: Low confidence reduces severity
        if confidence < 0.7:
            severity = max(severity - 1, 1)

        # Adjustment 3: Multiple secondary categories increase severity
        secondary_categories = classification_data.get("secondary_categories", [])
        if len(secondary_categories) >= 2:
            severity = min(severity + 1, 5)

        # Adjustment 4: Coordinated attack indicators always Level 5
        detected_entities = classification_data.get("detected_entities", {})
        if detected_entities.get("coordinated_indicators"):
            severity = 5

        # Adjustment 5: High visibility content increases severity
        views = content_item.engagement_metrics.get("views", 0)
        if views > 10000:
            severity = min(severity + 1, 5)

        # Adjustment 6: Threats always at least Level 4
        threats = detected_entities.get("threats", [])
        if threats:
            severity = max(severity, 4)

        # Adjustment 7: Doxxing (personal info) always at least Level 4
        personal_info = detected_entities.get("personal_info", [])
        if personal_info:
            severity = max(severity, 4)

        return severity

    async def _create_error_classification(
        self,
        content_item: ContentItem,
        athlete: Athlete,
        db: AsyncSession,
        error_message: str
    ) -> Classification:
        """
        Create a fallback classification when API call fails.

        Args:
            content_item: Content that failed to classify
            athlete: Athlete being protected
            db: Database session
            error_message: Error message from API

        Returns:
            Classification with error status
        """
        classification = Classification(
            content_item_id=content_item.id,
            athlete_id=athlete.id,
            primary_category=ClassificationCategory.NORMAL_CRITICISM,
            severity_level=1,
            confidence_score=0.0,
            reasoning=f"Classification failed: {error_message}",
            key_evidence=[],
            detected_entities={},
            model_used=self.model,
            recommended_action="monitor",
            status=ClassificationStatus.PENDING
        )

        db.add(classification)
        await db.commit()
        await db.refresh(classification)

        return classification

    async def reclassify_content(
        self,
        classification_id: str,
        db: AsyncSession
    ) -> Classification:
        """
        Re-run classification on existing content.

        Args:
            classification_id: ID of classification to re-run
            db: Database session

        Returns:
            Updated classification
        """
        # Get existing classification
        result = await db.execute(
            "SELECT * FROM classifications WHERE id = :id",
            {"id": classification_id}
        )
        classification = result.scalar_one_or_none()

        if not classification:
            raise ValueError(f"Classification {classification_id} not found")

        # Get content item and athlete
        content_item = await db.get(ContentItem, classification.content_item_id)
        athlete = await db.get(Athlete, classification.athlete_id)

        # Delete old classification
        await db.delete(classification)
        await db.commit()

        # Create new classification
        return await self.classify_content(content_item, athlete, db)

    def get_severity_description(self, severity_level: int) -> str:
        """Get human-readable description of severity level."""
        descriptions = {
            1: "Negative fan comment (log only)",
            2: "Bullying/personal attack (flag for review)",
            3: "Hate speech/sexual harassment (hide from athlete)",
            4: "Doxxing/credible threat (immediate human review)",
            5: "Coordinated attack/criminal threat (urgent escalation)"
        }
        return descriptions.get(severity_level, "Unknown severity")

    def get_category_description(self, category: str) -> str:
        """Get human-readable description of category."""
        descriptions = {
            "normal_criticism": "Legitimate sports commentary",
            "harassment": "Targeted personal attacks",
            "hate_speech": "Discriminatory content",
            "sexual_harassment": "Unwanted sexual comments",
            "threat_of_violence": "Threats to safety",
            "doxxing": "Sharing private information",
            "impersonation": "Fake accounts",
            "fake_quote": "False statements",
            "fake_endorsement": "False brand association",
            "deepfake": "Manipulated media",
            "coordinated_attack": "Organized harassment",
            "gambling_abuse": "Betting-related harassment"
        }
        return descriptions.get(category, "Unknown category")
