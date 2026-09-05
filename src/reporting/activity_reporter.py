"""
Activity Reporter and Audit Exporter.
Persists execution snapshots to the permanent documentation logs.
"""
from pathlib import Path
from datetime import datetime, timezone
from src.core.logger import logger
from src.reporting.report_generator import report_generator


class ActivityReporter:
    """Manages periodic audit logging and file-based execution dumps."""

    def __init__(self, reports_dir: str = "docs/PROJECT_REPORTS"):
        self.reports_dir = Path(reports_dir)
        self.generator = report_generator

    def export_latest_activity_report(self, filename: str = "LATEST_ACTIVITY_REPORT.md") -> str:
        """Exports full activity execution report to a permanent markdown file."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_content = self.generator.generate_activity_execution_report_md()
        out_path = self.reports_dir / filename
        out_path.write_text(report_content, encoding="utf-8")
        logger.info(f"Saved activity execution report to {out_path}")
        return str(out_path)

    def export_latest_performance_report(self, filename: str = "LATEST_PERFORMANCE_REPORT.md") -> str:
        """Exports page performance report to a permanent markdown file."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_content = self.generator.generate_page_performance_report_md()
        out_path = self.reports_dir / filename
        out_path.write_text(report_content, encoding="utf-8")
        logger.info(f"Saved performance report to {out_path}")
        return str(out_path)


activity_reporter = ActivityReporter()
