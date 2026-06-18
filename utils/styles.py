import streamlit as st

def inject_global_styles():
    """
    Injects global CSS styles and fonts for the Streamlit application.
    Call this function immediately after st.set_page_config() in every page.
    """
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;500;700&display=swap');
        
        /* Global Styles */
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Outfit', sans-serif;
            background-color: #0E1117;
            color: #E2E8F0;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            letter-spacing: -0.02em;
        }
        
        /* Top Banner Gradient */
        .banner-container {
            background: linear-gradient(135deg, #1E1B4B 0%, #311042 50%, #0F172A 100%);
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 30px;
            border: 1px solid #312E81;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .banner-title {
            font-family: 'Space Grotesk', sans-serif;
            color: #F8FAFC;
            font-size: 2.8rem;
            font-weight: 800;
            margin-bottom: 10px;
        }
        .banner-subtitle {
            color: #94A3B8;
            font-size: 1.1rem;
        }
        
        /* Section styling */
        .section-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: #F8FAFC;
            margin-top: 40px;
            margin-bottom: 20px;
            border-bottom: 2px solid rgba(168, 85, 247, 0.3);
            padding-bottom: 10px;
        }
        
        .content-box {
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 30px;
            font-size: 1.1rem;
            line-height: 1.8;
            color: #CBD5E1;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .highlight {
            color: #A855F7;
            font-weight: 600;
        }

        /* Panel Headers */
        .panel-header {
            background: linear-gradient(90deg, #1E3A8A 0%, #0F172A 100%);
            border-radius: 8px;
            padding: 15px 25px;
            margin-bottom: 25px;
            border-left: 5px solid #3B82F6;
        }
        .panel-title {
            color: #F8FAFC;
            font-size: 1.8rem;
            margin: 0;
            font-weight: 700;
        }
        .panel-desc {
            color: #94A3B8;
            font-size: 0.95rem;
            margin: 5px 0 0 0;
        }
        
        .filter-card {
            background: rgba(30, 41, 59, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        /* Metrics Custom Card Styling */
        .metric-card {
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            transition: transform 0.3s ease, border 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            min-height: 150px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            border: 1px solid #6366F1;
        }
        .metric-value {
            font-size: 2.2rem;
            font-weight: 800;
            color: #F8FAFC;
            margin-bottom: 5px;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        /* Badge styling */
        .badge-high {
            background-color: #EF4444;
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
        }
        .badge-med {
            background-color: #F59E0B;
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
        }
        .badge-low {
            background-color: #10B981;
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
        }
        .badge-loop {
            background-color: #F43F5E;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        /* Blacklist Cards Alignment */
        .blacklist-card {
            height: 100%;
            display: flex;
            flex-direction: column;
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
        }
        
        /* Connection status badges */
        .conn-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 2px 0;
        }
        .conn-ok { background: rgba(16, 185, 129, 0.2); color: #10B981; border: 1px solid #10B981; }
        .conn-fail { background: rgba(239, 68, 68, 0.2); color: #EF4444; border: 1px solid #EF4444; }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_kpi_card(title, value, subtitle, border_color="#3B82F6", bg_color_rgba="rgba(59, 130, 246, 0.05)", text_color="#F8FAFC"):
    """
    Renders a standardized KPI card.
    """
    st.markdown(
        f"""
        <div style="background: {bg_color_rgba}; border: 1px solid rgba(255, 255, 255, 0.05); border-left: 3px solid {border_color}; border-radius: 8px; padding: 15px; text-align: center; margin-bottom: 10px;">
            <h4 style="color: {border_color}; margin: 0; font-size: 1rem;">{title}</h4>
            <div style="font-size: 2.2rem; font-weight: 800; color: {text_color};">{value}</div>
            <span style="font-size: 0.8rem; color: #94A3B8;">{subtitle}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
