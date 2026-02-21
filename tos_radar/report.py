from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from tos_radar.change_classifier import is_suspicious_changed
from tos_radar.models import RunEntry

_REPORT_DATA_MARKER = "__REPORT_DATA_JSON__"


def write_report(entries: list[RunEntry], mode: str, tenant_id: str) -> Path:
    reports_dir = Path("reports") / tenant_id
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = reports_dir / f"report-{ts}.html"
    report_path.write_text(_render(entries, mode), encoding="utf-8")
    return report_path


def find_latest_report(tenant_id: str) -> Path | None:
    reports_dir = Path("reports") / tenant_id
    if not reports_dir.exists():
        return None
    reports = sorted(reports_dir.glob("report-*.html"))
    return reports[-1] if reports else None


def _render(entries: list[RunEntry], mode: str) -> str:
    template = _load_template()
    payload = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "items": [_entry_to_item(entry) for entry in entries],
    }
    return template.replace(_REPORT_DATA_MARKER, json.dumps(payload, ensure_ascii=False))


def _entry_to_item(entry: RunEntry) -> dict[str, object]:
    suspicious = (
        entry.status.value == "CHANGED"
        and entry.change_level is not None
        and entry.change_ratio is not None
        and is_suspicious_changed(entry.change_level, entry.change_ratio, entry.text_length)
    )
    return {
        "domain": entry.domain,
        "url": entry.url,
        "status": entry.status.value,
        "source": entry.source_type.value if entry.source_type else None,
        "duration": f"{entry.duration_sec:.2f}s",
        "error_code": entry.error_code.value if entry.error_code else None,
        "error": entry.error,
        "diff_html": entry.diff_html,
        "text_length": entry.text_length,
        "change_level": entry.change_level.value if entry.change_level else None,
        "change_ratio": entry.change_ratio,
        "suspicious": suspicious,
    }


def _load_template() -> str:
    local_template = Path("report.html")
    package_root_template = Path(__file__).resolve().parents[1] / "report.html"
    template_path = local_template if local_template.exists() else package_root_template
    template = template_path.read_text(encoding="utf-8")
    if _REPORT_DATA_MARKER not in template:
        msg = f"Report template is missing marker {_REPORT_DATA_MARKER}: {template_path}"
        raise ValueError(msg)
    return template
