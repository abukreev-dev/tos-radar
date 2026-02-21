from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from tos_radar.models import RunEntry


def write_report(entries: list[RunEntry], mode: str) -> Path:
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = reports_dir / f"report-{ts}.html"
    report_path.write_text(_render(entries, mode), encoding="utf-8")
    return report_path


def find_latest_report() -> Path | None:
    reports_dir = Path("reports")
    if not reports_dir.exists():
        return None
    reports = sorted(reports_dir.glob("report-*.html"))
    return reports[-1] if reports else None


def _render(entries: list[RunEntry], mode: str) -> str:
    rows = []
    for entry in entries:
        diff_block = entry.diff_html or ""
        error = escape(entry.error or "")
        error_code = entry.error_code.value if entry.error_code else "-"
        source = entry.source_type.value if entry.source_type else "-"
        rows.append(
            f"""
            <section class="card status-{entry.status.value.lower()}">
              <div class="meta">
                <div><b>domain</b>: {escape(entry.domain)}</div>
                <div><b>url</b>: <a href="{escape(entry.url)}">{escape(entry.url)}</a></div>
                <div><b>status</b>: {entry.status.value}</div>
                <div><b>source</b>: {source}</div>
                <div><b>duration</b>: {entry.duration_sec:.2f}s</div>
                <div><b>error_code</b>: {error_code}</div>
                <div><b>error</b>: {error or "-"}</div>
              </div>
              <div class="diff">{diff_block}</div>
            </section>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TOS Radar Report</title>
  <style>
    body {{ font-family: 'Courier New', monospace; background: #f7f4ef; color: #222; margin: 0; }}
    header {{ background: #1f4e5f; color: #fff; padding: 16px 20px; }}
    main {{ padding: 16px; display: grid; gap: 12px; }}
    .card {{ background: #fff; border: 1px solid #ddd; border-left: 6px solid #999; padding: 12px; }}
    .status-changed {{ border-left-color: #b11f1f; }}
    .status-unchanged {{ border-left-color: #207531; }}
    .status-failed {{ border-left-color: #7a4d00; }}
    .status-new {{ border-left-color: #0e4b8a; }}
    .meta {{ display: grid; gap: 4px; margin-bottom: 8px; }}
    table.diff {{ width: 100%; font-size: 12px; border-collapse: collapse; }}
    .diff_header {{ background: #e7e7e7; }}
    td.diff_next {{ display: none; }}
    td.diff_add {{ background: #d9f7de; }}
    td.diff_chg {{ background: #fff5c7; }}
    td.diff_sub {{ background: #ffd9d9; }}
  </style>
</head>
<body>
  <header>
    <h1>TOS Radar Report</h1>
    <div>Generated: {datetime.now().isoformat(timespec="seconds")}</div>
    <div>Mode: {escape(mode)}</div>
  </header>
  <main>
    {''.join(rows)}
  </main>
</body>
</html>"""
