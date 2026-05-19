"""
Classification prompts for Claude API.
"""
from typing import Dict, Any


def get_classification_prompt(
    content_text: str,
    author_username: str,
    author_follower_count: int,
    account_age_days: int,
    athlete_name: str,
    athlete_sport: str,
    athlete_age: int,
    athlete_gender: str,
    recent_context: str = ""
) -> str:
    """
    Generate classification prompt for Claude API.

    Args:
        content_text: The social media content to classify
        author_username: Username of content author
        author_follower_count: Follower count
        account_age_days: Age of author's account in days
        athlete_name: Name of the athlete
        athlete_sport: Sport the athlete participates in
        athlete_age: Age of the athlete
        athlete_gender: Gender of the athlete
        recent_context: Recent events or context about the athlete

    Returns:
        Formatted prompt string for Claude API
    """
    prompt = f"""You are an AI content moderator specializing in athlete protection.
Analyze the following social media content for harmful behavior.

CONTENT:
{content_text}

AUTHOR CONTEXT:
- Username: {author_username}
- Follower count: {author_follower_count:,}
- Account age: {account_age_days} days
- Engagement pattern: {"New account" if account_age_days < 30 else "Established account"}

ATHLETE CONTEXT:
- Name: {athlete_name}
- Sport: {athlete_sport}
- Age: {athlete_age} years old
- Gender: {athlete_gender}
{"- Recent events: " + recent_context if recent_context else ""}

CLASSIFICATION CATEGORIES (choose ONE primary):
1. normal_criticism - Legitimate sports commentary, even if negative. Fans expressing disappointment, critiquing performance, or debating strategy.
2. harassment - Targeted personal attacks, bullying, repeated negative comments aimed at causing distress.
3. hate_speech - Racist, sexist, homophobic, transphobic, or other discriminatory content targeting protected characteristics.
4. sexual_harassment - Unwanted sexual comments, objectification, explicit sexual content directed at the athlete.
5. threat_of_violence - Explicit or implied threats to physical safety, harm, or violence.
6. doxxing - Sharing private information such as home address, phone number, school, family details.
7. impersonation - Pretending to be the athlete, creating fake accounts, or falsely representing the athlete.
8. fake_quote - Falsely attributed statements, made-up quotes, or misrepresented comments.
9. fake_endorsement - False claims about product endorsements, brand partnerships, or sponsorships.
10. deepfake - AI-generated or manipulated images/videos, face swaps, synthetic media.
11. coordinated_attack - Organized harassment campaign, brigading, multiple accounts with similar messaging.
12. gambling_abuse - Betting-related harassment, match-fixing accusations, abuse related to sports gambling.

SEVERITY LEVELS (assign 1-5):
- Level 1: Negative fan comment (log only) - Disappointed fan, mild criticism
- Level 2: Bullying/personal attack (flag for review) - Mean-spirited comments, name-calling
- Level 3: Hate speech/sexual harassment (hide from athlete) - Discriminatory slurs, explicit sexual content
- Level 4: Doxxing/credible threat (immediate human review) - Private info shared, specific threats
- Level 5: Coordinated attack/criminal threat (urgent escalation) - Organized campaign, serious criminal threat

SPECIAL CONSIDERATIONS:
- Context matters: Criticism of athletic performance vs. personal attacks on character
- NCAA/College context: Gambling-related abuse is especially serious due to betting scandals
- Female athletes: Heightened risk of sexual harassment and objectification
- Youth athletes (under 18): Lower threshold for escalation, protect minors more aggressively
- Cultural nuances: Consider slang, regional expressions, and cultural context
- Sarcasm detection: Distinguish genuine threats from dark humor (context-dependent)

DECISION FRAMEWORK:
1. Is this about athletic performance or personal character?
2. Does it target protected characteristics (race, gender, sexuality)?
3. Does it contain explicit threats or private information?
4. Is the intent to harm, intimidate, or cause distress?
5. Would a reasonable person find this threatening or abusive?

OUTPUT FORMAT (JSON):
{{
  "primary_category": "category_name",
  "secondary_categories": ["category2", "category3"],
  "severity_level": 1-5,
  "confidence_score": 0.0-1.0,
  "reasoning": "2-3 sentence explanation focusing on specific harmful elements. Quote key phrases that led to this classification.",
  "key_evidence": ["exact phrase 1", "exact phrase 2", "exact phrase 3"],
  "requires_immediate_review": true/false,
  "recommended_action": "monitor|hide|escalate|takedown",
  "detected_entities": {{
    "threats": ["specific threat phrases"],
    "personal_info": ["any PII mentioned"],
    "hate_keywords": ["discriminatory terms used"],
    "sexual_content": ["explicit phrases"],
    "coordinated_indicators": {{"description": "evidence of coordination"}}
  }}
}}

IMPORTANT GUIDELINES:
- Be conservative with severity levels - err on the side of caution
- Level 4-5 should be reserved for genuine threats and serious abuse
- Normal sports criticism should be Level 1, even if harsh
- Provide specific evidence - quote exact phrases that led to the classification
- Consider the totality of circumstances, not just individual words
- Flag ambiguous cases for human review (confidence < 0.7)

Analyze the content now and provide your classification in JSON format:"""

    return prompt


def get_coordinated_attack_analysis_prompt(
    content_items: list[Dict[str, Any]]
) -> str:
    """
    Generate prompt for detecting coordinated attacks.

    Args:
        content_items: List of content items with similar characteristics

    Returns:
        Prompt for analyzing coordination patterns
    """
    content_summary = "\n\n".join([
        f"Content {i+1}:\n"
        f"- Author: {item['author_username']}\n"
        f"- Text: {item['content_text']}\n"
        f"- Posted: {item['published_at']}\n"
        f"- Platform: {item['platform']}"
        for i, item in enumerate(content_items[:10])  # Limit to 10 items
    ])

    prompt = f"""Analyze the following social media content for signs of a coordinated harassment campaign.

CONTENT ITEMS:
{content_summary}

COORDINATION INDICATORS TO LOOK FOR:
1. Similar or identical messaging across multiple accounts
2. Posting within a short time window (brigading)
3. Use of common hashtags or coordinating phrases
4. Newly created accounts all targeting the same athlete
5. Cross-platform coordination (same message on multiple platforms)
6. Organized from external forums (4chan, Discord, Reddit)

PROVIDE ANALYSIS IN JSON FORMAT:
{{
  "is_coordinated": true/false,
  "confidence": 0.0-1.0,
  "coordination_type": "brigade|organized_hate|astroturfing|bot_network|none",
  "evidence": [
    "specific evidence of coordination"
  ],
  "time_window_minutes": 0,
  "unique_authors": 0,
  "common_phrases": ["phrase1", "phrase2"],
  "recommended_action": "immediate_escalation|monitor|investigate"
}}

Analyze now:"""

    return prompt
