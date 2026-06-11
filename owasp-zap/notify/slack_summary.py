#!/usr/bin/env python3
"""Post a ZAP scan summary to Slack.

Without this step the only artifact is a 30-day HTML report nobody opens, so a
weekly scan delivers little. This script distills the ZAP findings into a single
Slack message so they are seen.

Inputs (all via env):
  SLACK_BOT_TOKEN   Slack bot token with chat:write (repo secret IA_SLACK_BOT_TOKEN).
  SLACK_CHANNEL     Channel id or name to post to (repo secret ZAP_SLACK_CHANNEL_ID).
  ZAP_JSON          Path to ZAP traditional-json report (default report/zap-report.json).
  RUN_URL           Link back to the CI run (optional).

Missing/empty SLACK_BOT_TOKEN or SLACK_CHANNEL -> print the summary and exit 0
(so the step is a no-op rather than a failure when Slack isn't configured).
"""

import json
import os
import sys
import urllib.error
import urllib.request

RISK_NAMES = {"3": "High", "2": "Medium", "1": "Low", "0": "Informational"}


def load_json(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"warning: could not read {path}: {e}", file=sys.stderr)
        return None


def summarize_zap(report):
    """Return (counts_by_risk, sorted_alerts) from a ZAP traditional-json report."""
    counts = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    alerts = []
    if not report:
        return counts, alerts
    for site in report.get("site", []):
        for alert in site.get("alerts", []):
            risk = RISK_NAMES.get(str(alert.get("riskcode")), "Informational")
            n = int(alert.get("count", 0) or 0)
            counts[risk] += n
            alerts.append((risk, alert.get("alert", "?"), n))
    order = {"High": 0, "Medium": 1, "Low": 2, "Informational": 3}
    alerts.sort(key=lambda a: (order[a[0]], -a[2]))
    return counts, alerts


def build_message(zap, run_url):
    counts, alerts = summarize_zap(zap)

    # Overall status emoji: red if High alerts, yellow if Medium, else green.
    if counts["High"]:
        emoji = ":red_circle:"
    elif counts["Medium"]:
        emoji = ":large_yellow_circle:"
    else:
        emoji = ":large_green_circle:"

    lines = [f"{emoji} *ZAP security scan — test environment*"]
    lines.append(
        f"*Alerts:* {counts['High']} High · {counts['Medium']} Medium · "
        f"{counts['Low']} Low · {counts['Informational']} Info"
    )
    # Show the High/Medium alert types (the ones worth acting on).
    notable = [a for a in alerts if a[0] in ("High", "Medium")]
    if notable:
        lines.append("*Notable:*")
        for risk, name, n in notable[:8]:
            lines.append(f"   • {risk}: {name} ({n})")

    if run_url:
        lines.append(f"<{run_url}|View run & full report>")
    return "\n".join(lines)


def post_to_slack(token, channel, text):
    payload = json.dumps({"channel": channel, "text": text, "unfurl_links": False}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError(f"Slack API error: {body.get('error')}")


def main():
    zap = load_json(os.environ.get("ZAP_JSON", "report/zap-report.json"))
    run_url = os.environ.get("RUN_URL", "")
    text = build_message(zap, run_url)

    print(text)

    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL")
    if not token or not channel:
        print("\nSLACK_BOT_TOKEN / SLACK_CHANNEL not set — skipping Slack post.", file=sys.stderr)
        return 0
    try:
        post_to_slack(token, channel, text)
        print("\nPosted summary to Slack.", file=sys.stderr)
    except (urllib.error.URLError, RuntimeError) as e:
        # Don't fail the build just because notification failed; the exitStatus
        # job already gates the build on real findings.
        print(f"::warning::Failed to post ZAP summary to Slack: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
