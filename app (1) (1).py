import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="SufraEats Business Intelligence Hub",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for a polished look
st.markdown("""
<style>
    .reportview-container { background: #f5f7f9; }
    .main-metric-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #ff4b4b;
    }
</style>
""", unsafe_scale=True)

# ==========================================
# DATA LOADING & CACHING PIPELINE
# ==========================================
@st.cache_data
def load_and_clean_data():
    # 1. Load data
    orders = pd.read_csv("sufraeats_orders.csv")
    restaurants = pd.read_csv("sufraeats_restaurants.csv")
    
    # 2. Text Standardization
    restaurants['zone'] = restaurants['zone'].astype(str).str.strip().str.lower()
    restaurants['cuisine'] = restaurants['cuisine'].astype(str).str.strip().str.lower()
    
    zone_mapping = {
        'jlt': 'jumeirah lake towers',
        'marina': 'dubai marina'
    }
    restaurants['zone'] = restaurants['zone'].replace(zone_mapping)
    
    for col in ['order_status', 'customer_type', 'order_channel', 'payment_method', 'device_platform']:
        if col in orders.columns:
            orders[col] = orders[col].astype(str).str.strip().str.lower()
            
    # 3. Deduplication
    orders = orders.drop_duplicates(subset=['order_id'], keep='first')
    restaurants = restaurants.drop_duplicates(subset=['restaurant_id'], keep='first')
    
    # 4. Merging via Inner Join
    df_clean = pd.merge(orders, restaurants, on='restaurant_id', how='inner')
    
    # 5. Advanced Mathematical Imputation
    df_clean['promo_code'] = df_clean['promo_code'].fillna('no promo')
    df_clean['discount_amount'] = df_clean['discount_amount'].fillna(0.0)
    
    df_clean['rating'] = df_clean.groupby('restaurant_id')['rating'].transform(
        lambda x: x.fillna(x.median()) if x.notnull().any() else x
    )
    df_clean['rating'] = df_clean.groupby('zone')['rating'].transform(
        lambda x: x.fillna(x.median()) if x.notnull().any() else x
    )
    global_median_rating = df_clean['rating'].median()
    df_clean['rating'] = df_clean['rating'].fillna(global_median_rating)
    
    # 6. Filtering Out Anomalies
    valid_condition = (
        (df_clean['basket_value'] >= 0) &
        (df_clean['delivery_time_min'] >= 0) &
        (df_clean['hour'] >= 0) & (df_clean['hour'] <= 23)
    )
    df_clean = df_clean[valid_condition]
    
    # 7. Feature Engineering Business Logic
    df_clean['gross_order_value'] = df_clean['basket_value']
    df_clean['is_completed'] = df_clean['order_status'] == 'delivered'
    
    df_clean['realised_revenue'] = np.where(
        df_clean['is_completed'],
        (df_clean['basket_value'] * df_clean['commission_rate']) + df_clean['delivery_fee'] - df_clean['discount_amount'],
        0.0
    )
    
    df_clean['date'] = pd.to_datetime(df_clean['date'])
    df_clean['month'] = df_clean['date'].dt.strftime('%B').str.lower()
    df_clean['month_num'] = df_clean['date'].dt.month
    df_clean['day_of_week'] = df_clean['date'].dt.strftime('%A').str.lower()
    df_clean['is_ramadan'] = df_clean['date'].between('2025-02-28', '2025-03-29')
    
    return df_clean

# Initialize Data
try:
    df_clean = load_and_clean_data()
except Exception as e:
    st.error(f"Error executing data loading pipeline: {e}. Please make sure 'sufraeats_orders.csv' and 'sufraeats_restaurants.csv' are in the same folder.")
    st.stop()

# ==========================================
# SIDEBAR NAVIGATION & INTERACTIVE FILTER
# ==========================================
st.sidebar.title("🍔 SufraEats NavCenter")
page = st.sidebar.radio("Go to:", ["📈 Executive Dashboard", "🗺️ Zone & Logistics Analysis", "🌙 Ramadan & Temporal Surges"])

# Interactive Sidebar Filter
selected_zones = st.sidebar.multiselect("Filter by Zone Focus Area:", 
                                        options=list(df_clean['zone'].unique().tolist()),
                                        default=list(df_clean['zone'].unique().tolist()))

# Filter Dataset Context
df_filtered = df_clean[df_clean['zone'].isin(selected_zones)]

