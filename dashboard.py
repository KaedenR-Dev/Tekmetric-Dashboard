"""
Complete Auto Repair - Performance Dashboard
Local browser dashboard. No additional Python packages required.

Run:
    python dashboard.py

Then open:
    http://localhost:8000
"""

import json
import threading
import time
import traceback
from auth import authenticate
from auth import create_session
from auth import destroy_session
from auth import validate_session
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from analytics import (
    get_revenue,
    get_monthly_trends,
    get_daily_trends,
    get_technician_metrics,
    get_technician_trend,
    get_advisor_metrics,
    get_period_comparison,
    get_job_category_metrics,
    get_missed_revenue,
)
from sync import run_full_sync


HOST = "127.0.0.1"
PORT = 8000

# How often to automatically pull fresh data from Tekmetric in the
# background, in minutes. Set to 0 to disable automatic syncing and
# rely on the "Sync Now" button only.
AUTO_SYNC_INTERVAL_MINUTES = 30


# ==================================================================
# BACKGROUND SYNC STATE
# ==================================================================
#
# A sync can take a while (it talks to Tekmetric for every repair
# order and job), so it always runs on a background thread rather
# than blocking a request. SYNC_STATE is the one place the dashboard
# and the scheduler both read/write, guarded by SYNC_LOCK.

SYNC_STATE = {
    "status": "idle",          # "idle" | "running" | "error"
    "last_started_at": None,
    "last_finished_at": None,
    "last_result": None,       # stats dict from run_full_sync()
    "last_error": None,
}

SYNC_LOCK = threading.Lock()


def _run_sync_in_background():
    """Run a full sync and record the outcome in SYNC_STATE."""

    with SYNC_LOCK:
        if SYNC_STATE["status"] == "running":
            return False
        SYNC_STATE["status"] = "running"
        SYNC_STATE["last_started_at"] = datetime.now().isoformat()

    def worker():
        try:
            result = run_full_sync()
            with SYNC_LOCK:
                SYNC_STATE["status"] = "idle"
                SYNC_STATE["last_result"] = result
                SYNC_STATE["last_error"] = None
                SYNC_STATE["last_finished_at"] = datetime.now().isoformat()
        except Exception:
            print("[Sync] FAILED:")
            print(traceback.format_exc())
            with SYNC_LOCK:
                SYNC_STATE["status"] = "error"
                SYNC_STATE["last_error"] = traceback.format_exc()
                SYNC_STATE["last_finished_at"] = datetime.now().isoformat()

    threading.Thread(target=worker, daemon=True).start()
    return True


def _auto_sync_loop():
    """Periodically trigger a background sync, if enabled."""

    if not AUTO_SYNC_INTERVAL_MINUTES:
        return

    while True:
        _run_sync_in_background()
        time.sleep(AUTO_SYNC_INTERVAL_MINUTES * 60)


LOGIN_HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Complete Auto Repair - Analytics Platform - Login</title>

<style>

body {
    margin: 0;
    height: 100vh;

    display: flex;
    justify-content: center;
    align-items: center;

    background: #0b1016;

    font-family: Inter, Arial, sans-serif;
}

.login-box {
    width: 360px;

    padding: 40px;

    background: #121922;

    border: 1px solid #263342;

    border-radius: 12px;
}

h1 {
    margin-top: 0;

    color: white;

    text-align: center;
}

input {
    width: 100%;

    margin-top: 12px;

    padding: 12px;

    box-sizing: border-box;

    border: 1px solid #263342;

    border-radius: 8px;

    background: #17212c;

    color: white;
}

button {
    width: 100%;

    margin-top: 16px;

    padding: 12px;

    border: none;

    border-radius: 8px;

    cursor: pointer;
}

.error {
    color: #ff6b6b;

    margin-top: 12px;

    text-align: center;
}

</style>
</head>

<body>

<div class="login-box">

<h1>Complete Auto Repair - Analytics Platform</h1>

<form method="POST" action="/login">

<input
    type="text"
    name="username"
    placeholder="Username"
    required
>

<input
    type="password"
    name="password"
    placeholder="Password"
    required
>

<button type="submit">

    Sign In

</button>

</form>

{error}

</div>

