"""
BharatTerm — India Manufacturing Intelligence Dashboard
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import yfinance as yf
import requests
import json
import time
from datetime import datetime, timedelta
import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

COMPANIES = [
    {"name": "Reliance Industries",    "sym": "RELIANCE.NS",     "short": "RELIANCE",  "sector": "Oil & Gas"},
    {"name": "Larsen & Toubro",        "sym": "LT.NS",           "short": "L&T",        "sector": "Engineering"},
    {"name": "Tata Steel",             "sym": "TATASTEEL.NS",    "short": "TATASTEEL",  "sector": "Steel"},
    {"name": "Maruti Suzuki",          "sym": "MARUTI.NS",       "short": "MARUTI",     "sector": "Auto"},
    {"name": "Mahindra & Mahindra",    "sym": "M&M.NS",          "short": "M&M",        "sector": "Auto"},
    {"name": "NTPC",                   "sym": "NTPC.NS",          "short": "NTPC",       "sector": "Power"},
    {"name": "JSW Steel",              "sym": "JSWSTEEL.NS",     "short": "JSWSTEEL",   "sector": "Steel"},
    {"name": "UltraTech Cement",       "sym": "ULTRACEMCO.NS",   "short": "ULTRACEMCO", "sector": "Cement"},
    {"name": "Sun Pharma",             "sym": "SUNPHARMA.NS",    "short": "SUNPHARMA",  "sector": "Pharma"},
    {"name": "Bajaj Auto",             "sym": "BAJAJ-AUTO.NS",   "short": "BAJAJ-AUTO", "sector": "Auto"},
    {"name": "Adani Ports",            "sym": "ADANIPORTS.NS",   "short": "ADANIPORTS", "sector": "Logistics"},
    {"name": "Bharat Electronics",     "sym": "BEL.NS",           "short": "BEL",        "sector": "Defence"},
    {"name": "Hindalco",               "sym": "HINDALCO.NS",     "short": "HINDALCO",   "sector": "Metals"},
    {"name": "Tata Motors",            "sym": "TATAMOTORS.NS",   "short": "TATAMOTORS", "sector": "Auto"},
    {"name": "Coal India",             "sym": "COALINDIA.NS",    "short": "COALINDIA",  "sector": "Mining"},
    {"name": "Grasim Industries",      "sym": "GRASIM.NS",       "short": "GRASIM",     "sector": "Cement/Chem"},
    {"name": "Hindustan Unilever",     "sym": "HINDUNILVR.NS",   "short": "HUL",        "sector": "FMCG"},
    {"name": "SAIL",                   "sym": "SAIL.NS",          "short": "SAIL",       "sector": "Steel"},
    {"name": "Tata Chemicals",         "sym": "TATACHEM.NS",     "short": "TATACHEM",   "sector": "Chemicals"},
    {"name": "Wipro",                  "sym": "WIPRO.NS",         "short": "WIPRO",      "sector": "Tech/Electronics"},
]

SECTOR_COLORS = {
    "Steel": "#e74c3c", "Auto": "#3498db", "Oil & Gas": "#9b59b6",
    "Engineering": "#2ecc71", "Cement": "#e67e22", "Defence": "#f39c12",
    "Power": "#1abc9c", "Pharma": "#e91e63", "Metals": "#ff7043",
    "Logistics": "#26c6da", "Mining": "#8d6e63", "FMCG": "#ab47bc",
    "Chemicals": "#66bb6a", "Cement/Chem": "#ffa726", "Tech/Electronics": "#42a5f5",
}

GEO_SCENARIOS = [
    {"id": "iran_us", "title": "Iran-US Conflict", "severity": "HIGH", "color": "#e74c3c", "probability": 0.7, "impact": 0.85,
     "desc": "Hormuz Strait disruption -> crude spike. India imports 85% of crude. Every $10/bbl rise = ~0.4% GDP drag.",
     "winners": ["BEL", "L&T (defence contracts)"], "losers": ["RELIANCE", "ADANIPORTS", "TATAMOTORS"],
     "signal": "SHORT refining; LONG BEL, L&T defence"},
    {"id": "trump_tariffs", "title": "Trump Tariff 2.0", "severity": "HIGH", "color": "#f5a623", "probability": 0.85, "impact": 0.75,
     "desc": "25% tariffs on steel/aluminium. JSW Steel, SAIL US-export revenue at risk (~8-12% of revenue).",
     "winners": ["Domestic infra plays", "L&T", "NTPC"], "losers": ["JSWSTEEL", "SAIL", "HINDALCO"],
     "signal": "AVOID export-heavy steel; BUY domestic infra"},
    {"id": "us_china", "title": "US-China Trade War", "severity": "MEDIUM-HIGH", "color": "#f5a623", "probability": 0.90, "impact": 0.65,
     "desc": "India as China+1 beneficiary. L&T, BEL gain from supply chain redirect.",
     "winners": ["L&T", "BEL", "HINDALCO"], "losers": ["SAIL (dumping risk)", "JSWSTEEL"],
     "signal": "BUY L&T, BEL, Hindalco; WATCH steel dumping"},
    {"id": "red_sea", "title": "Red Sea / Israel-Gaza", "severity": "MEDIUM", "color": "#e67e22", "probability": 0.75, "impact": 0.55,
     "desc": "18-25 extra days Europe-India routing. Container freight +3x peak.",
     "winners": ["BEL", "Domestic logistics"], "losers": ["SUNPHARMA (exports)", "MARUTI (parts imports)"],
     "signal": "BUY BEL; TRIM SUNPHARMA near-term"},
    {"id": "wb_elections", "title": "West Bengal Elections 2026", "severity": "SECTOR-SPECIFIC", "color": "#3498db", "probability": 1.0, "impact": 0.5,
     "desc": "Coal India (40% production from WB/Jharkhand), SAIL Burnpur plant, Adani Ports Haldia most exposed.",
     "winners": ["L&T (pre-poll contracts)", "COALINDIA (capex)"], "losers": ["SAIL (post-election labour risk)", "ADANIPORTS"],
     "signal": "BUY L&T pre-election; CAUTION SAIL post-results"},
    {"id": "india_ge", "title": "India General Election 2029", "severity": "POLICY-DRIVEN", "color": "#9b59b6", "probability": 1.0, "impact": 0.80,
     "desc": "Historical: NIFTY +12% avg 6M before if incumbent likely wins. Defence, infra, PSU banking surge pre-election.",
     "winners": ["BEL", "L&T", "NTPC", "COALINDIA"], "losers": ["None directly - broad rally"],
     "signal": "BUY defence + infra 12 months before polling"},
]

ELECTION_HISTORY = [
    {"year": "2004", "event": "UPA wins (shock)", "before_30d": 4.2,  "result_day": -17.3, "after_90d": 19.1, "note": "Circuit breaker triggered on result day"},
    {"year": "2009", "event": "UPA majority",      "before_30d": -12.1,"result_day": 17.3,  "after_90d": 42.1, "note": "Largest single-day NIFTY gain ever"},
    {"year": "2014", "event": "BJP landslide",     "before_30d": 8.4,  "result_day": 6.9,   "after_90d": 22.4, "note": "Modi premium built 3 months prior"},
    {"year": "2019", "event": "BJP 2nd term",      "before_30d": 6.1,  "result_day": 3.8,   "after_90d": 8.2,  "note": "Infra/defence PSU post-win surge"},
    {"year": "2024", "event": "BJP coalition",     "before_30d": 3.2,  "result_day": -5.9,  "after_90d": 11.8, "note": "Below-expectation majority - PSU correction"},
]

NEWS_ITEMS = [
    {"co": "Tata Steel",    "type": "CAPEX",       "date": "Mar 2025", "text": "Kalinganagar Phase 2 - 5 MTPA addition, Rs27,000Cr. ETA FY2026.", "color": "success"},
    {"co": "L&T",           "type": "ACQUISITION", "date": "Jan 2025", "text": "26% stake in ATCO UAE (energy tech) - Middle East infra play.", "color": "primary"},
    {"co": "Adani Ports",   "type": "CAPEX",       "date": "Feb 2025", "text": "Vizhinjam Phase 2 Rs12,000Cr - transshipment hub targeting Sri Lanka diversion.", "color": "success"},
    {"co": "BEL",           "type": "JV",          "date": "Dec 2024", "text": "JV with Israel Aerospace for drone systems - Rs1,800Cr program.", "color": "primary"},
    {"co": "Reliance",      "type": "MERGER",      "date": "Nov 2024", "text": "Disney+ Hotstar merger complete - 100M+ subscribers combined.", "color": "primary"},
    {"co": "SAIL",          "type": "LEGAL",       "date": "Jan 2025", "text": "CCI investigation - alleged price coordination in construction steel.", "color": "danger"},
    {"co": "Maruti Suzuki", "type": "CAPEX",       "date": "Oct 2024", "text": "Kharkhoda Plant Haryana Rs11,000Cr greenfield - 250k vehicles/yr by 2028.", "color": "success"},
    {"co": "JSW Steel",     "type": "ACQUISITION", "date": "Sep 2024", "text": "Bhushan Power integration complete; targeting 40 MTPA by FY27.", "color": "primary"},
    {"co": "Hindalco",      "type": "CAPEX",       "date": "Aug 2024", "text": "Novelis EV battery enclosure plant $400M in North America.", "color": "success"},
    {"co": "Coal India",    "type": "LEGAL",       "date": "Nov 2024", "text": "NGT penalty Rs440Cr for environmental violations in Jharkhand.", "color": "danger"},
]

CANDLE_PATTERNS = [
    {"name": "Doji",              "signal": "Trend indecision - possible reversal",      "conf": "Medium",    "action": "Wait for confirmation candle before acting",           "example": "RIL Aug 2022: Doji at Rs2680 -> 8% correction in 3 weeks"},
    {"name": "Hammer",            "signal": "Bullish reversal at support",                "conf": "High",      "action": "Buy on next bullish candle WITH volume confirmation",   "example": "Tata Steel Nov 2022: Hammer at Rs95 -> 60% rally over 4 months"},
    {"name": "Shooting Star",     "signal": "Bearish reversal at resistance",             "conf": "High",      "action": "Reduce longs; set stop above the high",                "example": "Nifty Metal Jul 2023: Shooting star at 7200 -> 12% fall"},
    {"name": "Bullish Engulfing", "signal": "Strong demand overwhelms prior supply",      "conf": "Very High", "action": "Buy with tight stop below engulfed candle low",         "example": "SAIL Mar 2023: Bull engulfing at Rs72 -> Rs140 in 6 months"},
    {"name": "Bearish Engulfing", "signal": "Supply overwhelms - distribution signal",   "conf": "Very High", "action": "Exit longs; consider short with stop above body high",  "example": "M&M Sep 2023: Bear engulfing at Rs1700 -> 15% drop in 3 weeks"},
    {"name": "Morning Star",      "signal": "3-candle bullish reversal pattern",          "conf": "High",      "action": "Enter long on close of third candle",                  "example": "Nifty 2020 COVID bottom: Morning star confirmed the floor"},
    {"name": "Evening Star",      "signal": "3-candle bearish reversal at top",           "conf": "High",      "action": "Exit positions; await breakdown confirmation",          "example": "JSW Steel Jan 2023: Evening star at Rs780 -> 18% correction"},
    {"name": "Inverted Hammer",   "signal": "Bullish reversal - buyers testing overhead", "conf": "Medium",    "action": "Buy only on next day follow-through above high",        "example": "BEL Mar 2024: Inv Hammer at Rs150 -> re-rated to Rs340"},
]

_cache = {}
_cache_time = {}
CACHE_TTL = 300

def get_cached(key, fetch_fn, *args, **kwargs):
    now = time.time()
    if key in _cache and now - _cache_time.get(key, 0) < CACHE_TTL:
        return _cache[key]
    try:
        result = fetch_fn(*args, **kwargs)
        _cache[key] = result
        _cache_time[key] = now
        return result
    except Exception as e:
        print(f"Cache fetch error for {key}: {e}")
        return _cache.get(key)

def fetch_price_data(sym, period="1y", interval="1d"):
    ticker = yf.Ticker(sym)
    hist = ticker.history(period=period, interval=interval)
    return hist

def fetch_info(sym):
    ticker = yf.Ticker(sym)
    return ticker.info

def fetch_financials(sym):
    ticker = yf.Ticker(sym)
    return {
        "income": ticker.financials,
        "balance": ticker.balance_sheet,
        "cashflow": ticker.cashflow,
    }

def call_claude(prompt):
    if not ANTHROPIC_API_KEY:
        return "Set ANTHROPIC_API_KEY environment variable for AI analysis."
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        data = resp.json()
        return data.get("content", [{}])[0].get("text", "No response.")
    except Exception as e:
        return f"AI analysis error: {e}"

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
    title="BharatTerm - India Manufacturing Intelligence",
    suppress_callback_exceptions=True,
)
server = app.server  # required for gunicorn deployment

GOLD = "#f5a623"
BG = "#0a0e1a"
CARD_BG = "#111827"
BORDER = "#1e2a42"

sidebar = html.Div([
    html.Div("TOP 20 MFG", style={"padding": "10px 12px", "fontSize": "10px",
             "color": "#5a6382", "letterSpacing": "1px", "borderBottom": f"1px solid {BORDER}"}),
    html.Div([
        html.Div(
            dbc.Row([
                dbc.Col(html.Span(c["short"], style={"fontSize": "11px", "color": GOLD}), width=8),
                dbc.Col(html.Span(c["sector"], style={"fontSize": "9px", "color": "#5a6382"}), width=4),
            ]),
            id={"type": "sidebar-item", "index": i},
            style={"padding": "7px 12px", "cursor": "pointer",
                   "borderBottom": f"1px solid {BORDER}"},
            n_clicks=0,
        )
        for i, c in enumerate(COMPANIES)
    ]),
], style={"width": "180px", "background": "#070b14", "borderRight": f"1px solid {BORDER}",
          "overflowY": "auto", "height": "calc(100vh - 95px)", "flexShrink": 0})

topbar = dbc.Navbar([
    dbc.NavbarBrand("BHARATTERM // INDIA MANUFACTURING INTELLIGENCE",
                    style={"color": GOLD, "fontFamily": "'Courier New', monospace",
                           "fontSize": "14px", "letterSpacing": "2px", "fontWeight": "700"}),
    html.Div(id="clock-display", style={"color": "#5a6382", "fontSize": "10px",
                                         "fontFamily": "'Courier New', monospace"}),
], color="#070b14", dark=True, style={"borderBottom": f"1px solid {BORDER}", "padding": "6px 16px"})

tabs = dbc.Tabs([
    dbc.Tab(label="Overview",         tab_id="overview"),
    dbc.Tab(label="Financials",       tab_id="financials"),
    dbc.Tab(label="Candlestick",      tab_id="candle"),
    dbc.Tab(label="Geopolitical",     tab_id="geo"),
    dbc.Tab(label="Competitor Intel", tab_id="competitor"),
    dbc.Tab(label="Election Effects", tab_id="elections"),
    dbc.Tab(label="News & Capex",     tab_id="news"),
    dbc.Tab(label="AI Analyst",       tab_id="aianalyst"),
], id="main-tabs", active_tab="overview",
   style={"background": "#0d1220", "borderBottom": f"1px solid {BORDER}",
          "fontFamily": "'Courier New', monospace", "fontSize": "11px"})

app.layout = html.Div([
    topbar,
    tabs,
    html.Div([
        sidebar,
        html.Div(id="tab-content", style={"flex": 1, "overflowY": "auto",
                                           "padding": "16px", "background": BG}),
    ], style={"display": "flex", "height": "calc(100vh - 95px)"}),
    dcc.Store(id="selected-company", data=0),
    dcc.Store(id="candle-period-store", data="6mo"),
    dcc.Interval(id="clock-interval", interval=30_000, n_intervals=0),
], style={"background": BG, "minHeight": "100vh", "fontFamily": "'Courier New', monospace", "color": "#c8d0e0"})

def metric_card(title, value, sub="", color="#fff"):
    return dbc.Card([
        dbc.CardBody([
            html.Div(title, style={"fontSize": "10px", "color": "#5a6382", "letterSpacing": "1px",
                                    "textTransform": "uppercase", "marginBottom": "4px"}),
            html.Div(value, style={"fontSize": "22px", "fontWeight": "700", "color": color}),
            html.Div(sub, style={"fontSize": "11px", "color": "#5a6382", "marginTop": "2px"}),
        ])
    ], style={"background": CARD_BG, "border": f"1px solid {BORDER}", "borderRadius": "4px"})

def ai_box(text, color=GOLD):
    return html.Div([
        html.Div("AI ANALYSIS", style={"fontSize": "9px", "color": "#5a6382",
                                          "letterSpacing": "1px", "marginBottom": "6px"}),
        html.Div(text, style={"fontSize": "12px", "lineHeight": "1.8",
                               "whiteSpace": "pre-wrap", "color": color}),
    ], style={"background": "#070b14", "border": f"1px solid {BORDER}",
              "borderLeft": f"3px solid {color}", "borderRadius": "4px",
              "padding": "12px", "marginTop": "8px"})

def section_head(text):
    return html.Div(text, style={"fontSize": "10px", "color": GOLD, "letterSpacing": "2px",
                                  "textTransform": "uppercase", "borderBottom": f"1px solid {BORDER}",
                                  "paddingBottom": "4px", "marginBottom": "10px", "marginTop": "18px"})

def badge(text, color="#2ecc71"):
    return html.Span(text, style={"background": color + "22", "color": color,
                                   "padding": "2px 7px", "borderRadius": "2px", "fontSize": "10px"})

def build_overview(selected_idx=0):
    rows = []
    for i, c in enumerate(COMPANIES):
        try:
            info = get_cached(f"info_{c['sym']}", fetch_info, c["sym"]) or {}
            cmp = info.get("currentPrice") or info.get("regularMarketPrice") or "—"
            chg = info.get("regularMarketChangePercent") or 0
            pe  = info.get("trailingPE") or "—"
            eps = info.get("trailingEps") or "—"
            cap = info.get("marketCap") or 0
            cap_str = f"Rs{cap/1e7:.0f}Cr" if cap else "—"
            chg_str = f"{chg:+.2f}%" if isinstance(chg, float) else "—"
            chg_color = "#2ecc71" if isinstance(chg, float) and chg >= 0 else "#e74c3c"
        except:
            cmp, chg_str, pe, eps, cap_str, chg_color = "—", "—", "—", "—", "—", "#fff"
        rows.append(html.Tr([
            html.Td(str(i+1), style={"color": "#5a6382"}),
            html.Td(c["name"],   style={"color": GOLD}),
            html.Td(c["short"],  style={"color": "#fff"}),
            html.Td(c["sector"], style={"color": "#5a6382", "fontSize": "10px"}),
            html.Td(cap_str),
            html.Td(str(cmp),    style={"color": "#fff", "fontWeight": "700"}),
            html.Td(chg_str,     style={"color": chg_color}),
            html.Td(str(pe) if pe != "—" else "—"),
            html.Td(str(eps) if eps != "—" else "—"),
        ]))

    sector_counts = {}
    for c in COMPANIES:
        sector_counts[c["sector"]] = sector_counts.get(c["sector"], 0) + 1
    sector_fig = go.Figure(go.Pie(
        labels=list(sector_counts.keys()),
        values=list(sector_counts.values()),
        marker_colors=[SECTOR_COLORS.get(s, "#888") for s in sector_counts.keys()],
        hole=0.4, textfont_size=11,
    ))
    sector_fig.update_layout(
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        font_color="#c8d0e0", margin=dict(t=20, b=20, l=20, r=20),
        legend=dict(font_size=10), height=240,
    )

    return html.Div([
        section_head("Market Universe - Top 20 Indian Manufacturing"),
        dbc.Row([
            dbc.Col(metric_card("Companies", "20", "NSE Listed"), width=3),
            dbc.Col(metric_card("Sectors", "15", "Covered"), width=3),
            dbc.Col(metric_card("Data Source", "Yahoo Finance", "Live via yfinance"), width=3),
            dbc.Col(metric_card("AI Engine", "Claude Sonnet", "Anthropic API"), width=3),
        ], className="mb-3"),
        section_head("All Companies - Live Data"),
        dbc.Table([
            html.Thead(html.Tr([
                html.Th("#"), html.Th("Company"), html.Th("NSE"), html.Th("Sector"),
                html.Th("Mkt Cap"), html.Th("CMP (Rs)"), html.Th("Chg%"),
                html.Th("P/E"), html.Th("EPS"),
            ], style={"background": "#070b14", "fontSize": "10px", "color": "#5a6382"})),
            html.Tbody(rows),
        ], striped=False, hover=True, bordered=False,
           style={"fontSize": "11px", "background": CARD_BG}),
        section_head("Sector Distribution"),
        dcc.Graph(figure=sector_fig, config={"displayModeBar": False}),
    ])

def build_financials(sym_idx=0):
    c = COMPANIES[sym_idx]
    sym = c["sym"]
    try:
        fin = get_cached(f"fin_{sym}", fetch_financials, sym) or {}
        info = get_cached(f"info_{sym}", fetch_info, sym) or {}
        income = fin.get("income")
        if income is not None and not income.empty:
            rev_row = income.loc["Total Revenue"] if "Total Revenue" in income.index else None
            net_row = income.loc["Net Income"]    if "Net Income"   in income.index else None
            years = [str(col.year) for col in income.columns[:5]]
            rev = [float(v)/1e7 for v in (rev_row.values[:5] if rev_row is not None else [])]
            net = [float(v)/1e7 for v in (net_row.values[:5] if net_row is not None else [])]
        else:
            years, rev, net = ["FY20","FY21","FY22","FY23","FY24"], [], []

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        if rev:
            fig.add_trace(go.Bar(x=years, y=rev, name="Revenue (RsCr)", marker_color="#3498db"), secondary_y=False)
        if net:
            fig.add_trace(go.Bar(x=years, y=net, name="Net Profit (RsCr)", marker_color="#2ecc71"), secondary_y=False)
        fig.update_layout(
            paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
            font_color="#c8d0e0", barmode="group",
            legend=dict(font_size=10), height=260,
            margin=dict(t=20, b=30, l=50, r=20),
            xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER),
        )

        pe  = info.get("trailingPE",    "—")
        eps = info.get("trailingEps",   "—")
        div = info.get("dividendYield", 0)
        de  = info.get("debtToEquity",  "—")
        roe = info.get("returnOnEquity","—")
        cmp = info.get("currentPrice",  "—")
        cap = info.get("marketCap", 0)
        cap_str = f"Rs{cap/1e7:,.0f}Cr" if cap else "—"

        metrics_row = dbc.Row([
            dbc.Col(metric_card("CMP",       f"Rs{cmp}" if cmp != '—' else '—'), width=2),
            dbc.Col(metric_card("Mkt Cap",   cap_str), width=2),
            dbc.Col(metric_card("P/E",       f"{pe:.1f}x" if isinstance(pe, float) else str(pe)), width=2),
            dbc.Col(metric_card("EPS (TTM)", f"Rs{eps:.1f}" if isinstance(eps, float) else str(eps)), width=2),
            dbc.Col(metric_card("Div Yield", f"{div*100:.1f}%" if div else "—"), width=2),
            dbc.Col(metric_card("D/E Ratio", f"{de:.2f}x" if isinstance(de, float) else str(de)), width=2),
        ], className="mb-3")

        ai_text = call_claude(
            f"You are a senior Indian equity analyst. For {c['name']} ({c['short']}.NS), provide a concise 150-word "
            f"financial analysis covering: trailing P/E {pe}, EPS {eps}, Dividend yield {div}, D/E ratio {de}, ROE {roe}. "
            f"Comment on valuation vs sector peers, earnings quality, debt comfort level, and give a BUY/HOLD/SELL "
            f"recommendation with 12-month price target rationale. Terminal style, specific."
        )
    except Exception as e:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG, height=260)
        metrics_row = html.Div(f"Loading data... ({e})", style={"color": "#5a6382"})
        ai_text = "Loading financial data - please wait."

    return html.Div([
        html.H5(f"{c['name']} ({c['short']})", style={"color": GOLD, "marginBottom": "12px"}),
        section_head("Key Metrics - Live from NSE"),
        metrics_row,
        section_head("Revenue & Profit Trend (5 Years)"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        section_head("AI Financial Analysis"),
        ai_box(ai_text),
    ])

def build_candle(sym_idx=0, period="6mo"):
    c = COMPANIES[sym_idx]
    sym = c["sym"]
    try:
        hist = get_cached(f"hist_{sym}_{period}", fetch_price_data, sym, period)
        if hist is None or hist.empty:
            raise ValueError("No data")

        fig = go.Figure(go.Candlestick(
            x=hist.index, open=hist["Open"], high=hist["High"],
            low=hist["Low"], close=hist["Close"],
            increasing_line_color="#2ecc71", decreasing_line_color="#e74c3c",
            name=c["short"],
        ))
        if len(hist) >= 20:
            hist["MA20"] = hist["Close"].rolling(20).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=hist["MA20"], name="MA20",
                                     line=dict(color="#f5a623", width=1, dash="dot")))
        if len(hist) >= 50:
            hist["MA50"] = hist["Close"].rolling(50).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=hist["MA50"], name="MA50",
                                     line=dict(color="#3498db", width=1, dash="dot")))
        fig.update_layout(
            paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
            font_color="#c8d0e0", height=400,
            margin=dict(t=30, b=30, l=60, r=20),
            xaxis=dict(gridcolor=BORDER, rangeslider_visible=False),
            yaxis=dict(gridcolor=BORDER, title="Price (Rs)"),
            legend=dict(font_size=10, bgcolor=CARD_BG),
        )

        vol_fig = go.Figure(go.Bar(
            x=hist.index, y=hist["Volume"],
            marker_color=["#2ecc71" if c >= o else "#e74c3c"
                          for c, o in zip(hist["Close"], hist["Open"])],
        ))
        vol_fig.update_layout(
            paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
            font_color="#c8d0e0", height=120,
            margin=dict(t=10, b=30, l=60, r=20),
            xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER, title="Volume"),
            showlegend=False,
        )

        last_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2])
        chg_pct    = (last_close - prev_close) / prev_close * 100
        high_52w   = float(hist["Close"].max())
        low_52w    = float(hist["Close"].min())

        stats_row = dbc.Row([
            dbc.Col(metric_card("Last Close",  f"Rs{last_close:.2f}"), width=3),
            dbc.Col(metric_card("Change",      f"{chg_pct:+.2f}%",
                                color="#2ecc71" if chg_pct >= 0 else "#e74c3c"), width=3),
            dbc.Col(metric_card("Period High", f"Rs{high_52w:.2f}", "Resistance"), width=3),
            dbc.Col(metric_card("Period Low",  f"Rs{low_52w:.2f}", "Support"), width=3),
        ], className="mb-3")

        ai_text = call_claude(
            f"You are an expert technical analyst covering Indian equities. Analyse {c['name']} ({c['short']}.NS). "
            f"Last close: Rs{last_close:.2f}, period high: Rs{high_52w:.2f}, period low: Rs{low_52w:.2f}, "
            f"recent change: {chg_pct:+.2f}%. Give: 1) likely candlestick pattern, 2) key support/resistance, "
            f"3) volume interpretation, 4) MA20 vs MA50 positioning, 5) trading signal with stop loss. "
            f"Under 200 words, terminal analyst style."
        )
    except Exception as e:
        fig = go.Figure()
        vol_fig = go.Figure()
        fig.update_layout(paper_bgcolor=CARD_BG, height=400)
        vol_fig.update_layout(paper_bgcolor=CARD_BG, height=120)
        stats_row = html.Div(f"Data loading error: {e}", style={"color": "#e74c3c"})
        ai_text = "Unable to load chart data."

    pattern_cards = dbc.Row([
        dbc.Col(dbc.Card([dbc.CardBody([
            html.Div(p["name"], style={"color": GOLD, "fontWeight": "700", "marginBottom": "4px"}),
            html.Div(p["signal"], style={"fontSize": "11px", "color": "#c8d0e0", "marginBottom": "4px"}),
            html.Div(p["action"], style={"fontSize": "10px", "color": "#5a6382", "marginBottom": "6px"}),
            html.Div(p["example"], style={"fontSize": "10px", "color": "#3498db",
                                           "borderTop": f"1px solid {BORDER}", "paddingTop": "6px"}),
        ])], style={"background": CARD_BG, "border": f"1px solid {BORDER}", "borderRadius": "4px",
                    "marginBottom": "8px"}), width=6)
        for p in CANDLE_PATTERNS
    ])

    return html.Div([
        html.H5(f"{c['name']} - Technical Analysis", style={"color": GOLD, "marginBottom": "12px"}),
        dbc.Row([
            dbc.Col([
                html.Label("Timeframe:", style={"fontSize": "10px", "color": "#5a6382"}),
                dcc.Dropdown(
                    id="candle-period",
                    options=[
                        {"label": "1 Week",   "value": "1wk"},
                        {"label": "1 Month",  "value": "1mo"},
                        {"label": "3 Months", "value": "3mo"},
                        {"label": "6 Months", "value": "6mo"},
                        {"label": "1 Year",   "value": "1y"},
                        {"label": "2 Years",  "value": "2y"},
                    ],
                    value=period,
                    clearable=False,
                    style={"background": CARD_BG, "color": "#000", "fontSize": "11px"},
                ),
            ], width=3),
        ], className="mb-3"),
        stats_row,
        section_head("Candlestick Chart with MA20 / MA50"),
        dcc.Graph(figure=fig, config={"displayModeBar": True, "scrollZoom": True}),
        section_head("Volume"),
        dcc.Graph(figure=vol_fig, config={"displayModeBar": False}),
        section_head("AI Technical Interpretation"),
        ai_box(ai_text, "#2ecc71"),
        section_head("Candlestick Pattern Encyclopedia"),
        pattern_cards,
    ])

def build_geo():
    bubble_fig = go.Figure()
    for s in GEO_SCENARIOS:
        bubble_fig.add_trace(go.Scatter(
            x=[s["probability"]], y=[s["impact"]],
            mode="markers+text",
            marker=dict(size=s["probability"]*s["impact"]*60, color=s["color"], opacity=0.7),
            text=[s["title"]], textposition="top center",
            name=s["title"], textfont=dict(size=9),
        ))
    bubble_fig.update_layout(
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        font_color="#c8d0e0", height=320,
        xaxis=dict(title="Probability", gridcolor=BORDER, range=[0, 1.1]),
        yaxis=dict(title="Impact on Indian Mfg", gridcolor=BORDER, range=[0, 1.1]),
        margin=dict(t=20, b=40, l=60, r=20), showlegend=False,
    )

    scenario_cards = []
    for s in GEO_SCENARIOS:
        scenario_cards.append(dbc.Col(dbc.Card([dbc.CardBody([
            dbc.Row([
                dbc.Col(html.Div(s["title"], style={"color": s["color"], "fontWeight": "700", "fontSize": "12px"}), width=8),
                dbc.Col(html.Span(s["severity"], style={"background": s["color"]+"22", "color": s["color"],
                                                         "padding": "2px 6px", "borderRadius": "2px", "fontSize": "9px"}), width=4),
            ]),
            html.Div(s["desc"], style={"fontSize": "10px", "color": "#5a6382", "marginTop": "8px", "lineHeight": "1.6"}),
            html.Div("Winners: " + ", ".join(s["winners"]), style={"fontSize": "10px", "color": "#2ecc71", "marginTop": "6px"}),
            html.Div("Losers: " + ", ".join(s["losers"]),  style={"fontSize": "10px", "color": "#e74c3c", "marginTop": "2px"}),
            html.Div(s["signal"], style={"fontSize": "10px", "color": GOLD,
                                          "borderTop": f"1px solid {BORDER}", "marginTop": "8px", "paddingTop": "6px"}),
        ])], style={"background": CARD_BG, "border": f"1px solid {BORDER}", "borderRadius": "4px",
                    "marginBottom": "8px", "height": "100%"}), width=6))

    ai_text = call_claude(
        "You are a geopolitical risk analyst for Indian equity markets. Analyse combined impact of: "
        "1) Iran-US conflict, 2) Trump 2.0 tariffs on steel/aluminium, 3) US-China trade war, "
        "4) Red Sea disruption, 5) West Bengal elections 2026, 6) India GE 2029. "
        "For each, name top 2 Indian manufacturing companies most impacted and give 6-month price direction signal. "
        "200 words, terminal analyst style."
    )

    return html.Div([
        section_head("Active Geopolitical Scenarios"),
        dbc.Row(scenario_cards),
        section_head("Risk Matrix - Probability vs Impact"),
        dcc.Graph(figure=bubble_fig, config={"displayModeBar": False}),
        section_head("AI Geopolitical Analysis"),
        ai_box(ai_text, GOLD),
    ])

def build_elections():
    df = pd.DataFrame(ELECTION_HISTORY)
    bar_fig = go.Figure()
    bar_fig.add_trace(go.Bar(x=df["year"], y=df["before_30d"], name="30D Before", marker_color="#3498db"))
    bar_fig.add_trace(go.Bar(x=df["year"], y=df["result_day"], name="Result Day",
                             marker_color=[("#2ecc71" if v >= 0 else "#e74c3c") for v in df["result_day"]]))
    bar_fig.add_trace(go.Bar(x=df["year"], y=df["after_90d"], name="90D After", marker_color="#9b59b6"))
    bar_fig.update_layout(
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        font_color="#c8d0e0", barmode="group", height=300,
        margin=dict(t=20, b=40, l=50, r=20),
        xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER, title="NIFTY Return %"),
        legend=dict(font_size=10, bgcolor=CARD_BG),
    )
    bar_fig.add_hline(y=0, line_color="#5a6382", line_width=0.5)

    table_rows = [
        html.Tr([
            html.Td(r["year"]), html.Td(r["event"]),
            html.Td(f"{r['before_30d']:+.1f}%", style={"color": "#2ecc71" if r["before_30d"] >= 0 else "#e74c3c"}),
            html.Td(f"{r['result_day']:+.1f}%",  style={"color": "#2ecc71" if r["result_day"] >= 0 else "#e74c3c"}),
            html.Td(f"{r['after_90d']:+.1f}%",   style={"color": "#2ecc71"}),
            html.Td(r["note"], style={"fontSize": "10px", "color": "#5a6382"}),
        ]) for r in ELECTION_HISTORY
    ]

    ai_text = call_claude(
        "You are a quantitative political economist specialising in Indian equity markets. "
        "1) How did each Indian general election since 2004 affect Nifty Metal, Auto, and Infra? "
        "2) How did West Bengal state elections in 2011, 2016, 2021 affect Coal India, SAIL, and L&T? "
        "3) What does WB 2026 mean for these companies? "
        "4) Investment strategy: how to position manufacturing stocks 6 months, 1 month, and post-results. "
        "220 words, terminal style."
    )

    return html.Div([
        section_head("NIFTY Behaviour Around Indian General Elections (2004-2024)"),
        dcc.Graph(figure=bar_fig, config={"displayModeBar": False}),
        dbc.Table([
            html.Thead(html.Tr([html.Th("Year"), html.Th("Result"), html.Th("30D Before"),
                                html.Th("Result Day"), html.Th("90D After"), html.Th("Notes")],
                               style={"background": "#070b14", "fontSize": "10px", "color": "#5a6382"})),
            html.Tbody(table_rows),
        ], striped=False, hover=True, style={"fontSize": "11px", "background": CARD_BG}),
        section_head("AI Election Analysis"),
        ai_box(ai_text, "#9b59b6"),
    ])

def build_news():
    color_map = {"success": "#2ecc71", "primary": "#3498db", "danger": "#e74c3c"}
    type_map   = {"CAPEX": GOLD, "ACQUISITION": "#3498db", "JV": "#9b59b6",
                  "MERGER": "#9b59b6", "LEGAL": "#e74c3c"}
    timeline = []
    for n in NEWS_ITEMS:
        c = color_map.get(n["color"], "#888")
        tc = type_map.get(n["type"], "#888")
        timeline.append(html.Div([
            html.Div(f"{n['date']} - {n['co']}", style={"fontSize": "10px", "color": "#5a6382", "marginBottom": "2px"}),
            html.Span(n["type"], style={"background": tc+"22", "color": tc, "padding": "1px 6px",
                                         "borderRadius": "2px", "fontSize": "9px", "marginRight": "8px"}),
            html.Span(n["text"], style={"fontSize": "11px", "lineHeight": "1.6"}),
        ], style={"padding": "8px 12px", "borderLeft": f"2px solid {c}", "marginBottom": "8px",
                  "background": CARD_BG, "borderRadius": "0 4px 4px 0"}))

    ai_text = call_claude(
        "Analyse these 2024-25 Indian corporate events: "
        "1) Tata Steel Kalinganagar Phase 2 (Rs27,000Cr capex), "
        "2) BEL-IAI drone JV, "
        "3) Adani Ports Vizhinjam expansion, "
        "4) SAIL CCI investigation, "
        "5) Reliance-Disney merger. "
        "For each: 2-sentence price impact + action signal. 200 words, terminal style."
    )

    return html.Div([
        section_head("Acquisitions, Mergers & Capex"),
        html.Div(timeline),
        section_head("AI Corporate Action Analysis"),
        ai_box(ai_text, "#e74c3c"),
    ])

def build_competitor(sym_idx=0):
    c = COMPANIES[sym_idx]
    ai_text = call_claude(
        f"Senior strategy analyst brief for {c['name']} ({c['short']}): "
        f"1) Where {c['short']} leads vs domestic peers in {c['sector']}, "
        f"2) Where it lags global leaders, "
        f"3) THREE historical examples where a competitor announcement caused {c['short']} stock to react - "
        f"describe event, price move %, and what investors should have done, "
        f"4) Current competitive threat map for next 2 years, "
        f"5) One contrarian position where market is wrong about {c['short']}. "
        f"200 words, terminal style."
    )

    return html.Div([
        html.H5(f"{c['name']} - Competitor Intelligence", style={"color": GOLD, "marginBottom": "12px"}),
        dbc.Row([
            dbc.Col(metric_card("Sector", c["sector"]), width=3),
            dbc.Col(metric_card("NSE Symbol", c["short"]), width=3),
            dbc.Col(metric_card("Analysis", "Live AI", "Powered by Claude"), width=3),
            dbc.Col(metric_card("Market", "NSE/BSE", "India Listed"), width=3),
        ], className="mb-3"),
        section_head("AI Competitor Intelligence"),
        ai_box(ai_text, "#3498db"),
    ])

def build_aianalyst():
    return html.Div([
        section_head("Ask the AI Analyst - BharatTerm Intelligence Engine"),
        dbc.Card([dbc.CardBody([
            html.Div("Powered by Claude Sonnet - Ask anything about Top 20 Indian Manufacturing Companies.",
                     style={"fontSize": "11px", "color": "#5a6382", "marginBottom": "10px"}),
            dcc.Textarea(
                id="ai-query-input",
                placeholder="e.g. How will Trump tariffs impact Tata Steel vs SAIL? What does the inverted hammer on Reliance signal?",
                style={"width": "100%", "minHeight": "80px", "background": "#070b14",
                       "color": "#c8d0e0", "border": f"1px solid {BORDER}", "padding": "8px",
                       "fontFamily": "'Courier New', monospace", "fontSize": "12px", "borderRadius": "4px"},
            ),
            html.Div([
                dbc.Button("Ask Analyst", id="ask-btn", color="warning", size="sm", className="me-2"),
                dbc.Button("Steel: Tata vs JSW vs SAIL", id="tmpl1", color="secondary", size="sm", className="me-2"),
                dbc.Button("Auto: M&M Geo Risk",         id="tmpl2", color="secondary", size="sm", className="me-2"),
                dbc.Button("RIL Candlestick History",    id="tmpl3", color="secondary", size="sm", className="me-2"),
                dbc.Button("WB Election + Coal India",   id="tmpl4", color="secondary", size="sm"),
            ], className="mt-2"),
        ])], style={"background": CARD_BG, "border": f"1px solid {BORDER}", "marginBottom": "12px"}),
        section_head("Analysis Output"),
        html.Div(id="ai-output-box",
                 children=ai_box("Enter your question above and click Ask Analyst", GOLD),
                 style={"minHeight": "120px"}),
    ])

@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs",        "active_tab"),
    Input("selected-company", "data"),
    Input("candle-period-store", "data"),
)
def render_tab(tab, selected_idx, candle_period):
    idx = selected_idx or 0
    period = candle_period or "6mo"
    if tab == "overview":   return build_overview(idx)
    if tab == "financials": return build_financials(idx)
    if tab == "candle":     return build_candle(idx, period)
    if tab == "geo":        return build_geo()
    if tab == "competitor": return build_competitor(idx)
    if tab == "elections":  return build_elections()
    if tab == "news":       return build_news()
    if tab == "aianalyst":  return build_aianalyst()
    return build_overview(idx)

@app.callback(
    Output("candle-period-store", "data"),
    Input("candle-period", "value"),
    prevent_initial_call=True,
)
def store_candle_period(value):
    return value or "6mo"

@app.callback(
    Output("selected-company", "data"),
    [Input({"type": "sidebar-item", "index": i}, "n_clicks") for i in range(len(COMPANIES))],
    prevent_initial_call=True,
)
def select_company(*args):
    ctx = callback_context
    if not ctx.triggered:
        return 0
    prop = ctx.triggered[0]["prop_id"]
    idx = json.loads(prop.split(".")[0])["index"]
    return idx

@app.callback(
    Output("clock-display", "children"),
    Input("clock-interval", "n_intervals"),
)
def update_clock(_):
    now = datetime.now(datetime.timezone.utc if hasattr(datetime, 'timezone') else None)
    try:
        import datetime as dt
        now = dt.datetime.now(dt.timezone.utc) + timedelta(hours=5, minutes=30)
    except:
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    mkt_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    mkt_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now.weekday() < 5 and mkt_open <= now <= mkt_close:
        status, col = "NSE LIVE", "#2ecc71"
    else:
        status, col = "NSE CLOSED", "#e74c3c"
    return html.Span([f"IST {now.strftime('%H:%M')}  ", html.Span(status, style={"color": col})])

@app.callback(
    Output("ai-output-box",  "children"),
    Output("ai-query-input", "value"),
    Input("ask-btn", "n_clicks"),
    Input("tmpl1",   "n_clicks"),
    Input("tmpl2",   "n_clicks"),
    Input("tmpl3",   "n_clicks"),
    Input("tmpl4",   "n_clicks"),
    State("ai-query-input", "value"),
    prevent_initial_call=True,
)
def run_ai_query(ask, t1, t2, t3, t4, query):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    btn = ctx.triggered[0]["prop_id"].split(".")[0]
    templates = {
        "tmpl1": "Compare Tata Steel, JSW Steel, and SAIL on ROE, D/E ratio, EBITDA margin, and capex cycle. Which is the best risk-adjusted buy in Indian steel right now?",
        "tmpl2": "What geopolitical events will impact Mahindra & Mahindra's auto business in the next 6 months? Quantify the likely EPS impact.",
        "tmpl3": "What are the most significant candlestick patterns in Reliance Industries history that preceded major corrections or rallies?",
        "tmpl4": "How will West Bengal 2026 state elections affect Coal India stock? Use historical data from WB 2011, 2016, 2021 elections.",
    }
    if btn in templates:
        query = templates[btn]
    if not query:
        return dash.no_update, dash.no_update
    system_ctx = (
        "You are BharatTerm AI - senior equity analyst covering India's top 20 manufacturing companies. "
        "Answer with specific data, named examples, and clear investment signals. Terminal analyst style."
    )
    result = call_claude(f"{system_ctx}\n\nQuestion: {query}")
    return ai_box(result, GOLD), query

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  BharatTerm - India Manufacturing Intelligence Dashboard")
    print("="*60)
    print(f"\n  API Key: {'Set' if ANTHROPIC_API_KEY else 'Not set (AI features disabled)'}")
    print("\n  Starting dashboard at http://localhost:8050")
    print("  Press Ctrl+C to stop\n")
    app.run(debug=False, host="0.0.0.0", port=8050)