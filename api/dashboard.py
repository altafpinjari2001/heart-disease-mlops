"""Server-rendered live monitoring page (no JS, refreshes every 5 s).

Prometheus + Grafana is the main monitoring stack; this page is a
zero-dependency fallback that works wherever the container runs.
"""

from html import escape


def _card(title, value, sub=""):
    return (f'<div class="card"><div class="k">{escape(title)}</div>'
            f'<div class="v">{escape(str(value))}</div>'
            f'<div class="s">{escape(sub)}</div></div>')


def _bars(values, labels, color):
    peak = max(values) or 1
    rows = []
    for lab, v in zip(labels, values):
        width = 100 * v / peak
        rows.append(
            f'<div class="row"><span class="lab">{escape(lab)}</span>'
            f'<span class="bar"><i style="width:{width:.1f}%;'
            f'background:{color}"></i></span><span class="n">{v}</span></div>')
    return "".join(rows)


def render(summary: dict, meta: dict, refresh: int = 5) -> str:
    lat = summary["latency_ms"]
    labels = summary["label_counts"]
    total = sum(labels.values())
    pos_share = labels.get("heart_disease", 0) / total if total else 0
    status_rows = _bars(list(summary["status_counts"].values()) or [0],
                        list(summary["status_counts"]) or ["-"], "#1f6f8b")
    risk_rows = _bars(summary["risk_histogram"],
                      [f"{i / 10:.1f}-{(i + 1) / 10:.1f}" for i in range(10)],
                      "#e8505b")
    recent = "".join(
        f"<tr><td>{p['ts']}</td><td>{escape(p['request_id'])}</td>"
        f"<td>{escape(p['label'])}</td><td>{p['risk']:.3f}</td></tr>"
        for p in summary["recent"]) or '<tr><td colspan="4">no traffic yet' \
                                       '</td></tr>'
    cards = "".join([
        _card("Uptime", f"{summary['uptime_s']} s"),
        _card("/predict requests", summary["window_requests"],
              "rolling window"),
        _card("Error rate (4xx/5xx)", f"{summary['error_rate']:.1%}"),
        _card("Latency p50 / p95", f"{lat['p50']} / {lat['p95']} ms"),
        _card("Positive share", f"{pos_share:.0%}",
              f"{total} predictions"),
        _card("Model", meta.get("family", "?"),
              f"v{meta.get('model_version', '?')}"),
    ])
    refresh_tag = (f'<meta http-equiv="refresh" content="{refresh}">'
                   if refresh > 0 else "")
    return f"""<!doctype html><html><head><meta charset="utf-8">
{refresh_tag}<title>Heart Risk API monitor</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;background:#f5f7f9;
color:#1d2b36}}h1{{margin:0 0 4px;font-size:22px}}.muted{{color:#6b7c88}}
.grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:18px 0}}
.card{{background:#fff;border-radius:8px;padding:14px;
box-shadow:0 1px 3px #0001}}.k{{font-size:12px;color:#6b7c88}}
.v{{font-size:22px;font-weight:600;margin-top:4px}}.s{{font-size:11px;
color:#99a8b2}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.panel{{background:#fff;border-radius:8px;padding:14px;
box-shadow:0 1px 3px #0001}}.row{{display:flex;align-items:center;gap:8px;
margin:4px 0;font-size:13px}}.lab{{width:70px}}.bar{{flex:1;background:#eef2f4;
height:14px;border-radius:3px}}.bar i{{display:block;height:100%;
border-radius:3px}}.n{{width:40px;text-align:right}}table{{width:100%;
border-collapse:collapse;font-size:13px}}td,th{{padding:5px;text-align:left;
border-bottom:1px solid #eef2f4}}
</style></head><body>
<h1>Heart Disease Risk API &mdash; live monitor</h1>
<div class="muted">Auto-refresh: {refresh or "off"} s &middot; Prometheus metrics at
<code>/metrics</code> &middot; JSON at <code>/monitor/summary</code></div>
<div class="grid">{cards}</div>
<div class="two">
<div class="panel"><b>HTTP status of /predict calls</b>{status_rows}</div>
<div class="panel"><b>Predicted risk distribution</b>{risk_rows}</div>
</div>
<div class="panel" style="margin-top:12px"><b>Latest predictions</b>
<table><tr><th>time</th><th>request id</th><th>label</th><th>P(disease)</th>
</tr>{recent}</table></div>
</body></html>"""
