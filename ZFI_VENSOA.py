
import os
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import snowflake.connector

# ============================================================
# Page Configuration
# ============================================================
st.set_page_config(
    page_title="BGR Energy - ZFI Vendor SOA Finance Dashboard",
    page_icon="💰",
    layout="wide",
)

# ============================================================
# External Snowflake Connection
# ============================================================
# Streamlit Cloud secrets.toml format:
# [snowflake]
# user="BGRE_CLIENT"
# password="BGRE@123456789a"
# account="TVSNEXT-TVSNEXT"
# warehouse="BGRE_WH"
# database="SNOWFLAKE_POC"
# schema="ME2J_SCHEMA"

def get_secret(name, default=""):
    try:
        return st.secrets["snowflake"][name]
    except Exception:
        return os.getenv(name.upper(), default)

conn = snowflake.connector.connect(
    user=get_secret("user", "BGRE_CLIENT"),
    password=get_secret("password", "BGRE@123456789a"),
    account=get_secret("account", "TVSNEXT-TVSNEXT"),
    warehouse=get_secret("warehouse", "BGRE_WH"),
    database=get_secret("database", "SNOWFLAKE_POC"),
    schema=get_secret("schema", "ME2J_SCHEMA"),
)

TABLE_FQN = "SNOWFLAKE_POC.ME2J_SCHEMA.ZFI_VENSOA_FINAL_REPORT"
AGENT_FQN = "SNOWFLAKE_POC.ME2J_SCHEMA.BGRE_ZFI_VENSOA_AGENT"

# ============================================================
# BGR Logo
# ============================================================
BGR_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 200" width="115" height="145">
  <circle cx="80" cy="52" r="38" fill="#003893"/>
  <circle cx="80" cy="52" r="26" fill="#ffffff"/>
  <circle cx="80" cy="52" r="11" fill="#E31937"/>
  <rect x="77" y="8" width="6" height="18" rx="3" fill="#E31937"/>
  <text x="80" y="130" text-anchor="middle" font-family="Arial Black, Impact, sans-serif" font-size="52" font-weight="900" fill="#003893">BGR</text>
  <text x="80" y="165" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700" fill="#E31937" letter-spacing="6">ENERGY</text>
</svg>"""

# ============================================================
# CSS Styling
# ============================================================
st.markdown("""
<style>
.block-container {
    padding-top: 1.1rem;
    padding-bottom: 2rem;
    max-width: 100%;
}
.kpi-card {
    background: white;
    padding: 20px 18px;
    border-radius: 18px;
    border: 1px solid #E5E7EB;
    box-shadow: 0 3px 12px rgba(0,0,0,0.08);
    min-height: 130px;
}
.kpi-title {
    font-size: 13px;
    color: #6B7280;
    margin-bottom: 10px;
    font-weight: 700;
}
.kpi-value {
    font-size: 24px;
    font-weight: 850;
    color: #111827;
    line-height: 1.25;
    white-space: normal;
    word-break: break-word;
}
.amount-value {
    font-size: 20px !important;
}
.section-title {
    font-size: 23px;
    font-weight: 850;
    margin-top: 18px;
    margin-bottom: 10px;
    color: #111827;
}
.small-note {
    color:#6B7280;
    font-size:13px;
}
.stPlotlyChart,
.stPlotlyChart *,
.js-plotly-plot,
.js-plotly-plot *,
.plot-container,
.plot-container *,
.svg-container,
.svg-container *,
.main-svg,
.main-svg *,
.cartesianlayer,
.cartesianlayer *,
.barlayer,
.barlayer *,
.scatterlayer,
.scatterlayer *,
.nsewdrag,
.drag,
.draglayer,
.draglayer *,
.zoomlayer,
.cursor-crosshair,
.cursor-move,
.cursor-pointer,
.cursor-ew-resize,
.cursor-ns-resize {
    cursor: default !important;
}
.modebar {
    display: none !important;
}
div[data-testid="stDataFrame"] {
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# Data Load Functions
# ============================================================
@st.cache_data(ttl=600)
def read_sql(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, conn)

@st.cache_data(ttl=600)
def load_data() -> pd.DataFrame:
    sql = f"""
        SELECT
            *,
            CASE WHEN DEBIT_CREDIT_IND = 'S' THEN AMOUNT_LC ELSE 0 END AS DEBIT,
            CASE WHEN DEBIT_CREDIT_IND = 'H' THEN AMOUNT_LC ELSE 0 END AS CREDIT
        FROM {TABLE_FQN}
        ORDER BY
            VENDOR,
            FISCAL_YEAR,
            POSTING_DATE,
            DOC_NO,
            ITEM
    """
    return read_sql(sql)

def clear_all_caches():
    st.cache_data.clear()

# ============================================================
# Formatting Helpers
# ============================================================
def fmt_inr(val):
    try:
        val = float(val)
    except Exception:
        val = 0.0

    sign = "-" if val < 0 else ""
    val = abs(val)

    if val >= 10000000:
        return f"{sign}INR {val/10000000:,.2f} Cr"
    if val >= 100000:
        return f"{sign}INR {val/100000:,.2f} L"
    return f"{sign}INR {val:,.2f}"

def num_fmt(val, decimals=0):
    try:
        return f"{float(val):,.{decimals}f}"
    except Exception:
        return "0"

def kpi(title, value, is_amount=False):
    value_class = "kpi-value amount-value" if is_amount else "kpi-value"
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="{value_class}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# Data Cleaning
# ============================================================
def clean_finance_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    numeric_cols = [
        "AMOUNT_LC", "DEBIT", "CREDIT", "TDS_AMOUNT", "TDS_BASE",
        "OUTSTANDING_BALANCE", "FISCAL_YEAR", "ITEM"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    text_cols = [
        "VENDOR", "VENDOR_NAME", "DOC_NO", "DOC_TYPE", "DOC_TYPE_DESC",
        "REFERENCE", "ASSIGNMENT", "CURRENCY", "DEBIT_CREDIT_IND",
        "TEXT", "GL_ACCT", "PROFIT_CTR", "PROFIT_CENTER_NAME",
        "SECTION_CODE_DESC", "TDS_TYPE", "TDS_CODE", "HEADER_TEXT",
        "ITEM_STATUS", "PAYMENT_METHOD", "POSTING_KEY"
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("N/A").astype(str)

    for col in ["POSTING_DATE", "DOC_DATE"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df

# ============================================================
# Business Summary Helpers
# ============================================================
def get_vendor_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "VENDOR", "VENDOR_NAME", "TOTAL_DEBIT", "TOTAL_CREDIT",
                "OUTSTANDING_BALANCE", "ABS_OUTSTANDING", "BALANCE_TYPE",
                "TRANSACTIONS", "OPEN_ITEMS", "LABEL"
            ]
        )

    summary = (
        df.groupby(["VENDOR", "VENDOR_NAME"], dropna=False, as_index=False)
        .agg(
            TOTAL_DEBIT=("DEBIT", "sum"),
            TOTAL_CREDIT=("CREDIT", "sum"),
            TRANSACTIONS=("DOC_NO", "count"),
            OPEN_ITEMS=("ITEM_STATUS", lambda s: (s.astype(str).str.upper() == "OPEN").sum()),
        )
        .fillna(0)
    )

    summary["OUTSTANDING_BALANCE"] = summary["TOTAL_DEBIT"] - summary["TOTAL_CREDIT"]
    summary["ABS_OUTSTANDING"] = summary["OUTSTANDING_BALANCE"].abs()
    summary["BALANCE_TYPE"] = summary["OUTSTANDING_BALANCE"].apply(
        lambda x: "Payable (+)" if x > 0 else ("Advance / Credit Balance (-)" if x < 0 else "Settled")
    )
    summary["LABEL"] = summary["VENDOR"].astype(str) + " - " + summary["VENDOR_NAME"].astype(str)

    return summary

def get_balance_status_df(df: pd.DataFrame) -> pd.DataFrame:
    vendor_bal = get_vendor_summary(df)
    if vendor_bal.empty:
        return pd.DataFrame(columns=["BALANCE_TYPE", "VENDOR_COUNT", "OUTSTANDING_VALUE"])

    return (
        vendor_bal.groupby("BALANCE_TYPE", as_index=False)
        .agg(
            VENDOR_COUNT=("VENDOR", "nunique"),
            OUTSTANDING_VALUE=("OUTSTANDING_BALANCE", "sum"),
        )
        .sort_values("VENDOR_COUNT", ascending=False)
    )

# ============================================================
# Table Helpers
# ============================================================
def transaction_table(df: pd.DataFrame, rows=500):
    cols = [
        "VENDOR", "VENDOR_NAME", "DOC_NO", "DOC_TYPE", "DOC_TYPE_DESC",
        "POSTING_DATE", "DOC_DATE", "FISCAL_YEAR", "REFERENCE", "ASSIGNMENT",
        "DEBIT", "CREDIT", "AMOUNT_LC", "CURRENCY", "DEBIT_CREDIT_IND",
        "TEXT", "GL_ACCT", "PROFIT_CTR", "PROFIT_CENTER_NAME",
        "SECTION_CODE_DESC", "TDS_TYPE", "TDS_CODE", "TDS_BASE", "TDS_AMOUNT",
        "HEADER_TEXT", "ITEM_STATUS"
    ]
    available = [c for c in cols if c in df.columns]
    show_df = df[available].head(rows).copy()

    st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "VENDOR_NAME": st.column_config.TextColumn("Vendor Name", width="large"),
            "DOC_TYPE_DESC": st.column_config.TextColumn("Document Type", width="large"),
            "TEXT": st.column_config.TextColumn("Text", width="large"),
            "HEADER_TEXT": st.column_config.TextColumn("Header Text", width="large"),
            "DEBIT": st.column_config.NumberColumn("Debit", format="INR %.2f"),
            "CREDIT": st.column_config.NumberColumn("Credit", format="INR %.2f"),
            "AMOUNT_LC": st.column_config.NumberColumn("Amount LC", format="INR %.2f"),
            "TDS_BASE": st.column_config.NumberColumn("TDS Base", format="INR %.2f"),
            "TDS_AMOUNT": st.column_config.NumberColumn("TDS Amount", format="INR %.2f"),
        },
    )

