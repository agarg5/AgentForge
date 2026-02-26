"""Generate an HTML eval report from a JSON results file.

Usage:
    python agent/evals/generate_report.py agent/evals/results/20260225_192618.json
    python agent/evals/generate_report.py  # auto-picks latest file in results/
"""

from __future__ import annotations

import json
import sys
import webbrowser
from collections import defaultdict
from pathlib import Path


def load_results(path: str | None = None) -> tuple[dict, Path]:
    if path:
        p = Path(path)
    else:
        results_dir = Path(__file__).resolve().parent / "results"
        files = sorted(results_dir.glob("*.json"))
        if not files:
            print("No result files found in evals/results/")
            sys.exit(1)
        p = files[-1]
        print(f"Using latest: {p.name}")

    with open(p) as f:
        return json.load(f), p


def bar_html(pct: float, label: str = "", width: int = 200) -> str:
    if pct >= 90:
        color = "#22c55e"
    elif pct >= 80:
        color = "#eab308"
    else:
        color = "#ef4444"
    fill = max(1, int(pct / 100 * width))
    return (
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'<div style="width:{width}px;height:20px;background:#e5e7eb;border-radius:4px;overflow:hidden">'
        f'<div style="width:{fill}px;height:100%;background:{color};border-radius:4px"></div>'
        f'</div>'
        f'<span style="font-weight:600;min-width:50px">{pct:.1f}%</span>'
        f'<span style="color:#6b7280;font-size:13px">{label}</span>'
        f'</div>'
    )


def status_badge(passed: bool) -> str:
    if passed:
        return '<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:9999px;font-size:12px;font-weight:600">PASS</span>'
    return '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:9999px;font-size:12px;font-weight:600">FAIL</span>'


