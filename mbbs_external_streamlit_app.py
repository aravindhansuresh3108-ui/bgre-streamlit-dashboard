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
    password=get_secret("password", "BGRE@123456789a"),
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
.modebar {display: none !important;}
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
# Plotly click / popup helpers
# ------------------------------------------------------------
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "scrollZoom": False,
    "doubleClick": False,
    "responsive": True,
}

def clean_chart(fig, height=560):
    fig.update_layout(
        height=height,
        dragmode=False,
        hovermode="closest",
        clickmode="event",
        margin=dict(l=10, r=110, t=55, b=55),
    )
    fig.update_traces(
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.95)),
    )
    return fig

def mark_active_chart(chart_key):
    st.session_state.mbbs_active_chart = chart_key

def chart_event(fig, key):
    # Callback records exactly which chart was clicked.
    # This prevents old selections from other charts from reopening the previous drilldown.
    return st.plotly_chart(
        fig,
        use_container_width=True,
        key=key,
        on_select=lambda chart_key=key: mark_active_chart(chart_key),
        config=PLOTLY_CONFIG,
    )

def get_clicked_value(event_result, preferred=None):
    try:
        points = event_result.selection.points
        if points:
            p = points[0]
            if preferred and preferred in p and p.get(preferred) is not None:
                return p.get(preferred)
            for alt in ["y", "x", "label", "customdata", "point_name", "name"]:
                if alt in p and p.get(alt) is not None:
                    val = p.get(alt)
                    if isinstance(val, (list, tuple)) and val:
                        return val[0]
                    return val
    except Exception:
        return None
    return None

