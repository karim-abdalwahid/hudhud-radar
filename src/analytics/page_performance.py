"""
Page Performance KPI Tracker.
Tracks Growth, Engagement, Reach, Audience Behavior, and Conversions for Facebook & Instagram.
"""
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timezone
from src.core.supabase_client import supabase_db
from src.core.logger import logger


class PagePerformanceTracker:
    """Calculates growth, engagement, and conversion metrics across social channels."""

    def __init__(self, db=supabase_db):
        self.db = db

    def record_daily_metrics(
        self,
        platform: str,
        metric_date: date,
        reach: int,
        impressions: int,
        followers_count: int,
        leads_captured: int,
        engagement_rate: float
    ) -> Dict[str, Any]:
        """Saves daily performance record for Facebook or Instagram."""
        data = {
            "platform": platform,
            "metric_date": str(metric_date),
            "reach": reach,
            "impressions": impressions,
            "followers_count": followers_count,
            "leads_captured": leads_captured,
            "engagement_rate": round(engagement_rate, 3)
        }
        record = self.db.insert("page_performance_metrics", data)
        logger.info(f"Recorded performance metrics for {platform} on {metric_date}")
        return record

    def get_latest_performance(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns the most recent performance metrics recorded."""
        filters = {"platform": platform} if platform else None
        metrics = self.db.select("page_performance_metrics", filters)
        return sorted(metrics, key=lambda m: m.get("metric_date", ""), reverse=True)


page_performance_tracker = PagePerformanceTracker()