def vendor_balance_table(df: pd.DataFrame, rows=100):
    vendor_bal = get_vendor_summary(df).sort_values("ABS_OUTSTANDING", ascending=False)
    if vendor_bal.empty:
        st.info("No vendor balance data available.")
        return

    st.dataframe(
        vendor_bal[
            [
                "VENDOR", "VENDOR_NAME", "TOTAL_DEBIT", "TOTAL_CREDIT",
                "OUTSTANDING_BALANCE", "BALANCE_TYPE", "TRANSACTIONS", "OPEN_ITEMS"
            ]
        ].head(rows),
        use_container_width=True,
        hide_index=True,
        height=360,
        column_config={
            "VENDOR_NAME": st.column_config.TextColumn("Vendor Name", width="large"),
            "TOTAL_DEBIT": st.column_config.NumberColumn("Total Debit", format="INR %.2f"),
            "TOTAL_CREDIT": st.column_config.NumberColumn("Total Credit", format="INR %.2f"),
            "OUTSTANDING_BALANCE": st.column_config.NumberColumn("Outstanding Balance", format="INR %.2f"),
            "BALANCE_TYPE": st.column_config.TextColumn("Balance Type", width="medium"),
        },
    )

# ============================================================
# Popup / Drilldown Helpers
# ============================================================
def mini_summary(df: pd.DataFrame, title: str):
    total_debit = df["DEBIT"].sum() if "DEBIT" in df.columns else 0
    total_credit = df["CREDIT"].sum() if "CREDIT" in df.columns else 0
    net_outstanding = total_debit - total_credit
    open_items = (df["ITEM_STATUS"].astype(str).str.upper() == "OPEN").sum() if "ITEM_STATUS" in df.columns else 0

    st.markdown(f"#### {title}")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Transactions", num_fmt(len(df)))
    with c2:
        kpi("Vendors", num_fmt(df["VENDOR"].nunique() if "VENDOR" in df.columns else 0))
    with c3:
        kpi("Net Outstanding", fmt_inr(net_outstanding), is_amount=True)
    with c4:
        kpi("Open Items", num_fmt(open_items))

@st.dialog("Drilldown Details", width="large")
def show_popup(title: str, df: pd.DataFrame):
    st.markdown(f"### {title}")
    mini_summary(df, title)

    st.markdown("#### Vendor Balance Summary")
    vendor_balance_table(df, rows=50)

    st.markdown("#### Transaction Details")
    transaction_table(df, rows=500)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Drilldown Records",
        csv,
        "ZFI_VENSOA_DRILLDOWN_RECORDS.csv",
        "text/csv",
        use_container_width=True,
    )

# ============================================================
# Plotly Helpers
# ============================================================
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "scrollZoom": False,
    "doubleClick": False,
    "responsive": True,
}

CHART_COLORS = [
    "#2563EB", "#DC2626", "#16A34A", "#F59E0B", "#7C3AED",
    "#0891B2", "#EA580C", "#4F46E5", "#65A30D", "#BE185D"
]

BALANCE_COLORS = {
    "Payable (+)": "#16A34A",
    "Advance / Credit Balance (-)": "#DC2626",
    "Settled": "#6B7280",
}

def clean_chart(fig, height=560):
    fig.update_layout(
        height=height,
        dragmode=False,
        hovermode="closest",
        clickmode="event",
        margin=dict(l=10, r=140, t=55, b=70),
        font=dict(size=11),
    )
    fig.update_traces(
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.95)),
    )
    return fig

def mark_active_chart(chart_key: str):
    st.session_state.zfi_active_chart = chart_key

def chart_event(fig, key: str):
    return st.plotly_chart(
        fig,
        use_container_width=True,
        key=key,
        on_select=lambda chart_key=key: mark_active_chart(chart_key),
        config=PLOTLY_CONFIG,
    )

def get_clicked_value(event_result, preferred=None):
    try:
        if event_result and event_result.selection.points:
            point = event_result.selection.points[0]

            if preferred and preferred in point and point.get(preferred) is not None:
                val = point.get(preferred)
                if isinstance(val, (list, tuple)) and val:
                    return val[0]
                return val

            for alt in ["customdata", "y", "x", "label", "name"]:
                if alt in point and point.get(alt) is not None:
                    val = point.get(alt)
                    if isinstance(val, (list, tuple)) and val:
                        return val[0]
                    return val
    except Exception:
        return None
    return None

def horizontal_bar(
    df,
    x,
    y,
    title,
    key,
    source_df,
    filter_col,
    selected_field="y",
    text_col=None,
    custom_data=None,
    height=560,
    x_title=None,
    y_title=None,
):
    if df.empty:
        st.caption("No data available.")
        return None, None

    fig = px.bar(
        df,
        x=x,
        y=y,
        orientation="h",
        text=text_col or x,
        custom_data=custom_data,
        title=title,
    )

    fig.update_traces(
        texttemplate="%{text:,.2f}",
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        yaxis={"automargin": True, "categoryorder": "total ascending"},
        xaxis_title=x_title or x,
        yaxis_title=y_title or y,
    )

    event = chart_event(clean_chart(fig, height), key)
    selected = get_clicked_value(event, selected_field) if st.session_state.get("zfi_active_chart") == key else None

    if selected is None:
        return None, None

    return selected, source_df[source_df[filter_col].astype(str) == str(selected)].copy()

