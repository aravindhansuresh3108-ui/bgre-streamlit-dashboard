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
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        min-height: 125px;
    }
    .kpi-title {font-size:14px;color:#6B7280;margin-bottom:8px;}
    .kpi-value {font-size:26px;font-weight:800;color:#111827;overflow-wrap:anywhere;}
    .drill-card {
        background:#F8FAFC;
        border:1px solid #CBD5E1;
        border-radius:16px;
        padding:18px;
        margin-top:12px;
    }
    </style>
    """, unsafe_allow_html=True)

    def money_fmt(v):
        try:
            return f"INR {float(v):,.2f}"
        except:
            return "INR 0.00"

    def num_fmt(v):
        try:
            return f"{float(v):,.0f}"
        except:
            return "0"

    def kpi(title, value):
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">{title}</div>
                <div class="kpi-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    def clean_numeric(df, cols):
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        return df

    def mini_summary(df, title):
        st.markdown(f"#### {title}")
        a, b, c, d = st.columns(4)
        a.metric("Records", f"{len(df):,}")
        b.metric("PO Count", f"{df['PurchDoc'].nunique():,.0f}")
        c.metric("PO Value", money_fmt(df["POH"].sum()))
        d.metric("Pending Qty", f"{df['Still to be del.'].clip(lower=0).sum():,.2f}")

    def detail_table(df, rows=15):
        show_cols = [
            "PurchDoc", "Item", "Item Doc Date", "Vendor Name",
            "Short Text", "Material", "PO Quantity Sto", "GR Qty",
            "Still to be del.", "Still to be inv.", "POH", "Plant", "Doc Type"
        ]
        available = [c for c in show_cols if c in df.columns]
        st.dataframe(df[available].head(rows), use_container_width=True, hide_index=True)

    st.subheader("Executive Summary")

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

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi("Total POs", num_fmt(filtered_df["PurchDoc"].nunique()))
    with k2:
        kpi("Total Vendors", num_fmt(filtered_df["Vendor/Supplying plant"].nunique()))
    with k3:
        kpi("Total PO Value", money_fmt(filtered_df["POH"].sum()))
    with k4:
        kpi("Pending Delivery Qty", num_fmt(filtered_df["Still to be del."].clip(lower=0).sum()))

    st.caption(f"Filtered Records: {len(filtered_df):,}")
    st.divider()

    chart1, chart2 = st.columns(2)

    with chart1:
        st.markdown("### Top Vendors by PO Value")

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

        fig_vendor = px.bar(
            vendor_chart,
            x="Total_PO_Value",
            y="Vendor Name",
            orientation="h",
            text="Total_PO_Value",
            hover_data=["PO_Count", "Total_Qty", "Pending_Qty"],
        )
        fig_vendor.update_layout(height=620, yaxis={"automargin": True}, margin=dict(l=10, r=40, t=20, b=40))
        fig_vendor.update_traces(texttemplate="%{text:,.2f}", textposition="outside")

        vendor_event = st.plotly_chart(
            fig_vendor,
            use_container_width=True,
            key="vendor_power_chart",
            on_select="rerun",
            selection_mode="points",
        )

        if vendor_event and vendor_event.selection.points:
            selected = vendor_event.selection.points[0]["y"]
            vendor_df = filtered_df[filtered_df["Vendor Name"].astype(str) == str(selected)]

            with st.container(border=True):
                mini_summary(vendor_df, f"Vendor Drilldown: {selected}")

                d1, d2 = st.columns(2)
                with d1:
                    plant_split = (
                        vendor_df.groupby("Plant", dropna=True)["POH"]
                        .sum().reset_index().sort_values("POH", ascending=False).head(10)
                    )
                    fig = px.bar(plant_split, x="POH", y="Plant", orientation="h", text="POH", title="Plant Split")
                    fig.update_layout(height=350, yaxis={"automargin": True})
                    fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
                    st.plotly_chart(fig, use_container_width=True)

                with d2:
                    mat_split = (
                        vendor_df.groupby("Short Text", dropna=True)["POH"]
                        .sum().reset_index().sort_values("POH", ascending=False).head(10)
                    )
                    fig = px.bar(mat_split, x="POH", y="Short Text", orientation="h", text="POH", title="Material Split")
                    fig.update_layout(height=350, yaxis={"automargin": True})
                    fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
                    st.plotly_chart(fig, use_container_width=True)

                detail_table(vendor_df)

    with chart2:
        st.markdown("### Top Materials by PO Value")

        material_chart = (
            filtered_df.groupby("Short Text", dropna=True)
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

        fig_material = px.bar(
            material_chart,
            x="Total_PO_Value",
            y="Short Text",
            orientation="h",
            text="Total_PO_Value",
            hover_data=["PO_Count", "Total_Qty", "Pending_Qty"],
        )
        fig_material.update_layout(height=620, yaxis={"automargin": True}, margin=dict(l=10, r=40, t=20, b=40))
        fig_material.update_traces(texttemplate="%{text:,.2f}", textposition="outside")

        material_event = st.plotly_chart(
            fig_material,
            use_container_width=True,
            key="material_power_chart",
            on_select="rerun",
            selection_mode="points",
        )

        if material_event and material_event.selection.points:
            selected = material_event.selection.points[0]["y"]
            mat_df = filtered_df[filtered_df["Short Text"].astype(str) == str(selected)]

            with st.container(border=True):
                mini_summary(mat_df, f"Material Drilldown: {selected}")

                d1, d2 = st.columns(2)
                with d1:
                    vendor_split = (
                        mat_df.groupby("Vendor Name", dropna=True)["POH"]
                        .sum().reset_index().sort_values("POH", ascending=False).head(10)
                    )
                    fig = px.bar(vendor_split, x="POH", y="Vendor Name", orientation="h", text="POH", title="Vendor Split")
                    fig.update_layout(height=350, yaxis={"automargin": True})
                    fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
                    st.plotly_chart(fig, use_container_width=True)

                with d2:
                    plant_split = (
                        mat_df.groupby("Plant", dropna=True)["POH"]
                        .sum().reset_index().sort_values("POH", ascending=False).head(10)
                    )
                    fig = px.bar(plant_split, x="POH", y="Plant", orientation="h", text="POH", title="Plant Split")
                    fig.update_layout(height=350, yaxis={"automargin": True})
                    fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
                    st.plotly_chart(fig, use_container_width=True)

                detail_table(mat_df)

    chart3, chart4 = st.columns(2)

    with chart3:
        st.markdown("### Plant Wise Procurement")

        plant_chart = (
            filtered_df.groupby("Plant", dropna=True)
            .agg(
                Total_Value=("POH", "sum"),
                Total_Qty=("PO Quantity Sto", "sum"),
                PO_Count=("PurchDoc", "nunique"),
            )
            .reset_index()
            .sort_values("Total_Value", ascending=False)
        )

        fig_plant = px.bar(
            plant_chart,
            x="Plant",
            y="Total_Value",
            text="Total_Value",
            hover_data=["Total_Qty", "PO_Count"],
        )
        fig_plant.update_layout(height=530, xaxis_tickangle=-45, margin=dict(l=10, r=40, t=20, b=80))
        fig_plant.update_traces(texttemplate="%{text:,.2f}", textposition="outside")

        plant_event = st.plotly_chart(
            fig_plant,
            use_container_width=True,
            key="plant_power_chart",
            on_select="rerun",
            selection_mode="points",
        )

        if plant_event and plant_event.selection.points:
            selected = plant_event.selection.points[0]["x"]
            plant_df = filtered_df[filtered_df["Plant"].astype(str) == str(selected)]

            with st.container(border=True):
                mini_summary(plant_df, f"Plant Drilldown: {selected}")

                vendor_split = (
                    plant_df.groupby("Vendor Name", dropna=True)["POH"]
                    .sum().reset_index().sort_values("POH", ascending=False).head(10)
                )
                fig = px.bar(vendor_split, x="POH", y="Vendor Name", orientation="h", text="POH", title="Top Vendors in Plant")
                fig.update_layout(height=380, yaxis={"automargin": True})
                fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
                st.plotly_chart(fig, use_container_width=True)

                detail_table(plant_df)

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

        fig_doc = px.pie(
            doc_chart,
            names="Doc Type",
            values="PO_Count",
            hole=0.45,
            hover_data=["Total_PO_Value", "Pending_Qty"],
        )
        fig_doc.update_traces(textposition="inside", textinfo="percent+label")
        fig_doc.update_layout(height=530, margin=dict(l=10, r=10, t=20, b=20))

        doc_event = st.plotly_chart(
            fig_doc,
            use_container_width=True,
            key="doc_power_chart",
            on_select="rerun",
            selection_mode="points",
        )

        if doc_event and doc_event.selection.points:
            selected = doc_event.selection.points[0]["label"]
            doc_df = filtered_df[filtered_df["Doc Type"].astype(str) == str(selected)]

            with st.container(border=True):
                mini_summary(doc_df, f"Document Type Drilldown: {selected}")

                d1, d2 = st.columns(2)
                with d1:
                    vendor_split = (
                        doc_df.groupby("Vendor Name", dropna=True)["POH"]
                        .sum().reset_index().sort_values("POH", ascending=False).head(10)
                    )
                    fig = px.bar(vendor_split, x="POH", y="Vendor Name", orientation="h", text="POH", title=f"Top Vendors for {selected}")
                    fig.update_layout(height=350, yaxis={"automargin": True})
                    fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
                    st.plotly_chart(fig, use_container_width=True)

                with d2:
                    mat_split = (
                        doc_df.groupby("Short Text", dropna=True)["POH"]
                        .sum().reset_index().sort_values("POH", ascending=False).head(10)
                    )
                    fig = px.bar(mat_split, x="POH", y="Short Text", orientation="h", text="POH", title=f"Top Materials for {selected}")
                    fig.update_layout(height=350, yaxis={"automargin": True})
                    fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
                    st.plotly_chart(fig, use_container_width=True)

                detail_table(doc_df)

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

        fig_delivery = px.bar(
            delivery_chart,
            x="Status",
            y="Quantity",
            text="Quantity",
        )
        fig_delivery.update_layout(height=480)
        fig_delivery.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
        st.plotly_chart(fig_delivery, use_container_width=True)

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

        fig_trend = px.line(
            trend_df,
            x="Month",
            y="PO_Value",
            markers=True,
            hover_data=["PO_Count"],
        )
        fig_trend.update_layout(height=480)
        st.plotly_chart(fig_trend, use_container_width=True)
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
        if isinstance(raw_resp, str):
            resp = json.loads(raw_resp)
        else:
            resp = raw_resp

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

            if item_type == "suggested_queries":
                for q in item.get("suggested_queries", []):
                    if q.get("query"):
                        suggestions.append(q["query"])

            if item_type == "tool_result":
                tool_result = item.get("tool_result", {})
                for content in tool_result.get("content", []):
                    if content.get("type") == "json":
                        json_data = content.get("json", {})

                        if json_data.get("text"):
                            final_text.append(json_data["text"])

                        if json_data.get("sql"):
                            final_sql = json_data["sql"]

                        result_set = json_data.get("result_set")
                        if result_set and result_set.get("data"):
                            columns = [
                                col["name"]
                                for col in result_set.get("resultSetMetaData", {}).get("rowType", [])
                            ]
                            final_table = pd.DataFrame(result_set["data"], columns=columns)

        return {
            "text": "\n\n".join(final_text) if final_text else "No text response from agent.",
            "sql": final_sql,
            "table": final_table,
            "suggestions": suggestions
        }

    if "me2j_agent_messages" not in st.session_state:
        st.session_state.me2j_agent_messages = []

    for msg in st.session_state.me2j_agent_messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown(msg["text"])

                if msg.get("sql"):
                    with st.expander("Generated SQL"):
                        st.code(msg["sql"], language="sql")

                if msg.get("table") is not None:
                    st.dataframe(msg["table"], use_container_width=True, hide_index=True)

                    num_cols = msg["table"].select_dtypes(include=["number"]).columns.tolist()
                    text_cols = msg["table"].select_dtypes(include=["object"]).columns.tolist()

                    if num_cols and text_cols:
                        st.bar_chart(msg["table"], x=text_cols[0], y=num_cols[0])

            else:
                st.markdown(msg["text"])

    user_question = st.chat_input("Ask about ME2J procurement data...")

    if user_question:
        st.session_state.me2j_agent_messages.append({
            "role": "user",
            "text": user_question
        })

        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Cortex Agent is analyzing..."):
                try:
                    raw_response = run_agent(user_question)
                    parsed = parse_agent_response(raw_response)

                    st.markdown(parsed["text"])

                    if parsed["sql"]:
                        with st.expander("Generated SQL"):
                            st.code(parsed["sql"], language="sql")

                    if parsed["table"] is not None:
                        st.dataframe(parsed["table"], use_container_width=True, hide_index=True)

                        num_cols = parsed["table"].select_dtypes(include=["number"]).columns.tolist()
                        text_cols = parsed["table"].select_dtypes(include=["object"]).columns.tolist()

                        if num_cols and text_cols:
                            st.bar_chart(parsed["table"], x=text_cols[0], y=num_cols[0])

                    if parsed["suggestions"]:
                        st.caption("Suggested follow-up questions:")
                        for q in parsed["suggestions"][:3]:
                            st.write(f"- {q}")

                    st.session_state.me2j_agent_messages.append({
                        "role": "assistant",
                        "text": parsed["text"],
                        "sql": parsed["sql"],
                        "table": parsed["table"]
                    })

                except Exception as e:
                    error_msg = f"Agent error: {e}"
                    st.error(error_msg)
                    st.session_state.me2j_agent_messages.append({
                        "role": "assistant",
                        "text": error_msg
                    })