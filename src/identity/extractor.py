"""
Zero-Assumption Profile Data Extractor.
Extracts only legitimately available data from Facebook and Instagram payloads.
Never assumes, guesses, or fabricates data.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from src.leads.models import LeadCreate, PlatformSource, DataProvenance, VerificationMethod
from src.core.logger import logger


class ProfileDataExtractor:
    """Extracts raw profile data strictly adhering to zero-assumption policy."""

    @staticmethod
    def extract_from_facebook(raw_data: Dict[str, Any]) -> LeadCreate:
        """
        Extract profile info from a Facebook Graph API payload or webhook sender object.
        Fields: name, username, profile_url, bio, location, email, phone, linked_instagram_id.
        """
        # Strictly extract only what exists in raw_data
        full_name = raw_data.get("name") or (
            f"{raw_data.get('first_name', '')} {raw_data.get('last_name', '')}".strip()
            if raw_data.get("first_name") or raw_data.get("last_name") else None
        )
        fb_id = str(raw_data.get("id")) if raw_data.get("id") else None
        username = raw_data.get("username")
        profile_url = raw_data.get("link") or (f"https://www.facebook.com/{fb_id}" if fb_id else None)
        bio = raw_data.get("about") or raw_data.get("bio")
        avatar_url = raw_data.get("profile_pic") or raw_data.get("avatar_url")
        
        # Location handling: Meta often returns a dict with 'name'
        location_raw = raw_data.get("location")
        location = location_raw.get("name") if isinstance(location_raw, dict) else location_raw

        # Contact details if legally and publicly accessible
        contact_email = raw_data.get("email")
        contact_phone = raw_data.get("phone")

        # Official linked Instagram account in Facebook account settings
        linked_ig = raw_data.get("instagram_accounts", {}).get("data", [])
        instagram_account_id = linked_ig[0].get("id") if linked_ig else raw_data.get("linked_instagram_account_id")

        provenance = DataProvenance(
            collected_at=datetime.now(timezone.utc),
            source_platform=PlatformSource.FACEBOOK,
            verification_method=VerificationMethod.DIRECT,
            source_account_id=fb_id,
            provenance_notes=["Directly extracted from Facebook Graph API payload"]
        )

        return LeadCreate(
            source=PlatformSource.FACEBOOK,
            full_name=full_name,
            username=username,
            avatar_url=avatar_url,
            profile_url=profile_url,
            bio=bio,
            location=location,
            contact_email=contact_email,
            contact_phone=contact_phone,
            facebook_account_id=fb_id,
            instagram_account_id=instagram_account_id,
            data_provenance=provenance
        )

    @staticmethod
    def extract_from_instagram(raw_data: Dict[str, Any]) -> LeadCreate:
        """
        Extract profile info from an Instagram Graph API payload.
        Fields: username, name, bio, profile_url, contact_details.
        """
        ig_id = str(raw_data.get("id")) if raw_data.get("id") else None
        username = raw_data.get("username")
        full_name = raw_data.get("name")
        bio = raw_data.get("biography") or raw_data.get("bio")
        profile_url = f"https://www.instagram.com/{username}/" if username else None
        avatar_url = raw_data.get("profile_pic") or raw_data.get("profile_picture_url") or raw_data.get("avatar_url")
        
        # Contact info if publicly exposed by business profile
        contact_email = raw_data.get("public_email") or raw_data.get("email")
        contact_phone = raw_data.get("public_phone_number") or raw_data.get("phone")
        
        # Linked Facebook page if officially present
        fb_page_id = raw_data.get("connected_facebook_page", {}).get("id") if isinstance(raw_data.get("connected_facebook_page"), dict) else None

        provenance = DataProvenance(
            collected_at=datetime.now(timezone.utc),
            source_platform=PlatformSource.INSTAGRAM,
            verification_method=VerificationMethod.DIRECT,
            source_account_id=ig_id or username,
            provenance_notes=["Directly extracted from Instagram Graph API payload"]
        )

        return LeadCreate(
            source=PlatformSource.INSTAGRAM,
            full_name=full_name,
            username=username,
            avatar_url=avatar_url,
            profile_url=profile_url,
            bio=bio,
            location=None,  # Not fabricated if not present
            contact_email=contact_email,
            contact_phone=contact_phone,
            facebook_account_id=fb_page_id,
            instagram_account_id=ig_id or username,
            data_provenance=provenance
        )

    @staticmethod
    def extract_from_threads(raw_data: Dict[str, Any]) -> LeadCreate:
        """
        Extract profile info from a Threads API payload (reply author or profile lookup).
        Official fields: username, name, thread_profile_picture_url. Zero fabrication.
        """
        th_id = str(raw_data.get("id")) if raw_data.get("id") else None
        username = raw_data.get("username")
        full_name = raw_data.get("name")
        avatar_url = raw_data.get("thread_profile_picture_url") or raw_data.get("profile_pic")
        profile_url = f"https://www.threads.net/@{username}" if username else None

        provenance = DataProvenance(
            collected_at=datetime.now(timezone.utc),
            source_platform=PlatformSource.THREADS,
            verification_method=VerificationMethod.DIRECT,
            source_account_id=th_id or username,
            provenance_notes=["Directly extracted from Threads API payload"]
        )

        return LeadCreate(
            source=PlatformSource.THREADS,
            full_name=full_name,
            username=username,
            avatar_url=avatar_url,
            profile_url=profile_url,
            threads_account_id=th_id,
            data_provenance=provenance
        )