</body>
</html>
"""


HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Complete Auto Repair — Shop Performance</title>
<style>
:root {
    --bg: #0b1016;
    --panel: #121922;
    --panel2: #17212c;
    --border: #263342;
    --text: #eef3f7;
    --muted: #8e9aaa;
    --accent: #4da3ff;
    --good: #45d483;
    --bad: #ff6b6b;
    --warn: #ffc857;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
header {
    padding: 24px 32px 18px;
    border-bottom: 1px solid var(--border);
    background: #0d141c;
}
.header-row {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:20px;
}
h1 { margin:0; font-size:24px; letter-spacing:.2px; }
.subtitle { color:var(--muted); margin-top:5px; font-size:13px; }
.controls {
    display:flex;
    flex-wrap:wrap;
    gap:10px;
    padding:18px 32px;
    border-bottom:1px solid var(--border);
    background:#0d141c;
}
select, input, button {
    background:var(--panel);
    color:var(--text);
    border:1px solid var(--border);
    border-radius:8px;
    padding:9px 12px;
    font:inherit;
}
button { cursor:pointer; }
button:hover { border-color:#4b6178; }
main { padding:24px 32px 40px; max-width:1500px; margin:auto; }
.section-title {
    margin:26px 0 12px;
    color:#cdd7e1;
    font-size:13px;
    text-transform:uppercase;
    letter-spacing:1.1px;
}
.kpis {
    display:grid;
    grid-template-columns:repeat(4, minmax(150px,1fr));
    gap:14px;
}
.card {
    background:var(--panel);
    border:1px solid var(--border);
    border-radius:12px;
    padding:18px;
}
.kpi-label { color:var(--muted); font-size:12px; }
.kpi-value { font-size:26px; font-weight:700; margin-top:7px; }
.kpi-change { font-size:12px; margin-top:7px; }
.good { color:var(--good); }
.bad { color:var(--bad); }
.warn { color:var(--warn); }
.muted { color:var(--muted); }
.grid2 {
    display:grid;
    grid-template-columns:1.65fr 1fr;
    gap:16px;
}
.chart-wrap { height:340px; position:relative; }
svg { width:100%; height:100%; overflow:visible; }
.table-card { padding:0; overflow:hidden; }
table { width:100%; border-collapse:collapse; }
th, td {
    text-align:left;
    padding:12px 14px;
    border-bottom:1px solid var(--border);
    font-size:13px;
}
th { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.7px; }
tr:last-child td { border-bottom:0; }
td.num, th.num { text-align:right; }
.bar-bg {
    width:120px; height:7px; background:#263342; border-radius:99px; overflow:hidden;
    display:inline-block; vertical-align:middle; margin-left:8px;
}
.bar { height:100%; background:var(--accent); border-radius:99px; }
.badge {
    display:inline-block;
    padding:4px 7px;
    border-radius:6px;
    font-size:11px;
    background:#1c2a38;
    color:#b9c8d7;
}
.loading { opacity:.65; }

.nav {
    display:flex;
    gap:6px;
    padding:10px 32px;
    border-bottom:1px solid var(--border);
    background:#0a1118;
}
.nav button {
    border:1px solid transparent;
    background:transparent;
    color:var(--muted);
    padding:9px 13px;
}
.nav button:hover {
    color:var(--text);
    border-color:var(--border);
}
.nav button.active {
    color:var(--text);
    background:var(--panel);
    border-color:var(--border);
}
.page { display:none; }
.page.active { display:block; }
@media (max-width:600px) {
    .nav { padding-left:16px; padding-right:16px; overflow-x:auto; }
    .nav button { white-space:nowrap; }
}

.tech-row { cursor:pointer; transition:background .12s ease; }
.tech-row:hover { background:#172330; }
.tech-row.selected { background:#1a2b3b; box-shadow:inset 3px 0 0 var(--accent); }
.scorecard {
    margin-top:14px;
    background:var(--panel);
    border:1px solid var(--border);
    border-radius:12px;
    padding:18px;
}
.scorecard-header {
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:16px;
    margin-bottom:16px;
}
.scorecard-name { font-size:20px; font-weight:700; }
.scorecard-sub { color:var(--muted); font-size:12px; margin-top:4px; }
.scorecard-status {
    padding:6px 9px;
    border-radius:7px;
    font-size:11px;
    font-weight:700;
    white-space:nowrap;
}
.scorecard-status.good { color:var(--good); background:rgba(69,212,131,.10); }
.scorecard-status.warn { color:var(--warn); background:rgba(255,200,87,.10); }
.scorecard-status.bad { color:var(--bad); background:rgba(255,107,107,.10); }
.scorecard-grid {
    display:grid;
    grid-template-columns:repeat(6,minmax(120px,1fr));
    gap:10px;
}
.score-item {
    background:var(--panel2);
    border:1px solid var(--border);
    border-radius:9px;
    padding:12px;
}
.score-label { color:var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:.6px; }
.score-value { font-size:19px; font-weight:700; margin-top:5px; }
.score-note { color:var(--muted); font-size:10px; margin-top:3px; }
.scorecard-explanation {
    margin-top:14px;
    padding-top:12px;
    border-top:1px solid var(--border);
    color:var(--muted);
    font-size:11px;
    line-height:1.5;
}
@media (max-width:1100px) {
    .scorecard-grid { grid-template-columns:repeat(3,1fr); }
}
@media (max-width:600px) {
    .scorecard-grid { grid-template-columns:repeat(2,1fr); }
}

.alert-grid {
    display:grid;
    grid-template-columns:repeat(3, minmax(220px,1fr));
    gap:14px;
    margin-bottom:2px;
}
.alert {
    position:relative;
    min-height:92px;
    background:linear-gradient(135deg,var(--panel),var(--panel2));
    border:1px solid var(--border);
    border-radius:12px;
    padding:16px 18px 15px 20px;
    box-shadow:0 6px 18px rgba(0,0,0,.12);
    overflow:hidden;
}
.alert::before {
    content:"";
    position:absolute;
    left:0;
    top:0;
    bottom:0;
    width:5px;
    background:var(--good);
}
.alert.warn::before { background:var(--warn); }
.alert.bad::before { background:var(--bad); }
.alert-title {
    font-weight:750;
    font-size:13px;
    margin-bottom:6px;
}
.alert-text {
    color:var(--muted);
    font-size:12px;
    line-height:1.5;
}
.alert {
    background:var(--panel);
    border:1px solid var(--border);
    border-left:4px solid var(--good);
    border-radius:10px;
    padding:14px 16px;
}
.alert.warn { border-left-color:var(--warn); }
.alert.bad { border-left-color:var(--bad); }
.alert-title { font-weight:700; font-size:13px; margin-bottom:5px; }
.alert-text { color:var(--muted); font-size:12px; line-height:1.45; }
.alert.good .alert-title { color:var(--good); }
.alert.warn .alert-title { color:var(--warn); }
.alert.bad .alert-title { color:var(--bad); }

.management-grid {
    display:grid;
    grid-template-columns:repeat(4, minmax(150px,1fr));
    gap:12px;
}
.mini-card {
    background:var(--panel);
    border:1px solid var(--border);
    border-radius:10px;
    padding:14px 16px;
}
.mini-label { color:var(--muted); font-size:11px; }
.mini-value { font-size:20px; font-weight:700; margin-top:5px; }
.mini-sub { color:var(--muted); font-size:11px; margin-top:3px; }

@media (max-width: 900px) {
    .alert-grid, .management-grid { grid-template-columns:1fr; }
}
.footer {
    color:var(--muted); font-size:11px; padding-top:24px; text-align:right;
}
@media (max-width:1200px) {
    .kpis { grid-template-columns:repeat(4,1fr); }
}
@media (max-width:1000px) {
    .kpis { grid-template-columns:repeat(2,1fr); }
    .grid2 { grid-template-columns:1fr; }
}
@media (max-width:600px) {
    header, main, .controls { padding-left:16px; padding-right:16px; }
    .kpis { grid-template-columns:1fr; }
}
</style>
</head>
<body>
<header>
  <div class="header-row">
    <div>
      <h1>Complete Auto Repair</h1>
      <div class="subtitle">Shop Overview</div>
    </div>
    <div>
      <div id="updated" class="subtitle" style="text-align:right">Loading...</div>
      <div id="syncStatus" class="subtitle" style="text-align:right;margin-top:3px">—</div>
    </div>
  </div>
</header>

<div class="controls">
  <select id="period">
    <option value="7">Last 7 Days</option>
    <option value="30" selected>Last 30 Days</option>
    <option value="90">Last 90 Days</option>
    <option value="365">Last 12 Months</option>
  </select>
  <select id="basis">
    <option value="revenue" selected>Revenue — Posted</option>
    <option value="production">Production — Completed</option>
    <option value="activity">Activity — Created</option>
  </select>
  <button onclick="loadDashboard()">Refresh</button>
  <button id="syncButton" onclick="triggerSync()">Sync from Tekmetric</button>
</div>

<nav class="nav" aria-label="Dashboard sections">
  <button id="navOverview" class="active" onclick="showPage('overview')">Overview</button>
  <button id="navProfitCenters" onclick="showPage('profitcenters')">Profit Centers</button>
  <button id="navMissedRevenue" onclick="showPage('missedrevenue')">Missed Revenue</button>
  <button id="navTechnicians" onclick="showPage('technicians')">Technicians</button>
  <button id="navFinancial" onclick="showPage('financial')">Advisors &amp; Financial</button>
</nav>

<main id="app">
  <section id="pageOverview" class="page active">
  <div class="section-title" style="margin-top:0">Management Alerts</div>
  <div class="alert-grid" id="alerts"></div>

  <div class="section-title">Executive Overview</div>
  <div class="kpis">
    <div class="card"><div class="kpi-label">Total Sales</div><div id="sales" class="kpi-value">—</div><div id="salesChange" class="kpi-change muted">—</div></div>
    <div class="card"><div class="kpi-label">Repair Orders</div><div id="ros" class="kpi-value">—</div><div id="rosChange" class="kpi-change muted">—</div></div>
    <div class="card"><div class="kpi-label">Average RO</div><div id="avgRo" class="kpi-value">—</div><div id="avgRoChange" class="kpi-change muted">—</div></div>
    <div class="card"><div class="kpi-label">Labor Sales</div><div id="labor" class="kpi-value">—</div><div class="kpi-change muted">—</div></div>
    <div class="card"><div class="kpi-label">Discounts</div><div id="discounts" class="kpi-value">—</div><div id="discountChange" class="kpi-change muted">—</div></div>
    <div class="card"><div class="kpi-label">Discount Rate</div><div id="discountRate" class="kpi-value">—</div><div class="kpi-change muted">Discounts ÷ Labor + Parts</div></div>
    <div class="card"><div class="kpi-label">Billed Hours</div><div id="billedHours" class="kpi-value">—</div><div class="kpi-change muted">Selected period</div></div>
    <div class="card"><div class="kpi-label">Effective Labor Rate</div><div id="effectiveLaborRate" class="kpi-value">—</div><div class="kpi-change muted">Labor Sales ÷ Billed Hours</div></div>
  </div>


  <div class="section-title">Revenue Trend</div>
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
      <div>
        <div style="font-size:15px;font-weight:700">Posted Revenue</div>
        <div class="muted" style="font-size:11px;margin-top:3px">Daily revenue for the selected reporting period</div>
      </div>
      <div id="overviewChartTotal" style="font-size:16px;font-weight:700">—</div>
    </div>
    <div id="overviewChart" class="chart-wrap"></div>
  </div>


  </section>

  <section id="pageProfitCenters" class="page">
  <div class="section-title" style="margin-top:0">Profit Centers by Job Category</div>
  <div class="card table-card">
    <table>
      <thead>
        <tr>
          <th>Category</th>
          <th class="num">Jobs</th>
          <th class="num">Labor Revenue</th>
          <th class="num">Parts Revenue</th>
          <th class="num">Parts Margin</th>
          <th class="num">Parts Margin %</th>
          <th class="num">Net Revenue</th>
          <th class="num">% of Shop</th>
        </tr>
      </thead>
      <tbody id="profitCenterTable"></tbody>
    </table>
  </div>

  <div class="card" style="margin-top:14px">
    <div class="alert-text" style="font-size:12px; line-height:1.5">
      <strong style="color:var(--text)">Reading this table:</strong> Parts Margin is a real,
      cost-based margin — dollars sold minus what the parts actually cost. Labor Revenue is
      top-line only; technician labor cost isn't tracked yet, so there's no way to turn labor
      revenue into a true labor margin. Treat categories with a lot of labor revenue as
      "high volume," not necessarily "high profit," until that's in place.
    </div>
  </div>
  </section>

  <section id="pageMissedRevenue" class="page">
  <div class="section-title" style="margin-top:0">Recommended Work — Sold vs. Declined</div>
  <div class="kpis">
    <div class="card"><div class="kpi-label">Declined Revenue</div><div id="declinedValue" class="kpi-value">—</div><div id="declinedCount" class="kpi-change muted">—</div></div>
    <div class="card"><div class="kpi-label">Conversion Rate</div><div id="conversionRate" class="kpi-value">—</div><div class="kpi-change muted">Authorized ÷ Recommended</div></div>
    <div class="card"><div class="kpi-label">Recommended Revenue</div><div id="recommendedValue" class="kpi-value">—</div><div class="kpi-change muted">Authorized + Declined</div></div>
    <div class="card"><div class="kpi-label">Avg. Declined Job</div><div id="avgDeclinedValue" class="kpi-value">—</div><div class="kpi-change muted">Per declined job</div></div>
  </div>

  <div class="section-title">Conversion by Category</div>
  <div class="card table-card">
    <table>
      <thead>
        <tr>
          <th>Category</th>
          <th class="num">Authorized</th>
          <th class="num">Declined</th>
          <th class="num">Recommended</th>
          <th class="num">Conversion Rate</th>
        </tr>
      </thead>
      <tbody id="missedRevenueCategoryTable"></tbody>
    </table>
  </div>

  <div class="section-title">Top Declined Jobs — Follow-Up List</div>
  <div class="card table-card">
    <table>
      <thead>
        <tr>
          <th>RO #</th>
          <th>Job</th>
          <th>Category</th>
          <th>Technician</th>
          <th>Advisor</th>
          <th class="num">Quoted Value</th>
        </tr>
      </thead>
      <tbody id="missedRevenueJobTable"></tbody>
    </table>
  </div>

  <div class="card" style="margin-top:14px">
    <div class="alert-text" style="font-size:12px; line-height:1.5">
      <strong style="color:var(--text)">Reading this page:</strong> "Declined" means a job was never
      authorized by the customer — Tekmetric doesn't distinguish "said no" from "still deciding"
      beyond that flag. On the Revenue basis, this only counts jobs on repair orders that have
      already posted, so it reflects final decisions, not estimates still sitting open. Switching
      to Production or Activity basis will surface jobs on ROs that may still be pending.
    </div>
  </div>
  </section>

  <section id="pageTechnicians" class="page">
  <div class="section-title">Technician Performance</div>
  <div class="card table-card">
    <table>
      <thead><tr><th>Technician</th><th class="num">Jobs</th><th class="num">Hours</th><th class="num">Labor Sales</th><th class="num">Labor $ / Job</th><th class="num">Avg Hrs / Job</th><th class="num">Effective Labor $/Hr</th></tr></thead>
      <tbody id="techTable"></tbody>
    </table>
  </div>

  <div id="technicianScorecard" class="scorecard">
    <div class="scorecard-header">
      <div>
        <div class="scorecard-name" id="scorecardName">Select a technician</div>
        <div class="scorecard-sub" id="scorecardSub">Click a technician above to view their performance.</div>
      </div>
      <div id="scorecardStatus" class="scorecard-status good">—</div>
    </div>

    <div class="scorecard-grid">
      <div class="score-item">
        <div class="score-label">Jobs</div>
        <div class="score-value" id="scJobs">—</div>
        <div class="score-note">Selected period</div>
      </div>
      <div class="score-item">
        <div class="score-label">Billed Hours</div>
        <div class="score-value" id="scHours">—</div>
        <div class="score-note">Sold labor hours</div>
      </div>
      <div class="score-item">
        <div class="score-label">Labor Sales</div>
        <div class="score-value" id="scSales">—</div>
        <div class="score-note">Labor revenue</div>
      </div>
      <div class="score-item">
        <div class="score-label">Labor / RO</div>
        <div class="score-value" id="scLaborPerRo">—</div>
        <div class="score-note">Average labor revenue</div>
      </div>
      <div class="score-item">
        <div class="score-label">Hrs / RO</div>
        <div class="score-value" id="scHoursPerRo">—</div>
        <div class="score-note">Average sold hours</div>
      </div>
      <div class="score-item">
        <div class="score-label">Effective $ / Hr</div>
        <div class="score-value" id="scRate">—</div>
        <div class="score-note">Labor sales ÷ billed hours</div>
      </div>
    </div>

    <div class="scorecard-explanation" id="scorecardExplanation">
      The comparison to the shop rate is a management review indicator only. Job mix, diagnostics,
      inspections, alignment work, comebacks, workflow, and the type of work assigned can all affect
      these numbers.
    </div>

    <div style="margin-top:16px; padding-top:14px; border-top:1px solid var(--border)">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px">
        <div style="font-size:13px; font-weight:700">Weekly Trend — Effective $/Hr</div>
        <div id="scorecardTrendBadge" class="badge">—</div>
      </div>
      <div id="scorecardTrendChart" style="height:120px; position:relative"></div>
      <div class="score-note" style="margin-top:6px">This chart is used to identify whether a technician's performance is improving or declining over time.</div>
    </div>
  </div>


  </section>

  <section id="pageFinancial" class="page">
  <div class="section-title">Revenue Mix</div>
  <div class="card">
      <div class="kpi-label">Revenue Mix</div>
      <div style="margin-top:22px">
        <div class="kpi-label">Labor</div>
        <div style="font-size:22px;font-weight:700;margin-top:4px" id="laborMix">—</div>
        <div style="height:8px;background:#263342;border-radius:99px;margin:7px 0 18px"><div id="laborBar" class="bar"></div></div>
        <div class="kpi-label">Parts</div>
        <div style="font-size:22px;font-weight:700;margin-top:4px" id="partsMix">—</div>
        <div style="height:8px;background:#263342;border-radius:99px;margin:7px 0 18px"><div id="partsBar" class="bar"></div></div>
        <div class="kpi-label">Discounts vs Labor + Parts</div>
        <div style="font-size:22px;font-weight:700;margin-top:4px" id="discountMix">—</div>
      </div>
    </div>


  <div class="section-title">Management Snapshot</div>
  <div class="management-grid">
    <div class="mini-card">
      <div class="mini-label">Labor Sales / RO</div>
      <div class="mini-value" id="laborPerRo">—</div>
      <div class="mini-sub">Labor sales divided by posted ROs</div>
    </div>
    <div class="mini-card">
      <div class="mini-label">Billed Hours / RO</div>
      <div class="mini-value" id="hoursPerRo">—</div>
      <div class="mini-sub">Sold labor hours per RO</div>
    </div>
    <div class="mini-card">
      <div class="mini-label">Parts Sales / RO</div>
      <div class="mini-value" id="partsPerRo">—</div>
      <div class="mini-sub">Parts sales divided by posted ROs</div>
    </div>
    <div class="mini-card">
      <div class="mini-label">Labor Mix</div>
      <div class="mini-value" id="managementLaborMix">—</div>
      <div class="mini-sub">Labor as % of labor + parts</div>
    </div>
  </div>


  <div class="section-title">Service Advisor Performance</div>
  <div class="card table-card">
    <table>
      <thead><tr><th>Advisor</th><th class="num">ROs</th><th class="num">Sales</th><th class="num">Avg RO</th></tr></thead>
      <tbody id="advisorTable"></tbody>
    </table>
  </div>


  <div class="footer">Local dashboard • Data source: Tekmetric / local SQLite database • Billed hours and effective labor rate use technician labor lines</div>

  </section>
</main>

<script>
const money = n => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n || 0);
const number = n => new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(n || 0);
const decimal = n => new Intl.NumberFormat('en-US',{minimumFractionDigits:1,maximumFractionDigits:2}).format(n || 0);
const laborRate = (sales, hours) => hours ? sales / hours : 0;

let selectedTechnicianId = null;

function technicianStatus(rate, shopRate) {
  if (!rate || !shopRate) {
    return { cls:"warn", label:"Insufficient data", explanation:"Not enough billed-hour data to compare this technician with the shop rate." };
  }

  const ratio = rate / shopRate;

  if (ratio >= 1.00) {
    return {
      cls:"good",
      label:"At / above shop rate",
      explanation:`Effective labor rate is ${money(rate)}/hr versus ${money(shopRate)}/hr for the shop.`
    };
  }

  if (ratio >= 0.85) {
    return {
      cls:"warn",
      label:"Review relative to shop",
      explanation:`Effective labor rate is ${money(rate)}/hr versus ${money(shopRate)}/hr for the shop. Review job mix and sold hours before drawing conclusions.`
    };
  }

  return {
    cls:"bad",
    label:"Below shop rate",
    explanation:`Effective labor rate is ${money(rate)}/hr versus ${money(shopRate)}/hr for the shop. Review job mix, pricing, sold hours, and workflow.`
  };
}

function showTechnicianScorecard(technician, shopRate) {
  if (!technician) return;

  const jobs = Number(technician.jobs) || 0;
  const hours = Number(technician.labor_hours) || 0;
  const sales = Number(technician.labor_sales) || 0;
  const laborPerRo = jobs ? sales / jobs : 0;
  const hoursPerRo = jobs ? hours / jobs : 0;
  const rate = laborRate(sales, hours);
  const status = technicianStatus(rate, shopRate);

  const shopLaborSales = window.dashboardShopLaborSales || 0;
  const shopLaborShare = shopLaborSales ? (sales / shopLaborSales) * 100 : 0;

  document.getElementById("scorecardName").textContent =
    technician.technician_name || "Unknown Technician";

  document.getElementById("scorecardSub").textContent =
    `${number(jobs)} jobs • ${decimal(hours)} billed hours • ${money(sales)} labor sales`;

  const statusEl = document.getElementById("scorecardStatus");
  statusEl.className = `scorecard-status ${status.cls}`;
  statusEl.textContent = status.label;

  document.getElementById("scJobs").textContent = number(jobs);
  document.getElementById("scHours").textContent = decimal(hours);
  document.getElementById("scSales").textContent = money(sales);
  document.getElementById("scLaborPerRo").textContent = money(laborPerRo);
  document.getElementById("scHoursPerRo").textContent = decimal(hoursPerRo);
  document.getElementById("scRate").textContent = money(rate);

  document.getElementById("scorecardExplanation").textContent =
    `${status.explanation} This technician represents ${shopLaborShare.toFixed(1)}% of shop labor sales for the selected period. ` +
    `These figures are production indicators, not a standalone measure of technician quality. ` +
    `Job mix, diagnostics, inspections, alignment work, comebacks, workflow, and assigned work can all affect the results.`;

  document.querySelectorAll(".tech-row").forEach(row => {
    row.classList.toggle(
      "selected",
      row.dataset.technicianId === String(technician.technician_id ?? "")
    );
  });

  loadTechnicianTrend(technician.technician_id);
}


function drawTechnicianTrendChart(weeks) {
  const el = document.getElementById("scorecardTrendChart");

  const weeksWithHours = (weeks || []).filter(w => Number(w.labor_hours) > 0);

  if (!weeksWithHours.length) {
    el.innerHTML = '<div class="muted" style="padding-top:40px; text-align:center">Not enough billed-hour data for a trend view yet.</div>';
    return;
  }

  const w = 700, h = 120, left = 46, right = 14, top = 10, bottom = 22;
  const pw = w - left - right, ph = h - top - bottom;

  const rates = weeks.map(wk => Number(wk.effective_labor_rate) || 0);
  const max = Math.max(...rates, 1);
  const min = Math.min(...rates, 0);
  const range = Math.max(max - min, 1);

  const points = weeks.map((wk, i) => {
    const x = left + (i / Math.max(weeks.length - 1, 1)) * pw;
    const y = top + ph - ((Number(wk.effective_labor_rate) || 0) - min) / range * ph;
    return [x, y];
  });

  const path = points.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");

  const labels = weeks.map((wk, i) => {
    if (weeks.length > 8 && i % Math.ceil(weeks.length / 6) !== 0 && i !== weeks.length - 1) return "";
    const d = new Date(wk.week_start + "T00:00:00");
    const label = d.toLocaleDateString([], { month: "short", day: "numeric" });
    return `<text x="${points[i][0]}" y="${h - 6}" text-anchor="middle" fill="#8e9aaa" font-size="9">${label}</text>`;
  }).join("");

  // Dim any week with no billed hours — its "rate" is 0/undefined and
  // shouldn't be read as a real data point, just a gap in the line.
  const dots = points.map((p, i) => {
    const hasHours = Number(weeks[i].labor_hours) > 0;
    return `<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="#4da3ff" opacity="${hasHours ? 1 : 0.25}"/>`;
  }).join("");

  el.innerHTML = `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="width:100%; height:100%">
    <path d="${path}" fill="none" stroke="#4da3ff" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
    ${dots}
    ${labels}
  </svg>`;
}

async function loadTechnicianTrend(technicianId) {
  const chartEl = document.getElementById("scorecardTrendChart");
  const badgeEl = document.getElementById("scorecardTrendBadge");

  if (technicianId === null || technicianId === undefined || technicianId === "") {
    chartEl.innerHTML = '<div class="muted" style="padding-top:40px; text-align:center">No technician ID available for a trend view.</div>';
    badgeEl.textContent = "—";
    badgeEl.style.color = "";
    return;
  }

  const basis = document.getElementById("basis").value;
  chartEl.innerHTML = '<div class="muted" style="padding-top:40px; text-align:center">Loading trend…</div>';
  badgeEl.textContent = "—";
  badgeEl.style.color = "";

  try {
    const res = await fetch(
      `/api/technician-trend?technician_id=${encodeURIComponent(technicianId)}&basis=${basis}&weeks=12`
    );
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not load trend");

    drawTechnicianTrendChart(data.weeks);

    if (data.trend_direction === "up") {
      badgeEl.textContent = "▲ Trending up";
      badgeEl.style.color = "var(--good)";
    } else if (data.trend_direction === "down") {
      badgeEl.textContent = "▼ Trending down";
      badgeEl.style.color = "var(--bad)";
    } else if (data.trend_direction === "flat") {
      badgeEl.textContent = "→ Steady";
      badgeEl.style.color = "var(--muted)";
    } else {
      badgeEl.textContent = "Not enough data";
      badgeEl.style.color = "var(--muted)";
    }
  } catch (e) {
    chartEl.innerHTML = `<div class="muted" style="padding-top:40px; text-align:center">${e.message}</div>`;
    badgeEl.textContent = "—";
  }
}

function selectTechnicianByIndex(index) {
  const technician = (window.dashboardTechnicians || [])[index];
  if (technician) {
    selectedTechnicianId = technician.technician_id ?? technician.technician_name;
    showTechnicianScorecard(technician, window.dashboardEffectiveLaborRate || 0);
  }
}

function selectTechnician(technician) {
  selectedTechnicianId = technician.technician_id ?? technician.technician_name;
  showTechnicianScorecard(
    technician,
    window.dashboardEffectiveLaborRate || 0
  );
}

function changeText(v) {
  if (v === null || v === undefined) return "No prior-period comparison";
  const cls = v >= 0 ? "good" : "bad";
  const sign = v > 0 ? "+" : "";
  return `<span class="${cls}">${sign}${v.toFixed(1)}%</span> vs prior period`;
}

function drawChart(rows) {
  const el = document.getElementById("overviewChart");
  if (!rows.length) {
    el.innerHTML = '<div class="muted">No data for this period.</div>';
    return;
  }

  // total_sales is normalized server-side by analytics.py, so it can be
  // trusted directly here without re-deriving it from components.
  const w = 900, h = 330, left=58, right=20, top=20, bottom=42;
  const pw=w-left-right, ph=h-top-bottom;
  const max=Math.max(...rows.map(r=>Number(r.total_sales)||0),1);
  const points=rows.map((r,i)=>{
    const value = Number(r.total_sales) || 0;
    const x=left+(i/(Math.max(rows.length-1,1)))*pw;
    const y=top+ph-(value/max)*ph;
    return [x,y];
  });
  const path=points.map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+" "+p[1].toFixed(1)).join(" ");
  const area=path+" L "+points[points.length-1][0]+" "+(top+ph)+" L "+points[0][0]+" "+(top+ph)+" Z";
  const labels=rows.map((r,i)=>{
    if(rows.length>15 && i%Math.ceil(rows.length/8)!==0 && i!==rows.length-1) return "";
    return `<text x="${points[i][0]}" y="${h-10}" text-anchor="middle" fill="#8e9aaa" font-size="10">${r.day || r.month}</text>`;
  }).join("");
  const grid=[0,.25,.5,.75,1].map(p=>{
    const y=top+ph-p*ph;
    return `<line x1="${left}" x2="${w-right}" y1="${y}" y2="${y}" stroke="#263342" stroke-width="1"/>
      <text x="${left-8}" y="${y+4}" text-anchor="end" fill="#8e9aaa" font-size="10">${money(max*p)}</text>`;
  }).join("");
  el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    ${grid}
    <path d="${area}" fill="rgba(77,163,255,.08)" stroke="none"/>
    <path d="${path}" fill="none" stroke="#4da3ff" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
    ${points.map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="3.5" fill="#4da3ff"/>`).join("")}
    ${labels}
  </svg>`;
}

function showPage(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));

  if (page === 'overview') {
    document.getElementById('pageOverview').classList.add('active');
    document.getElementById('navOverview').classList.add('active');
  } else if (page === 'profitcenters') {
    document.getElementById('pageProfitCenters').classList.add('active');
    document.getElementById('navProfitCenters').classList.add('active');
  } else if (page === 'missedrevenue') {
    document.getElementById('pageMissedRevenue').classList.add('active');
    document.getElementById('navMissedRevenue').classList.add('active');
  } else if (page === 'technicians') {
    document.getElementById('pageTechnicians').classList.add('active');
    document.getElementById('navTechnicians').classList.add('active');
  } else if (page === 'financial') {
    document.getElementById('pageFinancial').classList.add('active');
    document.getElementById('navFinancial').classList.add('active');
  }

  window.scrollTo({top:0, behavior:'smooth'});
}

async function loadDashboard() {
  document.getElementById("app").classList.add("loading");
  const days=document.getElementById("period").value;
  const basis=document.getElementById("basis").value;

  try {
    const res=await fetch(`/api/dashboard?days=${days}&basis=${basis}`);
    const data=await res.json();
    if(!res.ok) throw new Error(data.error || "Request failed");

    const r=data.revenue;

    // Some older dashboard/API responses can omit ro_count even though
    // total_sales and average_ro are correct. Derive it as a safe fallback.
    const reportedRoCount = Number(r.ro_count) || 0;
    const derivedRoCount = (Number(r.average_ro) > 0)
      ? Math.round((Number(r.total_sales) || 0) / Number(r.average_ro))
      : 0;
    const roCount = reportedRoCount || derivedRoCount;

    document.getElementById("sales").textContent=money(r.total_sales);
    document.getElementById("ros").textContent=number(roCount);
    document.getElementById("avgRo").textContent=money(r.average_ro);
    document.getElementById("labor").textContent=money(r.labor_sales);
    document.getElementById("discounts").textContent=money(r.discounts);

    const totalBilledHours = data.technicians.reduce((sum, t) => sum + (Number(t.labor_hours) || 0), 0);
    const effectiveLaborRate = totalBilledHours ? (Number(r.labor_sales) || 0) / totalBilledHours : 0;

    document.getElementById("discountRate").textContent=(r.discount_percent || 0).toFixed(1)+"%";
    document.getElementById("billedHours").textContent=decimal(totalBilledHours);
    document.getElementById("effectiveLaborRate").textContent=money(effectiveLaborRate);

    document.getElementById("salesChange").innerHTML=changeText(data.comparison.changes.total_sales_percent);
    const comparisonRoChange = data.comparison.changes.ro_count_percent;
    document.getElementById("rosChange").innerHTML=changeText(comparisonRoChange);
    document.getElementById("avgRoChange").innerHTML=changeText(data.comparison.changes.average_ro_percent);
    document.getElementById("discountChange").innerHTML=changeText(data.comparison.changes.discounts_percent);

    document.getElementById("laborMix").textContent=(r.labor_percent || 0).toFixed(1)+"%";
    document.getElementById("partsMix").textContent=(r.parts_percent || 0).toFixed(1)+"%";
    document.getElementById("discountMix").textContent=(r.discount_percent || 0).toFixed(1)+"%";
    document.getElementById("laborBar").style.width=Math.min(r.labor_percent || 0,100)+"%";
    document.getElementById("partsBar").style.width=Math.min(r.parts_percent || 0,100)+"%";

    // Management snapshot metrics.
    const safeRoCount = roCount || 0;
    const laborSales = Number(r.labor_sales) || 0;
    const partsSales = Number(r.parts_sales) || 0;
    const avgLaborPerRo = safeRoCount ? laborSales / safeRoCount : 0;
    const avgHoursPerRo = safeRoCount ? totalBilledHours / safeRoCount : 0;
    const avgPartsPerRo = safeRoCount ? partsSales / safeRoCount : 0;
    const laborPlusParts = laborSales + partsSales;
    const laborMix = laborPlusParts ? (laborSales / laborPlusParts) * 100 : 0;

    document.getElementById("laborPerRo").textContent=money(avgLaborPerRo);
    document.getElementById("hoursPerRo").textContent=decimal(avgHoursPerRo);
    document.getElementById("partsPerRo").textContent=money(avgPartsPerRo);
    document.getElementById("managementLaborMix").textContent=laborMix.toFixed(1)+"%";

    // Technician data is used by both the management alerts and the
    // technician table, so initialize it before any alert calculations.
    const tech = Array.isArray(data.technicians) ? data.technicians : [];

    // These are management review thresholds, not claims about technician
    // quality. They are intentionally conservative and can be changed later.
    const alerts = [];

    if (effectiveLaborRate < 125) {
      alerts.push({
        cls:"warn",
        title:"Shop effective labor rate needs review",
        text:`${money(effectiveLaborRate)}/hr is below the $125/hr review threshold. Check labor pricing, discounts, and sold hours.`
      });
    } else {
      alerts.push({
        cls:"good",
        title:"Shop labor rate is healthy",
        text:`${money(effectiveLaborRate)}/hr effective labor rate for the selected period.`
      });
    }

    const discountRate = Number(r.discount_percent) || 0;
    if (discountRate > 10) {
      alerts.push({
        cls:"warn",
        title:"Discounting is elevated",
        text:`Discounts are ${discountRate.toFixed(1)}% of labor + parts. Review large discounts and package adjustments.`
      });
    } else {
      alerts.push({
        cls:"good",
        title:"Discounting is controlled",
        text:`Discounts are ${discountRate.toFixed(1)}% of labor + parts for the selected period.`
      });
    }

    const techReviews = tech.filter(t => {
      const hours = Number(t.labor_hours) || 0;
      const sales = Number(t.labor_sales) || 0;
      const jobs = Number(t.jobs) || 0;
      const rate = laborRate(sales, hours);
      const avgHours = Number(t.average_hours_per_job) || (jobs ? hours/jobs : 0);
      return jobs >= 10 && (rate < 100 || avgHours > 1.75);
    });

    if (techReviews.length) {
      const names = techReviews.slice(0,3).map(t => {
        const rate = laborRate(Number(t.labor_sales)||0, Number(t.labor_hours)||0);
        const avgHours = Number(t.average_hours_per_job) || 0;
        const reasons = [];
        if (rate < 100) reasons.push(`effective rate ${money(rate)}/hr`);
        if (avgHours > 1.75) reasons.push(`${decimal(avgHours)} hrs/job`);
        return `${t.technician_name || "Unknown"} (${reasons.join(", ")})`;
      });
      alerts.push({
        cls:"warn",
        title:"Technician metrics to review",
        text:`${names.join("; ")}. Review job mix, sold hours, and workflow before drawing conclusions.`
      });
    } else {
      alerts.push({
        cls:"good",
        title:"No technician review flags",
        text:"No technician crossed the current review thresholds for the selected period."
      });
    }

    document.getElementById("alerts").innerHTML=alerts.map(a=>{
      const badge = a.cls === "good" ? "GOOD" : (a.cls === "warn" ? "REVIEW" : "ACTION");
      return `
      <div class="alert ${a.cls}">
        <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">
          <div class="alert-title">${a.title}</div>
          <div style="font-size:9px;font-weight:800;letter-spacing:.7px;color:${a.cls === "good" ? "var(--good)" : (a.cls === "warn" ? "var(--warn)" : "var(--bad)")};padding-top:1px">${badge}</div>
        </div>
        <div class="alert-text">${a.text}</div>
      </div>`;
    }).join("");

    const trendRows = Array.isArray(data.trend) ? data.trend : [];
    const trendTotal = trendRows.reduce(
      (sum, row) => sum + (Number(row.total_sales) || 0),
      0
    );

    const chartTotal = document.getElementById("overviewChartTotal");
    if (chartTotal) chartTotal.textContent = money(trendTotal);

    drawChart(trendRows);

    window.dashboardShopLaborSales = laborSales;
    window.dashboardEffectiveLaborRate = effectiveLaborRate;

    window.dashboardTechnicians = tech;

    document.getElementById("techTable").innerHTML=tech.map((t, index)=>`
      <tr
        class="tech-row"
        data-technician-index="${index}"
        data-technician-id="${String(t.technician_id ?? t.technician_name ?? "").replace(/"/g, '&quot;')}"
        onclick="selectTechnicianByIndex(${index})"
        title="Click to view technician scorecard"
      >
        <td>${t.technician_name || "Unknown"}</td>
        <td class="num">${number(t.jobs)}</td>
        <td class="num">${decimal(t.labor_hours)}</td>
        <td class="num">${money(t.labor_sales)}</td>
        <td class="num">${money((Number(t.jobs) || 0) ? (Number(t.labor_sales) || 0) / Number(t.jobs) : 0)}</td>
        <td class="num">${decimal(t.average_hours_per_job)}</td>
        <td class="num">${money(laborRate(Number(t.labor_sales) || 0, Number(t.labor_hours) || 0))}</td>
      </tr>`).join("");

    if (tech.length) {
      selectTechnician(tech[0]);
    } else {
      document.getElementById("scorecardName").textContent = "No technician data";
      document.getElementById("scorecardSub").textContent = "No technician labor was found for the selected period.";
      document.getElementById("scorecardStatus").textContent = "—";
    }

    document.getElementById("advisorTable").innerHTML=data.advisors.map(a=>`
      <tr>
        <td>${a.advisor_name || "Unknown"}</td>
        <td class="num">${number(a.ro_count)}</td>
        <td class="num">${money(a.total_sales)}</td>
        <td class="num">${money(a.average_ro)}</td>
      </tr>`).join("");

    const jobCategories = Array.isArray(data.job_categories) ? data.job_categories : [];

    document.getElementById("profitCenterTable").innerHTML = jobCategories.map(c => {
      const partsRevenue = Number(c.parts_revenue) || 0;
      const hasPartsCost = !!c.has_parts_cost_data;
      const marginPercent = Number(c.parts_margin_percent) || 0;
      const shopShare = Number(c.percent_of_shop_revenue) || 0;

      // parts_margin_dollars/percent come back as null (not 0) when a
      // category has parts revenue but no itemized cost data — that's
      // "unknown", not "zero margin", so it must render differently.
      let marginClass = "muted";
      if (hasPartsCost && partsRevenue > 0) {
        marginClass = marginPercent >= 40 ? "good" : (marginPercent >= 25 ? "warn" : "bad");
      }

      const marginDollarsText = hasPartsCost ? money(c.parts_margin_dollars) : "—";
      const marginPercentText = hasPartsCost && partsRevenue > 0
        ? marginPercent.toFixed(1) + "%"
        : "—";

      return `
      <tr>
        <td>${c.category || "Uncategorized"}</td>
        <td class="num">${number(c.job_count)}</td>
        <td class="num">${money(c.labor_revenue)}</td>
        <td class="num">${money(c.parts_revenue)}</td>
        <td class="num">${marginDollarsText}</td>
        <td class="num ${marginClass}">${marginPercentText}</td>
        <td class="num">${money(c.net_revenue)}</td>
        <td class="num">
          ${shopShare.toFixed(1)}%
          <span class="bar-bg"><span class="bar" style="width:${Math.min(shopShare, 100)}%"></span></span>
        </td>
      </tr>`;
    }).join("");

    const missed = data.missed_revenue || {};
    const missedSummary = missed.summary || {};

    document.getElementById("declinedValue").textContent = money(missedSummary.declined_value);
    document.getElementById("declinedCount").textContent =
      `${number(missedSummary.declined_count)} declined job${missedSummary.declined_count === 1 ? "" : "s"}`;
    document.getElementById("conversionRate").textContent =
      (Number(missedSummary.conversion_rate_percent) || 0).toFixed(1) + "%";
    document.getElementById("recommendedValue").textContent = money(missedSummary.recommended_value);
    document.getElementById("avgDeclinedValue").textContent = money(missedSummary.average_declined_value);

    const missedByCategory = Array.isArray(missed.by_category) ? missed.by_category : [];

    document.getElementById("missedRevenueCategoryTable").innerHTML = missedByCategory.map(c => {
      const rate = Number(c.conversion_rate_percent) || 0;
      const rateClass = rate >= 75 ? "good" : (rate >= 50 ? "warn" : "bad");
      return `
      <tr>
        <td>${c.category || "Uncategorized"}</td>
        <td class="num">${money(c.authorized_value)}</td>
        <td class="num">${money(c.declined_value)}</td>
        <td class="num">${money(c.recommended_value)}</td>
        <td class="num ${rateClass}">${rate.toFixed(1)}%</td>
      </tr>`;
    }).join("") || `<tr><td colspan="5" class="muted">No recommended work in this period.</td></tr>`;

    const topDeclinedJobs = Array.isArray(missed.top_declined_jobs) ? missed.top_declined_jobs : [];

    document.getElementById("missedRevenueJobTable").innerHTML = topDeclinedJobs.map(j => `
      <tr>
        <td>${j.ro_number ?? "—"}</td>
        <td>${j.job_name || "Unnamed job"}</td>
        <td>${j.category || "Uncategorized"}</td>
        <td>${j.technician_name || "Unassigned"}</td>
        <td>${j.advisor_name || "Unknown"}</td>
        <td class="num">${money(j.quoted_value)}</td>
      </tr>`).join("") || `<tr><td colspan="6" class="muted">No declined jobs in this period.</td></tr>`;

    document.getElementById("updated").textContent=
      `Updated ${new Date().toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})}`;
  } catch(e) {
    alert(e.message);
  } finally {
    document.getElementById("app").classList.remove("loading");
  }
}

document.getElementById("period").addEventListener("change", loadDashboard);
document.getElementById("basis").addEventListener("change", loadDashboard);

// --------------------------------------------------------------
// Tekmetric sync status / trigger
// --------------------------------------------------------------
// The actual sync (talking to Tekmetric) runs on the server in a
// background thread, whether started by this button or by the
// server's own periodic scheduler. This just polls /api/sync/status
// so the UI reflects whatever is really happening, and refreshes the
// dashboard automatically when a sync completes — including ones
// nobody in the browser triggered.

let syncPollTimer = null;
let lastKnownSyncStatus = null;

function formatSyncTimestamp(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleString([], {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit"
  });
}

function renderSyncStatus(data) {
  const el = document.getElementById("syncStatus");

  if (data.status === "running") {
    el.textContent = "Syncing from Tekmetric…";
  } else if (data.status === "error") {
    el.textContent = data.last_finished_at
      ? `Last sync failed at ${formatSyncTimestamp(data.last_finished_at)}`
      : "Last sync failed";
  } else if (data.last_finished_at) {
    el.textContent = `Last synced ${formatSyncTimestamp(data.last_finished_at)}`;
  } else {
    el.textContent = "Not yet synced from Tekmetric";
  }
}

async function refreshSyncStatus() {
  try {
    const res = await fetch("/api/sync/status");
    const data = await res.json();
    renderSyncStatus(data);

    const button = document.getElementById("syncButton");

    if (data.status === "running") {
      button.disabled = true;
      button.textContent = "Syncing…";
      if (!syncPollTimer) {
        syncPollTimer = setInterval(refreshSyncStatus, 3000);
      }
    } else {
      button.disabled = false;
      button.textContent = "Sync from Tekmetric";
      if (syncPollTimer) {
        clearInterval(syncPollTimer);
        syncPollTimer = null;
        // A sync just finished — possibly one the server kicked off on
        // its own schedule — so pull fresh numbers into view.
        if (lastKnownSyncStatus === "running") {
          loadDashboard();
        }
      }
    }

    lastKnownSyncStatus = data.status;
  } catch (e) {
    console.error("Sync status check failed:", e);
  }
}

async function triggerSync() {
  const button = document.getElementById("syncButton");
  button.disabled = true;
  button.textContent = "Syncing…";

  try {
    const res = await fetch("/api/sync", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not start sync");
  } catch (e) {
    alert(e.message);
  }

  refreshSyncStatus();
}

loadDashboard();
refreshSyncStatus();
setInterval(refreshSyncStatus, 15000);
</script>
</body>
</html>
"""


