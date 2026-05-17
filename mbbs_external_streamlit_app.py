import os
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import snowflake.connector

st.set_page_config(
    page_title="MBBS Inventory Dashboard",
    page_icon="📦",
    layout="wide",
)

# ------------------------------------------------------------
# Snowflake Connection
# ------------------------------------------------------------
# For Streamlit Cloud, add these in Secrets:
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
    password=get_secret("password", ""),
    account=get_secret("account", "TVSNEXT-TVSNEXT"),
    warehouse=get_secret("warehouse", "BGRE_WH"),
    database=get_secret("database", "SNOWFLAKE_POC"),
    schema=get_secret("schema", "ME2J_SCHEMA"),
)

TABLE_FQN = "SNOWFLAKE_POC.ME2J_SCHEMA.MBBS_FINAL_REPORT"
AGENT_FQN = "SNOWFLAKE_POC.ME2J_SCHEMA.BGRE_MBBS_MATERIAL_STOCK_AGENT"

BGR_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 200" width="105" height="130">
  <circle cx="80" cy="52" r="38" fill="#003893"/>
  <circle cx="80" cy="52" r="26" fill="#ffffff"/>
  <circle cx="80" cy="52" r="11" fill="#E31937"/>
  <rect x="77" y="8" width="6" height="18" rx="3" fill="#E31937"/>
  <text x="80" y="130" text-anchor="middle" font-family="Arial Black, Impact, sans-serif" font-size="52" font-weight="900" fill="#003893">BGR</text>
  <text x="80" y="165" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700" fill="#E31937" letter-spacing="6">ENERGY</text>
