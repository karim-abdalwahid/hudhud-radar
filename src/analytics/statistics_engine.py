"""
Statistics Engine for Root-Cause Analysis and Operational Insights.
Calculates what succeeded, what failed, why it failed, trends, and actionable insights.
"""
from typing import Dict, Any, List, Optional
from collections import Counter
from src.core.supabase_client import supabase_db


class StatisticsEngine:
    """Computes success/failure analytics and root-cause breakdowns."""

    def __init__(self, db=supabase_db):
        self.db = db

    def _require_owner_for_production_read(self, user_id: Optional[str]) -> None:
        """Prevent an omitted filter from becoming a cross-tenant report."""
        if not user_id and getattr(self.db, "is_connected", False):
            raise ValueError("A tenant owner is required for production analytics")

    def get_operations_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates comprehensive summary of all operations executed by the agent.
        """
        self._require_owner_for_production_read(user_id)
        logs = self.db.select("activity_logs", {"user_id": user_id} if user_id else None)
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

        # Honest agent + compliance metrics from real logs (frontend used to
        # fabricate 100% here — now computed or reported as unavailable).
        outbound = [l for l in logs if l.get("action_type") in ("send_message", "reply_comment", "send_dm", "private_reply")]
        window_failures = sum(
            1 for f in failures
            if "24h window" in (f.get("error_reason") or "").lower()
        )
        agent_reply_count = sum(1 for l in logs if l.get("action_type") == "ai_reply_sent")
        ai_reply_rate = round((agent_reply_count / max(len(outbound), 1)) * 100.0, 1) if outbound else None
        # Compliance = share of outbound attempts that did NOT violate the window
        window_compliance = round(((len(outbound) - window_failures) / len(outbound)) * 100.0, 1) if outbound else None

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
            "ai_agent_reply_rate_percent": ai_reply_rate,
            "window_compliance_percent": window_compliance,
            "failure_reasons_breakdown": dict(failure_reasons),
            "insights": insights
        }

    def get_lead_conversion_metrics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates lead capture and conversion efficiency."""
        self._require_owner_for_production_read(user_id)
        leads = self.db.select("leads", {"user_id": user_id} if user_id else None)
        total_leads = len(leads)
        if total_leads == 0:
            return {
                "total_leads": 0,
                "leads_with_contact": 0,
                "phone_leads": 0,
                "email_leads": 0,
                "conversion_rate_percent": 0.0,
                "by_platform": {}
            }

        phone_leads = sum(1 for l in leads if l.get("contact_phone"))
        email_leads = sum(1 for l in leads if l.get("contact_email"))
        with_contact = [l for l in leads if l.get("contact_email") or l.get("contact_phone")]
        platforms = Counter(l.get("source", "other") for l in leads)

        conversion_rate = (len(with_contact) / total_leads) * 100.0

        return {
            "total_leads": total_leads,
            "leads_with_contact": len(with_contact),
            "phone_leads": phone_leads,
            "email_leads": email_leads,
            "conversion_rate_percent": round(conversion_rate, 2),
            "by_platform": dict(platforms)
        }


statistics_engine = StatisticsEngine()
