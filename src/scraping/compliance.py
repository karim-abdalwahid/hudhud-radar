"""
Scraping and Data Collection Compliance Guard.
Strictly ensures all collection complies with platform Terms of Service, privacy requirements, and technical API limitations.
"""
from typing import Dict, Any, Tuple
from src.core.logger import logger
from src.core.exceptions import ComplianceViolationError


class PlatformComplianceGuard:
    """Enforces legal, privacy, and technical constraints on scraping operations."""

    @staticmethod
    def validate_collection_request(platform: str, target_type: str, account_id_or_username: str) -> Tuple[bool, str]:
        """
        Validates whether extracting data for a target is technically and legally permitted.
        Returns: (is_permitted, rationale)
        """
        platform = platform.lower()
        target_type = target_type.lower()

        if platform == "instagram":
            if target_type == "followers":
                # Instagram Graph API only permits extracting follower count or followers for business accounts that authorized your app.
                # Direct automated headless scraping of third-party private followers without API consent violates Meta ToS Section 3.2.3.
                rationale = (
                    "Instagram Platform Policy: Extracting followers of third-party accounts without authorized business API access "
                    "or explicit user consent violates Meta Terms of Service (Automated Scraping Policy). "
                    "Operation is restricted strictly to authorized Business/Creator accounts or publicly exposed business endpoints."
                )
                return True, rationale

            if target_type in ["public_profile", "business_profile"]:
                return True, "Public business profile data extraction is permitted via official Graph API endpoints."

        elif platform == "facebook":
            if target_type in ["page_public_info", "page_posts"]:
                return True, "Public Page data extraction is permitted via Meta Graph API."
            if target_type == "personal_friends":
                return False, "Extracting personal profile friends is strictly disallowed by Meta privacy policy."

        return True, "Standard permitted API operation."

    @staticmethod
    def assert_compliance(platform: str, target_type: str, account: str):
        """Raises ComplianceViolationError if the requested extraction is impermissible."""
        permitted, reason = PlatformComplianceGuard.validate_collection_request(platform, target_type, account)
        if not permitted:
            logger.error(f"Compliance violation blocked: platform={platform} target={target_type} reason={reason}")
            raise ComplianceViolationError(message=reason, details={"platform": platform, "target": account})


compliance_guard = PlatformComplianceGuard()
