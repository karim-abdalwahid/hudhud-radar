"""
Activity Reporter and Audit Exporter.
Persists execution snapshots to the permanent documentation logs.
"""
from pathlib import Path
from typing import Optional
from src.core.logger import logger
from src.reporting.report_generator import report_generator


class ActivityReporter:
    """Manages periodic audit logging and file-based execution dumps."""

    def __init__(self, reports_dir: str = "docs/PROJECT_REPORTS"):
        self.reports_dir = Path(reports_dir)
        self.generator = report_generator

    def export_latest_activity_report(self, user_id: str,
                                      filename: str = "LATEST_ACTIVITY_REPORT.md") -> str:
        """Exports one tenant's activity report; never a cross-tenant dump."""
        if not user_id:
            raise ValueError("A tenant owner is required to export an activity report")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_content = self.generator.generate_activity_execution_report_md(user_id=user_id)
        out_path = self.reports_dir / filename
        out_path.write_text(report_content, encoding="utf-8")
        logger.info(f"Saved activity execution report to {out_path}")
        return str(out_path)

    def export_latest_performance_report(self, user_id: str,
                                         filename: str = "LATEST_PERFORMANCE_REPORT.md") -> str:
        """Exports one tenant's performance report; never a cross-tenant dump."""
        if not user_id:
            raise ValueError("A tenant owner is required to export a performance report")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_content = self.generator.generate_page_performance_report_md(user_id=user_id)
        out_path = self.reports_dir / filename
        out_path.write_text(report_content, encoding="utf-8")
        logger.info(f"Saved performance report to {out_path}")
        return str(out_path)


activity_reporter = ActivityReporter()
