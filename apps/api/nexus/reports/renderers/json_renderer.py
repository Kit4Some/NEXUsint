"""JSON report renderer."""

from datetime import datetime, timezone
from typing import Any


class JSONRenderer:
    """Renders structured intelligence reports as JSON-serializable dicts."""

    def render(self, report_data: dict[str, Any]) -> dict[str, Any]:
        """Render report data as a structured JSON dict."""
        return {
            "format": "json",
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "classification": report_data.get("classification", "UNCLASSIFIED"),
            "title": report_data.get("title", "Intelligence Report"),
            "investigation_id": report_data.get("investigation_id", ""),
            "sections": {
                key: value
                for key, value in report_data.items()
                if key not in ("title", "investigation_id", "classification")
            },
        }
