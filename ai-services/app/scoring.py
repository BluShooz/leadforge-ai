"""
LeadForge AI - AI Lead Scoring
Uses Claude/OpenAI to score leads based on multiple factors
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ScoreBreakdown:
    """Individual score components"""
    size_score: int  # 0-20
    industry_score: int  # 0-20
    web_presence_score: int  # 0-20
    location_score: int  # 0-20
    growth_score: int  # 0-20

    def total(self) -> int:
        return sum([
            self.size_score,
            self.industry_score,
            self.web_presence_score,
            self.location_score,
            self.growth_score
        ])


class LeadScorer:
    """AI-powered lead scoring using LLMs"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "openai",  # or "anthropic"
        model: Optional[str] = None
    ):
        """
        Initialize lead scorer

        Args:
            api_key: API key for the provider
            provider: "openai" or "anthropic"
            model: Model name (optional, uses default if not specified)
        """
        self.provider = provider
        self.api_key = api_key or os.getenv("OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY")

        if provider == "openai" and OPENAI_AVAILABLE:
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
            self.model = model or "gpt-4"
        elif provider == "anthropic" and ANTHROPIC_AVAILABLE:
            self.client = Anthropic(api_key=self.api_key)
            self.model = model or "claude-3-sonnet-20240229"
        else:
            raise ValueError(f"Provider {provider} not available or missing dependencies")

    async def score_lead(self, lead_data: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
        """
        Score a lead using AI

        Args:
            lead_data: Dictionary containing lead information

        Returns:
            Tuple of (score_0_100, breakdown_dict)
        """
        # First, get rule-based score (fast)
        rule_score = self._rule_based_score(lead_data)

        # Then, enhance with AI analysis if key is available
        if self.api_key:
            try:
                ai_score, ai_breakdown = await self._ai_score(lead_data)
                # Blend rule-based and AI scores (70% AI, 30% rules)
                final_score = int((ai_score * 0.7) + (rule_score * 0.3))
                breakdown = ai_breakdown
            except Exception as e:
                print(f"AI scoring failed, using rule-based: {e}")
                final_score = rule_score
                breakdown = self._get_rule_breakdown(lead_data)
        else:
            final_score = rule_score
            breakdown = self._get_rule_breakdown(lead_data)

        return min(final_score, 100), breakdown

    def _rule_based_score(self, lead: Dict[str, Any]) -> int:
        """Calculate score based on rules (fast, no AI)"""
        score = 0

        # Company size (0-20 points)
        size = lead.get('company_size', '')
        if '500+' in size:
            score += 20
        elif '201' in size:
            score += 17
        elif '51' in size:
            score += 14
        elif '11' in size:
            score += 10
        elif '1' in size:
            score += 5

        # Website (0-20 points)
        if lead.get('website'):
            score += 20

        # Phone (0-10 points)
        if lead.get('phone'):
            score += 10

        # Email (0-10 points)
        if lead.get('email'):
            score += 10

        # LinkedIn (0-10 points)
        if lead.get('linkedin_url'):
            score += 10

        # Industry relevance (0-20 points)
        # High-value industries
        high_value_industries = [
            'technology', 'software', 'healthcare', 'finance',
            'real estate', 'manufacturing', 'legal', 'consulting'
        ]
        industry = lead.get('industry', '').lower()
        if any(hvi in industry for hvi in high_value_industries):
            score += 20
        elif industry:
            score += 10

        return score

    def _get_rule_breakdown(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Get score breakdown based on rules"""
        return {
            "company_size": lead.get('company_size', 'Unknown'),
            "has_website": bool(lead.get('website')),
            "has_phone": bool(lead.get('phone')),
            "has_email": bool(lead.get('email')),
            "industry": lead.get('industry', 'Unknown'),
            "factors": {
                "size_score": 20 if lead.get('company_size') else 0,
                "contact_score": 30 if (lead.get('phone') and lead.get('email')) else 15,
                "web_presence": 20 if lead.get('website') else 0,
                "industry_score": 20 if lead.get('industry') else 10,
                "growth_signals": 10 if lead.get('linkedin_url') else 0
            }
        }

    async def _ai_score(self, lead: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
        """Score lead using AI"""
        prompt = self._build_scoring_prompt(lead)

        if self.provider == "openai":
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert lead scoring specialist. Score leads 0-100 based on their potential value."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            response_text = response.choices[0].message.content

        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = response.content[0].text

        # Parse response
        return self._parse_ai_response(response_text)

    def _build_scoring_prompt(self, lead: Dict[str, Any]) -> str:
        """Build prompt for AI scoring"""
        return f"""Score this business lead (0-100):

Business Name: {lead.get('business_name', 'Unknown')}
Industry: {lead.get('industry', 'Unknown')}
Website: {lead.get('website', 'None')}
Phone: {lead.get('phone', 'None')}
Email: {lead.get('email', 'None')}
LinkedIn: {lead.get('linkedin_url', 'None')}
Company Size: {lead.get('company_size', 'Unknown')}
Location: {lead.get('city', '')}, {lead.get('state', '')}

Scoring factors (20 points each):
1. Company Size (larger = higher score)
2. Industry Relevance (B2B, tech, healthcare = higher)
3. Web Presence (website + LinkedIn = higher)
4. Location Quality (major metros = higher)
5. Growth Signals (professional presence = higher)

Return ONLY this format:
SCORE: [0-100]
BREAKDOWN:
size_score: [0-20]
industry_score: [0-20]
web_presence_score: [0-20]
location_score: [0-20]
growth_score: [0-20]
reasoning: [1-2 sentence explanation]"""

    def _parse_ai_response(self, response: str) -> tuple[int, Dict[str, Any]]:
        """Parse AI response into score and breakdown"""
        try:
            lines = response.strip().split('\n')

            score = 50  # default
            breakdown = {
                "size_score": 10,
                "industry_score": 10,
                "web_presence_score": 10,
                "location_score": 10,
                "growth_score": 10,
                "reasoning": "AI scoring unavailable"
            }

            for line in lines:
                if line.startswith('SCORE:'):
                    score = int(line.split(':')[1].strip())
                elif ':' in line and '_score:' in line:
                    key = line.split(':')[0].strip().lower()
                    value = int(line.split(':')[1].strip())
                    breakdown[f"{key}_score"] = value
                elif line.startswith('reasoning:'):
                    breakdown['reasoning'] = line.split(':', 1)[1].strip()

            return score, breakdown

        except Exception as e:
            print(f"Error parsing AI response: {e}")
            return 50, {"reasoning": "Parse error"}


async def score_leads_batch(
    leads: list[Dict[str, Any]],
    api_key: Optional[str] = None,
    provider: str = "openai"
) -> list[tuple[int, Dict[str, Any]]]:
    """
    Score multiple leads in batch

    Args:
        leads: List of lead dictionaries
        api_key: API key for AI provider
        provider: "openai" or "anthropic"

    Returns:
        List of (score, breakdown) tuples
    """
    scorer = LeadScorer(api_key=api_key, provider=provider)

    results = []
    for lead in leads:
        score, breakdown = await scorer.score_lead(lead)
        results.append((score, breakdown))

    return results
