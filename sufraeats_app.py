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
    page_title="SufraEats Executive Intelligence Deck",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 PREMIUM GOURMET DARK BOARDROOM PALETTE
DARK_BG        = "#0B132B" 
CARD_BG        = "#1C2541" 
SUFRA_CRIMSON  = "#FF4D4D" 
SAFFRON_GOLD   = "#FFB020" 
MINT_GARNISH   = "#22C55E" 

# Injecting comprehensive dark interface CSS styles with strict white text overrides
st.markdown(f"""
<style>
    /* STRICT GLOBAL WHITE TEXT OVERRIDES */
    .stApp, p, span, label, li, td, th, div, h1, h2, h3, h4 {{
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif !important;
    }}
    
    /* Global App Background */
    .stApp {{ background-color: {DARK_BG}; }}
    
    /* Top Blank Header Bar Styling */
    header[data-testid="stHeader"] {{
        background-color: {DARK_BG} !important;
    }}
    
    /* Left Sidebar Container Styling */
    section[data-testid="stSidebar"] {{
        background-color: #0E1731 !important;
        border-right: 1px solid #232E52;
    }}
    
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {{
        color: #FFFFFF !important;
    }}
    
    /* Left Filters Styling */
    div[data-baseweb="select"] {{
        background-color: #151F3C !important;
        border-radius: 8px;
    }}
    div[data-baseweb="select"] div {{
        color: #FFFFFF !important;
    }}
    div[data-baseweb="tag"] {{
        background-color: #2D395E !important;
        border-radius: 6px;
    }}
    
    /* Elegant Dark Executive Cards */
    .board-card {{
        background-color: {CARD_BG};
        padding: 24px;
        border-radius: 14px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
        border: 1px solid #3A4766;
        margin-bottom: 20px;
    }}
    .board-card-accent {{
        border-top: 5px solid {SUFRA_CRIMSON};
    }}
    
    .stDataFrame div {{
        color: #FFFFFF !important;
    }}
    
    [data-testid="stMetricValue"] {{ font-size: 34px !important; font-weight: 800 !important; color: #FFFFFF !important; }}
    [data-testid="stMetricLabel"] {{ font-size: 13px !important; text-transform: uppercase; letter-spacing: 0.8px; color: #FFFFFF !important; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATA LOADING & CACHING PIPELINE
# ==========================================
@st.cache_data
def load_and_clean_data():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    orders_path = os.path.join(BASE_DIR, "sufraeats_orders.csv")
    restaurants_path = os.path.join(BASE_DIR, "sufraeats_restaurants.csv")
    
    orders = pd.read_csv(orders_path)
    restaurants = pd.read_csv(restaurants_path)
    
    restaurants['zone'] = restaurants['zone'].astype(str).str.strip().str.lower()
    restaurants['cuisine'] = restaurants['cuisine'].astype(str).str.strip().str.lower()
    
    zone_mapping = {'jlt': 'jumeirah lake towers', 'marina': 'dubai marina'}
    restaurants['zone'] = restaurants['zone'].replace(zone_mapping)
    
    for col in ['order_status', 'customer_type', 'order_channel', 'payment_method', 'device_platform']:
        if col in orders.columns:
            orders[col] = orders[col].astype(str).str.strip().str.lower()
            
    orders = orders.drop_duplicates(subset=['order_id'], keep='first')
    restaurants = restaurants.drop_duplicates(subset=['restaurant_id'], keep='first')
    
    df_clean = pd.merge(orders, restaurants, on='restaurant_id', how='inner')
    
    df_clean['promo_code'] = df_clean['promo_code'].fillna('no promo').str.strip().str.lower()
    df_clean['discount_amount'] = df_clean['discount_amount'].fillna(0.0)
    
    df_clean['rating'] = df_clean.groupby('restaurant_id')['rating'].transform(lambda x: x.fillna(x.median()) if x.notnull().any() else x)
    df_clean['rating'] = df_clean.groupby('zone')['rating'].transform(lambda x: x.fillna(x.median()) if x.notnull().any() else x)
    df_clean['rating'] = df_clean['rating'].fillna(df_clean['rating'].median())
    
    valid_condition = (
        (df_clean['basket_value'] >= 0) &
        (df_clean['delivery_time_min'] >= 0) &
        (df_clean['hour'] >= 0) & (df_clean['hour'] <= 23)
    )
    df_clean = df_clean[valid_condition]
    
    df_clean['is_completed'] = df_clean['order_status'] == 'delivered'
    df_clean['is_cancelled'] = df_clean['order_status'] == 'cancelled'
    df_clean['is_refunded'] = df_clean['order_status'] == 'refunded'
    
    # Financial Leakage & Profit Logic
    df_clean['realised_revenue'] = np.where(
        df_clean['is_completed'],
        (df_clean['basket_value'] * df_clean['commission_rate']) + df_clean['delivery_fee'],
        0.0
    )
    df_clean['net_profit'] = np.where(
        df_clean['is_completed'],
        df_clean['realised_revenue'] - df_clean['discount_amount'],
        0.0  
    )
    df_clean['lost_to_cancellations'] = np.where(df_clean['is_cancelled'], df_clean['basket_value'], 0.0)
    df_clean['lost_to_refunds'] = np.where(df_clean['is_refunded'], df_clean['basket_value'], 0.0)
    
    df_clean['date'] = pd.to_datetime(df_clean['date'])
    df_clean['month_num'] = df_clean['date'].dt.month
    df_clean['month'] = df_clean['date'].dt.strftime('%B')
    df_clean['day_of_week'] = df_clean['date'].dt.strftime('%A')
    
    # Ramadan Seasonality Check
    df_clean['is_ramadan'] = df_clean['date'].between('2025-02-28', '2025-03-29')
    
    return df_clean

try:
    df_clean = load_and_clean_data()
except Exception as e:
    st.error(f"Error executing data loading pipeline: {e}. Make sure CSVs are pushed to GitHub in the same directory.")
    st.stop()

def apply_board_theme(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", size=12, color="#FFFFFF"),
        title=dict(font=dict(size=15, color="#FFFFFF", weight='bold')),
        margin=dict(t=50, b=40, l=40, r=40)
    )
    return fig

# ==========================================
# SIDEBAR NAVIGATION & CONTROLS
# ==========================================
st.sidebar.markdown(f"<br><h2 style='text-align: center; color: {SUFRA_CRIMSON}; font-size: 26px; letter-spacing: -0.5px;'>🍔 SufraEats</h2><p style='text-align: center; font-size: 11px; color: #FFFFFF; text-transform: uppercase; margin-top: -10px;'>Executive Intelligence Deck</p>", unsafe_allow_html=True)
page = st.sidebar.radio("Go to Slide:", [
    "📌 Expansion Strategy Mandate", 
    "👥 Target Customer Insights", 
    "📈 Operational Velocities", 
    "💰 Net Financial Performance"
])

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 11px; font-weight: bold; text-transform: uppercase; color: #FFFFFF; letter-spacing: 0.5px;'>Interactive Controls</p>", unsafe_allow_html=True)
selected_zones = st.sidebar.multiselect("Zone Focus Area:", options=df_clean['zone'].unique().tolist(), default=df_clean['zone'].unique().tolist())
selected_cuisines = st.sidebar.multiselect("Cuisine Categories:", options=df_clean['cuisine'].unique().tolist(), default=df_clean['cuisine'].unique().tolist())
status_options = df_clean['order_status'].unique().tolist()
selected_status = st.sidebar.multiselect("Order Status:", options=status_options, default=status_options)

df_filtered = df_clean[
    (df_clean['zone'].isin(selected_zones)) & 
    (df_clean['cuisine'].isin(selected_cuisines)) &
    (df_clean['order_status'].isin(selected_status))
]

# ==========================================
# PAGE 1: EXPANSION STRATEGY MANDATE
# ==========================================
if page == "📌 Expansion Strategy Mandate":
    st.title("🎯 Strategic Regional Expansion Recommendation")
    st.markdown("---")
    
    zone_perf = df_filtered.groupby('zone').agg(
        orders=('order_id', 'count'),
        gross_order_value=('basket_value', 'sum'),
        total_profit=('net_profit', 'sum'),
        avg_rating=('rating', 'mean'),
        del_time=('delivery_time_min', 'mean')
    ).reset_index()
    
    recommended_zone = zone_perf.sort_values(by='total_profit', ascending=False).iloc[0]['zone']
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="board-card board-card-accent">
            <h3 style='margin-top: 0; color: {SUFRA_CRIMSON} !important;'>🏆 DATA MANDATE SELECTOR</h3>
            <p style='color: #FFFFFF;'>Optimizing for bottom-line margin retention and real platform profit parameters over 5 months, our analytics engine identifies the ideal investment hub location as:</p>
            <h2 style='color: {SUFRA_CRIMSON}; margin: 10px 0; font-size: 38px; letter-spacing: -1px;'>{recommended_zone.upper()}</h2>
            <hr style='border-color: #3A4766; margin: 15px 0;'>
            <table style='width: 100%; font-size: 14px; color: #FFFFFF;'>
                <tr><td><b>Net Realized Profit Yield:</b></td><td style='text-align: right; color: #FFFFFF; font-weight: bold;'>{zone_perf[zone_perf['zone']==recommended_zone]['total_profit'].values[0]:,.2f} AED</td></tr>
                <tr><td><b>Quality Baseline Index:</b></td><td style='text-align: right; color: {SAFFRON_GOLD}; font-weight: bold;'>{zone_perf[zone_perf['zone']==recommended_zone]['avg_rating'].values[0]:.2f} ⭐</td></tr>
                <tr><td><b>Logistical Velocity Average:</b></td><td style='text-align: right; color: {MINT_GARNISH}; font-weight: bold;'>{zone_perf[zone_perf['zone']==recommended_zone]['del_time'].values[0]:.1f} Mins</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="board-card" style="height: 100%; background-color: #111827; border-color: #374151;">
            <h4 style='color: #FFFFFF !important; margin-top: 0;'>📊 Brand Health Optimization Logic</h4>
            <p style='font-size: 14px; line-height: 1.6; color: #FFFFFF;'>Top-line order numbers or simple gross volume figures create dangerous illusions in high-frequency delivery markets. A specific district might show massive transaction counts while silently running at a deficit due to persistent discount promo loops, operational cancellation liabilities, and customer support refunds. 
            SufraEats chooses <b>{recommended_zone.upper()}</b> because it successfully translates market demand into true corporate net value.</p>
        </div>
        """, unsafe_allow_html=True)

    # V2 ADDITION: The Gross vs Net Illusion 
    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("### 🔍 Strategic Context: The Gross vs. Net Profit Illusion")
    st.markdown("<p style='font-size: 14px;'>This visualization exposes the 'Top-Line Trap'. High transactional volume does not equal retained capital due to heavy subsidization and operational leakage.</p>", unsafe_allow_html=True)
    fig_illusion = go.Figure()
    fig_illusion.add_trace(go.Bar(x=zone_perf['zone'], y=zone_perf['gross_order_value'], name='Gross Order Value (Mirage)', marker_color='#3A4766'))
    fig_illusion.add_trace(go.Bar(x=zone_perf['zone'], y=zone_perf['total_profit'], name='True Net Profit Retained', marker_color=MINT_GARNISH))
    fig_illusion.update_layout(barmode='overlay', title="Gross Transaction Volume vs. Realized Net Profit by Zone")
    fig_illusion = apply_board_theme(fig_illusion)
    st.plotly_chart(fig_illusion, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    fig_zone_prof = px.bar(zone_perf, x='zone', y='total_profit', color='avg_rating',
                           labels={'total_profit': 'Net Profit Retained (AED)', 'zone': 'Dubai Operating Zone', 'avg_rating': 'Customer Score'},
                           title="Net Profit Contribution Margin by Territory vs Regional Customer Quality Index",
                           color_continuous_scale=[SAFFRON_GOLD, SUFRA_CRIMSON], text_auto=',.2f')
    fig_zone_prof.update_traces(textposition='outside', cliponaxis=False)
    fig_zone_prof = apply_board_theme(fig_zone_prof)
    st.plotly_chart(fig_zone_prof, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# PAGE 2: TARGET CUSTOMER INSIGHTS
# ==========================================
elif page == "👥 Target Customer Insights":
    st.title("👥 Cohort Demographics, Preferred Channels & Interfaces")
    st.markdown("---")
    
    c1, r1 = st.columns(2)
    with c1:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        cohort_counts = df_filtered['customer_type'].value_counts().reset_index()
        fig1 = go.Figure(data=[go.Pie(
            labels=cohort_counts['customer_type'].str.upper(), 
            values=cohort_counts['count'],
            hole=.45,
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=[SUFRA_CRIMSON, SAFFRON_GOLD], line=dict(color=CARD_BG, width=2))
        )])
        fig1.update_layout(title="1. Order Concentration Split: New vs. Repeat Base")
        fig1 = apply_board_theme(fig1)
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with r1:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        channel_counts = df_filtered['order_channel'].value_counts().reset_index()
        fig3 = go.Figure(data=[go.Pie(
            labels=channel_counts['order_channel'].str.upper(), 
            values=channel_counts['count'],
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=[SUFRA_CRIMSON, "#3A4766", SAFFRON_GOLD], line=dict(color=CARD_BG, width=2))
        )])
        fig3.update_layout(title="3. Distribution Channel Preference Share Matrix")
        fig3 = apply_board_theme(fig3)
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        pay_mix = df_filtered.groupby(['customer_type', 'payment_method']).size().reset_index(name='order_volume')
        fig2 = px.bar(pay_mix, x='payment_method', y='order_volume', color='customer_type', 
                      barmode='group', text_auto=True,
                      color_discrete_map={'new': "#5D6D7E", 'repeat': SUFRA_CRIMSON},
                      title="2. Preferred Settlement Frameworks Across Target Cohorts",
                      labels={'order_volume': 'Total Processed Transactions', 'payment_method': 'Payment Framework', 'customer_type': 'Cohort'})
        fig2.update_traces(textposition='outside', cliponaxis=False)
        fig2 = apply_board_theme(fig2)
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c4:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        device_mix = df_filtered['device_platform'].value_counts().reset_index()
        fig4 = go.Figure(data=[go.Pie(
            labels=device_mix['device_platform'].str.upper(), 
            values=device_mix['count'],
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=[SUFRA_CRIMSON, SAFFRON_GOLD, "#5D6D7E"], line=dict(color=CARD_BG, width=2))
        )])
        fig4.update_layout(title="4. Ecosystem Access Device Point Proportions")
        fig4 = apply_board_theme(fig4)
        st.plotly_chart(fig4, use_container_width=True)
        st.sidebar.markdown("---")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# PAGE 3: OPERATIONAL VELOCITIES
