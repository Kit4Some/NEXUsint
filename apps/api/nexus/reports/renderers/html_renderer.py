"""HTML report renderer using Jinja2 templates."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class HTMLRenderer:
    """Renders intelligence reports as HTML using Jinja2."""

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )

    def render(
        self,
        report_data: dict[str, Any],
        template_name: str = "default.html.j2",
    ) -> str:
        """Render report data to an HTML string."""
        template = self._env.get_template(template_name)
        return template.render(
            report=report_data,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
