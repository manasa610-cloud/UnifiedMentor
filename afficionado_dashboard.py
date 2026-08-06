"""
Afficionado Coffee Roasters
Product Optimization & Revenue Contribution Analysis — Streamlit Dashboard
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os

# ----------------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Afficionado Coffee Roasters | Product Analytics",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = os.path.join(os.path.dirname(__file__), "Afficionado Coffee Roasters.xlsx")


# ----------------------------------------------------------------------------
# Data loading & preparation
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading transaction data...")
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df["revenue"] = df["transaction_qty"] * df["unit_price"]
    df["transaction_time"] = pd.to_datetime(
        df["transaction_time"].astype(str), format="%H:%M:%S", errors="coerce"
    )
    df["hour"] = df["transaction_time"].dt.hour
    # A readable product label combining detail + type (handles size variants)
    df["product_label"] = df["product_detail"].astype(str)
    return df


if not os.path.exists(DATA_FILE):
    st.error(
        f"Data file not found at `{DATA_FILE}`. Place "
        "`Afficionado_Coffee_Roasters.xlsx` in the same folder as this app."
    )
    st.stop()

df_raw = load_data(DATA_FILE)

# ----------------------------------------------------------------------------
# Sidebar — filters
# ----------------------------------------------------------------------------
st.sidebar.title("☕ Filters")

store_options = ["All Stores"] + sorted(df_raw["store_location"].unique().tolist())
store_sel = st.sidebar.selectbox("Store location", store_options, index=0)

cat_options = sorted(df_raw["product_category"].unique().tolist())
cat_sel = st.sidebar.multiselect(
    "Product category", cat_options, default=cat_options
)

# Product type options depend on selected categories
type_pool = df_raw[df_raw["product_category"].isin(cat_sel)] if cat_sel else df_raw
type_options = sorted(type_pool["product_type"].unique().tolist())
type_sel = st.sidebar.multiselect(
    "Product type", type_options, default=type_options
)

top_n = st.sidebar.slider("Top-N products to display", min_value=5, max_value=40, value=15, step=1)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data: 2025 transaction-level sales across 3 NYC store locations. "
    "Revenue = transaction_qty × unit_price."
)

# ----------------------------------------------------------------------------
# Apply filters
# ----------------------------------------------------------------------------
df = df_raw.copy()
if store_sel != "All Stores":
    df = df[df["store_location"] == store_sel]
if cat_sel:
    df = df[df["product_category"].isin(cat_sel)]
if type_sel:
    df = df[df["product_type"].isin(type_sel)]

if df.empty:
    st.warning("No data matches the selected filters. Please broaden your selection.")
    st.stop()

total_revenue = df["revenue"].sum()
total_units = df["transaction_qty"].sum()
total_txn = df["transaction_id"].nunique()
n_products = df["product_id"].nunique()

# ----------------------------------------------------------------------------
# Header + KPIs
# ----------------------------------------------------------------------------
st.title("Product Optimization & Revenue Contribution Analysis")
st.caption("Afficionado Coffee Roasters — live product analytics dashboard")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"${total_revenue:,.0f}")
k2.metric("Units Sold", f"{total_units:,.0f}")
k3.metric("Transactions", f"{total_txn:,.0f}")
k4.metric("Active Products (SKUs)", f"{n_products}")

st.markdown("---")

# ----------------------------------------------------------------------------
# Tabs for the four core modules
# ----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📊 Product Ranking",
        "🗂️ Category Revenue Distribution",
        "🎯 Popularity vs Revenue",
        "🔍 Product Drill-Down",
    ]
)

# --- Product-level aggregation used throughout ---
prod = (
    df.groupby(["product_id", "product_category", "product_type", "product_label"])
    .agg(units=("transaction_qty", "sum"), revenue=("revenue", "sum"), transactions=("transaction_id", "count"))
    .reset_index()
)
prod["revenue_share_pct"] = prod["revenue"] / total_revenue * 100
prod["efficiency_score"] = prod["revenue"] / prod["units"]
prod["volume_rank"] = prod["units"].rank(ascending=False, method="min").astype(int)
prod["revenue_rank"] = prod["revenue"].rank(ascending=False, method="min").astype(int)
prod = prod.sort_values("revenue", ascending=False).reset_index(drop=True)

# ============================== TAB 1: PRODUCT RANKING ======================
with tab1:
    st.subheader("Product Ranking by Volume & Revenue")

    rank_metric = st.radio(
        "Rank by:", ["Revenue", "Units Sold"], horizontal=True, key="rank_metric"
    )
    sort_col = "revenue" if rank_metric == "Revenue" else "units"
    top_df = prod.sort_values(sort_col, ascending=False).head(top_n)
    bottom_df = prod.sort_values(sort_col, ascending=True).head(top_n)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Top {top_n} products by {rank_metric.lower()}**")
        fig = px.bar(
            top_df.sort_values(sort_col),
            x=sort_col,
            y="product_label",
            orientation="h",
            color="product_category",
            labels={sort_col: rank_metric, "product_label": "Product"},
        )
        fig.update_layout(height=500, legend_title="Category")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown(f"**Bottom {top_n} products by {rank_metric.lower()}** (candidates for review)")
        fig2 = px.bar(
            bottom_df.sort_values(sort_col, ascending=False),
            x=sort_col,
            y="product_label",
            orientation="h",
            color="product_category",
            labels={sort_col: rank_metric, "product_label": "Product"},
        )
        fig2.update_layout(height=500, legend_title="Category")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**Full ranking table**")
    st.dataframe(
        prod[["product_label", "product_category", "product_type", "units", "revenue", "revenue_share_pct"]]
        .rename(columns={
            "product_label": "Product", "product_category": "Category", "product_type": "Type",
            "units": "Units Sold", "revenue": "Revenue ($)", "revenue_share_pct": "Revenue Share (%)"
        }),
        use_container_width=True,
        height=350,
        column_config={
            "Revenue ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Revenue Share (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

# ============================== TAB 2: CATEGORY DISTRIBUTION ================
with tab2:
    st.subheader("Category Revenue Distribution")

    cat_agg = (
        df.groupby("product_category")
        .agg(units=("transaction_qty", "sum"), revenue=("revenue", "sum"), n_products=("product_id", "nunique"))
        .reset_index()
    )
    cat_agg["revenue_share_pct"] = cat_agg["revenue"] / total_revenue * 100
    cat_agg = cat_agg.sort_values("revenue", ascending=False)

    c1, c2 = st.columns([1, 1])
    with c1:
        fig = px.pie(
            cat_agg, names="product_category", values="revenue", hole=0.45,
            title="Revenue Share by Category",
        )
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(
            cat_agg, x="product_category", y="revenue", color="product_category",
            title="Total Revenue by Category", labels={"revenue": "Revenue ($)", "product_category": "Category"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Product-type contribution within each category**")
    cat_focus = st.selectbox("Select category to drill into", cat_agg["product_category"].tolist())
    type_agg = (
        df[df["product_category"] == cat_focus]
        .groupby("product_type")
        .agg(units=("transaction_qty", "sum"), revenue=("revenue", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    type_agg["revenue_share_pct_of_category"] = type_agg["revenue"] / type_agg["revenue"].sum() * 100
    fig = px.bar(
        type_agg, x="revenue", y="product_type", orientation="h",
        labels={"revenue": "Revenue ($)", "product_type": "Product Type"},
        title=f"Revenue by Product Type — {cat_focus}",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        cat_agg.rename(columns={
            "product_category": "Category", "units": "Units Sold", "revenue": "Revenue ($)",
            "n_products": "# SKUs", "revenue_share_pct": "Revenue Share (%)"
        }),
        use_container_width=True,
        column_config={
            "Revenue ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Revenue Share (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

# ============================== TAB 3: POPULARITY VS REVENUE ================
with tab3:
    st.subheader("Popularity vs Revenue — Where Do Products Fall?")
    st.caption(
        "Bubble size = revenue share. Products in the top-right are both popular and "
        "high-revenue (menu anchors). Products in the bottom-left are low-impact long-tail items."
    )

    fig = px.scatter(
        prod, x="units", y="revenue", size="revenue_share_pct", color="product_category",
        hover_name="product_label",
        hover_data={"volume_rank": True, "revenue_rank": True, "revenue_share_pct": ":.2f"},
        labels={"units": "Units Sold (Popularity)", "revenue": "Revenue ($)"},
        size_max=40,
    )
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Volume rank vs. revenue rank — biggest mismatches**")
    prod["rank_gap"] = prod["volume_rank"] - prod["revenue_rank"]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("_High popularity, low revenue rank (loss-leader candidates)_")
        st.dataframe(
            prod.sort_values("rank_gap").head(8)[
                ["product_label", "product_category", "units", "revenue", "volume_rank", "revenue_rank"]
            ].rename(columns={"product_label": "Product", "product_category": "Category"}),
            use_container_width=True,
        )
    with c2:
        st.markdown("_High revenue rank relative to volume (premium performers)_")
        st.dataframe(
            prod.sort_values("rank_gap", ascending=False).head(8)[
                ["product_label", "product_category", "units", "revenue", "volume_rank", "revenue_rank"]
            ].rename(columns={"product_label": "Product", "product_category": "Category"}),
            use_container_width=True,
        )

# ============================== TAB 4: PRODUCT DRILL-DOWN ===================
with tab4:
    st.subheader("Product Drill-Down Performance Table")

    search = st.text_input("Search product name", "")
    drill = prod.copy()
    if search:
        drill = drill[drill["product_label"].str.contains(search, case=False, na=False)]

    drill_display = drill[[
        "product_label", "product_category", "product_type", "units", "revenue",
        "revenue_share_pct", "efficiency_score", "volume_rank", "revenue_rank"
    ]].rename(columns={
        "product_label": "Product", "product_category": "Category", "product_type": "Type",
        "units": "Units Sold", "revenue": "Revenue ($)", "revenue_share_pct": "Revenue Share (%)",
        "efficiency_score": "Revenue per Unit ($)", "volume_rank": "Volume Rank", "revenue_rank": "Revenue Rank",
    })
    st.dataframe(
        drill_display,
        use_container_width=True,
        height=450,
        column_config={
            "Revenue ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Revenue Share (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "Revenue per Unit ($)": st.column_config.NumberColumn(format="$%.2f"),
        },
    )

    st.markdown("---")
    st.markdown("### Revenue Concentration (Pareto / 80–20) Analysis")
    pareto = prod.sort_values("revenue", ascending=False).reset_index(drop=True)
    pareto["cum_revenue"] = pareto["revenue"].cumsum()
    pareto["cum_share_pct"] = pareto["cum_revenue"] / total_revenue * 100
    pareto["sku_number"] = pareto.index + 1

    n_skus_80 = int((pareto["cum_share_pct"] <= 80).sum() + 1)
    pct_skus_80 = n_skus_80 / len(pareto) * 100

    c1, c2 = st.columns([2, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=pareto["sku_number"], y=pareto["revenue"], name="Revenue"))
        fig.add_trace(go.Scatter(
            x=pareto["sku_number"], y=pareto["cum_share_pct"], name="Cumulative Revenue %",
            yaxis="y2", mode="lines+markers"
        ))
        fig.update_layout(
            title="Pareto Chart — Revenue Concentration Across SKUs",
            xaxis_title="Product rank (by revenue)",
            yaxis=dict(title="Revenue ($)"),
            yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 100]),
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.metric("SKUs needed for 80% of revenue", f"{n_skus_80} of {len(pareto)}")
        st.metric("Share of SKU menu", f"{pct_skus_80:.1f}%")
        st.metric("Top-10 SKU revenue concentration", f"{pareto.head(10)['revenue'].sum()/total_revenue*100:.1f}%")
        st.caption(
            "A lower % of SKUs needed for 80% of revenue indicates higher menu risk "
            "(dependence on few products)."
        )

st.markdown("---")
st.caption("Afficionado Coffee Roasters · Product Optimization & Revenue Contribution Analysis · Built with Streamlit")