</svg>"""

# ------------------------------------------------------------
# CSS - avoids short cards/dot-dot feeling and gives Power BI style
# ------------------------------------------------------------
st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 100%;}
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
.amount-value {font-size: 20px !important;}
.section-title {
    font-size: 23px;
    font-weight: 850;
    margin-top: 18px;
    margin-bottom: 10px;
    color: #111827;
}
.small-note {color:#6B7280; font-size:13px;}
div[data-testid="stDataFrame"] {width: 100%;}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Data functions
# ------------------------------------------------------------
@st.cache_data(ttl=300)
def read_sql(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, conn)

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    return read_sql(f"SELECT * FROM {TABLE_FQN}")

def clear_all_caches():
    st.cache_data.clear()

def money_fmt(v):
    try:
        return f"INR {float(v):,.2f}"
    except Exception:
        return "INR 0.00"

def num_fmt(v, decimals=0):
    try:
        return f"{float(v):,.{decimals}f}"
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
        unsafe_allow_html=True
    )

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for c in ["TOTAL_VALUE", "TOTAL_STOCK", "VAL_AREA"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    for c in ["MATERIAL", "MATERIAL_DESCRIPTION", "WBS_ELEMENT", "VAL_TYPE", "BUN", "CURRENCY", "S"]:
        if c in df.columns:
            df[c] = df[c].fillna("N/A").astype(str)

    if "MATERIAL_DESCRIPTION" in df.columns:
        df["MATERIAL_DISPLAY"] = df["MATERIAL_DESCRIPTION"].where(
            df["MATERIAL_DESCRIPTION"].str.strip().ne("") & df["MATERIAL_DESCRIPTION"].ne("N/A"),
            df["MATERIAL"]
        )
    else:
        df["MATERIAL_DISPLAY"] = df["MATERIAL"]

    return df

def detail_table(df: pd.DataFrame, rows=100):
    show_cols = [
        "MATERIAL", "MATERIAL_DESCRIPTION", "VAL_AREA", "VAL_TYPE", "S",
        "WBS_ELEMENT", "TOTAL_STOCK", "BUN", "TOTAL_VALUE", "CURRENCY"
    ]
    available = [c for c in show_cols if c in df.columns]
    st.dataframe(
        df[available].head(rows),
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "MATERIAL": st.column_config.TextColumn("Material", width="medium"),
            "MATERIAL_DESCRIPTION": st.column_config.TextColumn("Material Description", width="large"),
            "WBS_ELEMENT": st.column_config.TextColumn("WBS Element", width="medium"),
            "TOTAL_VALUE": st.column_config.NumberColumn("Total Value", format="INR %.2f", width="medium"),
            "TOTAL_STOCK": st.column_config.NumberColumn("Total Stock", format="%.3f", width="medium"),
            "CURRENCY": st.column_config.TextColumn("Currency", width="small"),
        }
    )

def mini_summary(df, title):
    st.markdown(f"#### {title}")
    a, b, c, d = st.columns(4)
    with a: kpi("Records", num_fmt(len(df)))
    with b: kpi("Materials", num_fmt(df["MATERIAL"].nunique()))
    with c: kpi("Inventory Value", money_fmt(df["TOTAL_VALUE"].sum()), is_amount=True)
    with d: kpi("Stock Qty", num_fmt(df["TOTAL_STOCK"].sum(), 3))

def plot_horizontal_bar(df, x, y, title, hover_data=None, text=None, height=650):
    fig = px.bar(
        df,
        x=x,
        y=y,
        orientation="h",
        text=text or x,
        hover_data=hover_data,
        title=title,
    )
    fig.update_layout(
        height=height,
        yaxis={"automargin": True, "categoryorder": "total ascending"},
        margin=dict(l=10, r=120, t=55, b=40),
        xaxis_title=x.replace("_", " ").title(),
        yaxis_title=y.replace("_", " ").title(),
    )
    fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside", cliponaxis=False)
    return fig

# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------
with st.sidebar:
    st.markdown(BGR_LOGO_SVG, unsafe_allow_html=True)
    st.caption("MBBS Inventory Dashboard")
    st.button("🔄 Refresh data", on_click=clear_all_caches, use_container_width=True)
    st.divider()
    st.subheader("Quick AI Questions")
    quick_questions = [
        "What is the total inventory value?",
        "Show top 10 materials by stock value",
        "WBS element wise stock summary",
        "Which materials have negative stock?",
        "Show zero stock but non-zero value materials",
        "Show high value items above 1 crore",
        "Stock summary by valuation area",
        "How many distinct materials are available?",
    ]
    for q in quick_questions:
        if st.button(q, key=f"quick_{q}", use_container_width=True):
            st.session_state["mbbs_ai_prompt"] = q

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.markdown(BGR_LOGO_SVG, unsafe_allow_html=True)
st.title("MBBS Inventory Dashboard")
st.caption("Material stock, WBS-wise inventory value, valuation area analysis and AI-powered Q&A.")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔍 Data Explorer", "🤖 AI Assistant"])

# ------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------
with tab1:
    st.markdown('<div class="section-title">Executive Inventory Command Center</div>', unsafe_allow_html=True)

    with st.spinner("Loading MBBS data from Snowflake..."):
        df_all = clean_df(load_data())

    st.sidebar.subheader("Dashboard Filters")

    wbs_list = ["All"] + sorted(df_all["WBS_ELEMENT"].dropna().astype(str).unique().tolist())
    val_area_list = ["All"] + sorted(df_all["VAL_AREA"].dropna().astype(str).unique().tolist())
    val_type_list = ["All"] + sorted(df_all["VAL_TYPE"].dropna().astype(str).unique().tolist())
    bun_list = ["All"] + sorted(df_all["BUN"].dropna().astype(str).unique().tolist())

    selected_wbs = st.sidebar.selectbox("WBS Element", wbs_list, key="dash_wbs")
    selected_area = st.sidebar.selectbox("Valuation Area", val_area_list, key="dash_area")
    selected_type = st.sidebar.selectbox("Valuation Type", val_type_list, key="dash_type")
    selected_bun = st.sidebar.selectbox("Unit", bun_list, key="dash_bun")
    top_n = st.sidebar.slider("Top N", 5, 30, 15, key="dash_topn")

    filtered_df = df_all.copy()
    if selected_wbs != "All":
        filtered_df = filtered_df[filtered_df["WBS_ELEMENT"].astype(str) == selected_wbs]
    if selected_area != "All":
        filtered_df = filtered_df[filtered_df["VAL_AREA"].astype(str) == selected_area]
    if selected_type != "All":
        filtered_df = filtered_df[filtered_df["VAL_TYPE"].astype(str) == selected_type]
    if selected_bun != "All":
        filtered_df = filtered_df[filtered_df["BUN"].astype(str) == selected_bun]

    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi("Total Materials", num_fmt(filtered_df["MATERIAL"].nunique()))
    with k2: kpi("WBS Elements", num_fmt(filtered_df["WBS_ELEMENT"].nunique()))
    with k3: kpi("Inventory Value", money_fmt(filtered_df["TOTAL_VALUE"].sum()), is_amount=True)
    with k4: kpi("Stock Quantity", num_fmt(filtered_df["TOTAL_STOCK"].sum(), 3))

    k5, k6, k7, k8 = st.columns(4)
    with k5: kpi("Records", num_fmt(len(filtered_df)))
    with k6: kpi("Positive Stock Items", num_fmt((filtered_df["TOTAL_STOCK"] > 0).sum()))
    with k7: kpi("Negative Stock Items", num_fmt((filtered_df["TOTAL_STOCK"] < 0).sum()))
    with k8: kpi("High Value Items", num_fmt((filtered_df["TOTAL_VALUE"] >= 10000000).sum()))

    st.caption(f"Filtered Records: {len(filtered_df):,} of {len(df_all):,}")
    st.divider()

    # Aggregations
    wbs_chart = (
        filtered_df.groupby("WBS_ELEMENT", dropna=True)
        .agg(TOTAL_VALUE=("TOTAL_VALUE", "sum"), TOTAL_STOCK=("TOTAL_STOCK", "sum"),
             MATERIAL_COUNT=("MATERIAL", "nunique"), RECORD_COUNT=("MATERIAL", "count"))
        .reset_index().sort_values("TOTAL_VALUE", ascending=False).head(top_n)
    )

    material_chart = (
        filtered_df.groupby(["MATERIAL", "MATERIAL_DISPLAY"], dropna=True)
        .agg(TOTAL_VALUE=("TOTAL_VALUE", "sum"), TOTAL_STOCK=("TOTAL_STOCK", "sum"),
             WBS_COUNT=("WBS_ELEMENT", "nunique"), RECORD_COUNT=("MATERIAL", "count"))
        .reset_index().sort_values("TOTAL_VALUE", ascending=False).head(top_n)
    )

    valarea_chart = (
        filtered_df.groupby("VAL_AREA", dropna=True)
        .agg(TOTAL_VALUE=("TOTAL_VALUE", "sum"), TOTAL_STOCK=("TOTAL_STOCK", "sum"),
             MATERIAL_COUNT=("MATERIAL", "nunique"))
        .reset_index().sort_values("TOTAL_VALUE", ascending=False)
    )

    valtype_chart = (
        filtered_df.groupby("VAL_TYPE", dropna=True)
        .agg(TOTAL_VALUE=("TOTAL_VALUE", "sum"), TOTAL_STOCK=("TOTAL_STOCK", "sum"),
             RECORD_COUNT=("MATERIAL", "count"))
        .reset_index().sort_values("TOTAL_VALUE", ascending=False)
    )

    bun_chart = (
        filtered_df.groupby("BUN", dropna=True)
        .agg(TOTAL_VALUE=("TOTAL_VALUE", "sum"), TOTAL_STOCK=("TOTAL_STOCK", "sum"),
             RECORD_COUNT=("MATERIAL", "count"))
        .reset_index().sort_values("TOTAL_VALUE", ascending=False).head(top_n)
    )

    # Row 1
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### WBS Value Concentration")
        fig_wbs = plot_horizontal_bar(
            wbs_chart, "TOTAL_VALUE", "WBS_ELEMENT", "Top WBS Elements by Inventory Value",
            hover_data={"TOTAL_VALUE": ":,.2f", "TOTAL_STOCK": ":,.3f", "MATERIAL_COUNT": ":,.0f", "RECORD_COUNT": ":,.0f"},
            height=700
        )
        wbs_event = st.plotly_chart(fig_wbs, use_container_width=True, key="wbs_chart", on_select="rerun", selection_mode="points")

    with c2:
        st.markdown("### Top Materials by Inventory Value")
        fig_mat = plot_horizontal_bar(
            material_chart, "TOTAL_VALUE", "MATERIAL_DISPLAY", "Top Materials by Inventory Value",
            hover_data={"MATERIAL": True, "TOTAL_VALUE": ":,.2f", "TOTAL_STOCK": ":,.3f", "WBS_COUNT": ":,.0f", "RECORD_COUNT": ":,.0f"},
            height=700
        )
        mat_event = st.plotly_chart(fig_mat, use_container_width=True, key="material_chart", on_select="rerun", selection_mode="points")

    # Row 2
    c3, c4 = st.columns(2)

    with c3:
        st.markdown("### Valuation Area Contribution")
        fig_area = px.bar(
            valarea_chart, x="VAL_AREA", y="TOTAL_VALUE", text="TOTAL_VALUE",
            hover_data={"TOTAL_VALUE": ":,.2f", "TOTAL_STOCK": ":,.3f", "MATERIAL_COUNT": ":,.0f"},
            title="Valuation Area Wise Inventory"
        )
        fig_area.update_layout(height=560, margin=dict(l=10, r=100, t=55, b=80), xaxis_tickangle=-45)
        fig_area.update_traces(texttemplate="%{text:,.2f}", textposition="outside", cliponaxis=False)
        area_event = st.plotly_chart(fig_area, use_container_width=True, key="area_chart", on_select="rerun", selection_mode="points")

    with c4:
        st.markdown("### Valuation Type Split")
        fig_vt = px.pie(
            valtype_chart, names="VAL_TYPE", values="TOTAL_VALUE", hole=0.45,
            hover_data={"TOTAL_STOCK": ":,.3f", "RECORD_COUNT": ":,.0f"},
            title="Valuation Type Split by Value"
        )
        fig_vt.update_traces(textposition="inside", textinfo="percent+label")
        fig_vt.update_layout(height=560)
        vt_event = st.plotly_chart(fig_vt, use_container_width=True, key="vt_chart", on_select="rerun", selection_mode="points")

    # Row 3
    c5, c6 = st.columns(2)

    with c5:
        st.markdown("### Unit-wise Inventory")
        fig_bun = px.bar(
            bun_chart, x="BUN", y="TOTAL_VALUE", text="TOTAL_VALUE",
            hover_data={"TOTAL_VALUE": ":,.2f", "TOTAL_STOCK": ":,.3f", "RECORD_COUNT": ":,.0f"},
            title="Unit of Measure Wise Inventory Value"
        )
        fig_bun.update_layout(height=520, margin=dict(l=10, r=100, t=55, b=60))
        fig_bun.update_traces(texttemplate="%{text:,.2f}", textposition="outside", cliponaxis=False)
        bun_event = st.plotly_chart(fig_bun, use_container_width=True, key="bun_chart", on_select="rerun", selection_mode="points")

    with c6:
        st.markdown("### Stock Quantity vs Inventory Value")
        scatter_df = filtered_df[(filtered_df["TOTAL_VALUE"] > 0) & (filtered_df["TOTAL_STOCK"] > 0)].copy().head(1000)
        fig_scatter = px.scatter(
            scatter_df, x="TOTAL_STOCK", y="TOTAL_VALUE", size="TOTAL_VALUE",
            hover_name="MATERIAL_DISPLAY", hover_data=["MATERIAL", "WBS_ELEMENT", "VAL_TYPE", "BUN"],
            title="Material Stock vs Value Analysis"
        )
        fig_scatter.update_layout(height=520, margin=dict(l=10, r=40, t=55, b=60))
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Click / drilldown helper
    def get_clicked_value(event_result, preferred=None):
        try:
            points = event_result.selection.points
            if points:
                p = points[0]
                if preferred and preferred in p:
                    return p[preferred]
                return p.get("y") or p.get("x") or p.get("label")
        except Exception:
            return None
        return None

    clicked_wbs = get_clicked_value(wbs_event, "y")
    clicked_mat = get_clicked_value(mat_event, "y")
    clicked_area = get_clicked_value(area_event, "x")
    clicked_vt = get_clicked_value(vt_event, "label")
    clicked_bun = get_clicked_value(bun_event, "x")

    drill_label = "All Data"
    drill_df = filtered_df.copy()

    if clicked_wbs:
        drill_label = f"WBS Element: {clicked_wbs}"
        drill_df = drill_df[drill_df["WBS_ELEMENT"].astype(str) == str(clicked_wbs)]
    elif clicked_mat:
        drill_label = f"Material: {clicked_mat}"
        drill_df = drill_df[drill_df["MATERIAL_DISPLAY"].astype(str) == str(clicked_mat)]
    elif clicked_area:
        drill_label = f"Valuation Area: {clicked_area}"
        drill_df = drill_df[drill_df["VAL_AREA"].astype(str) == str(clicked_area)]
    elif clicked_vt:
        drill_label = f"Valuation Type: {clicked_vt}"
        drill_df = drill_df[drill_df["VAL_TYPE"].astype(str) == str(clicked_vt)]
    elif clicked_bun:
        drill_label = f"Unit: {clicked_bun}"
        drill_df = drill_df[drill_df["BUN"].astype(str) == str(clicked_bun)]

    st.divider()
    st.markdown('<div class="section-title">Interactive Drill-down Panel</div>', unsafe_allow_html=True)

    if drill_label == "All Data":
        st.info("Click any chart above to drill down. Example: click one WBS / Material / Valuation Area.")
    else:
        st.success(f"Drill-down applied for {drill_label}")

    mini_summary(drill_df, "Selected Drilldown Summary")

    dc1, dc2 = st.columns(2)

    with dc1:
        st.markdown("### Drilled Material Contribution")
        drill_mat = (
            drill_df.groupby(["MATERIAL", "MATERIAL_DISPLAY"], dropna=True)
            .agg(TOTAL_VALUE=("TOTAL_VALUE", "sum"), TOTAL_STOCK=("TOTAL_STOCK", "sum"))
            .reset_index().sort_values("TOTAL_VALUE", ascending=False).head(12)
        )
        fig_drill_mat = plot_horizontal_bar(
            drill_mat, "TOTAL_VALUE", "MATERIAL_DISPLAY", "Material Split in Selection",
            hover_data={"MATERIAL": True, "TOTAL_VALUE": ":,.2f", "TOTAL_STOCK": ":,.3f"},
            height=520
        )
        st.plotly_chart(fig_drill_mat, use_container_width=True)

    with dc2:
        st.markdown("### Drilled WBS Contribution")
        drill_wbs = (
            drill_df.groupby("WBS_ELEMENT", dropna=True)
            .agg(TOTAL_VALUE=("TOTAL_VALUE", "sum"), TOTAL_STOCK=("TOTAL_STOCK", "sum"), MATERIAL_COUNT=("MATERIAL", "nunique"))
            .reset_index().sort_values("TOTAL_VALUE", ascending=False).head(12)
        )
        fig_drill_wbs = plot_horizontal_bar(
            drill_wbs, "TOTAL_VALUE", "WBS_ELEMENT", "WBS Split in Selection",
            hover_data={"TOTAL_VALUE": ":,.2f", "TOTAL_STOCK": ":,.3f", "MATERIAL_COUNT": ":,.0f"},
            height=520
        )
        st.plotly_chart(fig_drill_wbs, use_container_width=True)

    st.markdown("### Deep Dive Filters")
    s1, s2, s3 = st.columns(3)
    with s1:
        deep_material = st.selectbox("Select Material", ["All"] + sorted(drill_df["MATERIAL"].astype(str).unique().tolist()), key="deep_material")
    with s2:
        deep_wbs = st.selectbox("Select WBS", ["All"] + sorted(drill_df["WBS_ELEMENT"].astype(str).unique().tolist()), key="deep_wbs")
    with s3:
        min_value = st.number_input("Minimum Inventory Value", min_value=0.0, value=0.0, step=100000.0, key="min_value")

    deep_df = drill_df.copy()
    if deep_material != "All":
        deep_df = deep_df[deep_df["MATERIAL"].astype(str) == deep_material]
    if deep_wbs != "All":
        deep_df = deep_df[deep_df["WBS_ELEMENT"].astype(str) == deep_wbs]
    if min_value > 0:
        deep_df = deep_df[deep_df["TOTAL_VALUE"] >= min_value]

    st.markdown("### Material Level Detail Records")
    detail_table(deep_df.sort_values("TOTAL_VALUE", ascending=False), rows=500)

    csv = deep_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Drilled Records", csv, "MBBS_DRILLED_RECORDS.csv", "text/csv", use_container_width=True)

# ------------------------------------------------------------
# Data Explorer
# ------------------------------------------------------------
with tab2:
    st.subheader("Filter & Explore MBBS Stock Data")
    df = clean_df(load_data())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_wbs = st.selectbox("WBS Element", ["All"] + sorted(df["WBS_ELEMENT"].astype(str).unique().tolist()), key="exp_wbs")
    with c2:
        sel_area = st.selectbox("Valuation Area", ["All"] + sorted(df["VAL_AREA"].astype(str).unique().tolist()), key="exp_area")
    with c3:
        sel_type = st.selectbox("Valuation Type", ["All"] + sorted(df["VAL_TYPE"].astype(str).unique().tolist()), key="exp_type")
    with c4:
        sel_bun = st.selectbox("Unit", ["All"] + sorted(df["BUN"].astype(str).unique().tolist()), key="exp_bun")

    search_text = st.text_input("Search Material / Description / WBS", "")

    filtered = df.copy()
    if sel_wbs != "All":
        filtered = filtered[filtered["WBS_ELEMENT"].astype(str) == sel_wbs]
    if sel_area != "All":
        filtered = filtered[filtered["VAL_AREA"].astype(str) == sel_area]
    if sel_type != "All":
        filtered = filtered[filtered["VAL_TYPE"].astype(str) == sel_type]
    if sel_bun != "All":
        filtered = filtered[filtered["BUN"].astype(str) == sel_bun]
    if search_text.strip():
        s = search_text.strip().lower()
        filtered = filtered[
            filtered["MATERIAL"].str.lower().str.contains(s, na=False) |
            filtered["MATERIAL_DESCRIPTION"].str.lower().str.contains(s, na=False) |
            filtered["WBS_ELEMENT"].str.lower().str.contains(s, na=False)
        ]

    a, b, c = st.columns(3)
    with a: kpi("Filtered Records", num_fmt(len(filtered)))
    with b: kpi("Filtered Materials", num_fmt(filtered["MATERIAL"].nunique()))
    with c: kpi("Filtered Value", money_fmt(filtered["TOTAL_VALUE"].sum()), is_amount=True)

    st.caption(f"Showing {len(filtered):,} of {len(df):,} records")
    detail_table(filtered.sort_values("TOTAL_VALUE", ascending=False), rows=1000)

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download Filtered CSV", csv, "MBBS_FILTERED_REPORT.csv", "text/csv", use_container_width=True)

# ------------------------------------------------------------
# AI Assistant
# ------------------------------------------------------------
with tab3:
    st.subheader("AI Assistant")
    st.caption("Connected to Snowflake Cortex Agent: BGRE_MBBS_MATERIAL_STOCK_AGENT")

    def run_agent(question):
        payload = json.dumps({
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": question}]}
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
            return {"text": str(raw_resp), "sql": None, "table": None, "chart_spec": None, "suggestions": []}

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
                        t = content.get("text", "")
                        if t:
                            final_text.append(t)

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
            "suggestions": suggestions
        }

    def make_ai_chart(df):
        if df is None or df.empty:
            return

        try:
            chart_df = df.copy()
            chart_df.columns = [str(c) for c in chart_df.columns]

            date_cols = []
            for col in chart_df.columns:
                if any(x in col.upper() for x in ["DATE", "MONTH", "YEAR", "PERIOD"]):
                    converted = pd.to_datetime(chart_df[col], errors="coerce")
                    if converted.notna().sum() > 0:
                        chart_df[col] = converted
                        date_cols.append(col)

            for col in chart_df.columns:
                if col not in date_cols:
                    converted_num = pd.to_numeric(chart_df[col], errors="coerce")
                    if converted_num.notna().sum() > 0:
                        chart_df[col] = converted_num

            num_cols = chart_df.select_dtypes(include=["number"]).columns.tolist()
            date_cols = chart_df.select_dtypes(include=["datetime64[ns]"]).columns.tolist()
            text_cols = chart_df.select_dtypes(include=["object"]).columns.tolist()

            if not num_cols and not text_cols:
                return

            st.markdown("### Visual Insight")

            if len(chart_df) == 1 and num_cols:
                cols = st.columns(min(len(num_cols), 4))
                for i, col in enumerate(num_cols[:4]):
                    with cols[i]:
                        kpi(col.replace("_", " ").title(), num_fmt(chart_df[col].iloc[0], 2))
                return

            if date_cols and num_cols:
                x_col = date_cols[0]
                y_col = num_cols[0]
                trend_df = chart_df[[x_col, y_col]].dropna().sort_values(x_col)

                fig = px.line(trend_df, x=x_col, y=y_col, markers=True, text=y_col, title=f"{y_col} Trend by {x_col}")
                fig.update_traces(texttemplate="%{text:,.2f}", textposition="top center")
                fig.update_layout(height=600, margin=dict(l=10, r=80, t=60, b=50))
                st.plotly_chart(fig, use_container_width=True)
                return

            if text_cols and num_cols:
                label_col = text_cols[0]
                value_col = num_cols[0]

                bar_df = chart_df[[label_col, value_col]].dropna().sort_values(value_col, ascending=False).head(20)
                fig = px.bar(bar_df, x=value_col, y=label_col, orientation="h", text=value_col, title=f"{value_col} by {label_col}")
                fig.update_layout(height=720, yaxis={"automargin": True}, margin=dict(l=10, r=120, t=60, b=40))
                fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside", cliponaxis=False)
                st.plotly_chart(fig, use_container_width=True)
                return

            if len(num_cols) >= 2:
                st.line_chart(chart_df[num_cols].head(50))
                return

            if len(num_cols) == 1:
                value_col = num_cols[0]
                fig = px.histogram(chart_df, x=value_col, title=f"Distribution of {value_col}")
                fig.update_layout(height=550)
                st.plotly_chart(fig, use_container_width=True)
                return

            if text_cols:
                label_col = text_cols[0]
                count_df = chart_df[label_col].astype(str).value_counts().reset_index()
                count_df.columns = [label_col, "Count"]
                fig = px.bar(count_df.head(20), x="Count", y=label_col, orientation="h", text="Count", title=f"Count by {label_col}")
                fig.update_layout(height=650, yaxis={"automargin": True})
                fig.update_traces(textposition="outside", cliponaxis=False)
                st.plotly_chart(fig, use_container_width=True)
                return

        except Exception:
            st.info("Chart could not be generated for this result format, but the answer and data are available above.")

    def render_agent_result(parsed):
        st.markdown("### Answer")
        st.markdown(parsed["text"])

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
            st.download_button("Download AI Result", csv, "MBBS_AI_RESULT.csv", "text/csv", use_container_width=True)

        if parsed.get("suggestions"):
            st.markdown("### Suggested Follow-up Questions")
            for q in parsed["suggestions"][:5]:
                if st.button(q, key=f"suggest_{hash(q)}"):
                    st.session_state["mbbs_ai_prompt"] = q
                    st.rerun()

    if "mbbs_agent_messages" not in st.session_state:
        st.session_state.mbbs_agent_messages = []

    for msg in st.session_state.mbbs_agent_messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                render_agent_result(msg["content"])
            else:
                st.markdown(msg["content"])

    default_prompt = st.session_state.pop("mbbs_ai_prompt", None)
    user_question = st.chat_input("Ask about MBBS inventory data...")
    if default_prompt and not user_question:
        user_question = default_prompt

    if user_question:
        st.session_state.mbbs_agent_messages.append({"role": "user", "content": user_question})

        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Cortex Agent is analyzing MBBS inventory data..."):
                try:
                    raw_response = run_agent(user_question)
                    parsed = parse_agent_response(raw_response)
                    render_agent_result(parsed)
                    st.session_state.mbbs_agent_messages.append({"role": "assistant", "content": parsed})
                except Exception as e:
                    err = {
                        "text": f"AI response could not be generated for this question.\n\nError: {e}",
                        "sql": None,
                        "table": None,
                        "chart_spec": None,
                        "suggestions": []
                    }
                    render_agent_result(err)
                    st.session_state.mbbs_agent_messages.append({"role": "assistant", "content": err})
