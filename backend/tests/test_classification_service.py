"""
Test classification service.
"""
import pytest
from app.services.classification_service import ClassificationService
from app.models.athlete import Athlete, RiskLevel


@pytest.mark.asyncio
async def test_severity_calculation(test_athlete):
    """Test severity scoring algorithm."""
    service = ClassificationService()

    # Base case: harassment for adult athlete
    classification = {
        'primary_category': 'harassment',
        'secondary_categories': [],
        'confidence_score': 0.9,
        'detected_entities': {}
    }

    severity = service._calculate_severity(
        classification=classification,
        athlete=test_athlete,
        engagement_metrics={'views': 100}
    )
    assert severity == 2  # Base harassment severity

    # Youth athlete adjustment
    youth_athlete = Athlete(
        first_name="Young",
        last_name="Athlete",
        date_of_birth="2010-01-01",  # 16 years old
        sport="Soccer",
        risk_level=RiskLevel.MEDIUM,
        organization_id=test_athlete.organization_id
    )

    severity = service._calculate_severity(
        classification=classification,
        athlete=youth_athlete,
        engagement_metrics={'views': 100}
    )
    assert severity == 3  # +1 for youth

    # High visibility adjustment
    severity = service._calculate_severity(
        classification=classification,
        athlete=test_athlete,
        engagement_metrics={'views': 15000}
    )
    assert severity == 3  # +1 for high views

    # Multiple categories
    classification['secondary_categories'] = ['hate_speech', 'sexual_harassment']
    severity = service._calculate_severity(
        classification=classification,
        athlete=test_athlete,
        engagement_metrics={'views': 100}
    )
    assert severity == 3  # +1 for multiple categories

    # Coordinated attack
    classification['detected_entities'] = {'coordinated_indicators': True}
    severity = service._calculate_severity(
        classification=classification,
        athlete=test_athlete,
        engagement_metrics={'views': 100}
    )
    assert severity == 5  # Force Level 5

    # Threat detected
    classification = {
        'primary_category': 'harassment',
        'secondary_categories': [],
        'confidence_score': 0.9,
        'detected_entities': {'threats': ['gonna hurt you']}
    }
    severity = service._calculate_severity(
        classification=classification,
        athlete=test_athlete,
        engagement_metrics={'views': 100}
    )
    assert severity == 4  # Minimum Level 4 for threats


def test_category_base_severity():
    """Test base severity levels for categories."""
    service = ClassificationService()

    test_cases = {
        'normal_criticism': 1,
        'harassment': 2,
        'hate_speech': 3,
        'sexual_harassment': 3,
        'threat_of_violence': 4,
        'doxxing': 4,
        'impersonation': 3,
        'fake_quote': 2,
        'fake_endorsement': 2,
        'deepfake': 4,
        'coordinated_attack': 5,
        'gambling_abuse': 3
    }

    for category, expected_severity in test_cases.items():
        classification = {
            'primary_category': category,
            'secondary_categories': [],
            'confidence_score': 0.9,
            'detected_entities': {}
        }

        # Create mock athlete
        athlete = Athlete(
            first_name="Test",
            last_name="Athlete",
            date_of_birth="2000-01-01",
            sport="Soccer",
            risk_level=RiskLevel.MEDIUM,
            organization_id="test-org-id"
        )

        severity = service._calculate_severity(
            classification=classification,
            athlete=athlete,
            engagement_metrics={'views': 100}
        )

        assert severity == expected_severity, f"Category {category} should have severity {expected_severity}, got {severity}"