def api_response(days, basis):
    end = datetime.now().date()
    start = end - timedelta(days=int(days) - 1)

    start_s = start.isoformat()
    end_s = end.isoformat()

    revenue = get_revenue(
        start_date=start_s,
        end_date=end_s,
        basis=basis,
    )

    # Daily data for short periods; monthly data for a 12-month view.
    if int(days) <= 90:
        trend = get_daily_trends(
            start_date=start_s,
            end_date=end_s,
            basis=basis,
        )
    else:
        trend = get_monthly_trends(
            start_date=start_s,
            end_date=end_s,
            basis=basis,
        )

    technicians = get_technician_metrics(
        start_date=start_s,
        end_date=end_s,
        basis=basis,
    )

    advisors = get_advisor_metrics(
        start_date=start_s,
        end_date=end_s,
        basis=basis,
    )

    job_categories = get_job_category_metrics(
        start_date=start_s,
        end_date=end_s,
        basis=basis,
    )

    missed_revenue = get_missed_revenue(
        start_date=start_s,
        end_date=end_s,
        basis=basis,
    )

    comparison = get_period_comparison(
        start_date=start_s,
        end_date=end_s,
        basis=basis,
    )

    return {
        "revenue": revenue,
        "trend": trend,
        "technicians": technicians,
        "advisors": advisors,
        "job_categories": job_categories,
        "missed_revenue": missed_revenue,
        "comparison": comparison,
    }