@st.dialog("Drilldown Details", width="large")
def show_drilldown_popup(title, df):
    st.markdown(f"### {title}")
    mini_summary(df, title)
    st.markdown("#### Detailed Records")
    detail_table(df.sort_values("TOTAL_VALUE", ascending=False), rows=500)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Drilldown Records",
        csv,
        "MBBS_DRILLDOWN_RECORDS.csv",
        "text/csv",
        use_container_width=True,
    )

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

    popup_title = None
    popup_df = None

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi("Total Materials", num_fmt(filtered_df["MATERIAL"].nunique()))
        if st.button("View details", key="kpi_total_materials", use_container_width=True):
            popup_title = "Total Materials Drilldown"
            popup_df = filtered_df.copy()
    with k2:
        kpi("WBS Elements", num_fmt(filtered_df["WBS_ELEMENT"].nunique()))
        if st.button("View details", key="kpi_wbs_elements", use_container_width=True):
            popup_title = "WBS Elements Drilldown"
            popup_df = filtered_df.copy()
    with k3:
        kpi("Inventory Value", money_fmt(filtered_df["TOTAL_VALUE"].sum()), is_amount=True)
        if st.button("View details", key="kpi_inventory_value", use_container_width=True):
            popup_title = "Inventory Value Drilldown"
            popup_df = filtered_df[filtered_df["TOTAL_VALUE"] > 0].copy()
    with k4:
        kpi("Stock Quantity", num_fmt(filtered_df["TOTAL_STOCK"].sum(), 3))
        if st.button("View details", key="kpi_stock_qty", use_container_width=True):
            popup_title = "Stock Quantity Drilldown"
            popup_df = filtered_df[filtered_df["TOTAL_STOCK"] != 0].copy()

    k5, k6, k7, k8 = st.columns(4)
    with k5:
        kpi("Records", num_fmt(len(filtered_df)))
        if st.button("View details", key="kpi_records", use_container_width=True):
            popup_title = "All Records Drilldown"
            popup_df = filtered_df.copy()
    with k6:
        kpi("Positive Stock Items", num_fmt((filtered_df["TOTAL_STOCK"] > 0).sum()))
        if st.button("View details", key="kpi_positive_stock", use_container_width=True):
            popup_title = "Positive Stock Items Drilldown"
            popup_df = filtered_df[filtered_df["TOTAL_STOCK"] > 0].copy()
    with k7:
        kpi("Negative Stock Items", num_fmt((filtered_df["TOTAL_STOCK"] < 0).sum()))
        if st.button("View details", key="kpi_negative_stock", use_container_width=True):
            popup_title = "Negative Stock Items Drilldown"
            popup_df = filtered_df[filtered_df["TOTAL_STOCK"] < 0].copy()
    with k8:
        kpi("High Value Items", num_fmt((filtered_df["TOTAL_VALUE"] >= 10000000).sum()))
        if st.button("View details", key="kpi_high_value", use_container_width=True):
            popup_title = "High Value Items Drilldown"
            popup_df = filtered_df[filtered_df["TOTAL_VALUE"] >= 10000000].copy()

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
        fig_wbs = px.bar(
            wbs_chart,
            x="TOTAL_VALUE",
            y="WBS_ELEMENT",
            orientation="h",
            text="TOTAL_VALUE",
            custom_data=["TOTAL_STOCK", "MATERIAL_COUNT", "RECORD_COUNT"],
            title="Top WBS Elements by Inventory Value",
        )
        fig_wbs.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Total Value: INR %{x:,.2f}<br>Total Stock: %{customdata[0]:,.3f}<br>Material Count: %{customdata[1]:,.0f}<br>Record Count: %{customdata[2]:,.0f}<extra></extra>"
        )
        fig_wbs.update_layout(yaxis={"automargin": True, "categoryorder": "total ascending"}, xaxis_title="Inventory Value", yaxis_title="WBS Element")
        wbs_event = chart_event(clean_chart(fig_wbs, 700), "wbs_chart_popup")
        clicked_wbs = get_clicked_value(wbs_event, "y") if st.session_state.get("mbbs_active_chart") == "wbs_chart_popup" else None
        if clicked_wbs:
            popup_title = f"WBS Element Drilldown: {clicked_wbs}"
            popup_df = filtered_df[filtered_df["WBS_ELEMENT"].astype(str) == str(clicked_wbs)].copy()

    with c2:
        st.markdown("### Top Materials by Inventory Value")
        fig_mat = px.bar(
            material_chart,
            x="TOTAL_VALUE",
            y="MATERIAL_DISPLAY",
            orientation="h",
            text="TOTAL_VALUE",
            custom_data=["MATERIAL", "TOTAL_STOCK", "WBS_COUNT", "RECORD_COUNT"],
            title="Top Materials by Inventory Value",
        )
        fig_mat.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Material: %{customdata[0]}<br>Total Value: INR %{x:,.2f}<br>Total Stock: %{customdata[1]:,.3f}<br>WBS Count: %{customdata[2]:,.0f}<br>Record Count: %{customdata[3]:,.0f}<extra></extra>"
        )
        fig_mat.update_layout(yaxis={"automargin": True, "categoryorder": "total ascending"}, xaxis_title="Inventory Value", yaxis_title="Material")
        mat_event = chart_event(clean_chart(fig_mat, 700), "material_chart_popup")
        clicked_mat = get_clicked_value(mat_event, "y") if st.session_state.get("mbbs_active_chart") == "material_chart_popup" else None
        if clicked_mat:
            popup_title = f"Material Drilldown: {clicked_mat}"
            popup_df = filtered_df[filtered_df["MATERIAL_DISPLAY"].astype(str) == str(clicked_mat)].copy()

    # Row 2
    c3, c4 = st.columns(2)

    with c3:
        st.markdown("### Valuation Area Contribution")
        fig_area = px.bar(
            valarea_chart,
            x="VAL_AREA",
            y="TOTAL_VALUE",
            text="TOTAL_VALUE",
            custom_data=["TOTAL_STOCK", "MATERIAL_COUNT"],
            title="Valuation Area Wise Inventory"
        )
        fig_area.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>Valuation Area %{x}</b><br>Total Value: INR %{y:,.2f}<br>Total Stock: %{customdata[0]:,.3f}<br>Material Count: %{customdata[1]:,.0f}<extra></extra>"
        )
        fig_area.update_layout(xaxis_tickangle=-45, xaxis_title="Valuation Area", yaxis_title="Inventory Value")
        area_event = chart_event(clean_chart(fig_area, 560), "area_chart_popup")
        clicked_area = get_clicked_value(area_event, "x") if st.session_state.get("mbbs_active_chart") == "area_chart_popup" else None
        if clicked_area is not None:
            popup_title = f"Valuation Area Drilldown: {clicked_area}"
            popup_df = filtered_df[filtered_df["VAL_AREA"].astype(str) == str(clicked_area)].copy()

    with c4:
        st.markdown("### Valuation Type Split")
        # Donut/pie click is unstable in Streamlit, so using bar chart for reliable drilldown.
        fig_vt = px.bar(
            valtype_chart,
            x="TOTAL_VALUE",
            y="VAL_TYPE",
            orientation="h",
            text="TOTAL_VALUE",
            custom_data=["TOTAL_STOCK", "RECORD_COUNT"],
            title="Valuation Type Split by Value"
        )
        fig_vt.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Total Value: INR %{x:,.2f}<br>Total Stock: %{customdata[0]:,.3f}<br>Record Count: %{customdata[1]:,.0f}<extra></extra>"
        )
        fig_vt.update_layout(yaxis={"automargin": True, "categoryorder": "total ascending"}, xaxis_title="Inventory Value", yaxis_title="Valuation Type")
        vt_event = chart_event(clean_chart(fig_vt, 560), "vt_chart_popup")
        clicked_vt = get_clicked_value(vt_event, "y") if st.session_state.get("mbbs_active_chart") == "vt_chart_popup" else None
        if clicked_vt:
            popup_title = f"Valuation Type Drilldown: {clicked_vt}"
            popup_df = filtered_df[filtered_df["VAL_TYPE"].astype(str) == str(clicked_vt)].copy()

    # Row 3
    c5, c6 = st.columns(2)

    with c5:
        st.markdown("### Unit-wise Inventory")
        fig_bun = px.bar(
            bun_chart,
            x="BUN",
            y="TOTAL_VALUE",
            text="TOTAL_VALUE",
            custom_data=["TOTAL_STOCK", "RECORD_COUNT"],
            title="Unit of Measure Wise Inventory Value"
        )
        fig_bun.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Total Value: INR %{y:,.2f}<br>Total Stock: %{customdata[0]:,.3f}<br>Record Count: %{customdata[1]:,.0f}<extra></extra>"
        )
        fig_bun.update_layout(xaxis_title="Unit", yaxis_title="Inventory Value")
        bun_event = chart_event(clean_chart(fig_bun, 520), "bun_chart_popup")
        clicked_bun = get_clicked_value(bun_event, "x") if st.session_state.get("mbbs_active_chart") == "bun_chart_popup" else None
        if clicked_bun:
            popup_title = f"Unit Drilldown: {clicked_bun}"
            popup_df = filtered_df[filtered_df["BUN"].astype(str) == str(clicked_bun)].copy()

    with c6:
        st.markdown("### Stock Quantity vs Inventory Value")
        scatter_df = filtered_df[(filtered_df["TOTAL_VALUE"] > 0) & (filtered_df["TOTAL_STOCK"] > 0)].copy().head(1000)
        fig_scatter = px.scatter(
            scatter_df,
            x="TOTAL_STOCK",
            y="TOTAL_VALUE",
            size="TOTAL_VALUE",
            hover_name="MATERIAL_DISPLAY",
            custom_data=["MATERIAL_DISPLAY"],
            hover_data=["MATERIAL", "WBS_ELEMENT", "VAL_TYPE", "BUN"],
            title="Material Stock vs Value Analysis"
        )
        fig_scatter.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>Stock Qty: %{x:,.3f}<br>Inventory Value: INR %{y:,.2f}<extra></extra>"
        )
        fig_scatter.update_layout(xaxis_title="Stock Quantity", yaxis_title="Inventory Value")
        scatter_event = chart_event(clean_chart(fig_scatter, 520), "scatter_chart_popup")
        clicked_scatter = get_clicked_value(scatter_event, "customdata") if st.session_state.get("mbbs_active_chart") == "scatter_chart_popup" else None
        if clicked_scatter:
            popup_title = f"Stock vs Value Drilldown: {clicked_scatter}"
            popup_df = filtered_df[filtered_df["MATERIAL_DISPLAY"].astype(str) == str(clicked_scatter)].copy()

    # Row 4 - More client-facing insights
    st.divider()
    st.markdown('<div class="section-title">Additional Inventory Insights</div>', unsafe_allow_html=True)

    c7, c8 = st.columns(2)

    with c7:
        st.markdown("### Top Materials by Stock Quantity")
        stock_qty_chart = (
            filtered_df.groupby(["MATERIAL", "MATERIAL_DISPLAY"], dropna=True)
            .agg(TOTAL_STOCK=("TOTAL_STOCK", "sum"), TOTAL_VALUE=("TOTAL_VALUE", "sum"), WBS_COUNT=("WBS_ELEMENT", "nunique"))
            .reset_index()
            .sort_values("TOTAL_STOCK", ascending=False)
            .head(top_n)
        )
        fig_stock_qty = px.bar(
            stock_qty_chart,
            x="TOTAL_STOCK",
            y="MATERIAL_DISPLAY",
            orientation="h",
            text="TOTAL_STOCK",
            custom_data=["MATERIAL", "TOTAL_VALUE", "WBS_COUNT"],
            title="Top Materials by Stock Quantity"
        )
        fig_stock_qty.update_traces(
            texttemplate="%{text:,.3f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Material: %{customdata[0]}<br>Stock Qty: %{x:,.3f}<br>Total Value: INR %{customdata[1]:,.2f}<br>WBS Count: %{customdata[2]:,.0f}<extra></extra>"
        )
        fig_stock_qty.update_layout(yaxis={"automargin": True, "categoryorder": "total ascending"}, xaxis_title="Stock Quantity", yaxis_title="Material")
        qty_event = chart_event(clean_chart(fig_stock_qty, 560), "stock_qty_chart_popup")
        clicked_qty = get_clicked_value(qty_event, "y") if st.session_state.get("mbbs_active_chart") == "stock_qty_chart_popup" else None
        if clicked_qty:
            popup_title = f"Stock Quantity Material Drilldown: {clicked_qty}"
            popup_df = filtered_df[filtered_df["MATERIAL_DISPLAY"].astype(str) == str(clicked_qty)].copy()

    with c8:
        st.markdown("### High Value Materials")
        high_value_chart = (
            filtered_df[filtered_df["TOTAL_VALUE"] >= 10000000]
            .groupby(["MATERIAL", "MATERIAL_DISPLAY"], dropna=True)
            .agg(TOTAL_VALUE=("TOTAL_VALUE", "sum"), TOTAL_STOCK=("TOTAL_STOCK", "sum"), WBS_COUNT=("WBS_ELEMENT", "nunique"))
            .reset_index()
            .sort_values("TOTAL_VALUE", ascending=False)
            .head(top_n)
        )
        fig_high = px.bar(
            high_value_chart,
            x="TOTAL_VALUE",
            y="MATERIAL_DISPLAY",
            orientation="h",
            text="TOTAL_VALUE",
            custom_data=["MATERIAL", "TOTAL_STOCK", "WBS_COUNT"],
            title="Materials Above 1 Crore Inventory Value"
        )
        fig_high.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Material: %{customdata[0]}<br>Total Value: INR %{x:,.2f}<br>Total Stock: %{customdata[1]:,.3f}<br>WBS Count: %{customdata[2]:,.0f}<extra></extra>"
        )
        fig_high.update_layout(yaxis={"automargin": True, "categoryorder": "total ascending"}, xaxis_title="Inventory Value", yaxis_title="Material")
        high_event = chart_event(clean_chart(fig_high, 560), "high_value_chart_popup")
        clicked_high = get_clicked_value(high_event, "y") if st.session_state.get("mbbs_active_chart") == "high_value_chart_popup" else None
        if clicked_high:
            popup_title = f"High Value Material Drilldown: {clicked_high}"
            popup_df = filtered_df[filtered_df["MATERIAL_DISPLAY"].astype(str) == str(clicked_high)].copy()

    c9, c10 = st.columns(2)

    with c9:
        st.markdown("### WBS Material Count")
        wbs_count_chart = (
            filtered_df.groupby("WBS_ELEMENT", dropna=True)
            .agg(MATERIAL_COUNT=("MATERIAL", "nunique"), TOTAL_VALUE=("TOTAL_VALUE", "sum"), TOTAL_STOCK=("TOTAL_STOCK", "sum"))
            .reset_index()
            .sort_values("MATERIAL_COUNT", ascending=False)
            .head(top_n)
        )
        fig_wbs_count = px.bar(
            wbs_count_chart,
            x="MATERIAL_COUNT",
            y="WBS_ELEMENT",
            orientation="h",
            text="MATERIAL_COUNT",
            custom_data=["TOTAL_VALUE", "TOTAL_STOCK"],
            title="Material Count by WBS Element"
        )
        fig_wbs_count.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Material Count: %{x:,.0f}<br>Total Value: INR %{customdata[0]:,.2f}<br>Total Stock: %{customdata[1]:,.3f}<extra></extra>"
        )
        fig_wbs_count.update_layout(yaxis={"automargin": True, "categoryorder": "total ascending"}, xaxis_title="Material Count", yaxis_title="WBS Element")
        wbs_count_event = chart_event(clean_chart(fig_wbs_count, 540), "wbs_count_chart_popup")
        clicked_wbs_count = get_clicked_value(wbs_count_event, "y") if st.session_state.get("mbbs_active_chart") == "wbs_count_chart_popup" else None
        if clicked_wbs_count:
            popup_title = f"WBS Material Count Drilldown: {clicked_wbs_count}"
            popup_df = filtered_df[filtered_df["WBS_ELEMENT"].astype(str) == str(clicked_wbs_count)].copy()

    with c10:
        st.markdown("### Stock Status Split")
        status_df = filtered_df.copy()
        status_df["STOCK_STATUS"] = "Zero Stock"
        status_df.loc[status_df["TOTAL_STOCK"] > 0, "STOCK_STATUS"] = "Positive Stock"
        status_df.loc[status_df["TOTAL_STOCK"] < 0, "STOCK_STATUS"] = "Negative Stock"

        stock_status_chart = (
            status_df.groupby("STOCK_STATUS", dropna=True)
            .agg(RECORD_COUNT=("MATERIAL", "count"), TOTAL_VALUE=("TOTAL_VALUE", "sum"), TOTAL_STOCK=("TOTAL_STOCK", "sum"))
            .reset_index()
            .sort_values("RECORD_COUNT", ascending=False)
        )
        fig_status = px.bar(
            stock_status_chart,
            x="RECORD_COUNT",
            y="STOCK_STATUS",
            orientation="h",
            text="RECORD_COUNT",
            custom_data=["TOTAL_VALUE", "TOTAL_STOCK"],
            title="Stock Status by Record Count"
        )
        fig_status.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Record Count: %{x:,.0f}<br>Total Value: INR %{customdata[0]:,.2f}<br>Total Stock: %{customdata[1]:,.3f}<extra></extra>"
        )
        fig_status.update_layout(yaxis={"automargin": True, "categoryorder": "total ascending"}, xaxis_title="Record Count", yaxis_title="Stock Status")
        status_event = chart_event(clean_chart(fig_status, 540), "stock_status_chart_popup")
        clicked_status = get_clicked_value(status_event, "y") if st.session_state.get("mbbs_active_chart") == "stock_status_chart_popup" else None
        if clicked_status:
            popup_title = f"Stock Status Drilldown: {clicked_status}"
            if clicked_status == "Positive Stock":
                popup_df = filtered_df[filtered_df["TOTAL_STOCK"] > 0].copy()
            elif clicked_status == "Negative Stock":
                popup_df = filtered_df[filtered_df["TOTAL_STOCK"] < 0].copy()
            else:
                popup_df = filtered_df[filtered_df["TOTAL_STOCK"] == 0].copy()

    if popup_title and popup_df is not None:
        show_drilldown_popup(popup_title, popup_df)

    st.divider()
    st.markdown('<div class="section-title">Material Level Detail Records</div>', unsafe_allow_html=True)
    detail_table(filtered_df.sort_values("TOTAL_VALUE", ascending=False), rows=500)

    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Filtered Records", csv, "MBBS_FILTERED_RECORDS.csv", "text/csv", use_container_width=True)


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
            st.download_button("Download AI Result", csv, "MBBS_AI_RESULT.csv", "text/csv", use_container_width=True, key=f"ai_download_{len(st.session_state.mbbs_agent_messages)}")

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
