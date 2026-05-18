import json
import streamlit as st
import pandas as pd
import plotly.express as px
import snowflake.connector

st.set_page_config(
    page_title="ME2J Procurement Dashboard",
    page_icon="📊",
    layout="wide",
)

conn = snowflake.connector.connect(
    user="BGRE_CLIENT",
    password="BGRE@123456789a",
    account="TVSNEXT-TVSNEXT",
    warehouse="BGRE_WH",
    database="SNOWFLAKE_POC",
    schema="ME2J_SCHEMA"
)

BGR_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 200" width="120" height="150">
  <circle cx="80" cy="52" r="38" fill="#003893"/>
  <circle cx="80" cy="52" r="26" fill="#ffffff"/>
  <circle cx="80" cy="52" r="11" fill="#E31937"/>
  <rect x="77" y="8" width="6" height="18" rx="3" fill="#E31937"/>
  <text x="80" y="130" text-anchor="middle" font-family="Arial Black, Impact, sans-serif" font-size="52" font-weight="900" fill="#003893">BGR</text>
  <text x="80" y="165" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700" fill="#E31937" letter-spacing="6">ENERGY</text>
</svg>"""

PLOTLY_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "scrollZoom": False,
    "doubleClick": False,
    "responsive": True,
}

@st.cache_data(ttl=300)
def load_data():
    return pd.read_sql("SELECT * FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT", conn)

@st.cache_data(ttl=300)
def get_kpis():
    return pd.read_sql("""
        SELECT
            COUNT(DISTINCT "PurchDoc") AS TOTAL_POS,
            COUNT(DISTINCT "Vendor/Supplying plant") AS TOTAL_VENDORS,
            SUM("POH") AS TOTAL_PO_VALUE,
            SUM(CASE WHEN "Still to be del." > 0 THEN "Still to be del." ELSE 0 END) AS PENDING_DELIVERY_QTY
        FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT
    """, conn)

@st.cache_data(ttl=300)
def get_top_vendors():
    return pd.read_sql("""
        SELECT "Vendor Name", SUM("POH") AS "Total PO Value"
        FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT
        WHERE "Vendor Name" IS NOT NULL
        GROUP BY "Vendor Name"
        ORDER BY "Total PO Value" DESC
        LIMIT 10
    """, conn)

@st.cache_data(ttl=300)
def get_doc_type_dist():
    return pd.read_sql("""
        SELECT "Doc Type", COUNT(DISTINCT "PurchDoc") AS "PO Count"
        FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT
        WHERE "Doc Type" IS NOT NULL
        GROUP BY "Doc Type"
        ORDER BY "PO Count" DESC
    """, conn)

@st.cache_data(ttl=300)
def get_company_summary():
    return pd.read_sql("""
        SELECT "Company Name",
               SUM("POH") AS "Total PO Value",
               COUNT(DISTINCT "PurchDoc") AS "PO Count"
        FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT
        WHERE "Company Name" IS NOT NULL
        GROUP BY "Company Name"
        ORDER BY "Total PO Value" DESC
    """, conn)

@st.cache_data(ttl=300)
def get_plant_summary():
    return pd.read_sql("""
        SELECT "Plant",
               SUM("POH") AS "Total Value",
               SUM("PO Quantity Sto") AS "Total Qty"
        FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT
        WHERE "Plant" IS NOT NULL
        GROUP BY "Plant"
        ORDER BY "Total Value" DESC
    """, conn)

@st.cache_data(ttl=300)
def get_matl_group_spend():
    return pd.read_sql("""
        SELECT "Matl Group", SUM("POH") AS "Total Spend"
        FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT
        WHERE "Matl Group" IS NOT NULL
        GROUP BY "Matl Group"
        ORDER BY "Total Spend" DESC
        LIMIT 10
    """, conn)

@st.cache_data(ttl=300)
def get_delivery_status():
    return pd.read_sql("""
        SELECT
            COALESCE(SUM("GR Qty"), 0) AS "Delivered",
            COALESCE(SUM(CASE WHEN "Still to be del." > 0 THEN "Still to be del." ELSE 0 END), 0) AS "Pending Delivery",
            COALESCE(SUM(CASE WHEN "Still to be inv." > 0 THEN "Still to be inv." ELSE 0 END), 0) AS "Pending Invoice"
        FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT
    """, conn)

@st.cache_data(ttl=300)
def get_monthly_po_trend():
    return pd.read_sql("""
        SELECT DATE_TRUNC('MONTH', "Item Doc Date") AS "Month",
               COUNT(DISTINCT "PurchDoc") AS "PO Count",
               SUM("POH") AS "PO Value"
        FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT
        WHERE "Item Doc Date" IS NOT NULL
        GROUP BY DATE_TRUNC('MONTH', "Item Doc Date")
        ORDER BY "Month"
    """, conn)

@st.cache_data(ttl=300)
def get_top_matl_by_qty():
    return pd.read_sql("""
        SELECT "Short Text", SUM("PO Quantity Sto") AS "Total Qty", SUM("POH") AS "Total Value"
        FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT
        WHERE "Short Text" IS NOT NULL
        GROUP BY "Short Text"
        ORDER BY "Total Value" DESC
        LIMIT 10
    """, conn)

@st.cache_data(ttl=300)
def get_vendor_count_by_plant():
    return pd.read_sql("""
        SELECT "Plant", COUNT(DISTINCT "Vendor/Supplying plant") AS "Vendor Count"
        FROM SNOWFLAKE_POC.ME2J_SCHEMA.ME2J_FINAL_REPORT
        WHERE "Plant" IS NOT NULL
        GROUP BY "Plant"
        ORDER BY "Vendor Count" DESC
    """, conn)

def clear_all_caches():
    st.cache_data.clear()

def money_fmt(v):
    try:
        return f"INR {float(v):,.2f}"
    except Exception:
        return "INR 0.00"

def num_fmt(v):
    try:
        return f"{float(v):,.0f}"
    except Exception:
        return "0"

def clean_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

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

def mini_summary(df, title):
    st.markdown(f"#### {title}")
    a, b, c, d = st.columns(4)
    with a:
        kpi("Records", num_fmt(len(df)))
    with b:
        kpi("PO Count", num_fmt(df["PurchDoc"].nunique() if "PurchDoc" in df.columns else 0))
    with c:
        kpi("PO Value", money_fmt(df["POH"].sum() if "POH" in df.columns else 0), is_amount=True)
    with d:
        pending = df["Still to be del."].clip(lower=0).sum() if "Still to be del." in df.columns else 0
        kpi("Pending Qty", num_fmt(pending))

def detail_table(df, rows=20):
    show_cols = [
        "PurchDoc", "Item", "Item Doc Date", "Vendor/Supplying plant",
        "Vendor Name", "Short Text", "Material", "Material Description",
        "PO Quantity Sto", "GR Qty", "Still to be del.", "Still to be inv.",
        "POH", "Plant", "Doc Type", "Company Name", "Matl Group"
    ]
    available = [c for c in show_cols if c in df.columns]
    st.dataframe(df[available].head(rows), use_container_width=True, hide_index=True, height=420)

def clean_chart(fig, height=520):
    fig.update_layout(
        height=height,
        dragmode=False,
        hovermode="closest",
        clickmode="event",
        margin=dict(l=10, r=80, t=25, b=60),
        font=dict(size=11),
    )
    fig.update_traces(
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.95)),
    )
    return fig

def mark_active_chart(chart_key):
    st.session_state.me2j_active_chart = chart_key

def chart_event(fig, key):
    # Callback marks only the chart that was clicked, so old selections from other charts
    # will not keep opening the previous drilldown.
    return st.plotly_chart(
        fig,
        use_container_width=True,
        key=key,
        on_select=lambda chart_key=key: mark_active_chart(chart_key),
        config=PLOTLY_CONFIG,
    )

def pie_chart_event(fig, key):
    # Pie/donut charts need explicit point selection in some Streamlit/Plotly versions.
    return st.plotly_chart(
        fig,
        use_container_width=True,
        key=key,
        on_select="rerun",
        selection_mode="points",
        config=PLOTLY_CONFIG,
    )

@st.dialog("Drilldown Details", width="large")
def show_popup(title, df):
    st.markdown(f"### {title}")
    mini_summary(df, title)
    st.markdown("#### Detailed Records")
    detail_table(df, rows=50)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Drilldown Data",
        csv,
        "ME2J_DRILLDOWN_DATA.csv",
        "text/csv",
        use_container_width=True
    )

def get_clicked_value(event, field):
    try:
        if event and event.selection.points:
            pt = event.selection.points[0]
            if field in pt and pt.get(field) is not None:
                return pt.get(field)
            # Pie charts sometimes expose the clicked slice under different keys.
            for alt in ["label", "theta", "legendgroup", "customdata", "point_name", "name"]:
                if alt in pt and pt.get(alt) is not None:
                    val = pt.get(alt)
                    if isinstance(val, (list, tuple)) and val:
                        return val[0]
                    return val
    except Exception:
        return None
    return None

with st.sidebar:
    st.markdown(BGR_LOGO_SVG, unsafe_allow_html=True)
    st.caption("ME2J Procurement Dashboard")
    st.button("🔄 Refresh data", on_click=clear_all_caches, use_container_width=True)

kpis = get_kpis()

st.markdown(BGR_LOGO_SVG, unsafe_allow_html=True)
st.title("ME2J Procurement Dashboard")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔍 Data Explorer", "🤖 AI Assistant"])

with tab1:
    st.markdown("""
    <style>
    .kpi-card {
        background: white;
        padding: 22px;
        border-radius: 18px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 3px 12px rgba(0,0,0,0.08);
        min-height: 135px;
        width: 100%;
    }
    .kpi-title {
        font-size: 14px;
        color: #6B7280;
        margin-bottom: 10px;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 25px;
        font-weight: 800;
        color: #111827;
        line-height: 1.25;
        white-space: normal;
        word-break: break-word;
    }
    .amount-value {
        font-size: 20px !important;
    }
    .section-title {
        font-size: 22px;
        font-weight: 800;
        margin-top: 20px;
        margin-bottom: 12px;
        color: #111827;
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
    .pielayer,
    .pielayer *,
    .slice,
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
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Executive Summary</div>', unsafe_allow_html=True)

    df_all = load_data()
    df_all = clean_numeric(df_all, ["POH", "PO Quantity Sto", "GR Qty", "Still to be del.", "Still to be inv."])

    st.sidebar.subheader("Dashboard Filters")

    vendor_list = ["All"] + sorted(df_all["Vendor Name"].dropna().astype(str).unique().tolist())
    plant_list = ["All"] + sorted(df_all["Plant"].dropna().astype(str).unique().tolist())
    doc_type_list = ["All"] + sorted(df_all["Doc Type"].dropna().astype(str).unique().tolist())
    matl_group_list = ["All"] + sorted(df_all["Matl Group"].dropna().astype(str).unique().tolist())

    selected_vendor = st.sidebar.selectbox("Vendor", vendor_list, key="dash_vendor")
    selected_plant = st.sidebar.selectbox("Plant", plant_list, key="dash_plant")
    selected_doc_type = st.sidebar.selectbox("Doc Type", doc_type_list, key="dash_doc_type")
    selected_matl_group = st.sidebar.selectbox("Material Group", matl_group_list, key="dash_matl_group")

    filtered_df = df_all.copy()

    if selected_vendor != "All":
        filtered_df = filtered_df[filtered_df["Vendor Name"].astype(str) == selected_vendor]
    if selected_plant != "All":
        filtered_df = filtered_df[filtered_df["Plant"].astype(str) == selected_plant]
    if selected_doc_type != "All":
        filtered_df = filtered_df[filtered_df["Doc Type"].astype(str) == selected_doc_type]
    if selected_matl_group != "All":
        filtered_df = filtered_df[filtered_df["Matl Group"].astype(str) == selected_matl_group]

    popup_title = None
    popup_df = None

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi("Total POs", num_fmt(filtered_df["PurchDoc"].nunique()))
        if st.button("View details", key="kpi_total_pos", use_container_width=True):
            popup_title = "Total POs Drilldown"
            popup_df = filtered_df.copy()
    with k2:
        kpi("Total Vendors", num_fmt(filtered_df["Vendor/Supplying plant"].nunique()))
        if st.button("View details", key="kpi_total_vendors", use_container_width=True):
            popup_title = "Total Vendors Drilldown"
            popup_df = filtered_df.copy()
    with k3:
        kpi("Total PO Value", money_fmt(filtered_df["POH"].sum()), is_amount=True)
        if st.button("View details", key="kpi_total_po_value", use_container_width=True):
            popup_title = "Total PO Value Drilldown"
            popup_df = filtered_df[filtered_df["POH"] > 0].copy()
    with k4:
        kpi("Pending Delivery Qty", num_fmt(filtered_df["Still to be del."].clip(lower=0).sum()))
        if st.button("View details", key="kpi_pending_delivery", use_container_width=True):
            popup_title = "Pending Delivery Drilldown"
            popup_df = filtered_df[filtered_df["Still to be del."] > 0].copy()

    k5, k6, k7, k8 = st.columns(4)
    with k5:
        kpi("Total PO Quantity", num_fmt(filtered_df["PO Quantity Sto"].sum()))
        if st.button("View details", key="kpi_total_po_qty", use_container_width=True):
            popup_title = "Total PO Quantity Drilldown"
            popup_df = filtered_df[filtered_df["PO Quantity Sto"] > 0].copy()
    with k6:
        kpi("GR Quantity", num_fmt(filtered_df["GR Qty"].sum()))
        if st.button("View details", key="kpi_gr_qty", use_container_width=True):
            popup_title = "GR Quantity Drilldown"
            popup_df = filtered_df[filtered_df["GR Qty"] > 0].copy()
    with k7:
        kpi("Pending Invoice Qty", num_fmt(filtered_df["Still to be inv."].clip(lower=0).sum()))
        if st.button("View details", key="kpi_pending_invoice", use_container_width=True):
            popup_title = "Pending Invoice Drilldown"
            popup_df = filtered_df[filtered_df["Still to be inv."] > 0].copy()
    with k8:
        avg_po = filtered_df["POH"].sum() / filtered_df["PurchDoc"].nunique() if filtered_df["PurchDoc"].nunique() else 0
        kpi("Average PO Value", money_fmt(avg_po), is_amount=True)
        if st.button("View details", key="kpi_avg_po_value", use_container_width=True):
            popup_title = "Average PO Value Drilldown"
            popup_df = filtered_df[filtered_df["POH"] > 0].copy()

    st.caption(f"Filtered Records: {len(filtered_df):,}")

    if popup_title and popup_df is not None:
        show_popup(popup_title, popup_df)

    st.divider()

    # Pre-aggregations
    vendor_chart = (
        filtered_df.groupby("Vendor Name", dropna=True)
        .agg(
            Total_PO_Value=("POH", "sum"),
            PO_Count=("PurchDoc", "nunique"),
            Total_Qty=("PO Quantity Sto", "sum"),
            Pending_Qty=("Still to be del.", "sum"),
        )
        .reset_index()
        .sort_values("Total_PO_Value", ascending=False)
        .head(15)
    )

    material_chart = (
        filtered_df.groupby("Short Text", dropna=True)
        .agg(
            Total_PO_Value=("POH", "sum"),
            PO_Count=("PurchDoc", "nunique"),
            Total_Qty=("PO Quantity Sto", "sum"),
            Pending_Qty=("Still to be del.", "sum"),
            Pending_Invoice=("Still to be inv.", "sum"),
        )
        .reset_index()
        .sort_values("Total_PO_Value", ascending=False)
        .head(15)
    )

    chart1, chart2 = st.columns(2)

    with chart1:
        st.markdown("### Top Vendors by PO Value")
        fig_vendor = px.bar(
            vendor_chart,
            x="Total_PO_Value",
            y="Vendor Name",
            orientation="h",
            text="Total_PO_Value",
            custom_data=["PO_Count", "Total_Qty", "Pending_Qty"],
        )
        fig_vendor.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>PO Value: INR %{x:,.2f}<br>PO Count: %{customdata[0]:,.0f}<br>Total Qty: %{customdata[1]:,.2f}<br>Pending Qty: %{customdata[2]:,.2f}<extra></extra>"
        )
        fig_vendor.update_layout(yaxis={"automargin": True}, xaxis_title="PO Value", yaxis_title="Vendor Name")
        event = chart_event(clean_chart(fig_vendor, 620), "vendor_chart_click")
        selected = get_clicked_value(event, "y") if st.session_state.get("me2j_active_chart") == "vendor_chart_click" else None
        if selected:
            popup_title = f"Vendor Drilldown: {selected}"
            popup_df = filtered_df[filtered_df["Vendor Name"].astype(str) == str(selected)]

    with chart2:
        st.markdown("### Top Materials by PO Value")
        fig_material = px.bar(
            material_chart,
            x="Total_PO_Value",
            y="Short Text",
            orientation="h",
            text="Total_PO_Value",
            custom_data=["PO_Count", "Total_Qty", "Pending_Qty", "Pending_Invoice"],
        )
        fig_material.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>PO Value: INR %{x:,.2f}<br>PO Count: %{customdata[0]:,.0f}<br>Total Qty: %{customdata[1]:,.2f}<br>Pending Delivery: %{customdata[2]:,.2f}<br>Pending Invoice: %{customdata[3]:,.2f}<extra></extra>"
        )
        fig_material.update_layout(yaxis={"automargin": True}, xaxis_title="PO Value", yaxis_title="Material / Short Text")
        event = chart_event(clean_chart(fig_material, 620), "material_chart_click")
        selected = get_clicked_value(event, "y") if st.session_state.get("me2j_active_chart") == "material_chart_click" else None
        if selected:
            popup_title = f"Material Drilldown: {selected}"
            popup_df = filtered_df[filtered_df["Short Text"].astype(str) == str(selected)]

    chart3, chart4 = st.columns(2)

    with chart3:
        st.markdown("### Plant Wise Procurement")
        plant_chart = (
            filtered_df.groupby("Plant", dropna=True)
            .agg(Total_Value=("POH", "sum"), Total_Qty=("PO Quantity Sto", "sum"), PO_Count=("PurchDoc", "nunique"))
            .reset_index()
            .sort_values("Total_Value", ascending=False)
        )
        fig_plant = px.bar(
            plant_chart,
            x="Plant",
            y="Total_Value",
            text="Total_Value",
            custom_data=["Total_Qty", "PO_Count"],
        )
        fig_plant.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            hovertemplate="<b>Plant %{x}</b><br>Total Value: INR %{y:,.2f}<br>Total Qty: %{customdata[0]:,.2f}<br>PO Count: %{customdata[1]:,.0f}<extra></extra>"
        )
        fig_plant.update_layout(xaxis_tickangle=-45, xaxis_title="Plant", yaxis_title="Total Value")
        event = chart_event(clean_chart(fig_plant, 520), "plant_chart_click")
        selected = get_clicked_value(event, "x") if st.session_state.get("me2j_active_chart") == "plant_chart_click" else None
        if selected:
            popup_title = f"Plant Drilldown: {selected}"
            popup_df = filtered_df[filtered_df["Plant"].astype(str) == str(selected)]

    with chart4:
        st.markdown("### Document Type Distribution")

        doc_chart = (
            filtered_df.groupby("Doc Type", dropna=True)
            .agg(
                PO_Count=("PurchDoc", "nunique"),
                Total_PO_Value=("POH", "sum"),
                Pending_Qty=("Still to be del.", "sum"),
            )
            .reset_index()
            .sort_values("PO_Count", ascending=False)
        )

        fig_doc = px.bar(
            doc_chart,
            x="PO_Count",
            y="Doc Type",
            orientation="h",
            text="PO_Count",
            custom_data=["Total_PO_Value", "Pending_Qty"],
        )
        fig_doc.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>PO Count: %{x:,.0f}<br>PO Value: INR %{customdata[0]:,.2f}<br>Pending Qty: %{customdata[1]:,.2f}<extra></extra>"
        )
        fig_doc.update_layout(
            yaxis={"automargin": True},
            xaxis_title="PO Count",
            yaxis_title="Document Type"
        )

        event = chart_event(clean_chart(fig_doc, 520), "doc_type_bar_chart_click")
        selected = get_clicked_value(event, "y") if st.session_state.get("me2j_active_chart") == "doc_type_bar_chart_click" else None

        if selected:
            selected = str(selected)
            popup_title = f"Document Type Drilldown: {selected}"
            popup_df = filtered_df[filtered_df["Doc Type"].astype(str) == selected]

    chart5, chart6 = st.columns(2)

    with chart5:
        st.markdown("### Delivery / Invoice Status")
        delivery_chart = pd.DataFrame({
            "Status": ["Delivered", "Pending Delivery", "Pending Invoice"],
            "Quantity": [
                filtered_df["GR Qty"].sum(),
                filtered_df["Still to be del."].clip(lower=0).sum(),
                filtered_df["Still to be inv."].clip(lower=0).sum(),
            ],
        })
        fig_delivery = px.bar(delivery_chart, x="Status", y="Quantity", text="Quantity")
        fig_delivery.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Quantity: %{y:,.2f}<extra></extra>"
        )
        fig_delivery.update_layout(xaxis_title="Status", yaxis_title="Quantity")
        event = chart_event(clean_chart(fig_delivery, 500), "delivery_chart_click")
        selected = get_clicked_value(event, "x") if st.session_state.get("me2j_active_chart") == "delivery_chart_click" else None
        if selected:
            if selected == "Delivered":
                popup_df = filtered_df[filtered_df["GR Qty"] > 0]
            elif selected == "Pending Delivery":
                popup_df = filtered_df[filtered_df["Still to be del."] > 0]
            else:
                popup_df = filtered_df[filtered_df["Still to be inv."] > 0]
            popup_title = f"Status Drilldown: {selected}"

    with chart6:
        st.markdown("### Monthly PO Value Trend")
        trend_df = filtered_df.copy()
        trend_df["Item Doc Date"] = pd.to_datetime(trend_df["Item Doc Date"], errors="coerce")
        trend_df = (
            trend_df.dropna(subset=["Item Doc Date"])
            .groupby(trend_df["Item Doc Date"].dt.to_period("M"))
            .agg(PO_Value=("POH", "sum"), PO_Count=("PurchDoc", "nunique"))
            .reset_index()
        )
        trend_df["Month"] = trend_df["Item Doc Date"].astype(str)
        fig_trend = px.line(trend_df, x="Month", y="PO_Value", markers=True, text="PO_Value", custom_data=["PO_Count"])
        fig_trend.update_traces(
            texttemplate="%{text:,.2f}",
            textposition="top center",
            hovertemplate="<b>%{x}</b><br>PO Value: INR %{y:,.2f}<br>PO Count: %{customdata[0]:,.0f}<extra></extra>"
        )
        fig_trend.update_layout(xaxis_title="Month", yaxis_title="PO Value")
        event = chart_event(clean_chart(fig_trend, 500), "trend_chart_click")
        selected = get_clicked_value(event, "x") if st.session_state.get("me2j_active_chart") == "trend_chart_click" else None
        if selected:
            temp = filtered_df.copy()
            temp["Item Doc Date"] = pd.to_datetime(temp["Item Doc Date"], errors="coerce")
            popup_df = temp[temp["Item Doc Date"].dt.to_period("M").astype(str) == str(selected)]
            popup_title = f"Monthly Drilldown: {selected}"

    st.divider()
    st.markdown('<div class="section-title">Additional Procurement Insights</div>', unsafe_allow_html=True)

    chart7, chart8 = st.columns(2)

    with chart7:
        st.markdown("### Top Vendors by Pending Delivery")
        pending_vendor = (
            filtered_df.groupby("Vendor Name", dropna=True)
            .agg(Pending_Delivery=("Still to be del.", "sum"), PO_Value=("POH", "sum"), PO_Count=("PurchDoc", "nunique"))
            .reset_index()
        )
        pending_vendor = pending_vendor[pending_vendor["Pending_Delivery"] > 0].sort_values("Pending_Delivery", ascending=False).head(15)
        fig = px.bar(pending_vendor, x="Pending_Delivery", y="Vendor Name", orientation="h", text="Pending_Delivery", custom_data=["PO_Value", "PO_Count"])
        fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside", hovertemplate="<b>%{y}</b><br>Pending Delivery: %{x:,.2f}<br>PO Value: INR %{customdata[0]:,.2f}<br>PO Count: %{customdata[1]:,.0f}<extra></extra>")
        fig.update_layout(yaxis={"automargin": True}, xaxis_title="Pending Delivery", yaxis_title="Vendor Name")
        event = chart_event(clean_chart(fig, 560), "pending_vendor_click")
        selected = get_clicked_value(event, "y") if st.session_state.get("me2j_active_chart") == "pending_vendor_click" else None
        if selected:
            popup_title = f"Pending Delivery Vendor Drilldown: {selected}"
            popup_df = filtered_df[(filtered_df["Vendor Name"].astype(str) == str(selected)) & (filtered_df["Still to be del."] > 0)]

    with chart8:
        st.markdown("### Top Materials by Pending Invoice")
        pending_material = (
            filtered_df.groupby("Short Text", dropna=True)
            .agg(Pending_Invoice=("Still to be inv.", "sum"), PO_Value=("POH", "sum"), PO_Count=("PurchDoc", "nunique"))
            .reset_index()
        )
        pending_material = pending_material[pending_material["Pending_Invoice"] > 0].sort_values("Pending_Invoice", ascending=False).head(15)
        fig = px.bar(pending_material, x="Pending_Invoice", y="Short Text", orientation="h", text="Pending_Invoice", custom_data=["PO_Value", "PO_Count"])
        fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside", hovertemplate="<b>%{y}</b><br>Pending Invoice: %{x:,.2f}<br>PO Value: INR %{customdata[0]:,.2f}<br>PO Count: %{customdata[1]:,.0f}<extra></extra>")
        fig.update_layout(yaxis={"automargin": True}, xaxis_title="Pending Invoice", yaxis_title="Material / Short Text")
        event = chart_event(clean_chart(fig, 560), "pending_material_click")
        selected = get_clicked_value(event, "y") if st.session_state.get("me2j_active_chart") == "pending_material_click" else None
        if selected:
            popup_title = f"Pending Invoice Material Drilldown: {selected}"
            popup_df = filtered_df[(filtered_df["Short Text"].astype(str) == str(selected)) & (filtered_df["Still to be inv."] > 0)]

    chart9, chart10 = st.columns(2)

    with chart9:
        st.markdown("### Company Wise PO Value")
        company_chart = (
            filtered_df.groupby("Company Name", dropna=True)
            .agg(Total_PO_Value=("POH", "sum"), PO_Count=("PurchDoc", "nunique"))
            .reset_index()
            .sort_values("Total_PO_Value", ascending=False)
            .head(15)
        )
        fig = px.bar(company_chart, x="Total_PO_Value", y="Company Name", orientation="h", text="Total_PO_Value", custom_data=["PO_Count"])
        fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside", hovertemplate="<b>%{y}</b><br>PO Value: INR %{x:,.2f}<br>PO Count: %{customdata[0]:,.0f}<extra></extra>")
        fig.update_layout(yaxis={"automargin": True}, xaxis_title="PO Value", yaxis_title="Company Name")
        event = chart_event(clean_chart(fig, 540), "company_chart_click")
        selected = get_clicked_value(event, "y") if st.session_state.get("me2j_active_chart") == "company_chart_click" else None
        if selected:
            popup_title = f"Company Drilldown: {selected}"
            popup_df = filtered_df[filtered_df["Company Name"].astype(str) == str(selected)]

    with chart10:
        st.markdown("### Material Group Spend")
        group_chart = (
            filtered_df.groupby("Matl Group", dropna=True)
            .agg(Total_Spend=("POH", "sum"), PO_Count=("PurchDoc", "nunique"))
            .reset_index()
            .sort_values("Total_Spend", ascending=False)
            .head(15)
        )
        fig = px.bar(group_chart, x="Total_Spend", y="Matl Group", orientation="h", text="Total_Spend", custom_data=["PO_Count"])
        fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside", hovertemplate="<b>%{y}</b><br>Total Spend: INR %{x:,.2f}<br>PO Count: %{customdata[0]:,.0f}<extra></extra>")
        fig.update_layout(yaxis={"automargin": True}, xaxis_title="Spend", yaxis_title="Material Group")
        event = chart_event(clean_chart(fig, 540), "matl_group_chart_click")
        selected = get_clicked_value(event, "y") if st.session_state.get("me2j_active_chart") == "matl_group_chart_click" else None
        if selected:
            popup_title = f"Material Group Drilldown: {selected}"
            popup_df = filtered_df[filtered_df["Matl Group"].astype(str) == str(selected)]

    chart11, chart12 = st.columns(2)

    with chart11:
        st.markdown("### Vendor Count by Plant")
        vendor_count_chart = (
            filtered_df.groupby("Plant", dropna=True)
            .agg(Vendor_Count=("Vendor/Supplying plant", "nunique"), PO_Value=("POH", "sum"))
            .reset_index()
            .sort_values("Vendor_Count", ascending=False)
        )
        fig = px.bar(vendor_count_chart, x="Plant", y="Vendor_Count", text="Vendor_Count", custom_data=["PO_Value"])
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", hovertemplate="<b>Plant %{x}</b><br>Vendor Count: %{y:,.0f}<br>PO Value: INR %{customdata[0]:,.2f}<extra></extra>")
        fig.update_layout(xaxis_tickangle=-45, xaxis_title="Plant", yaxis_title="Vendor Count")
        event = chart_event(clean_chart(fig, 500), "vendor_count_plant_click")
        selected = get_clicked_value(event, "x") if st.session_state.get("me2j_active_chart") == "vendor_count_plant_click" else None
        if selected:
            popup_title = f"Vendor Count Plant Drilldown: {selected}"
            popup_df = filtered_df[filtered_df["Plant"].astype(str) == str(selected)]

    with chart12:
        st.markdown("### PO Quantity vs GR Quantity by Plant")
        qty_chart = (
            filtered_df.groupby("Plant", dropna=True)
            .agg(PO_Quantity=("PO Quantity Sto", "sum"), GR_Quantity=("GR Qty", "sum"), PO_Value=("POH", "sum"))
            .reset_index()
            .sort_values("PO_Quantity", ascending=False)
            .head(15)
        )
        fig = px.bar(qty_chart, x="Plant", y=["PO_Quantity", "GR_Quantity"], barmode="group")
        fig.update_traces(hovertemplate="<b>Plant %{x}</b><br>%{fullData.name}: %{y:,.2f}<extra></extra>")
        fig.update_layout(height=500, dragmode=False, hovermode="closest", clickmode="event", xaxis_tickangle=-45, xaxis_title="Plant", yaxis_title="Quantity", margin=dict(l=10, r=60, t=25, b=80))
        event = chart_event(fig, "qty_compare_click")
        selected = get_clicked_value(event, "x") if st.session_state.get("me2j_active_chart") == "qty_compare_click" else None
        if selected:
            popup_title = f"PO vs GR Quantity Drilldown: {selected}"
            popup_df = filtered_df[filtered_df["Plant"].astype(str) == str(selected)]

    if popup_title and popup_df is not None:
        show_popup(popup_title, popup_df)

    st.divider()
    st.markdown('<div class="section-title">Detailed Data Preview</div>', unsafe_allow_html=True)
    detail_table(filtered_df, rows=25)

    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Filtered Data",
        csv,
        "ME2J_FILTERED_DATA.csv",
        "text/csv",
        use_container_width=True
    )