# ============================================================
# Load Data
# ============================================================
with st.spinner("Loading ZFI Vendor SOA data from Snowflake..."):
    df_all = clean_finance_df(load_data())

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown(BGR_LOGO_SVG, unsafe_allow_html=True)
    st.caption("ZFI Vendor SOA Finance Dashboard | Currency: INR")

    st.button("🔄 Refresh data", on_click=clear_all_caches, use_container_width=True)

    st.divider()
    st.markdown("### Filters")

    vendors = sorted(df_all["VENDOR"].dropna().unique().tolist()) if "VENDOR" in df_all.columns else []
    vendor_names = sorted(df_all["VENDOR_NAME"].dropna().unique().tolist()) if "VENDOR_NAME" in df_all.columns else []
    doc_types = sorted(df_all["DOC_TYPE_DESC"].dropna().unique().tolist()) if "DOC_TYPE_DESC" in df_all.columns else []
    statuses = sorted(df_all["ITEM_STATUS"].dropna().unique().tolist()) if "ITEM_STATUS" in df_all.columns else []
    fiscal_years = sorted(df_all["FISCAL_YEAR"].dropna().astype(str).unique().tolist()) if "FISCAL_YEAR" in df_all.columns else []

    sel_vendor = st.multiselect("Vendor ID", vendors, default=[], placeholder="All vendors")
    sel_vendor_name = st.multiselect("Vendor Name", vendor_names, default=[], placeholder="All vendor names")
    sel_doc_type = st.multiselect("Document type", doc_types, default=[], placeholder="All types")
    sel_status = st.multiselect("Item status", statuses, default=[], placeholder="All statuses")
    sel_fiscal_year = st.multiselect("Fiscal year", fiscal_years, default=[], placeholder="All years")
    sel_dc = st.multiselect("Debit / Credit", ["S (Debit)", "H (Credit)"], default=[], placeholder="All")
    balance_view = st.selectbox(
        "Outstanding view",
        ["All", "Payable (+)", "Advance / Credit Balance (-)", "Settled"]
    )
    top_n = st.slider("Top N", 5, 30, 15)
    dashboard_theme = st.selectbox("Dashboard theme", ["Light", "Dark"], index=0)

# ============================================================
# Header
# ============================================================
st.markdown(BGR_LOGO_SVG, unsafe_allow_html=True)
st.title("ZFI Vendor Statement of Account - Finance Dashboard")
st.caption("Vendor-wise outstanding balance, payable / advance split, transaction analytics, TDS, profit center, and AI-powered finance Q&A.")


