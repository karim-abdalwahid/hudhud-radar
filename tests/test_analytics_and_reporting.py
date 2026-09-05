"""
Unit Tests for Statistics Engine, Root Cause Analysis, and Report Generator.
"""
import pytest
from datetime import date
from src.core.supabase_client import InMemoryDatabase
from src.analytics.statistics_engine import StatisticsEngine
from src.analytics.page_performance import PagePerformanceTracker
from src.reporting.report_generator import ReportGenerator


@pytest.fixture
def populated_db():
    db = InMemoryDatabase()
    # Add activities: 3 successes, 2 failures
    db.insert("activity_logs", {
        "action_type": "send_message", "platform": "facebook", "status": "success", "error_reason": None
    })
    db.insert("activity_logs", {
        "action_type": "send_message", "platform": "facebook", "status": "success", "error_reason": None
    })
    db.insert("activity_logs", {
        "action_type": "send_message", "platform": "instagram", "status": "success", "error_reason": None
    })
    db.insert("activity_logs", {
        "action_type": "send_message", "platform": "facebook", "status": "failed",
        "error_reason": "Cannot send Facebook DM: 24h window expired (26.2h)"
    })
    db.insert("activity_logs", {
        "action_type": "send_message", "platform": "instagram", "status": "failed",
        "error_reason": "Rate limit exceeded on instagram. Retry after 45s."
    })

    # Add page metric
    db.insert("page_performance_metrics", {
        "platform": "facebook",
        "metric_date": "2026-09-03",
        "reach": 15000,
        "impressions": 28000,
        "followers_count": 8500,
        "leads_captured": 12,
        "engagement_rate": 4.5
    })

    # Add leads
    db.insert("leads", {"source": "facebook", "full_name": "Lead 1", "contact_email": "l1@example.com"})
    db.insert("leads", {"source": "instagram", "full_name": "Lead 2", "contact_phone": "+9665555555"})
    db.insert("leads", {"source": "facebook", "full_name": "Lead 3"})

    return db


def test_statistics_engine_root_cause_analysis(populated_db):
    """Verify calculation of success rate and categorization of failure root causes."""
    stats = StatisticsEngine(db=populated_db)
    summary = stats.get_operations_summary()

    assert summary["total_operations"] == 5
    assert summary["success_count"] == 3
    assert summary["failure_count"] == 2
    assert summary["success_rate_percent"] == 60.0

    breakdown = summary["failure_reasons_breakdown"]
    assert "Policy: 24-Hour Messaging Window Expired" in breakdown
    assert "Safety: Rate Limit Throttled" in breakdown
    assert len(summary["insights"]) > 0


def test_lead_conversion_metrics(populated_db):
    """Verify lead conversion rate calculation."""
    stats = StatisticsEngine(db=populated_db)
    metrics = stats.get_lead_conversion_metrics()

    assert metrics["total_leads"] == 3
    assert metrics["leads_with_contact"] == 2
    assert round(metrics["conversion_rate_percent"], 1) == 66.7


def test_report_generation(populated_db):
    """Verify generation of Markdown reports."""
    report_gen = ReportGenerator(db=populated_db)

    perf_report = report_gen.generate_page_performance_report_md()
    assert "# 📈 تقرير أداء الصفحات" in perf_report
    assert "Facebook" in perf_report or "facebook" in perf_report

    act_report = report_gen.generate_activity_execution_report_md()
    assert "# 📋 تقرير تنفيذ الأنشطة والعمليات" in act_report
    assert "Policy: 24-Hour Messaging Window Expired" in act_report