with tab2:
    st.subheader("Filter & Explore Data")
    df = load_data()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        vendors = ["All"] + sorted(df["Vendor Name"].dropna().unique().tolist())
        sel_vendor = st.selectbox("Vendor", vendors)

    with col2:
        plants = ["All"] + sorted(df["Plant"].dropna().unique().tolist())
        sel_plant = st.selectbox("Plant", plants)

    with col3:
        doc_types = ["All"] + sorted(df["Doc Type"].dropna().unique().tolist())
        sel_doc_type = st.selectbox("Doc Type", doc_types)

    with col4:
        matl_groups = ["All"] + sorted(df["Matl Group"].dropna().unique().tolist())
        sel_matl = st.selectbox("Material Group", matl_groups)

    filtered = df.copy()

    if sel_vendor != "All":
        filtered = filtered[filtered["Vendor Name"] == sel_vendor]
    if sel_plant != "All":
        filtered = filtered[filtered["Plant"] == sel_plant]
    if sel_doc_type != "All":
        filtered = filtered[filtered["Doc Type"] == sel_doc_type]
    if sel_matl != "All":
        filtered = filtered[filtered["Matl Group"] == sel_matl]

    st.caption(f"Showing {len(filtered):,} of {len(df):,} records")
    st.dataframe(filtered, use_container_width=True, height=500, hide_index=True)

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download Filtered CSV", csv, "ME2J_FILTERED_REPORT.csv", "text/csv")

