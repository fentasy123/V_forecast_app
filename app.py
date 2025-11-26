import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- 1. Page Configuration ---
st.set_page_config(page_title="V Advanced Budgeting (Monthly)", layout="wide")
st.title("📅 V forecast model")
st.markdown("Simulating **OneStream** monthly allocation logic: Includes detailed P&L with seasonality and segmentation.")

# --- 2. Sidebar: Drivers ---
st.sidebar.header("⚙️ Budget Assumptions (Drivers)")

# 2.1 Annual Growth Targets + Revenue Retention
st.sidebar.subheader("Annual Growth Targets")
corp_growth = st.sidebar.slider("Corporate Net Growth %", -5.0, 10.0, 4.0, 0.1)
fund_growth = st.sidebar.slider("Fund AUA Growth %", -5.0, 20.0, 9.0, 0.5)
advisory_growth = st.sidebar.slider("Advisory Growth %", -5.0, 10.0, 2.0, 0.5)

# 放在 growth 下面：Revenue Retention / Churn driver
revenue_retention = st.sidebar.slider(
    "Revenue Retention % (100% - churn)",
    70.0,   # 30% churn
    110.0,  # 110% net retention
    95.0,   # default 95% retention
    0.5
)

# 2.2 Cost & Seasonality
st.sidebar.subheader("Cost & Seasonality")
wage_inflation = st.sidebar.slider("Wage Inflation (Starts Apr)", 0.0, 10.0, 4.5, 0.1)
q1_seasonality = st.sidebar.checkbox("Enable Q1 Seasonality Peak (Corporate Invoicing)", value=True)

# --- 3. Calculation Engine ---

def generate_forecast(revenue_retention):
    # Create 12-month timeline
    months = pd.date_range(start='2025-01-01', periods=12, freq='ME') 
    
    # Base Data (Base Run Rate - Monthly)
    base_corp = 690 / 12
    base_fund = 290 / 12
    base_adv = 170 / 12
    base_cost = 520 / 12
    base_opex = 285 / 12
    
    # Revenue retention factor
    retention_factor = revenue_retention / 100.0
    
    data = []

    for i, date in enumerate(months):
        month_num = i + 1
        
        # A. Corporate Revenue
        monthly_growth_factor = (1 + corp_growth/100) ** (month_num/12) 
        
        season_factor = 1.0
        if q1_seasonality:
            if month_num in [1, 2]:
                season_factor = 1.15
            elif month_num == 3:
                season_factor = 1.05
            else:
                season_factor = 0.95
            
        rev_corp = base_corp * monthly_growth_factor * season_factor * retention_factor
        
        # B. Fund Revenue
        rev_fund = base_fund * ((1 + fund_growth/100) ** (month_num/12)) * retention_factor
        
        # C. Advisory Revenue
        random_shock = np.random.normal(1.0, 0.02)
        rev_adv = base_adv * ((1 + advisory_growth/100) ** (month_num/12)) * random_shock * retention_factor
        
        # D. Costs
        inflation_impact = 1.0
        if month_num >= 4:
            inflation_impact = 1 + (wage_inflation/100)
            
        cost_direct = base_cost * inflation_impact
        cost_opex = base_opex * 1.02
        
        total_rev = rev_corp + rev_fund + rev_adv
        ebitda = total_rev - cost_direct - cost_opex
        
        data.append({
            "Month": date.strftime("%b"),
            "Month_Num": month_num,
            "Rev_Corporate": rev_corp,
            "Rev_Fund": rev_fund,
            "Rev_Advisory": rev_adv,
            "Total_Revenue": total_rev,
            "Direct_Costs": -cost_direct,
            "OpEx": -cost_opex,
            "EBITDA": ebitda
        })
        
    return pd.DataFrame(data)

df_monthly = generate_forecast(revenue_retention)

# --- 4. Pivot & Visualization ---

tab1, tab2 = st.tabs(["📊 Chart Analysis", "📋 Detailed Monthly Grid"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Revenue Trend (by Segment)")
        fig_rev = px.bar(
            df_monthly,
            x="Month",
            y=["Rev_Corporate", "Rev_Fund", "Rev_Advisory"],
            title="Monthly Revenue by Segment",
            labels={"value": "Revenue ($M)", "variable": "Segment"},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_rev, use_container_width=True)
        
    with col2:
        st.subheader("EBITDA Margin Trend")
        df_monthly["EBITDA_Margin"] = (df_monthly["EBITDA"] / df_monthly["Total_Revenue"]) * 100
        
        fig_margin = px.line(
            df_monthly,
            x="Month",
            y="EBITDA_Margin",
            title="Monthly EBITDA Margin %",
            markers=True,
            text="EBITDA_Margin"
        )
        fig_margin.update_traces(
            texttemplate='%{text:.1f}%',
            textposition='top center',
            line_color='green'
        )
        fig_margin.update_yaxes(range=[20, 40])
        st.plotly_chart(fig_margin, use_container_width=True)

with tab2:
    st.subheader("Detailed P&L Statement (By Month)")
    
    df_display = df_monthly.set_index("Month").drop(columns=["Month_Num", "EBITDA_Margin"]).T
    df_display["Full Year 2025"] = df_display.sum(axis=1)
    
    st.dataframe(
        df_display.style.format("${:,.1f}"),
        use_container_width=True,
        height=400
    )
    
    csv = df_monthly.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Excel (CSV) File",
        csv,
        "vistra_monthly_forecast.csv",
        "text/csv",
        key='download-csv'
    )

# --- 5. AI Analysis Hint ---
st.divider()
st.info(f"""
**💡 AI Analysis Insights:**
1. **Seasonality Impact:** With 'Q1 Seasonality Peak' on, Corporate Revenue is higher in Jan–Feb, smoothing out the rest of the year.
2. **Wage Shock:** EBITDA Margin dips from April as wage inflation kicks in.
3. **Churn / Retention:** With Revenue Retention at {revenue_retention:.1f}%, you can see how small changes in churn directly impact total revenue and EBITDA.
""")