# ==========================================
# PAGE 1: EXECUTIVE DASHBOARD
# ==========================================
if page == "📈 Executive Dashboard":
    st.title("📊 SufraEats Executive Summary Hub")
    st.markdown("---")
    
    # Macro KPI Metric Blocks
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Total Order Volume", f"{len(df_filtered):,}")
    with kpi2:
        st.metric("Gross Basket Value", f"{(df_filtered['gross_order_value'].sum()):,.2f} AED")
    with kpi3:
        st.metric("Realised Net Profit", f"{(df_filtered['realised_revenue'].sum()):,.2f} AED")
    with kpi4:
        success_rate = df_filtered['is_completed'].mean() * 100
        st.metric("Platform Success Rate", f"{success_rate:.2f}%")
        
    st.markdown("### 👑 Automated Expansion Strategy Analytics")
    
    # Investment Expansion Model Logic
    zone_rankings = df_clean.groupby('zone').agg(
        total_orders=('order_id', 'count'),
        net_realised_profit=('realised_revenue', 'sum'),
        avg_customer_rating=('rating', 'mean')
    ).reset_index()
    top_zone = zone_rankings.sort_values(by='net_realised_profit', ascending=False).iloc[0]['zone']
    
    target_zone_storefronts = df_clean[df_clean['zone'] == top_zone]
    restaurant_rankings = target_zone_storefronts.groupby('restaurant_name').agg(
        total_orders=('order_id', 'count'),
        net_realised_profit=('realised_revenue', 'sum'),
        avg_customer_rating=('rating', 'mean')
    ).reset_index()
    top_rest = restaurant_rankings.sort_values(by='net_realised_profit', ascending=False).iloc[0]
    
    exp1, exp2 = st.columns(2)
    with exp1:
        st.info(f"🏆 **RECOMMENDED EXPANSION ZONE:** `{top_zone.upper()}`\n"
                f"* **Net Profit Retained:** {zone_rankings[zone_rankings['zone']==top_zone]['net_realised_profit'].values[0]:,.2f} AED\n"
                f"* **Market Quality Score:** {zone_rankings[zone_rankings['zone']==top_zone]['avg_customer_rating'].values[0]:.2f} ⭐")
    with exp2:
        st.success(f"🏪 **RECOMMENDED ANCHOR MERCHANT:** `{top_rest['restaurant_name'].upper()}`\n"
                   f"* **Hub Order Throughput:** {top_rest['total_orders']:,} orders\n"
                   f"* **Storefront Net Profit:** {top_rest['net_realised_profit']:,.2f} AED")

    st.markdown("---")
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### 💵 Financial Performance Ledger by Region")
        zone_performance = df_filtered.groupby('zone').agg(
            total_orders=('order_id', 'count'),
            gross_order_value=('basket_value', 'sum'),
            realised_revenue=('realised_revenue', 'sum')
        ).reset_index()
        
        fig_fin = px.bar(zone_performance, x='zone', y=['gross_order_value', 'realised_revenue'],
                         barmode='group', title="Gross Value vs Realised Revenue",
                         labels={'value': 'AED Amount', 'zone': 'Zone'},
                         color_discrete_sequence=['#4F46E5', '#10B981'])
        st.plotly_chart(fig_fin, use_container_width=True)
        
    with col_right:
        st.markdown("#### 👥 Customer Profiles & Preferred Ecosystem Channels")
        cohort_counts = df_filtered['customer_type'].value_counts().reset_index()
        fig_pie = px.pie(cohort_counts, values='count', names='customer_type', 
                         title="Ecosystem Order Split: New vs Repeat Cohorts",
                         color_discrete_sequence=['#EC4899', '#F59E0B'])
        st.plotly_chart(fig_pie, use_container_width=True)

    # Monthly Financial Tracking Graph
    st.markdown("#### 📅 Monthly Revenue Performance vs Marketing Costs (Discounts)")
    monthly_perf = df_filtered.groupby(['month_num', 'month']).agg(
        gross_basket=('basket_value', 'sum'),
        total_discounts=('discount_amount', 'sum'),
        realised_revenue=('realised_revenue', 'sum')
    ).reset_index().sort_values(by='month_num')
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=monthly_perf['month'], y=monthly_perf['gross_basket'], name='Gross Basket Size', line=dict(color='#3B82F6', width=3)))
    fig_line.add_trace(go.Scatter(x=monthly_perf['month'], y=monthly_perf['total_discounts'], name='Marketing Discounts Borne', line=dict(color='#EF4444', width=2, dash='dash')))
    fig_line.add_trace(go.Scatter(x=monthly_perf['month'], y=monthly_perf['realised_revenue'], name='Net Realised Revenue', line=dict(color='#10B981', width=3)))
    fig_line.update_layout(title="Monthly Financial Ledger Overview", xaxis_title="Month", yaxis_title="AED Value")
    st.plotly_chart(fig_line, use_container_width=True)