with tab3:
    AGENT_FQN = "SNOWFLAKE_POC.ME2J_SCHEMA.BGRE_ME2J_PROCUREMENT_AGENT"

    st.subheader("AI Assistant")
    st.caption("Connected to Cortex Agent: BGRE_ME2J_PROCUREMENT_AGENT")

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
            if isinstance(raw_resp, str):
                resp = json.loads(raw_resp)
            else:
                resp = raw_resp
        except Exception:
            return {
                "text": str(raw_resp),
                "sql": None,
                "table": None,
                "suggestions": []
            }

        final_text = []
        final_sql = None
        final_table = None
        suggestions = []

        for item in resp.get("content", []):
            item_type = item.get("type")

            if item_type == "text":
                text = item.get("text", "")
                if text:
                    final_text.append(text)

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
                            cols = [
                                c["name"]
                                for c in rs.get("resultSetMetaData", {}).get("rowType", [])
                            ]
                            final_table = pd.DataFrame(rs["data"], columns=cols if cols else None)

        return {
            "text": "\n\n".join(final_text) if final_text else "No detailed response received from agent.",
            "sql": final_sql,
            "table": final_table,
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
                        st.metric(col.replace("_", " ").title(), f"{chart_df[col].iloc[0]:,.2f}")
                return

            if date_cols and num_cols:
                x_col = date_cols[0]
                y_col = num_cols[0]

                trend_df = chart_df[[x_col, y_col]].dropna().sort_values(x_col)

                fig = px.line(
                    trend_df,
                    x=x_col,
                    y=y_col,
                    markers=True,
                    text=y_col,
                    title=f"{y_col} Trend by {x_col}"
                )
                fig.update_traces(texttemplate="%{text:,.2f}", textposition="top center")
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
                return

            if text_cols and num_cols:
                label_col = text_cols[0]
                value_col = num_cols[0]

                bar_df = (
                    chart_df[[label_col, value_col]]
                    .dropna()
                    .sort_values(value_col, ascending=False)
                    .head(20)
                )

                fig = px.bar(
                    bar_df,
                    x=value_col,
                    y=label_col,
                    orientation="h",
                    text=value_col,
                    title=f"{value_col} by {label_col}"
                )
                fig.update_layout(
                    height=700,
                    yaxis={"automargin": True},
                    margin=dict(l=10, r=100, t=60, b=40)
                )
                fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
                st.plotly_chart(fig, use_container_width=True)
                return

            if len(num_cols) >= 2:
                st.line_chart(chart_df[num_cols].head(50))
                return

            if len(num_cols) == 1:
                value_col = num_cols[0]
                fig = px.histogram(
                    chart_df,
                    x=value_col,
                    title=f"Distribution of {value_col}"
                )
                fig.update_layout(height=550)
                st.plotly_chart(fig, use_container_width=True)
                return

            if text_cols:
                label_col = text_cols[0]
                count_df = (
                    chart_df[label_col]
                    .astype(str)
                    .value_counts()
                    .reset_index()
                )
                count_df.columns = [label_col, "Count"]

                fig = px.bar(
                    count_df.head(20),
                    x="Count",
                    y=label_col,
                    orientation="h",
                    text="Count",
                    title=f"Count by {label_col}"
                )
                fig.update_layout(height=650, yaxis={"automargin": True})
                fig.update_traces(textposition="outside")
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

        if parsed.get("table") is not None and not parsed["table"].empty:
            st.markdown("### Result Data")
            st.dataframe(parsed["table"], use_container_width=True, hide_index=True)

            make_ai_chart(parsed["table"])

            csv = parsed["table"].to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download AI Result",
                csv,
                "AI_RESULT.csv",
                "text/csv",
                use_container_width=True
            )

        if parsed.get("suggestions"):
            st.markdown("### Suggested Follow-up Questions")
            for q in parsed["suggestions"][:5]:
                st.write(f"- {q}")

    if "me2j_agent_messages" not in st.session_state:
        st.session_state.me2j_agent_messages = []

    for msg in st.session_state.me2j_agent_messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                render_agent_result(msg["content"])
            else:
                st.markdown(msg["content"])

    user_question = st.chat_input("Ask about ME2J procurement data...")

    if user_question:
        st.session_state.me2j_agent_messages.append({
            "role": "user",
            "content": user_question
        })

        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Cortex Agent is analyzing..."):
                try:
                    raw_response = run_agent(user_question)
                    parsed = parse_agent_response(raw_response)
                    render_agent_result(parsed)

                    st.session_state.me2j_agent_messages.append({
                        "role": "assistant",
                        "content": parsed
                    })

                except Exception:
                    st.info("AI response could not be generated for this question. Please try rephrasing the question.")
