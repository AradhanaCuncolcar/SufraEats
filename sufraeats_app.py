import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="SufraEats Executive Intelligence",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Palette
DARK_BG        = "#0B132B" 
CARD_BG        = "#1C2541" 
SUFRA_CRIMSON  = "#FF4D4D" 
SAFFRON_GOLD   = "#FFB020" 
MINT_GARNISH   = "#22C55E" 
LEAKAGE_RED    = "#E63946"

st.markdown(f"""
<style>
    .stApp {{ background-color: {DARK_BG}; color: #FFFFFF; font-family: 'Inter', sans-serif; }}
    .board-card {{
        background-color: {CARD_BG};
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #3A4766;
        margin-bottom: 20px;
    }}
    hr {{ border-color: #3A4766; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATA LOADING PIPELINE
# ==========================================
@st.cache_data
def load_and_clean_data():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    orders = pd.read_csv(os.path.join(BASE_DIR, "sufraeats_orders.csv"))
    restaurants = pd.read_csv(os.path.join(BASE_DIR, "sufraeats_restaurants.csv"))
    
    # Cleaning & Merging
    restaurants['zone'] = restaurants['zone'].astype(str).str.strip().str.lower()
    restaurants['cuisine'] = restaurants['cuisine'].astype(str).str.strip().str.lower()
    restaurants['zone'] = restaurants['zone'].replace({'jlt': 'jumeirah lake towers', 'marina': 'dubai marina'})
    
    for col in ['order_status', 'customer_type', 'order_channel', 'payment_method']:
        if col in orders.columns:
            orders[col] = orders[col].astype(str).str.strip().str.lower()
            
    orders = orders.drop_duplicates(subset=['order_id'])
    restaurants = restaurants.drop_duplicates(subset=['restaurant_id'])
    df = pd.merge(orders, restaurants, on='restaurant_id', how='inner')
    
    # Imputation
    df['promo_code'] = df['promo_code'].fillna('no promo').str.strip().str.lower()
    df['discount_amount'] = df['discount_amount'].fillna(0.0)
    df['rating'] = df['rating'].fillna(df['rating'].median())
    
    # Logical Constraints
    df = df[(df['basket_value'] >= 0) & (df['delivery_time_min'] >= 0)]
    
    # Advanced Feature Engineering
    df['is_completed'] = df['order_status'] == 'delivered'
    df['is_cancelled'] = df['order_status'] == 'cancelled'
    df['is_refunded'] = df['order_status'] == 'refunded'
    
    df['realised_revenue'] = np.where(df['is_completed'], (df['basket_value'] * df['commission_rate']) + df['delivery_fee'], 0.0)
    df['net_profit'] = np.where(df['is_completed'], df['realised_revenue'] - df['discount_amount'], 0.0)
    
    # Leakage Calculation (Money left on the table)
    df['lost_to_cancellations'] = np.where(df['is_cancelled'], df['basket_value'], 0.0)
    df['lost_to_refunds'] = np.where(df['is_refunded'], df['basket_value'], 0.0)
    
    # Seasonality
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%B')
    df['is_ramadan'] = df['date'].between('2025-02-28', '2025-03-29')
    
    return df

df_clean = load_and_clean_data()

def apply_theme(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, b=30, l=30, r=30))
    return fig

# ==========================================
# SIDEBAR NAVIGATION & FILTERS
# ==========================================
st.sidebar.markdown(f"<h2 style='text-align: center; color: {SUFRA_CRIMSON};'>🍔 SufraEats</h2>", unsafe_allow_html=True)
page = st.sidebar.radio("Navigation", [
    "1. Expansion Strategy (The Decision)", 
    "2. Operational Leakage (COO)", 
    "3. Marketing & Ramadan (CMO)", 
    "4. Partner Cuisines (Partnerships)"
])

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Global Filters")
zones = df_clean['zone'].unique().tolist()
selected_zones = st.sidebar.multiselect("Active Zones", zones, default=zones)
cuisines = df_clean['cuisine'].unique().tolist()
selected_cuisines = st.sidebar.multiselect("Cuisine Categories", cuisines, default=cuisines)

df_filtered = df_clean[(df_clean['zone'].isin(selected_zones)) & (df_clean['cuisine'].isin(selected_cuisines))]

# ==========================================
# PAGE 1: EXPANSION STRATEGY
# ==========================================
if page == "1. Expansion Strategy (The Decision)":
    st.title("🎯 Strategic Expansion Recommendation")
    
    zone_perf = df_filtered.groupby('zone').agg(
        orders=('order_id', 'count'), gross=('basket_value', 'sum'), net_profit=('net_profit', 'sum'),
        avg_rating=('rating', 'mean'), del_time=('delivery_time_min', 'mean')
    ).reset_index()
    
    recommended_zone = zone_perf.sort_values(by='net_profit', ascending=False).iloc[0]['zone']
    
    st.markdown(f"""
    <div class="board-card" style="border-top: 5px solid {MINT_GARNISH}; text-align: center;">
        <h3 style='color: #A0AEC0; margin-bottom: 0;'>THE BOARD MANDATE</h3>
        <h1 style='font-size: 48px; color: {MINT_GARNISH}; margin-top: 10px;'>{recommended_zone.upper()}</h1>
        <p style='font-size: 16px;'>While other zones may show higher gross transactional volume, {recommended_zone.title()} retains the highest <b>realized net profit</b> by maintaining strict operational hygiene and low promotion dependency.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # The Gross vs Net Illusion Chart (CRITICAL INSIGHT)
    st.markdown("### The Gross vs. Net Illusion")
    fig_illusion = go.Figure()
    fig_illusion.add_trace(go.Bar(x=zone_perf['zone'], y=zone_perf['gross'], name='Gross Order Value (Mirage)', marker_color='#3A4766'))
    fig_illusion.add_trace(go.Bar(x=zone_perf['zone'], y=zone_perf['net_profit'], name='True Net Profit (Reality)', marker_color=MINT_GARNISH))
    fig_illusion.update_layout(barmode='overlay', title="Gross Value vs. Actual Retained Profit by Zone")
    st.plotly_chart(apply_theme(fig_illusion), use_container_width=True)

# ==========================================
# PAGE 2: OPERATIONAL LEAKAGE
# ==========================================
elif page == "2. Operational Leakage (COO)":
    st.title("💧 Revenue Leakage & Operational Bottlenecks")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Order Volume", f"{len(df_filtered):,}")
    c2.metric("Lost to Cancellations", f"{df_filtered['lost_to_cancellations'].sum():,.0f} AED", delta="Negative impact", delta_color="inverse")
    c3.metric("Lost to Refunds", f"{df_filtered['lost_to_refunds'].sum():,.0f} AED", delta="Negative impact", delta_color="inverse")
    
    st.markdown("---")
    c4, c5 = st.columns([1, 1])
    
    with c4:
        st.markdown("### Leakage by Zone")
        leakage = df_filtered.groupby('zone')[['lost_to_cancellations', 'lost_to_refunds']].sum().reset_index()
        fig_leak = px.bar(leakage, x='zone', y=['lost_to_cancellations', 'lost_to_refunds'], 
                          title="Capital Drain from Failed Operations", color_discrete_sequence=[SUFRA_CRIMSON, SAFFRON_GOLD])
        st.plotly_chart(apply_theme(fig_leak), use_container_width=True)
        
    with c5:
        st.markdown("### The Delivery Penalty")
        del_penalty = df_filtered[df_filtered['order_channel'] == 'delivery'].groupby('delivery_time_min')['rating'].mean().reset_index()
        # Smoothing the curve for presentation
        del_penalty['rating_smooth'] = del_penalty['rating'].rolling(window=5, min_periods=1).mean()
        fig_del = px.line(del_penalty, x='delivery_time_min', y='rating_smooth', 
                          title="How Slow Delivery Kills Customer Ratings", labels={'delivery_time_min': 'Delivery Time (Mins)', 'rating_smooth': 'Avg Rating'})
        fig_del.add_hline(y=4.0, line_dash="dot", line_color=LEAKAGE_RED, annotation_text="Danger Zone (< 4.0)")
        st.plotly_chart(apply_theme(fig_del), use_container_width=True)

# ==========================================
# PAGE 3: MARKETING & RAMADAN
# ==========================================
elif page == "3. Marketing & Ramadan (CMO)":
    st.title("🌙 Seasonality & Promotion ROI")
    
    is_ram_filter = st.radio("Toggle Seasonality Context:", ["Full Year Data", "Ramadan Period Only", "Non-Ramadan Only"], horizontal=True)
    if is_ram_filter == "Ramadan Period Only":
        view_df = df_filtered[df_filtered['is_ramadan'] == True]
    elif is_ram_filter == "Non-Ramadan Only":
        view_df = df_filtered[df_filtered['is_ramadan'] == False]
    else:
        view_df = df_filtered

    c1, c2 = st.columns(2)
    with c1:
        hourly_peaks = view_df.groupby('hour').size().reset_index(name='orders')
        fig_hr = px.line(hourly_peaks, x='hour', y='orders', title="Diurnal Demand Curves", markers=True, color_discrete_sequence=[SAFFRON_GOLD])
        st.plotly_chart(apply_theme(fig_hr), use_container_width=True)
        
    with c2:
        promo_roi = view_df[view_df['promo_code'] != 'no promo'].groupby('promo_code').agg(
            new_customers=('customer_type', lambda x: (x == 'new').sum()),
            subsidy_cost=('discount_amount', 'sum')
        ).reset_index()
        promo_roi['cost_per_acquisition'] = promo_roi['subsidy_cost'] / promo_roi['new_customers']
        fig_roi = px.scatter(promo_roi, x='subsidy_cost', y='new_customers', text='promo_code', size='cost_per_acquisition',
                             title="Promo Code Efficiency (Cost vs New User Acquisition)", color='cost_per_acquisition', color_continuous_scale="Reds")
        fig_roi.update_traces(textposition='top center')
        st.plotly_chart(apply_theme(fig_roi), use_container_width=True)

# ==========================================
# PAGE 4: PARTNERSHIPS
# ==========================================
elif page == "4. Partner Cuisines (Partnerships)":
    st.title("🍽️ Cuisine Onboarding Priority Matrix")
    
    st.markdown("""
    **Guide for Partnerships Team:** Focus onboarding efforts on cuisines in the top right quadrant (High Volume & High Margin). 
    Avoid allocating resources to the bottom left.
    """)
    
    cuisine_matrix = df_filtered.groupby('cuisine').agg(
        volume=('order_id', 'count'), net_profit=('net_profit', 'sum'), avg_rating=('rating', 'mean')
    ).reset_index()
    
    fig_matrix = px.scatter(cuisine_matrix, x='volume', y='net_profit', text='cuisine', color='avg_rating', size='net_profit',
                            title="Cuisine Strategy Matrix", color_continuous_scale=[LEAKAGE_RED, MINT_GARNISH])
    fig_matrix.update_traces(textposition='top center')
    st.plotly_chart(apply_theme(fig_matrix), use_container_width=True)