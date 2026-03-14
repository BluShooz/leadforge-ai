"""
LeadForge AI - AI Outreach Email Generator
Uses AI to generate personalized outreach emails and follow-up sequences
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import os

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
class EmailTemplate:
    """Generated email template"""
    subject: str
    body: str
    variables: List[str]  # List of variable names to replace


class OutreachGenerator:
    """AI-powered outreach email generator"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None
    ):
        """
        Initialize outreach generator

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
            raise ValueError(f"Provider {provider} not available")

    async def generate_initial_email(
        self,
        lead: Dict[str, Any],
        sender_info: Dict[str, Any],
        service_type: str = "digital marketing"
    ) -> EmailTemplate:
        """
        Generate initial outreach email

        Args:
            lead: Lead information dictionary
            sender_info: Sender's information (name, company, etc.)
            service_type: Type of service being offered

        Returns:
            EmailTemplate with subject and body
        """
        prompt = self._build_email_prompt(lead, sender_info, service_type, "initial")

        if self.provider == "openai":
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert sales email writer. Generate personalized, professional outreach emails."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            response_text = response.choices[0].message.content
        else:  # anthropic
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.content[0].text

        return self._parse_email_response(response_text)

    async def generate_follow_up_email(
        self,
        lead: Dict[str, Any],
        sender_info: Dict[str, Any],
        sequence_number: int,
        service_type: str = "digital marketing"
    ) -> EmailTemplate:
        """
        Generate follow-up email

        Args:
            lead: Lead information
            sender_info: Sender's information
            sequence_number: Which follow-up in sequence (1, 2, 3...)
            service_type: Type of service being offered

        Returns:
            EmailTemplate for follow-up
        """
        prompt = self._build_email_prompt(lead, sender_info, service_type, f"follow-up {sequence_number}")

        if self.provider == "openai":
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert sales email writer. Generate professional follow-up emails."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            response_text = response.choices[0].message.content
        else:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.content[0].text

        return self._parse_email_response(response_text)

    async def generate_email_sequence(
        self,
        lead: Dict[str, Any],
        sender_info: Dict[str, Any],
        service_type: str = "digital marketing",
        num_emails: int = 3
    ) -> List[EmailTemplate]:
        """
        Generate complete email sequence

        Args:
            lead: Lead information
            sender_info: Sender's information
            service_type: Type of service
            num_emails: Number of emails in sequence

        Returns:
            List of EmailTemplates
        """
        sequence = []

        # Initial email
        initial = await self.generate_initial_email(lead, sender_info, service_type)
        sequence.append(initial)

        # Follow-ups
        for i in range(1, num_emails):
            follow_up = await self.generate_follow_up_email(
                lead, sender_info, i, service_type
            )
            sequence.append(follow_up)

        return sequence

    def _build_email_prompt(
        self,
        lead: Dict[str, Any],
        sender_info: Dict[str, Any],
        service_type: str,
        email_type: str
    ) -> str:
        """Build prompt for email generation"""

        if email_type == "initial":
            instruction = """Write a personalized INITIAL outreach email with:
- Compelling subject line (under 50 characters)
- Personalized opening mentioning their business
- Brief value proposition
- Clear call-to-action
- Professional closing

Keep it under 150 words."""
        else:
            instruction = f"""Write a {email_type.upper()} email with:
- Reference previous email
- New value or angle
- Soft call-to-action
- Professional tone

Keep it under 120 words."""

        return f"""{instruction}

BUSINESS BEING CONTACTED:
Name: {lead.get('business_name', 'their business')}
Industry: {lead.get('industry', 'Unknown')}
Website: {lead.get('website', 'N/A')}
Location: {lead.get('city', '')}, {lead.get('state', '')}
Contact: {lead.get('contact_name', 'there')}

SENDER INFO:
Name: {sender_info.get('name', 'Your Name')}
Company: {sender_info.get('company', 'Your Company')}
Title: {sender_info.get('title', 'Business Development')}

SERVICE: {service_type}

Return format:
SUBJECT: [subject line]

BODY: [email body with placeholders like {business_name}, {contact_name}, etc.]"""

    def _parse_email_response(self, response: str) -> EmailTemplate:
        """Parse AI response into EmailTemplate"""
        parts = response.split('BODY:', 1)

        if len(parts) == 2:
            subject = parts[0].replace('SUBJECT:', '').strip()
            body = parts[1].strip()
        else:
            # Fallback
            lines = response.split('\n')
            subject = lines[0] if lines else "Introduction"
            body = '\n'.join(lines[1:]) if len(lines) > 1 else response

        # Extract variables
        variables = []
        if '{business_name}' in body:
            variables.append('business_name')
        if '{contact_name}' in body:
            variables.append('contact_name')
        if '{sender_name}' in body:
            variables.append('sender_name')
        if '{sender_company}' in body:
            variables.append('sender_company')
        if '{industry}' in body:
            variables.append('industry')
        if '{location}' in body:
            variables.append('location')

        return EmailTemplate(
            subject=subject,
            body=body,
            variables=variables
        )

    def fill_template(
        self,
        template: EmailTemplate,
        lead: Dict[str, Any],
        sender_info: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Fill email template with actual data

        Args:
            template: EmailTemplate to fill
            lead: Lead data
            sender_info: Sender data

        Returns:
            Dictionary with subject and filled body
        """
        body = template.body

        # Replace variables
        replacements = {
            '{business_name}': lead.get('business_name', 'their business'),
            '{contact_name}': lead.get('contact_name', 'there'),
            '{sender_name}': sender_info.get('name', 'Your Name'),
            '{sender_company}': sender_info.get('company', 'Your Company'),
            '{industry}': lead.get('industry', 'your industry'),
            '{location}': f"{lead.get('city', '')}, {lead.get('state', '')}".strip(', ') or 'your area',
            '{website}': lead.get('website', ''),
        }

        for placeholder, value in replacements.items():
            body = body.replace(placeholder, value)

        return {
            'subject': template.subject,
            'body': body
        }


async def generate_outreach_campaign(
    leads: List[Dict[str, Any]],
    sender_info: Dict[str, Any],
    service_type: str = "digital marketing",
    api_key: Optional[str] = None,
    provider: str = "openai"
) -> Dict[str, List[EmailTemplate]]:
    """
    Generate email templates for multiple leads

    Args:
        leads: List of lead dictionaries
        sender_info: Sender information
        service_type: Type of service
        api_key: API key for AI provider
        provider: "openai" or "anthropic"

    Returns:
        Dictionary mapping lead business names to their email sequences
    """
    generator = OutreachGenerator(api_key=api_key, provider=provider)

    results = {}
    for lead in leads:
        sequence = await generator.generate_email_sequence(
            lead, sender_info, service_type, num_emails=3
        )
        results[lead.get('business_name', 'unknown')] = sequence

    return results