# ==========================================
# PAGE 2: ZONE & LOGISTICS ANALYSIS
# ==========================================
elif page == "🗺️ Zone & Logistics Analysis":
    st.title("🗺️ Regional Quality & Logistics Assessment")
    st.markdown("---")
    
    col_log1, col_log2 = st.columns(2)
    with col_log1:
        st.markdown("#### ⚡ Operational Health Metrics Matrix")
        zone_summary = df_filtered.groupby('zone').agg(
            total_orders=('order_id', 'count'),
            avg_delivery_time=('delivery_time_min', 'mean'),
            avg_rating=('rating', 'mean'),
            cancelled_count=('order_status', lambda x: (x == 'cancelled').sum()),
            refunded_count=('order_status', lambda x: (x == 'refunded').sum())
        ).reset_index()
        zone_summary['order_failure_rate'] = ((zone_summary['cancelled_count'] + zone_summary['refunded_count']) / zone_summary['total_orders']) * 100
        
        st.dataframe(zone_summary[['zone', 'total_orders', 'avg_delivery_time', 'avg_rating', 'order_failure_rate']].style.format({
            'avg_delivery_time': '{:.2f} mins',
            'avg_rating': '{:.2f} ⭐',
            'order_failure_rate': '{:.2f}%'
        }))
        
    with col_log2:
        st.markdown("#### 🍽️ Top Performing Cuisines by Platform Revenue Flow")
        cuisine_analysis = df_filtered.groupby('cuisine').agg(
            total_orders=('order_id', 'count'),
            total_realised_revenue=('realised_revenue', 'sum')
        ).reset_index().sort_values(by='total_realised_revenue', ascending=False)
        
        fig_cuis = px.bar(cuisine_analysis, x='total_realised_revenue', y='cuisine', orientation='h',
                          title="Cuisine Net Revenue Yield", color='total_realised_revenue',
                          color_continuous_scale='Viridis')
        st.plotly_chart(fig_cuis, use_container_width=True)

    st.markdown("---")
    st.markdown("### ⭐ Comprehensive Non-Duplicated Restaurant Ratings Ledger")
    
    # 1. Macro Area Boxplot Visual
    st.markdown("#### Macro Customer Ratings Quality Range Spread by Zone")
    restaurant_zone_ratings = df_filtered.groupby(['zone', 'restaurant_name'])['rating'].mean().reset_index()
    
    fig_box = px.box(restaurant_zone_ratings, x='zone', y='rating', points="all",
                     title="Restaurant Quality Dispersion Matrix (Points represent unique restaurant profiles without repetition)",
                     color='zone')
    st.plotly_chart(fig_box, use_container_width=True)

    # 2. Pivot Table Ledger View
    st.markdown("#### Restaurant Quality Matrix Pivot View")
    restaurant_cohort_matrix = df_filtered.pivot_table(
        values='rating',
        index=['zone', 'restaurant_name'],
        columns='customer_type',
        aggfunc='mean'
    ).reset_index()
    st.dataframe(restaurant_cohort_matrix.style.format({'new': '{:.2f} ⭐', 'repeat': '{:.2f} ⭐'}))

# ==========================================
# PAGE 3: RAMADAN & TEMPORAL SURGES
# ==========================================
elif page == "🌙 Ramadan & Temporal Surges":
    st.title("🌙 Seasonality Performance & Peak Hourly Surges")
    st.markdown("---")
    
    st.markdown("### 🌙 Ramadan vs. Regular Operational Shifts")
    ramadan_vs_normal = df_filtered.groupby('is_ramadan').agg(
        total_orders=('order_id', 'count'),
        avg_basket_value=('basket_value', 'mean'),
        avg_delivery_time=('delivery_time_min', 'mean'),
        realised_revenue=('realised_revenue', 'sum')
    ).reset_index()
    ramadan_vs_normal['is_ramadan'] = ramadan_vs_normal['is_ramadan'].map({True: '🌙 Ramadan Window', False: '🗓️ Normal Operations'})
    st.dataframe(ramadan_vs_normal)
    
    st.markdown("---")
    st.markdown("### ⏰ Diurnal Structural Shift: Peak Traffic Surge Distribution Analysis")
    
    hourly_peaks = df_filtered.groupby(['is_ramadan', 'hour']).agg(
        order_volume=('order_id', 'count')
    ).reset_index()
    hourly_peaks['Period'] = hourly_peaks['is_ramadan'].map({True: 'Ramadan Fasting Season', False: 'Standard Baseline Months'})
    
    fig_hour = px.line(hourly_peaks, x='hour', y='order_volume', color='Period',
                       title="Hourly Order Volume Curves: Ramadan Iftar Surge vs Standard Daily Routine",
                       labels={'hour': 'Hour of Day (00:00 - 23:00)', 'order_volume': 'Total Orders Captured'},
                       line_shape='spline')
    st.plotly_chart(fig_hour, use_container_width=True)
    
    # Coupon Campaign ROI Breakdown Section
    st.markdown("---")
    st.markdown("### 🎟️ Marketing Voucher Campaign Performance & ROI Evaluation")
    promo_analysis = df_filtered.groupby('promo_code').agg(
        total_usages=('order_id', 'count'),
        total_discounts_given=('discount_amount', 'sum'),
        total_realised_revenue=('realised_revenue', 'sum')
    ).reset_index().sort_values(by='total_discounts_given', ascending=False)
    
    fig_promo = px.bar(promo_analysis, x='promo_code', y='total_realised_revenue',
                       color='total_discounts_given', title="Campaign Net Financial Impact vs Discount Expenses",
                       labels={'total_realised_revenue': 'Net Revenue Flow (AED)', 'total_discounts_given': 'Discounts Spent'},
                       color_continuous_scale='Reds')
    st.plotly_chart(fig_promo, use_container_width=True)