if dashboard_theme == "Dark":
    st.markdown("""
    <style>
    .stApp {background-color:#0F172A; color:#E5E7EB;}
    .block-container {background-color:#0F172A;}
    [data-testid="stSidebar"] {background-color:#111827;}
    .kpi-card {background:#1F2937 !important; border:1px solid #374151 !important; box-shadow:0 4px 14px rgba(0,0,0,0.35) !important;}
    .kpi-title {color:#CBD5E1 !important;}
    .kpi-value {color:#FFFFFF !important;}
    .section-title, h1, h2, h3, h4 {color:#F8FAFC !important;}
    p, label, span {color:#E5E7EB;}
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    .stApp {background-color:#FFFFFF;}
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# Apply Filters
# ============================================================
fdf = df_all.copy()

if sel_vendor:
    fdf = fdf[fdf["VENDOR"].isin(sel_vendor)]
if sel_vendor_name:
    fdf = fdf[fdf["VENDOR_NAME"].isin(sel_vendor_name)]
if sel_doc_type:
    fdf = fdf[fdf["DOC_TYPE_DESC"].isin(sel_doc_type)]
if sel_status:
    fdf = fdf[fdf["ITEM_STATUS"].isin(sel_status)]
if sel_fiscal_year and "FISCAL_YEAR" in fdf.columns:
    fdf = fdf[fdf["FISCAL_YEAR"].astype(str).isin(sel_fiscal_year)]
if sel_dc:
    dc_map = {"S (Debit)": "S", "H (Credit)": "H"}
    dc_values = [dc_map[d] for d in sel_dc]
    fdf = fdf[fdf["DEBIT_CREDIT_IND"].isin(dc_values)]

vendor_summary_df = get_vendor_summary(fdf)

if balance_view != "All":
    keep_vendors = vendor_summary_df[vendor_summary_df["BALANCE_TYPE"] == balance_view]["VENDOR"].astype(str).tolist()
    fdf = fdf[fdf["VENDOR"].astype(str).isin(keep_vendors)]
    vendor_summary_df = get_vendor_summary(fdf)

# ============================================================
# Tabs
# ============================================================
tab1, tab2, tab3 = st.tabs([
    "📊 Dashboard",
    "🔍 Data Explorer",
    "🤖 AI Assistant"
])

# ============================================================
# Dashboard Tab
# ============================================================
with tab1:
    st.markdown('<div class="section-title">Executive Finance Command Center</div>', unsafe_allow_html=True)

    popup_title = None
    popup_df = None

    total_debit = fdf["DEBIT"].sum() if "DEBIT" in fdf.columns else 0
    total_credit = fdf["CREDIT"].sum() if "CREDIT" in fdf.columns else 0
    net_outstanding = total_debit - total_credit
    total_tds = fdf["TDS_AMOUNT"].sum() if "TDS_AMOUNT" in fdf.columns else 0
    total_transactions = len(fdf)
    unique_vendors = fdf["VENDOR"].nunique() if "VENDOR" in fdf.columns else 0
    open_items = (fdf["ITEM_STATUS"].astype(str).str.upper() == "OPEN").sum() if "ITEM_STATUS" in fdf.columns else 0
    cleared_items = (fdf["ITEM_STATUS"].astype(str).str.upper() == "CLEARED").sum() if "ITEM_STATUS" in fdf.columns else 0

    payable_vendor_count = (vendor_summary_df["OUTSTANDING_BALANCE"] > 0).sum() if not vendor_summary_df.empty else 0
    advance_vendor_count = (vendor_summary_df["OUTSTANDING_BALANCE"] < 0).sum() if not vendor_summary_df.empty else 0

    # --------------------------------------------------------
    # KPI Row 1
    # --------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi("Total Debit", fmt_inr(total_debit), is_amount=True)
        if st.button("View details", key="zfi_kpi_debit", use_container_width=True):
            st.session_state.zfi_active_chart = "__kpi__"
            popup_title = "Total Debit Transactions"
            popup_df = fdf[fdf["DEBIT"] > 0].copy()

    with k2:
        kpi("Total Credit", fmt_inr(total_credit), is_amount=True)
        if st.button("View details", key="zfi_kpi_credit", use_container_width=True):
            st.session_state.zfi_active_chart = "__kpi__"
            popup_title = "Total Credit Transactions"
            popup_df = fdf[fdf["CREDIT"] > 0].copy()

    with k3:
        kpi("Net Outstanding", fmt_inr(net_outstanding), is_amount=True)
        if st.button("View details", key="zfi_kpi_net", use_container_width=True):
            st.session_state.zfi_active_chart = "__kpi__"
            popup_title = "Net Outstanding Transactions"
            popup_df = fdf.copy()

    with k4:
        kpi("TDS Deducted", fmt_inr(total_tds), is_amount=True)
        if st.button("View details", key="zfi_kpi_tds", use_container_width=True):
            st.session_state.zfi_active_chart = "__kpi__"
            popup_title = "TDS Transactions"
            popup_df = fdf[fdf.get("TDS_AMOUNT", 0) > 0].copy()

    # --------------------------------------------------------
    # KPI Row 2
    # --------------------------------------------------------
    k5, k6, k7, k8 = st.columns(4)

    with k5:
        kpi("Transactions", num_fmt(total_transactions))
        if st.button("View details", key="zfi_kpi_transactions", use_container_width=True):
            st.session_state.zfi_active_chart = "__kpi__"
            popup_title = "All Transactions"
            popup_df = fdf.copy()

    with k6:
        kpi("Unique Vendors", num_fmt(unique_vendors))
        if st.button("View details", key="zfi_kpi_vendors", use_container_width=True):
            st.session_state.zfi_active_chart = "__kpi__"
            popup_title = "Vendor Summary"
            popup_df = fdf.copy()

    with k7:
        kpi("Payable Vendors (+)", num_fmt(payable_vendor_count))
        if st.button("View details", key="zfi_kpi_payable", use_container_width=True):
            st.session_state.zfi_active_chart = "__kpi__"
            vendors_pos = vendor_summary_df[vendor_summary_df["OUTSTANDING_BALANCE"] > 0]["VENDOR"].astype(str).tolist()
            popup_title = "Payable Vendors"
            popup_df = fdf[fdf["VENDOR"].astype(str).isin(vendors_pos)].copy()

    with k8:
        kpi("Advance / Credit Vendors (-)", num_fmt(advance_vendor_count))
        if st.button("View details", key="zfi_kpi_advance", use_container_width=True):
            st.session_state.zfi_active_chart = "__kpi__"
            vendors_neg = vendor_summary_df[vendor_summary_df["OUTSTANDING_BALANCE"] < 0]["VENDOR"].astype(str).tolist()
            popup_title = "Advance / Credit Balance Vendors"
            popup_df = fdf[fdf["VENDOR"].astype(str).isin(vendors_neg)].copy()

    st.caption(f"Filtered records: {len(fdf):,} | Vendors: {unique_vendors:,} | Open items: {open_items:,} | Cleared items: {cleared_items:,}")
    st.divider()

    # --------------------------------------------------------
    # Main Outstanding Chart
    # --------------------------------------------------------
    st.markdown("### Vendor-wise Outstanding Balance - Payable and Advance")

    outstanding_chart = (
        vendor_summary_df[vendor_summary_df["OUTSTANDING_BALANCE"] != 0]
        .sort_values("ABS_OUTSTANDING", ascending=False)
        .head(top_n)
        .copy()
    )

    if not outstanding_chart.empty:
        fig_outstanding = px.bar(
            outstanding_chart,
            x="OUTSTANDING_BALANCE",
            y="LABEL",
            orientation="h",
            text="OUTSTANDING_BALANCE",
            custom_data=[
                "VENDOR", "VENDOR_NAME", "TOTAL_DEBIT", "TOTAL_CREDIT",
                "OUTSTANDING_BALANCE", "BALANCE_TYPE", "TRANSACTIONS", "OPEN_ITEMS"
            ],
            color="BALANCE_TYPE",
            color_discrete_map=BALANCE_COLORS,
            title="Top Vendor Outstanding Balance"
        )

        fig_outstanding.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=
                "<b>%{customdata[1]}</b><br>" +
                "Vendor ID: %{customdata[0]}<br>" +
                "Total Debit: INR %{customdata[2]:,.2f}<br>" +
                "Total Credit: INR %{customdata[3]:,.2f}<br>" +
                "Outstanding: INR %{customdata[4]:,.2f}<br>" +
                "Balance Type: %{customdata[5]}<br>" +
                "Transactions: %{customdata[6]:,.0f}<br>" +
                "Open Items: %{customdata[7]:,.0f}<extra></extra>"
        )

        fig_outstanding.update_layout(
            yaxis={"automargin": True, "categoryorder": "total ascending"},
            xaxis_title="Outstanding Balance (Debit - Credit)",
            yaxis_title="Vendor",
        )

        event = chart_event(clean_chart(fig_outstanding, 720), "zfi_outstanding_chart")
        selected_vendor = get_clicked_value(event, "customdata") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_outstanding_chart") else None

        if selected_vendor:
            popup_title = f"Outstanding Vendor Drilldown: {selected_vendor}"
            popup_df = fdf[fdf["VENDOR"].astype(str) == str(selected_vendor)].copy()
    else:
        st.info("No outstanding vendor balance available for current filters.")

    vendor_balance_table(fdf, rows=50)

    # --------------------------------------------------------
    # Row 2: Positive / Negative Balance
    # --------------------------------------------------------
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Top Payable Vendors (+)")
        payable_df = (
            vendor_summary_df[vendor_summary_df["OUTSTANDING_BALANCE"] > 0]
            .sort_values("OUTSTANDING_BALANCE", ascending=False)
            .head(top_n)
            .copy()
        )

        if not payable_df.empty:
            fig_payable = px.bar(
                payable_df,
                x="OUTSTANDING_BALANCE",
                y="LABEL",
                orientation="h",
                text="OUTSTANDING_BALANCE",
                custom_data=["VENDOR", "VENDOR_NAME", "TOTAL_DEBIT", "TOTAL_CREDIT", "TRANSACTIONS"],
                title="Top Payable Vendors",
                color_discrete_sequence=["#16A34A"]
            )

            fig_payable.update_traces(
                texttemplate="%{text:,.2f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=
                    "<b>%{customdata[1]}</b><br>" +
                    "Vendor ID: %{customdata[0]}<br>" +
                    "Debit: INR %{customdata[2]:,.2f}<br>" +
                    "Credit: INR %{customdata[3]:,.2f}<br>" +
                    "Payable: INR %{x:,.2f}<br>" +
                    "Transactions: %{customdata[4]:,.0f}<extra></extra>"
            )

            fig_payable.update_layout(
                yaxis={"automargin": True, "categoryorder": "total ascending"},
                xaxis_title="Payable Outstanding",
                yaxis_title="Vendor",
            )

            event = chart_event(clean_chart(fig_payable, 560), "zfi_payable_chart")
            selected_vendor = get_clicked_value(event, "customdata") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_payable_chart") else None

            if selected_vendor:
                popup_title = f"Payable Vendor Drilldown: {selected_vendor}"
                popup_df = fdf[fdf["VENDOR"].astype(str) == str(selected_vendor)].copy()
        else:
            st.caption("No payable vendors available.")

    with c2:
        st.markdown("### Top Advance / Credit Balance Vendors (-)")
        advance_df = vendor_summary_df[vendor_summary_df["OUTSTANDING_BALANCE"] < 0].copy()
        advance_df["DISPLAY_ADVANCE"] = advance_df["OUTSTANDING_BALANCE"].abs()
        advance_df = advance_df.sort_values("DISPLAY_ADVANCE", ascending=False).head(top_n)

        if not advance_df.empty:
            fig_advance = px.bar(
                advance_df,
                x="DISPLAY_ADVANCE",
                y="LABEL",
                orientation="h",
                text="DISPLAY_ADVANCE",
                custom_data=["VENDOR", "VENDOR_NAME", "TOTAL_DEBIT", "TOTAL_CREDIT", "OUTSTANDING_BALANCE"],
                title="Top Advance / Credit Balance Vendors",
                color_discrete_sequence=["#DC2626"]
            )

            fig_advance.update_traces(
                texttemplate="%{text:,.2f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=
                    "<b>%{customdata[1]}</b><br>" +
                    "Vendor ID: %{customdata[0]}<br>" +
                    "Debit: INR %{customdata[2]:,.2f}<br>" +
                    "Credit: INR %{customdata[3]:,.2f}<br>" +
                    "Outstanding: INR %{customdata[4]:,.2f}<extra></extra>"
            )

            fig_advance.update_layout(
                yaxis={"automargin": True, "categoryorder": "total ascending"},
                xaxis_title="Advance / Credit Balance Amount",
                yaxis_title="Vendor",
            )

            event = chart_event(clean_chart(fig_advance, 560), "zfi_advance_chart")
            selected_vendor = get_clicked_value(event, "customdata") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_advance_chart") else None

            if selected_vendor:
                popup_title = f"Advance / Credit Vendor Drilldown: {selected_vendor}"
                popup_df = fdf[fdf["VENDOR"].astype(str) == str(selected_vendor)].copy()
        else:
            st.caption("No advance / credit balance vendors available.")

    # --------------------------------------------------------
    # Row 3: Document and Status
    # --------------------------------------------------------
    c3, c4 = st.columns(2)

    with c3:
        st.markdown("### Debit / Credit Activity by Document Type")
        if not fdf.empty and "DOC_TYPE_DESC" in fdf.columns:
            doc_chart = (
                fdf.groupby("DOC_TYPE_DESC", as_index=False)
                .agg(
                    DEBIT=("DEBIT", "sum"),
                    CREDIT=("CREDIT", "sum"),
                    TRANSACTIONS=("DOC_NO", "count")
                )
                .fillna(0)
            )
            doc_chart["TOTAL_ACTIVITY"] = doc_chart["DEBIT"] + doc_chart["CREDIT"]
            doc_chart = doc_chart.sort_values("TOTAL_ACTIVITY", ascending=False).head(top_n)

            fig_doc = px.bar(
                doc_chart,
                x="TOTAL_ACTIVITY",
                y="DOC_TYPE_DESC",
                orientation="h",
                text="TOTAL_ACTIVITY",
                custom_data=["DEBIT", "CREDIT", "TRANSACTIONS"],
                title="Document Type Activity",
                color_discrete_sequence=["#7C3AED"]
            )

            fig_doc.update_traces(
                texttemplate="%{text:,.2f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=
                    "<b>%{y}</b><br>" +
                    "Total Activity: INR %{x:,.2f}<br>" +
                    "Debit: INR %{customdata[0]:,.2f}<br>" +
                    "Credit: INR %{customdata[1]:,.2f}<br>" +
                    "Transactions: %{customdata[2]:,.0f}<extra></extra>"
            )

            fig_doc.update_layout(
                yaxis={"automargin": True, "categoryorder": "total ascending"},
                xaxis_title="Debit + Credit",
                yaxis_title="Document Type"
            )

            event = chart_event(clean_chart(fig_doc, 540), "zfi_doc_type_chart")
            selected_doc = get_clicked_value(event, "y") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_doc_type_chart") else None

            if selected_doc:
                popup_title = f"Document Type Drilldown: {selected_doc}"
                popup_df = fdf[fdf["DOC_TYPE_DESC"].astype(str) == str(selected_doc)].copy()

    with c4:
        st.markdown("### Open vs Cleared Items")
        if not fdf.empty and "ITEM_STATUS" in fdf.columns:
            status_chart = (
                fdf.groupby("ITEM_STATUS", as_index=False)
                .agg(
                    TRANSACTIONS=("ITEM_STATUS", "size"),
                    AMOUNT=("AMOUNT_LC", "sum")
                )
                .fillna(0)
                .sort_values("TRANSACTIONS", ascending=False)
            )

            fig_status = px.bar(
                status_chart,
                x="TRANSACTIONS",
                y="ITEM_STATUS",
                orientation="h",
                text="TRANSACTIONS",
                custom_data=["AMOUNT"],
                title="Item Status Split",
                color_discrete_sequence=["#F59E0B"]
            )

            fig_status.update_traces(
                texttemplate="%{text:,.0f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=
                    "<b>%{y}</b><br>" +
                    "Transactions: %{x:,.0f}<br>" +
                    "Amount: INR %{customdata[0]:,.2f}<extra></extra>"
            )

            fig_status.update_layout(
                yaxis={"automargin": True, "categoryorder": "total ascending"},
                xaxis_title="Transactions",
                yaxis_title="Item Status"
            )

            event = chart_event(clean_chart(fig_status, 540), "zfi_status_chart")
            selected_status = get_clicked_value(event, "y") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_status_chart") else None

            if selected_status:
                popup_title = f"Item Status Drilldown: {selected_status}"
                popup_df = fdf[fdf["ITEM_STATUS"].astype(str) == str(selected_status)].copy()

    # --------------------------------------------------------
    # Row 4: Monthly and Profit Center
    # --------------------------------------------------------
    c5, c6 = st.columns(2)

    with c5:
        st.markdown("### Monthly Debit / Credit / Outstanding Trend")
        if not fdf.empty and "POSTING_DATE" in fdf.columns:
            mdf = fdf.dropna(subset=["POSTING_DATE"]).copy()
            mdf["MONTH"] = mdf["POSTING_DATE"].dt.to_period("M").astype(str)

            monthly_chart = (
                mdf.groupby("MONTH", as_index=False)
                .agg(
                    DEBIT=("DEBIT", "sum"),
                    CREDIT=("CREDIT", "sum")
                )
                .fillna(0)
                .sort_values("MONTH")
            )

            monthly_chart["OUTSTANDING"] = monthly_chart["DEBIT"] - monthly_chart["CREDIT"]

            fig_month = px.line(
                monthly_chart,
                x="MONTH",
                y=["DEBIT", "CREDIT", "OUTSTANDING"],
                markers=True,
                title="Monthly Finance Trend",
                color_discrete_sequence=["#2563EB", "#DC2626", "#16A34A"]
            )

            fig_month.update_traces(
                hovertemplate="<b>%{x}</b><br>%{fullData.name}: INR %{y:,.2f}<extra></extra>"
            )

            fig_month.update_layout(
                xaxis_title="Month",
                yaxis_title="Amount"
            )

            event = chart_event(clean_chart(fig_month, 540), "zfi_monthly_chart")
            selected_month = get_clicked_value(event, "x") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_monthly_chart") else None

            if selected_month:
                popup_title = f"Monthly Drilldown: {selected_month}"
                popup_df = mdf[mdf["MONTH"].astype(str) == str(selected_month)].copy()

    with c6:
        st.markdown("### Profit Center Wise Amount")
        if not fdf.empty and "PROFIT_CENTER_NAME" in fdf.columns:
            pc_chart = (
                fdf[fdf["PROFIT_CENTER_NAME"].notna()]
                .groupby("PROFIT_CENTER_NAME", as_index=False)
                .agg(
                    DEBIT=("DEBIT", "sum"),
                    CREDIT=("CREDIT", "sum"),
                    TRANSACTIONS=("DOC_NO", "count")
                )
                .fillna(0)
            )
            pc_chart["TOTAL_ACTIVITY"] = pc_chart["DEBIT"] + pc_chart["CREDIT"]
            pc_chart = pc_chart.sort_values("TOTAL_ACTIVITY", ascending=False).head(top_n)

            fig_pc = px.bar(
                pc_chart,
                x="TOTAL_ACTIVITY",
                y="PROFIT_CENTER_NAME",
                orientation="h",
                text="TOTAL_ACTIVITY",
                custom_data=["DEBIT", "CREDIT", "TRANSACTIONS"],
                title="Profit Center Activity",
                color_discrete_sequence=["#0891B2"]
            )

            fig_pc.update_traces(
                texttemplate="%{text:,.2f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=
                    "<b>%{y}</b><br>" +
                    "Total Activity: INR %{x:,.2f}<br>" +
                    "Debit: INR %{customdata[0]:,.2f}<br>" +
                    "Credit: INR %{customdata[1]:,.2f}<br>" +
                    "Transactions: %{customdata[2]:,.0f}<extra></extra>"
            )

            fig_pc.update_layout(
                yaxis={"automargin": True, "categoryorder": "total ascending"},
                xaxis_title="Debit + Credit",
                yaxis_title="Profit Center"
            )

            event = chart_event(clean_chart(fig_pc, 540), "zfi_profit_center_chart")
            selected_pc = get_clicked_value(event, "y") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_profit_center_chart") else None

            if selected_pc:
                popup_title = f"Profit Center Drilldown: {selected_pc}"
                popup_df = fdf[fdf["PROFIT_CENTER_NAME"].astype(str) == str(selected_pc)].copy()

    # --------------------------------------------------------
    # Row 5: TDS and GL
    # --------------------------------------------------------
    c7, c8 = st.columns(2)

    with c7:
        st.markdown("### TDS Analysis by Type")
        if not fdf.empty and "TDS_TYPE" in fdf.columns:
            tds_source = fdf[
                fdf["TDS_TYPE"].notna() &
                (fdf["TDS_TYPE"].astype(str) != "") &
                (fdf["TDS_TYPE"].astype(str) != "N/A")
            ].copy()

            tds_chart = (
                tds_source.groupby("TDS_TYPE", as_index=False)
                .agg(
                    TDS_BASE=("TDS_BASE", "sum"),
                    TDS_AMOUNT=("TDS_AMOUNT", "sum"),
                    TRANSACTIONS=("TDS_TYPE", "size")
                )
                .fillna(0)
                .sort_values("TDS_AMOUNT", ascending=False)
                .head(top_n)
            )

            if not tds_chart.empty:
                fig_tds = px.bar(
                    tds_chart,
                    x="TDS_AMOUNT",
                    y="TDS_TYPE",
                    orientation="h",
                    text="TDS_AMOUNT",
                    custom_data=["TDS_BASE", "TRANSACTIONS"],
                    title="TDS Amount by Type",
                    color_discrete_sequence=["#BE185D"]
                )

                fig_tds.update_traces(
                    texttemplate="%{text:,.2f}",
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=
                        "<b>%{y}</b><br>" +
                        "TDS Amount: INR %{x:,.2f}<br>" +
                        "TDS Base: INR %{customdata[0]:,.2f}<br>" +
                        "Transactions: %{customdata[1]:,.0f}<extra></extra>"
                )

                fig_tds.update_layout(
                    yaxis={"automargin": True, "categoryorder": "total ascending"},
                    xaxis_title="TDS Amount",
                    yaxis_title="TDS Type"
                )

                event = chart_event(clean_chart(fig_tds, 520), "zfi_tds_chart")
                selected_tds = get_clicked_value(event, "y") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_tds_chart") else None

                if selected_tds:
                    popup_title = f"TDS Type Drilldown: {selected_tds}"
                    popup_df = fdf[fdf["TDS_TYPE"].astype(str) == str(selected_tds)].copy()
            else:
                st.caption("No TDS data available for current filters.")

    with c8:
        st.markdown("### Vendor Count by Document Type")
        if not fdf.empty and "DOC_TYPE_DESC" in fdf.columns:
            vendor_doc_chart = (
                fdf.groupby("DOC_TYPE_DESC", as_index=False)
                .agg(
                    VENDOR_COUNT=("VENDOR", "nunique"),
                    TRANSACTIONS=("DOC_NO", "count"),
                    AMOUNT=("AMOUNT_LC", "sum")
                )
                .fillna(0)
                .sort_values("VENDOR_COUNT", ascending=False)
                .head(top_n)
            )

            if not vendor_doc_chart.empty:
                fig_vendor_doc = px.bar(
                    vendor_doc_chart,
                    x="VENDOR_COUNT",
                    y="DOC_TYPE_DESC",
                    orientation="h",
                    text="VENDOR_COUNT",
                    custom_data=["TRANSACTIONS", "AMOUNT"],
                    title="Vendor Count by Document Type",
                    color_discrete_sequence=["#4F46E5"]
                )

                fig_vendor_doc.update_traces(
                    texttemplate="%{text:,.0f}",
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=
                        "<b>%{y}</b><br>" +
                        "Vendor Count: %{x:,.0f}<br>" +
                        "Transactions: %{customdata[0]:,.0f}<br>" +
                        "Amount: INR %{customdata[1]:,.2f}<extra></extra>"
                )

                fig_vendor_doc.update_layout(
                    yaxis={"automargin": True, "categoryorder": "total ascending"},
                    xaxis_title="Vendor Count",
                    yaxis_title="Document Type"
                )

                event = chart_event(clean_chart(fig_vendor_doc, 520), "zfi_vendor_doc_chart")
                selected_vendor_doc = get_clicked_value(event, "y") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_vendor_doc_chart") else None

                if selected_vendor_doc:
                    popup_title = f"Vendor Count by Document Type Drilldown: {selected_vendor_doc}"
                    popup_df = fdf[fdf["DOC_TYPE_DESC"].astype(str) == str(selected_vendor_doc)].copy()
            else:
                st.caption("No document type data available.")

    # --------------------------------------------------------
    # Row 6: Section Code and Daily Transaction
    # --------------------------------------------------------
    c9, c10 = st.columns(2)

    with c9:
        st.markdown("### Section Code Wise Amount")
        if not fdf.empty and "SECTION_CODE_DESC" in fdf.columns:
            section_chart = (
                fdf[fdf["SECTION_CODE_DESC"].notna()]
                .groupby("SECTION_CODE_DESC", as_index=False)
                .agg(
                    DEBIT=("DEBIT", "sum"),
                    CREDIT=("CREDIT", "sum"),
                    TRANSACTIONS=("DOC_NO", "count")
                )
                .fillna(0)
            )
            section_chart["TOTAL_ACTIVITY"] = section_chart["DEBIT"] + section_chart["CREDIT"]
            section_chart = section_chart.sort_values("TOTAL_ACTIVITY", ascending=False).head(top_n)

            if not section_chart.empty:
                fig_section = px.bar(
                    section_chart,
                    x="TOTAL_ACTIVITY",
                    y="SECTION_CODE_DESC",
                    orientation="h",
                    text="TOTAL_ACTIVITY",
                    custom_data=["DEBIT", "CREDIT", "TRANSACTIONS"],
                    title="Section Code Activity",
                    color_discrete_sequence=["#EA580C"]
                )

                fig_section.update_traces(
                    texttemplate="%{text:,.2f}",
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=
                        "<b>%{y}</b><br>" +
                        "Total Activity: INR %{x:,.2f}<br>" +
                        "Debit: INR %{customdata[0]:,.2f}<br>" +
                        "Credit: INR %{customdata[1]:,.2f}<br>" +
                        "Transactions: %{customdata[2]:,.0f}<extra></extra>"
                )

                fig_section.update_layout(
                    yaxis={"automargin": True, "categoryorder": "total ascending"},
                    xaxis_title="Debit + Credit",
                    yaxis_title="Section Code"
                )

                event = chart_event(clean_chart(fig_section, 520), "zfi_section_chart")
                selected_section = get_clicked_value(event, "y") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_section_chart") else None

                if selected_section:
                    popup_title = f"Section Code Drilldown: {selected_section}"
                    popup_df = fdf[fdf["SECTION_CODE_DESC"].astype(str) == str(selected_section)].copy()

    with c10:
        st.markdown("### Daily Transaction Volume")
        if not fdf.empty and "POSTING_DATE" in fdf.columns:
            daily_source = fdf.dropna(subset=["POSTING_DATE"]).copy()
            daily_source["POSTING_DATE_STR"] = daily_source["POSTING_DATE"].dt.strftime("%Y-%m-%d")

            daily_chart = (
                daily_source.groupby("POSTING_DATE_STR", as_index=False)
                .agg(
                    TRANSACTIONS=("DOC_NO", "size"),
                    AMOUNT=("AMOUNT_LC", "sum")
                )
                .fillna(0)
                .sort_values("POSTING_DATE_STR")
            )

            fig_daily = px.bar(
                daily_chart,
                x="POSTING_DATE_STR",
                y="TRANSACTIONS",
                text="TRANSACTIONS",
                custom_data=["POSTING_DATE_STR", "AMOUNT"],
                title="Daily Transaction Volume",
                color_discrete_sequence=["#65A30D"]
            )

            fig_daily.update_traces(
                texttemplate="%{text:,.0f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=
                    "<b>%{customdata[0]}</b><br>" +
                    "Transactions: %{y:,.0f}<br>" +
                    "Amount: INR %{customdata[1]:,.2f}<extra></extra>"
            )

            fig_daily.update_layout(
                xaxis_title="Posting Date",
                yaxis_title="Transactions",
                xaxis_tickangle=-45
            )

            event = chart_event(clean_chart(fig_daily, 560), "zfi_daily_chart")
            selected_date = get_clicked_value(event, "customdata") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_daily_chart") else None

            if selected_date:
                popup_title = f"Daily Transaction Drilldown: {selected_date}"
                popup_df = daily_source[daily_source["POSTING_DATE_STR"].astype(str) == str(selected_date)].copy()

    # --------------------------------------------------------
    # Row 7: Posting Key and Payment Method
    # --------------------------------------------------------
    c11, c12 = st.columns(2)

    with c11:
        st.markdown("### Posting Key Analysis")
        if not fdf.empty and "POSTING_KEY" in fdf.columns:
            pk_chart = (
                fdf.groupby("POSTING_KEY", as_index=False)
                .agg(
                    TRANSACTIONS=("POSTING_KEY", "size"),
                    AMOUNT=("AMOUNT_LC", "sum")
                )
                .fillna(0)
                .sort_values("TRANSACTIONS", ascending=False)
                .head(top_n)
            )

            fig_pk = px.bar(
                pk_chart,
                x="TRANSACTIONS",
                y="POSTING_KEY",
                orientation="h",
                text="TRANSACTIONS",
                custom_data=["AMOUNT"],
                title="Posting Key Transaction Volume",
                color_discrete_sequence=["#0F766E"]
            )

            fig_pk.update_traces(
                texttemplate="%{text:,.0f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=
                    "<b>%{y}</b><br>" +
                    "Transactions: %{x:,.0f}<br>" +
                    "Amount: INR %{customdata[0]:,.2f}<extra></extra>"
            )

            fig_pk.update_layout(
                yaxis={"automargin": True, "categoryorder": "total ascending"},
                xaxis_title="Transactions",
                yaxis_title="Posting Key"
            )

            event = chart_event(clean_chart(fig_pk, 520), "zfi_posting_key_chart")
            selected_pk = get_clicked_value(event, "y") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_posting_key_chart") else None

            if selected_pk:
                popup_title = f"Posting Key Drilldown: {selected_pk}"
                popup_df = fdf[fdf["POSTING_KEY"].astype(str) == str(selected_pk)].copy()

    with c12:
        st.markdown("### Payment Method Distribution")
        if not fdf.empty and "PAYMENT_METHOD" in fdf.columns:
            pm_source = fdf[
                fdf["PAYMENT_METHOD"].notna() &
                (fdf["PAYMENT_METHOD"].astype(str) != "") &
                (fdf["PAYMENT_METHOD"].astype(str) != "N/A")
            ].copy()

            pm_chart = (
                pm_source.groupby("PAYMENT_METHOD", as_index=False)
                .agg(
                    TRANSACTIONS=("PAYMENT_METHOD", "size"),
                    AMOUNT=("AMOUNT_LC", "sum")
                )
                .fillna(0)
                .sort_values("AMOUNT", ascending=False)
                .head(top_n)
            )

            if not pm_chart.empty:
                fig_pm = px.bar(
                    pm_chart,
                    x="AMOUNT",
                    y="PAYMENT_METHOD",
                    orientation="h",
                    text="AMOUNT",
                    custom_data=["TRANSACTIONS"],
                    title="Payment Method Amount",
                    color_discrete_sequence=["#9333EA"]
                )

                fig_pm.update_traces(
                    texttemplate="%{text:,.2f}",
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=
                        "<b>%{y}</b><br>" +
                        "Amount: INR %{x:,.2f}<br>" +
                        "Transactions: %{customdata[0]:,.0f}<extra></extra>"
                )

                fig_pm.update_layout(
                    yaxis={"automargin": True, "categoryorder": "total ascending"},
                    xaxis_title="Amount",
                    yaxis_title="Payment Method"
                )

                event = chart_event(clean_chart(fig_pm, 520), "zfi_payment_method_chart")
                selected_pm = get_clicked_value(event, "y") if (popup_title is None and st.session_state.get("zfi_active_chart") == "zfi_payment_method_chart") else None

                if selected_pm:
                    popup_title = f"Payment Method Drilldown: {selected_pm}"
                    popup_df = fdf[fdf["PAYMENT_METHOD"].astype(str) == str(selected_pm)].copy()
            else:
                st.caption("No payment method data available for current filters.")

    if popup_title and popup_df is not None:
        show_popup(popup_title, popup_df)

# ============================================================
# Data Explorer Tab
# ============================================================
with tab2:
    st.subheader("Filter & Explore ZFI Vendor SOA Data")

    search_text = st.text_input("Search Vendor / Document / Text / Reference", "")
    explorer_df = fdf.copy()

    if search_text.strip():
        s = search_text.strip().lower()
        mask = pd.Series(False, index=explorer_df.index)

        for col in ["VENDOR", "VENDOR_NAME", "DOC_NO", "DOC_TYPE_DESC", "TEXT", "REFERENCE", "ASSIGNMENT", "HEADER_TEXT"]:
            if col in explorer_df.columns:
                mask = mask | explorer_df[col].astype(str).str.lower().str.contains(s, na=False)

        explorer_df = explorer_df[mask]

    e1, e2, e3, e4 = st.columns(4)

    with e1:
        kpi("Filtered Transactions", num_fmt(len(explorer_df)))
    with e2:
        kpi("Filtered Vendors", num_fmt(explorer_df["VENDOR"].nunique() if "VENDOR" in explorer_df.columns else 0))
    with e3:
        kpi("Filtered Debit", fmt_inr(explorer_df["DEBIT"].sum() if "DEBIT" in explorer_df.columns else 0), is_amount=True)
    with e4:
        kpi("Filtered Credit", fmt_inr(explorer_df["CREDIT"].sum() if "CREDIT" in explorer_df.columns else 0), is_amount=True)

    st.markdown("### Vendor Balance Summary")
    vendor_balance_table(explorer_df, rows=1000)

    st.markdown("### Final Report Full Table")
    final_table_df = explorer_df.reset_index(drop=True).copy()
    final_table_df.insert(0, "S.No", range(1, len(final_table_df) + 1))
    st.dataframe(
        final_table_df,
        use_container_width=True,
        hide_index=True,
        height=650,
        column_config={
            "S.No": st.column_config.NumberColumn("S.No", width="small"),
            "VENDOR_NAME": st.column_config.TextColumn("Vendor Name", width="large"),
            "DOC_TYPE_DESC": st.column_config.TextColumn("Document Type", width="large"),
            "TEXT": st.column_config.TextColumn("Text", width="large"),
            "HEADER_TEXT": st.column_config.TextColumn("Header Text", width="large"),
            "DEBIT": st.column_config.NumberColumn("Debit", format="INR %.2f"),
            "CREDIT": st.column_config.NumberColumn("Credit", format="INR %.2f"),
            "AMOUNT_LC": st.column_config.NumberColumn("Amount LC", format="INR %.2f"),
            "TDS_AMOUNT": st.column_config.NumberColumn("TDS Amount", format="INR %.2f"),
        }
    )

    csv = final_table_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Filtered CSV",
        csv,
        "ZFI_VENSOA_FILTERED_REPORT.csv",
        "text/csv",
        use_container_width=True,
    )

# ============================================================
# AI Assistant Tab
# ============================================================
with tab3:
    st.subheader("AI Finance Assistant")
    st.caption("Connected to Snowflake Cortex Agent: BGRE_ZFI_VENSOA_AGENT")

    def run_agent(question):
        payload = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": question}]
                }
            ]
        })

        safe_payload = payload.replace("$$", "$ $")

        agent_sql = f"""
            SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
                '{AGENT_FQN}',
                $${safe_payload}$$
            ) AS RESP
        """

        result_df = pd.read_sql(agent_sql, conn)
        return result_df["RESP"].iloc[0]

    def parse_agent_response(raw_resp):
        try:
            resp = json.loads(raw_resp) if isinstance(raw_resp, str) else raw_resp
        except Exception:
            return {
                "text": str(raw_resp),
                "sql": None,
                "table": None,
                "chart_spec": None,
                "suggestions": []
            }

        final_text = []
        final_sql = None
        final_table = None
        chart_spec = None
        suggestions = []

        for item in resp.get("content", []):
            item_type = item.get("type")

            if item_type == "text":
                text = item.get("text", "")
                if text:
                    final_text.append(text)

            elif item_type == "chart":
                spec_str = item.get("chart", {}).get("chart_spec")
                if spec_str:
                    try:
                        chart_spec = json.loads(spec_str) if isinstance(spec_str, str) else spec_str
                    except Exception:
                        chart_spec = None

            elif item_type == "suggested_queries":
                for q in item.get("suggested_queries", []):
                    if q.get("query"):
                        suggestions.append(q["query"])

            elif item_type == "tool_result":
                for content in item.get("tool_result", {}).get("content", []):
                    if content.get("type") == "json":
                        j = content.get("json", {})

                        if j.get("text"):
                            final_text.append(j["text"])

                        if j.get("sql"):
                            final_sql = j["sql"]

                        rs = j.get("result_set")
                        if rs and rs.get("data"):
                            cols = [c["name"] for c in rs.get("resultSetMetaData", {}).get("rowType", [])]
                            final_table = pd.DataFrame(rs["data"], columns=cols if cols else None)

                    elif content.get("type") == "text":
                        text = content.get("text", "")
                        if text:
                            final_text.append(text)

            elif item_type == "table":
                tbl = item.get("table", {})
                rs = tbl.get("result_set")
                if rs and rs.get("data"):
                    cols = [c["name"] for c in rs.get("resultSetMetaData", {}).get("rowType", [])]
                    final_table = pd.DataFrame(rs["data"], columns=cols if cols else None)

        return {
            "text": "\n\n".join(final_text) if final_text else "No detailed response received from agent.",
            "sql": final_sql,
            "table": final_table,
            "chart_spec": chart_spec,
            "suggestions": suggestions,
        }

    def make_ai_chart(df):
        if df is None or df.empty:
            return

        try:
            chart_df = df.copy()
            chart_df.columns = [str(c) for c in chart_df.columns]

            for col in chart_df.columns:
                converted_num = pd.to_numeric(chart_df[col], errors="coerce")
                if converted_num.notna().sum() > 0:
                    chart_df[col] = converted_num

            num_cols = chart_df.select_dtypes(include=["number"]).columns.tolist()
            text_cols = chart_df.select_dtypes(include=["object"]).columns.tolist()

            if len(chart_df) == 1 and num_cols:
                st.markdown("### Visual Insight")
                cols = st.columns(min(len(num_cols), 4))
                for i, col in enumerate(num_cols[:4]):
                    with cols[i]:
                        kpi(col.replace("_", " ").title(), num_fmt(chart_df[col].iloc[0], 2))
                return

            if text_cols and num_cols:
                label_col = text_cols[0]
                value_col = num_cols[0]

                chart_data = (
                    chart_df[[label_col, value_col]]
                    .dropna()
                    .sort_values(value_col, ascending=False)
                    .head(20)
                )

                st.markdown("### Visual Insight")
                fig_ai = px.bar(
                    chart_data,
                    x=value_col,
                    y=label_col,
                    orientation="h",
                    text=value_col,
                    title=f"{value_col} by {label_col}",
                    color_discrete_sequence=["#2563EB"]
                )

                fig_ai.update_traces(
                    texttemplate="%{text:,.2f}",
                    textposition="outside",
                    cliponaxis=False
                )

                fig_ai.update_layout(
                    height=650,
                    yaxis={"automargin": True, "categoryorder": "total ascending"},
                    margin=dict(l=10, r=130, t=60, b=50)
                )

                st.plotly_chart(fig_ai, use_container_width=True, config=PLOTLY_CONFIG)
                return

        except Exception:
            st.info("Chart could not be generated for this result format, but the answer and data are available above.")

    def render_agent_result(parsed):
        st.markdown("### Answer")
        st.markdown(parsed.get("text", ""))

        if parsed.get("sql"):
            with st.expander("Generated SQL"):
                st.code(parsed["sql"], language="sql")

        if parsed.get("chart_spec"):
            try:
                st.vega_lite_chart(parsed["chart_spec"], use_container_width=True)
            except Exception:
                pass

        if parsed.get("table") is not None and not parsed["table"].empty:
            st.markdown("### Result Data")
            st.dataframe(parsed["table"], use_container_width=True, hide_index=True, height=420)

            if not parsed.get("chart_spec"):
                make_ai_chart(parsed["table"])

            csv = parsed["table"].to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download AI Result",
                csv,
                "ZFI_AI_RESULT.csv",
                "text/csv",
                use_container_width=True,
                key=f"zfi_ai_download_{len(st.session_state.zfi_agent_messages)}"
            )

        if parsed.get("suggestions"):
            st.markdown("### Suggested Follow-up Questions")
            for q in parsed["suggestions"][:5]:
                if st.button(q, key=f"zfi_suggest_{hash(q)}"):
                    st.session_state["zfi_ai_prompt"] = q
                    st.rerun()

    if "zfi_agent_messages" not in st.session_state:
        st.session_state.zfi_agent_messages = []

    quick_questions = [
        "Show top 10 vendors by outstanding balance",
        "Which vendors have advance or credit balance?",
        "Show vendor-wise debit, credit and outstanding balance",
        "What is the total payable outstanding?",
        "Show open items by vendor",
        "Show TDS amount by type",
    ]

    st.markdown("#### Quick Questions")
    qcols = st.columns(3)
    for idx, question in enumerate(quick_questions):
        with qcols[idx % 3]:
            if st.button(question, key=f"zfi_quick_{idx}", use_container_width=True):
                st.session_state["zfi_ai_prompt"] = question

    for msg in st.session_state.zfi_agent_messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                render_agent_result(msg["content"])
            else:
                st.markdown(msg["content"])

    default_prompt = st.session_state.pop("zfi_ai_prompt", None)
    user_question = st.chat_input("Ask about ZFI vendor SOA finance data...")

    if default_prompt and not user_question:
        user_question = default_prompt

    if user_question:
        st.session_state.zfi_agent_messages.append({
            "role": "user",
            "content": user_question
        })

        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Cortex Agent is analyzing ZFI vendor SOA data..."):
                try:
                    raw_response = run_agent(user_question)
                    parsed = parse_agent_response(raw_response)
                    render_agent_result(parsed)
                    st.session_state.zfi_agent_messages.append({
                        "role": "assistant",
                        "content": parsed
                    })

                except Exception as e:
                    err = {
                        "text": f"AI response could not be generated for this question.\n\nError: {e}",
                        "sql": None,
                        "table": None,
                        "chart_spec": None,
                        "suggestions": []
                    }
                    render_agent_result(err)
                    st.session_state.zfi_agent_messages.append({
                        "role": "assistant",
                        "content": err
                    })

st.caption(f"Data source: {TABLE_FQN} | Filtered records: {len(fdf):,}")
