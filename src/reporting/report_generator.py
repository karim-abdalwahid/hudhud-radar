"""
Comprehensive Performance and Activity Report Generator.
Generates human-readable Markdown and structured data reports for executive review.
"""
from typing import Dict, Any, List
from datetime import datetime, timezone
from src.core.supabase_client import supabase_db
from src.analytics.statistics_engine import StatisticsEngine
from src.analytics.page_performance import PagePerformanceTracker


class ReportGenerator:
    """Generates detailed reports for page performance and agent activity."""

    def __init__(self, db=supabase_db):
        self.db = db
        self.stats = StatisticsEngine(db=self.db)
        self.tracker = PagePerformanceTracker(db=self.db)

    def generate_page_performance_report_md(self, platform: str = "all") -> str:
        """Generates executive Markdown report of page performance metrics and KPIs."""
        perf_data = self.tracker.get_latest_performance(None if platform == "all" else platform)
        conversion_data = self.stats.get_lead_conversion_metrics()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"# 📈 تقرير أداء الصفحات — SocailManager",
            f"**تاريخ التوليد**: `{now_str}` | **المنصة**: `{platform.upper()}`",
            "",
            "## 🎯 الملخص التنفيذي ومؤشرات الأداء الرئيسية (KPIs)",
            f"- **إجمالي العملاء المحتملين المسجلين**: `{conversion_data['total_leads']}`",
            f"- **العملاء المؤهلين (وسائل اتصال متوفرة)**: `{conversion_data['leads_with_contact']}`",
            f"- **معدل تحويل العملاء**: `{conversion_data['conversion_rate_percent']}%`",
            "",
            "## 📊 سجل المقاييس اليومية",
            "| المنصة | التاريخ | مرات الظهور (Impressions) | الوصول (Reach) | المتابعون | العملاء المستقطبون | معدل التفاعل |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        if not perf_data:
            lines.append("| - | لا توجد بيانات يومية مسجلة بعد | - | - | - | - | - |")
        else:
            for row in perf_data[:15]:
                lines.append(
                    f"| {row.get('platform')} | {row.get('metric_date')} | {row.get('impressions', 0):,} | "
                    f"{row.get('reach', 0):,} | {row.get('followers_count', 0):,} | {row.get('leads_captured', 0)} | "
                    f"{row.get('engagement_rate', 0.0)}% |"
                )

        lines.extend([
            "",
            "## 🔍 توزيع العملاء حسب المنصة",
        ])
        for plat, count in conversion_data.get("by_platform", {}).items():
            lines.append(f"- **{plat.capitalize()}**: {count} عميل")

        return "\n".join(lines)

    def generate_activity_execution_report_md(self) -> str:
        """Generates executive Markdown report of all processed actions, failures, and root causes."""
        ops_summary = self.stats.get_operations_summary()
        all_logs = self.db.select("activity_logs")
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"# 📋 تقرير تنفيذ الأنشطة والعمليات — SocailManager",
            f"**تاريخ التوليد**: `{now_str}`",
            "",
            "## ⚖️ إحصاءات النجاح والفشل",
            f"- **إجمالي العمليات المنفذة**: `{ops_summary['total_operations']}`",
            f"- **العمليات الناجحة**: `{ops_summary['success_count']}`",
            f"- **العمليات الفاشلة**: `{ops_summary['failure_count']}`",
            f"- **نسبة النجاح التشغيلي**: `{ops_summary['success_rate_percent']}%`",
            "",
            "## 🛑 التحليل الجذري لأسباب الفشل (Failure Root Causes)",
        ]

        if not ops_summary["failure_reasons_breakdown"]:
            lines.append("- *لم يتم رصد أي عمليات فاشلة حتى الآن.*")
        else:
            for cause, count in ops_summary["failure_reasons_breakdown"].items():
                lines.append(f"- **{cause}**: {count} حالة")

        lines.extend([
            "",
            "## 💡 التوصيات والرؤى التشغيلية لتحسين القرارات",
        ])
        for insight in ops_summary.get("insights", []):
            lines.append(f"- {insight}")

        lines.extend([
            "",
            "## 📜 أحدث العمليات المعالجة (آخر 20 عملية)",
            "| التوقيت | نوع العملية | المنصة | الهدف | الحالة | السبب / الملاحظات |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ])

        recent_logs = sorted(all_logs, key=lambda l: l.get("executed_at", ""), reverse=True)[:20]
        if not recent_logs:
            lines.append("| - | لا توجد عمليات مسجلة بعد | - | - | - | - |")
        else:
            for log in recent_logs:
                lines.append(
                    f"| {log.get('executed_at', '')[:19]} | {log.get('action_type')} | {log.get('platform')} | "
                    f"{log.get('target_id', '-')} | {log.get('status')} | {log.get('error_reason') or 'ناجحة بالكامل'} |"
                )

        return "\n".join(lines)


report_generator = ReportGenerator()
