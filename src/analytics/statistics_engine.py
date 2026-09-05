"""
Statistics Engine for Root-Cause Analysis and Operational Insights.
Calculates what succeeded, what failed, why it failed, trends, and actionable insights.
"""
from typing import Dict, Any, List
from collections import Counter
from src.core.supabase_client import supabase_db


class StatisticsEngine:
    """Computes success/failure analytics and root-cause breakdowns."""

    def __init__(self, db=supabase_db):
        self.db = db

    def get_operations_summary(self) -> Dict[str, Any]:
        """
        Calculates comprehensive summary of all operations executed by the agent.
        """
        logs = self.db.select("activity_logs")
        total_ops = len(logs)
        if total_ops == 0:
            return {
                "total_operations": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate_percent": 0.0,
                "failure_reasons_breakdown": {},
                "insights": ["No activities recorded yet. System is initialized and ready."]
            }

        successes = [l for l in logs if l.get("status") == "success"]
        failures = [l for l in logs if l.get("status") == "failed"]

        # Granular root cause grouping
        failure_reasons = Counter()
        for f in failures:
            reason = f.get("error_reason") or "Unknown error"
            # Normalize common failure messages
            if "24h window expired" in reason.lower():
                category = "Policy: 24-Hour Messaging Window Expired"
            elif "rate limit" in reason.lower():
                category = "Safety: Rate Limit Throttled"
            elif "token" in reason.lower() or "auth" in reason.lower():
                category = "Auth: Expired or Invalid Access Token"
            else:
                category = f"API/Network: {reason[:60]}"
            failure_reasons[category] += 1

        success_rate = (len(successes) / total_ops) * 100.0

        # Formulate actionable insights
        insights = []
        if failure_reasons.get("Policy: 24-Hour Messaging Window Expired", 0) > 0:
            insights.append("Recommendation: Inbound leads are responding after 24h. Implement approved Message Tags or follow up immediately upon incoming DM.")
        if failure_reasons.get("Safety: Rate Limit Throttled", 0) > 0:
            insights.append("Recommendation: Outbound messaging pace is approaching platform thresholds. Reduce MAX_MESSAGES_PER_MINUTE by 20%.")
        if success_rate >= 90.0:
            insights.append("Performance: High operational stability achieved. Workflow execution is reliable.")

        return {
            "total_operations": total_ops,
            "success_count": len(successes),
            "failure_count": len(failures),
            "success_rate_percent": round(success_rate, 2),
            "failure_reasons_breakdown": dict(failure_reasons),
            "insights": insights
        }

    def get_lead_conversion_metrics(self) -> Dict[str, Any]:
        """Calculates lead capture and conversion efficiency."""
        leads = self.db.select("leads")
        total_leads = len(leads)
        if total_leads == 0:
            return {
                "total_leads": 0,
                "leads_with_contact": 0,
                "conversion_rate_percent": 0.0,
                "by_platform": {}
            }

        with_contact = [l for l in leads if l.get("contact_email") or l.get("contact_phone")]
        platforms = Counter(l.get("source", "other") for l in leads)

        conversion_rate = (len(with_contact) / total_leads) * 100.0

        return {
            "total_leads": total_leads,
            "leads_with_contact": len(with_contact),
            "conversion_rate_percent": round(conversion_rate, 2),
            "by_platform": dict(platforms)
        }


statistics_engine = StatisticsEngine()