def generate_html(data: dict) -> str:
    cases = data["cases"]
    scorers = data["scorers"]
    latency = data["latency"]
    total = data["total_cases"]
    elapsed = data["elapsed_seconds"]
    errors = data["errors"]

    # Compute overall pass rate (case passes if all scores > 0)
    pass_count = 0
    for c in cases:
        if not c["error"] and all(s["score"] > 0 for s in c["scores"]):
            pass_count += 1
    overall_pct = pass_count / total * 100 if total else 0

    # Category breakdown
    cat_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "passed": 0, "latencies": []})
    for c in cases:
        cat = c["category"]
        cat_stats[cat]["total"] += 1
        all_pass = not c["error"] and all(s["score"] > 0 for s in c["scores"])
        if all_pass:
            cat_stats[cat]["passed"] += 1
        if not c["error"]:
            cat_stats[cat]["latencies"].append(c["duration_s"])

    # Source breakdown
    source_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "passed": 0})
    for c in cases:
        src = c["source"]
        source_stats[src]["total"] += 1
        if not c["error"] and all(s["score"] > 0 for s in c["scores"]):
            source_stats[src]["passed"] += 1

    # Failures
    failures = []
    for c in cases:
        for s in c["scores"]:
            if s["score"] == 0:
                failures.append(c)
                break

    # Performance targets
    tools_pct = scorers.get("ToolsMatch", {}).get("score", 0)
    halluc_pct = scorers.get("NoHallucination", {}).get("score", 0)
    targets = [
        ("Eval pass rate", overall_pct, 80, "%"),
        ("Tool success rate", tools_pct, 95, "%"),
        ("Hallucination rate", 100 - halluc_pct, 5, "% (lower is better)"),
        ("Avg latency", latency["avg_seconds"], 15, "s"),
        ("Max latency", latency["max_seconds"], 60, "s"),
    ]

    ts = data.get("timestamp", "unknown")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AgentForge Eval Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f9fafb; color: #111827; padding: 24px; max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 28px; margin-bottom: 4px; }}
  h2 {{ font-size: 20px; margin: 32px 0 12px; border-bottom: 2px solid #e5e7eb; padding-bottom: 6px; }}
  h3 {{ font-size: 16px; margin: 20px 0 8px; }}
  .meta {{ color: #6b7280; font-size: 14px; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .card .label {{ font-size: 13px; color: #6b7280; margin-bottom: 4px; }}
  .card .value {{ font-size: 28px; font-weight: 700; }}
  .card .value.green {{ color: #16a34a; }}
  .card .value.yellow {{ color: #ca8a04; }}
  .card .value.red {{ color: #dc2626; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 16px; }}
  th, td {{ text-align: left; padding: 10px 14px; border-bottom: 1px solid #f3f4f6; font-size: 14px; }}
  th {{ background: #f9fafb; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f9fafb; }}
  .reason {{ color: #6b7280; font-size: 13px; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .query {{ max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .target-met {{ color: #16a34a; font-weight: 600; }}
  .target-miss {{ color: #dc2626; font-weight: 600; }}
  details {{ margin-bottom: 8px; }}
  details summary {{ cursor: pointer; padding: 8px 0; font-weight: 500; }}
  .footer {{ margin-top: 40px; text-align: center; color: #9ca3af; font-size: 13px; }}
</style>
</head>
<body>

<h1>AgentForge Eval Report</h1>
<div class="meta">{ts} &middot; {total} cases &middot; {elapsed:.0f}s runtime &middot; {data.get('agent_url', '')}</div>

<div class="grid">
  <div class="card">
    <div class="label">Overall Pass Rate</div>
    <div class="value {'green' if overall_pct >= 80 else 'yellow' if overall_pct >= 60 else 'red'}">{overall_pct:.1f}%</div>
  </div>
  <div class="card">
    <div class="label">Cases Passed</div>
    <div class="value">{pass_count} / {total}</div>
  </div>
  <div class="card">
    <div class="label">Avg Latency</div>
    <div class="value {'green' if latency['avg_seconds'] < 15 else 'red'}">{latency['avg_seconds']:.1f}s</div>
  </div>
  <div class="card">
    <div class="label">Errors</div>
    <div class="value {'green' if errors == 0 else 'red'}">{errors}</div>
  </div>
</div>

<h2>Scorer Breakdown</h2>
<table>
  <tr><th>Scorer</th><th>Score</th><th>Cases</th></tr>
"""

    for name, info in sorted(scorers.items()):
        html += f'  <tr><td>{name}</td><td>{bar_html(info["score"])}</td><td>{info["cases"]}</td></tr>\n'

    html += """</table>

<h2>Performance Targets</h2>
<table>
  <tr><th>Metric</th><th>Actual</th><th>Target</th><th>Status</th></tr>
"""

    for label, actual, target, unit in targets:
        if "lower" in unit:
            met = actual <= target
            actual_str = f"{actual:.1f}{unit.split(' ')[0]}"
            target_str = f"<{target}{unit.split(' ')[0]}"
        elif unit == "s":
            met = actual <= target
            actual_str = f"{actual:.1f}s"
            target_str = f"<{target}s"
        else:
            met = actual >= target
            actual_str = f"{actual:.1f}%"
            target_str = f">{target}%"
        css = "target-met" if met else "target-miss"
        icon = "&#10003;" if met else "&#10007;"
        html += f'  <tr><td>{label}</td><td class="{css}">{actual_str}</td><td>{target_str}</td><td class="{css}">{icon}</td></tr>\n'

    html += """</table>

<h2>By Dataset</h2>
<table>
  <tr><th>Dataset</th><th>Pass Rate</th><th>Passed</th><th>Total</th></tr>
"""

    for src, info in sorted(source_stats.items()):
        pct = info["passed"] / info["total"] * 100 if info["total"] else 0
        html += f'  <tr><td>{src}</td><td>{bar_html(pct)}</td><td>{info["passed"]}</td><td>{info["total"]}</td></tr>\n'

    html += """</table>

<h2>By Category</h2>
<table>
  <tr><th>Category</th><th>Pass Rate</th><th>Passed</th><th>Total</th><th>Avg Latency</th></tr>
"""

    for cat, info in sorted(cat_stats.items(), key=lambda x: x[0]):
        pct = info["passed"] / info["total"] * 100 if info["total"] else 0
        avg_lat = sum(info["latencies"]) / len(info["latencies"]) if info["latencies"] else 0
        html += f'  <tr><td>{cat}</td><td>{bar_html(pct)}</td><td>{info["passed"]}</td><td>{info["total"]}</td><td>{avg_lat:.1f}s</td></tr>\n'

    html += """</table>
"""

    if failures:
        html += f"""
<h2>Failures ({len(failures)})</h2>
<table>
  <tr><th>Case</th><th>Category</th><th>Query</th><th>Failed Scorer</th><th>Reason</th></tr>
"""
        for c in failures:
            failed_scores = [s for s in c["scores"] if s["score"] == 0]
            for s in failed_scores:
                q = c["query"][:60] + ("..." if len(c["query"]) > 60 else "")
                r = s["reason"][:80] + ("..." if len(s["reason"]) > 80 else "")
                html += f'  <tr><td>{c["case_id"]}</td><td>{c["category"]}</td><td class="query" title="{c["query"]}">{q}</td><td>{s["name"]}</td><td class="reason" title="{s["reason"]}">{r}</td></tr>\n'

        html += "</table>\n"

    # Expandable full results
    html += """
<h2>All Cases</h2>
<table>
  <tr><th>Case</th><th>Category</th><th>Status</th><th>Tools Used</th><th>Latency</th><th>Query</th></tr>
"""
    for c in sorted(cases, key=lambda x: x["case_id"]):
        all_pass = not c["error"] and all(s["score"] > 0 for s in c["scores"])
        badge = status_badge(all_pass)
        tools = ", ".join(c["tools_used"]) if c["tools_used"] else "—"
        q = c["query"][:50] + ("..." if len(c["query"]) > 50 else "")
        dur = f'{c["duration_s"]:.1f}s' if not c["error"] else "error"
        html += f'  <tr><td>{c["case_id"]}</td><td>{c["category"]}</td><td>{badge}</td><td>{tools}</td><td>{dur}</td><td class="query" title="{c["query"]}">{q}</td></tr>\n'

    html += """</table>

<div class="footer">Generated by AgentForge Eval Report</div>
</body>
</html>
"""
    return html


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    data, source_path = load_results(path)

    html = generate_html(data)

    out_path = source_path.with_suffix(".html")
    with open(out_path, "w") as f:
        f.write(html)

    print(f"Report: {out_path}")
    webbrowser.open(f"file://{out_path.resolve()}")


if __name__ == "__main__":
    main()