class Handler(BaseHTTPRequestHandler):


    def _redirect(self, location):

      self.send_response(302)

      self.send_header(
        "Location",
        location,
      )

      self.end_headers()

    def _current_user(self):
      cookie = self.headers.get("Cookie", "")

      for item in cookie.split(";"):

        item = item.strip()

        if item.startswith("session_token="):

            token = item.split("=", 1)[1]

            return validate_session(token)

      return None

    def _send(self, body, content_type="text/html; charset=utf-8", status=200):
        if isinstance(body, str):
            body = body.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        user = self._current_user()

        if parsed.path == "/login":

            if user:
                self._redirect("/")
                return

            self._send(LOGIN_HTML.replace("{error}", ""))
            return

        if parsed.path == "/logout":

            cookie = self.headers.get("Cookie", "")

            for item in cookie.split(";"):
                item = item.strip()

                if item.startswith("session_token="):
                    token = item.split("=", 1)[1]
                    destroy_session(token)
                    break

            self.send_response(302)
            self.send_header("Location", "/login")
            self.send_header(
                "Set-Cookie",
                "session_token=; Max-Age=0; Path=/",
            )
            self.end_headers()
            return

        if not user:
            self._redirect("/login")
            return

        if parsed.path == "/":

          if not user:
            self._redirect("/login")
          return

          self._send(HTML)

          return

        if parsed.path.startswith("/api/") and not user:

          self._send(
            json.dumps({"error": "Unauthorized"}),
            "application/json; charset=utf-8",
            401,
          )

          return

        if parsed.path == "/api/dashboard":
            try:
                params = parse_qs(parsed.query)
                days = int(params.get("days", ["30"])[0])
                basis = params.get("basis", ["revenue"])[0]

                if days not in (7, 30, 90, 365):
                    raise ValueError("Invalid period.")

                if basis not in ("revenue", "production", "activity"):
                    raise ValueError("Invalid reporting basis.")

                payload = api_response(days, basis)
                self._send(
                    json.dumps(payload),
                    "application/json; charset=utf-8",
                )
            except Exception as exc:
                self._send(
                    json.dumps({"error": str(exc)}),
                    "application/json; charset=utf-8",
                    500,
                )
            return

        if parsed.path == "/api/technician-trend":
            try:
                params = parse_qs(parsed.query)

                technician_id_raw = params.get("technician_id", [None])[0]
                if technician_id_raw is None:
                    raise ValueError("technician_id is required.")
                technician_id = int(technician_id_raw)

                basis = params.get("basis", ["revenue"])[0]
                if basis not in ("revenue", "production", "activity"):
                    raise ValueError("Invalid reporting basis.")

                weeks = int(params.get("weeks", ["12"])[0])
                if weeks < 1 or weeks > 52:
                    raise ValueError("weeks must be between 1 and 52.")

                payload = get_technician_trend(
                    technician_id=technician_id,
                    weeks=weeks,
                    basis=basis,
                )
                self._send(
                    json.dumps(payload),
                    "application/json; charset=utf-8",
                )
            except Exception as exc:
                self._send(
                    json.dumps({"error": str(exc)}),
                    "application/json; charset=utf-8",
                    500,
                )
            return

        if parsed.path == "/api/sync/status":
            with SYNC_LOCK:
                payload = dict(SYNC_STATE)
            self._send(
                json.dumps(payload),
                "application/json; charset=utf-8",
            )
            return

        self._send("Not Found", status=404)

    def do_POST(self):
      parsed = urlparse(self.path)

      # --------------------------------------------------
      # Login
      # --------------------------------------------------

      if parsed.path == "/login":

          content_length = int(
              self.headers.get(
                  "Content-Length",
                  0,
              )
          )

          body = self.rfile.read(
              content_length
          ).decode(
              "utf-8"
          )

          form = parse_qs(body)

          username = form.get(
              "username",
              [""]
          )[0]

          password = form.get(
              "password",
              [""]
          )[0]

          if authenticate(
              username,
              password,
          ):

            token = create_session(
                username
            )

            self.send_response(
                302
            )

            self.send_header(
                "Location",
                "/",
            )

            self.send_header(
                "Set-Cookie",
                (
                    f"session_token={token}; "
                    "Max-Age=2592000; "
                    "Path=/"
                ),
            )

            self.end_headers()

            return

          self._send(
              LOGIN_HTML.replace(
                  "{error}",
                  (
                      '<div class="error">'
                      "Invalid username or password."
                      "</div>"
                  ),
              ),
            )

          return

      # --------------------------------------------------
      # Sync
      # --------------------------------------------------

      user = self._current_user()

      if (
          parsed.path.startswith("/api/")
          and not user
      ):

          self._send(
              json.dumps(
                  {
                      "error": "Unauthorized"
                  }
              ),
              "application/json; charset=utf-8",
              401,
          )

          return

      if parsed.path == "/api/sync":

          started = (
              _run_sync_in_background()
          )

          payload = {
              "status": (
                  "started"
                  if started
                  else "already_running"
              )
          }

          self._send(
              json.dumps(
                  payload
              ),
              "application/json; charset=utf-8",
          )

          return

      self._send(
          "Not Found",
          status=404,
      )

    def log_message(self, format, *args):
        print(f"[Dashboard] {args[0]}")


if __name__ == "__main__":
    print("=" * 60)
    print("COMPLETE AUTO REPAIR — PERFORMANCE DASHBOARD")
    print("=" * 60)
    print()
    print(f"Dashboard running at: http://localhost:{PORT}")

    if AUTO_SYNC_INTERVAL_MINUTES:
        print(
            f"Auto-sync from Tekmetric: every "
            f"{AUTO_SYNC_INTERVAL_MINUTES} minutes"
        )
        threading.Thread(target=_auto_sync_loop, daemon=True).start()
    else:
        print("Auto-sync from Tekmetric: disabled")

    print("Press CTRL+C to stop.")
    print()

    server = ThreadingHTTPServer((HOST, PORT), Handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()