# ==========================================
elif page == "📈 Operational Velocities":
    st.title("📈 Logistical Metrics, Quality Leakage & Merchant Ranks")
    st.markdown("---")
    
    avg_del_time = df_filtered['delivery_time_min'].mean()
    success_rate = (df_filtered['is_completed'].sum() / len(df_filtered)) * 100
    refunded_rate = (df_filtered['is_refunded'].sum() / len(df_filtered)) * 100
    cancelled_rate = (df_filtered['is_cancelled'].sum() / len(df_filtered)) * 100
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f"<div class='board-card'><p style='margin:0; font-size:12px; color:#FFFFFF; font-weight:600;'>5. AVG DELIVERY TIME</p><h2 style='margin:5px 0; color:#FFFFFF;'>{avg_del_time:.1f} Mins</h2></div>", unsafe_allow_html=True)
    with kpi2:
        st.markdown(f"<div class='board-card'><p style='margin:0; font-size:12px; color:#FFFFFF; font-weight:600;'>8. SUCCESS DELIVERY RATE</p><h2 style='margin:5px 0; color:{MINT_GARNISH};'>{success_rate:.2f}%</h2></div>", unsafe_allow_html=True)
    with kpi3:
        st.markdown(f"<div class='board-card'><p style='margin:0; font-size:12px; color:#FFFFFF; font-weight:600;'>8. REFUNDED ORDER RATE</p><h2 style='margin:5px 0; color:{SAFFRON_GOLD};'>{refunded_rate:.2f}%</h2></div>", unsafe_allow_html=True)
    with kpi4:
        st.markdown(f"<div class='board-card'><p style='margin:0; font-size:12px; color:#FFFFFF; font-weight:600;'>8. CANCELLATION RATE</p><h2 style='margin:5px 0; color:{SUFRA_CRIMSON};'>{cancelled_rate:.2f}%</h2></div>", unsafe_allow_html=True)
    
    # V2 ADDITION: Revenue Leakage & Operations Bottlenecks
    st.markdown("---")
    st.markdown("### 💧 Capital Leakage & Logistical Bottlenecks")
    c_leak1, c_leak2 = st.columns(2)
    with c_leak1:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        leakage = df_filtered.groupby('zone')[['lost_to_cancellations', 'lost_to_refunds']].sum().reset_index()
        fig_leak = px.bar(leakage, x='zone', y=['lost_to_cancellations', 'lost_to_refunds'], 
                          title="Capital Drain from Failed Operations", color_discrete_sequence=[SUFRA_CRIMSON, SAFFRON_GOLD],
                          labels={'value': 'Capital Lost (AED)', 'variable': 'Leakage Source', 'zone': 'Operating Zone'})
        fig_leak = apply_board_theme(fig_leak)
        st.plotly_chart(fig_leak, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c_leak2:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        del_penalty = df_filtered[df_filtered['order_channel'] == 'delivery'].groupby('delivery_time_min')['rating'].mean().reset_index()
        del_penalty['rating_smooth'] = del_penalty['rating'].rolling(window=5, min_periods=1).mean()
        fig_del = px.line(del_penalty, x='delivery_time_min', y='rating_smooth', 
                          title="The Delivery Penalty: How Delay Destroys Quality Index", 
                          labels={'delivery_time_min': 'Delivery Time (Mins)', 'rating_smooth': 'Smoothed Avg Rating'},
                          color_discrete_sequence=[MINT_GARNISH])
        fig_del.add_hline(y=4.0, line_dash="dot", line_color=SUFRA_CRIMSON, annotation_text="Critical Danger Zone (< 4.0)")
        fig_del = apply_board_theme(fig_del)
        st.plotly_chart(fig_del, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("### 🍽️ 6. Market Demand Preference & Cuisine Performance Leader")
    rest_perf = df_filtered.groupby(['restaurant_name', 'cuisine']).agg(
        total_orders=('order_id', 'count'),
        avg_overall_rating=('rating', 'mean')
    ).reset_index().sort_values(by='total_orders', ascending=False)
    
    if not rest_perf.empty:
        top_merchant = rest_perf.iloc[0]
        st.markdown(
            f"**Top Customer Preferred Merchant:** The platform establishment displaying peak demand is "
            f"**{top_merchant['restaurant_name'].upper()}** serving **{top_merchant['cuisine'].upper()}** "
            f"culinary profiles, capturing **{top_merchant['total_orders']:,}** completed orders."
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🍽️ Multi-Dimensional Cuisine Yield & Satisfaction Analysis")
    
    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        cuisine_metrics = df_filtered.groupby('cuisine').agg(
            volume=('order_id', 'count'),
            score=('rating', 'mean'),
            net_profit=('net_profit', 'sum')
        ).reset_index().sort_values(by='volume', ascending=False)
        
        fig_cuis_deep = px.bar(
            cuisine_metrics, x='cuisine', y='volume', color='score',
            labels={'volume': 'Total Captured Orders', 'cuisine': 'Cuisine Grouping', 'score': 'Rating Index'},
            title="Cuisine Order Throughput Volumetrics vs Customer Sentiment Matrix",
            color_continuous_scale=[SUFRA_CRIMSON, MINT_GARNISH]
        )
        fig_cuis_deep = apply_board_theme(fig_cuis_deep)
        st.plotly_chart(fig_cuis_deep, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_c2:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        st.markdown("#### Comprehensive Cuisine Operations Matrix")
        cuisine_ledger = df_filtered.groupby('cuisine').agg(
            total_orders=('order_id', 'count'),
            avg_basket_value=('basket_value', 'mean'),
            net_profit_yield=('net_profit', 'sum'),
            avg_rating=('rating', 'mean')
        ).reset_index().sort_values(by='net_profit_yield', ascending=False)
        
        st.dataframe(cuisine_ledger.style.format({
            'total_orders': '{:,}',
            'avg_basket_value': '{:,.2f} AED',
            'net_profit_yield': '{:,.2f} AED',
            'avg_rating': '{:.2f} ⭐'
        }), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # V2 ADDITION: Cuisine Priority Matrix 
    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("### 🎯 Partnerships: Cuisine Onboarding Priority Matrix")
    st.markdown("<p style='font-size: 14px;'>Guide for Partnerships Team: Focus onboarding resources strictly on culinary categories plotting in the upper-right (High Volume, High Margin Yield) quadrant.</p>", unsafe_allow_html=True)
    fig_matrix = px.scatter(cuisine_metrics, x='volume', y='net_profit', text='cuisine', color='score', size='net_profit',
                            title="Strategic Onboarding: Volume vs Net Profit Yield", color_continuous_scale=[SUFRA_CRIMSON, MINT_GARNISH],
                            labels={'volume': 'Total Processed Orders', 'net_profit': 'Net Profit Yield (AED)', 'score': 'Customer Score'})
    fig_matrix.update_traces(textposition='top center')
    fig_matrix = apply_board_theme(fig_matrix)
    st.plotly_chart(fig_matrix, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("#### 11. Complete Multi-Tiered Restaurant Ratings Matrix (By Cohort Type)")
    rating_pivot = df_filtered.pivot_table(
        values='rating', index=['zone', 'restaurant_name'], columns='customer_type', aggfunc='mean'
    ).reset_index()
    st.dataframe(rating_pivot.style.format({'new': '{:.2f} ⭐', 'repeat': '{:.2f} ⭐'}), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# PAGE 4: NET FINANCIAL PERFORMANCE
# ==========================================
elif page == "💰 Net Financial Performance":
    st.title("💰 Capital Ledger, Seasonal Trends & Promo ROI")
    st.markdown("---")
    
    # V2 ADDITION: Ramadan Toggle Filter
    st.markdown("### 🌙 Ramadan Seasonality Context Engine")
    is_ram_filter = st.radio("Isolate Chronological Periods to View Event Demand Shifts:", ["Full Year Data", "Ramadan Period Only", "Non-Ramadan Only"], horizontal=True)
    
    if is_ram_filter == "Ramadan Period Only":
        view_df = df_filtered[df_filtered['is_ramadan'] == True]
    elif is_ram_filter == "Non-Ramadan Only":
        view_df = df_filtered[df_filtered['is_ramadan'] == False]
    else:
        view_df = df_filtered
        
    st.markdown("---")
    
    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("### 9. Consolidated Operational Financial Log")
    monthly_ledger = view_df.groupby(['month_num', 'month']).agg(
        expenditure=('discount_amount', 'sum'),
        revenue=('realised_revenue', 'sum'),
        profit=('net_profit', 'sum'),
        total_orders=('order_id', 'count')
    ).reset_index().sort_values(by='month_num')
    
    st.dataframe(monthly_ledger.style.format({
        'expenditure': '{:,.2f} AED', 'revenue': '{:,.2f} AED', 'profit': '{:,.2f} AED', 'total_orders': '{:,}'
    }), use_container_width=True)
    
    total_5m_profit = monthly_ledger['profit'].sum()
    st.markdown(f"<h3 style='color:{MINT_GARNISH} !important;'>📊 Cumulative Filtered Platform Net Profit: {total_5m_profit:,.2f} AED</h3>", unsafe_allow_html=True)
    
    if not monthly_ledger.empty:
        highest_month = monthly_ledger.sort_values(by='total_orders', ascending=False).iloc[0]
        lowest_month = monthly_ledger.sort_values(by='total_orders', ascending=True).iloc[0]
        st.markdown(f"📈 **Volume Milestones:** Seasonal demand peaked highest during **{highest_month['month'].upper()}** with **{highest_month['total_orders']:,}** orders, while dropping to its low baseline point during **{lowest_month['month'].upper()}** with **{lowest_month['total_orders']:,}** orders.")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    c5, c6 = st.columns(2)
    with c5:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        hourly_peaks = view_df.groupby('hour').size().reset_index(name='orders')
        fig_hr = px.line(hourly_peaks, x='hour', y='orders', markers=True, 
                         line_shape='spline', color_discrete_sequence=[SUFRA_CRIMSON],
                         title="10. Diurnal Distribution: Peak Daily Delivery Demand Curves")
        fig_hr.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=2))
        fig_hr = apply_board_theme(fig_hr)
        st.plotly_chart(fig_hr, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c6:
        st.markdown("<div class='board-card'>", unsafe_allow_html=True)
        day_peaks = view_df.groupby(['day_of_week', 'customer_type']).size().reset_index(name='orders')
        fig_day = px.bar(day_peaks, x='day_of_week', y='orders', color='customer_type', 
                         barmode='group', text_auto=True,
                         color_discrete_map={'new': "#5D6D7E", 'repeat': SAFFRON_GOLD},
                         title="10. Weekly Transaction Patterns Segregated by Customer Type")
        fig_day.update_traces(textposition='outside', cliponaxis=False)
        fig_day = apply_board_theme(fig_day)
        st.plotly_chart(fig_day, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    # V2 ADDITION: Promo ROI Scatter Plot
    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("### 🎟️ Promo Code Efficiency: Subsidization Cost vs User Acquisition")
    promo_roi = view_df[view_df['promo_code'] != 'no promo'].groupby('promo_code').agg(
        new_customers=('customer_type', lambda x: (x == 'new').sum()),
        subsidy_cost=('discount_amount', 'sum')
    ).reset_index()
    # Math logic to calculate efficient spend
    promo_roi['cost_per_acquisition'] = promo_roi['subsidy_cost'] / promo_roi['new_customers'].replace(0, 1)
    fig_roi = px.scatter(promo_roi, x='subsidy_cost', y='new_customers', text='promo_code', size='cost_per_acquisition',
                         title="Voucher Subsidization Bleed vs New Market Penetration (Larger Bubble = Worse Efficiency)", 
                         color='cost_per_acquisition', color_continuous_scale="Reds", 
                         labels={'subsidy_cost': 'Total Discount Subsidized (AED)', 'new_customers': 'New Users Acquired'})
    fig_roi.update_traces(textposition='top center')
    fig_roi = apply_board_theme(fig_roi)
    st.plotly_chart(fig_roi, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("### 7. Region-Wise Voucher Code ROI Analysis (Acquisition vs Subsidization Yield)")
    promo_perf = view_df[view_df['promo_code'] != 'no promo'].groupby(['zone', 'promo_code']).agg(
        usages=('order_id', 'count'),
        total_discount_borne=('discount_amount', 'sum'),
        acquired_new_users=('customer_type', lambda x: (x == 'new').sum())
    ).reset_index().sort_values(by=['zone', 'usages'], ascending=[True, False])
    
    st.dataframe(promo_perf.style.format({
        'total_discount_borne': '{:,.2f} AED', 
        'usages': '{:,}', 
        'acquired_new_users': '{:,}'
    }), use_container_width=True)
    
    st.markdown(
        "💡 **Strategic Sales Insight:** Evaluate the geographic distribution of voucher parameters. "
        "If a specific zone displays steep marketing discount burn with low relative `acquired_new_users`, "
        "the campaign in that zone is simply degrading profit margins by subsidizing existing repeat customer behavior "
        "rather than scaling new market pipelines."
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='board-card'>", unsafe_allow_html=True)
    st.markdown("### 🎟️ Chronological Voucher Lifecycle Pipeline Tracking Matrix (By Zone & Month)")
    
    promo_time_matrix = view_df[view_df['promo_code'] != 'no promo'].groupby(['zone', 'month_num', 'month', 'promo_code']).agg(
        volume_utilized=('order_id', 'count'),
        subsidy_costs=('discount_amount', 'sum'),
        net_profit_margin=('net_profit', 'sum')
    ).reset_index().sort_values(by=['zone', 'month_num', 'volume_utilized'], ascending=[True, True, False]).drop(columns=['month_num'])
    
    st.dataframe(promo_time_matrix.style.format({
        'volume_utilized': '{:,}',
        'subsidy_costs': '{:,.2f} AED',
        'net_profit_margin': '{:,.2f} AED'
    }), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
