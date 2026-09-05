"""
Modular Data Collector & Scraper Architecture.
Designed for clean extensibility so additional platforms can be added in the future.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from src.scraping.compliance import compliance_guard
from src.core.logger import logger
from src.leads.models import LeadCreate, PlatformSource
from src.identity.extractor import ProfileDataExtractor


class BaseDataCollector(ABC):
    """Abstract base class for platform-specific data collectors."""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    @abstractmethod
    async def get_profile(self, identifier: str) -> Optional[LeadCreate]:
        """Fetch profile information for an account if permitted."""
        pass

    @abstractmethod
    async def collect_contacts(self, target_account: str, max_results: int = 50) -> List[LeadCreate]:
        """Collect eligible contacts/leads from the target account if permitted."""
        pass


class InstagramDataCollector(BaseDataCollector):
    """Instagram collector operating strictly within official Graph API and public business scopes."""

    def __init__(self):
        super().__init__("instagram")

    async def get_profile(self, username: str) -> Optional[LeadCreate]:
        compliance_guard.assert_compliance("instagram", "business_profile", username)
        logger.info(f"[InstagramCollector] Fetching public business profile for @{username}")
        # In production, queries Instagram Graph API business discovery endpoint
        raw_mock = {
            "id": f"ig_{username}",
            "username": username,
            "name": username.replace("_", " ").title(),
            "biography": "Official business account",
        }
        return ProfileDataExtractor.extract_from_instagram(raw_mock)

    async def collect_contacts(self, target_account: str, max_results: int = 50) -> List[LeadCreate]:
        compliance_guard.assert_compliance("instagram", "followers", target_account)
        logger.info(f"[InstagramCollector] Processing eligible contacts for account @{target_account}")
        # Only returns accounts that have legitimately engaged or provided authorized business access
        return []


class FacebookDataCollector(BaseDataCollector):
    """Facebook collector operating strictly within Page Graph API scopes."""

    def __init__(self):
        super().__init__("facebook")

    async def get_profile(self, page_id: str) -> Optional[LeadCreate]:
        compliance_guard.assert_compliance("facebook", "page_public_info", page_id)
        logger.info(f"[FacebookCollector] Fetching public page info for {page_id}")
        raw_mock = {
            "id": page_id,
            "name": f"Page {page_id}",
            "link": f"https://www.facebook.com/{page_id}"
        }
        return ProfileDataExtractor.extract_from_facebook(raw_mock)

    async def collect_contacts(self, target_account: str, max_results: int = 50) -> List[LeadCreate]:
        logger.info(f"[FacebookCollector] Processing eligible contacts for Page {target_account}")
        return []


# Registry of supported data sources
DATA_COLLECTORS: Dict[str, BaseDataCollector] = {
    "instagram": InstagramDataCollector(),
    "facebook": FacebookDataCollector()
}


def get_data_collector(platform: str) -> BaseDataCollector:
    """Factory to retrieve collector for a given platform."""
    collector = DATA_COLLECTORS.get(platform.lower())
    if not collector:
        raise ValueError(f"Platform '{platform}' is not currently supported for data collection.")
    return collector
