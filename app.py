import streamlit as st
import pandas as pd
import engine

# Set page to wide mode for better table visibility
st.set_page_config(page_title="EN 1337-3 Bearing Tool", layout="wide")

# --- SIDEBAR: MODE & SETTINGS ---
with st.sidebar:
    st.title("Settings & Modes")
    # Selection for App Mode
    mode = st.radio(
        "Select Operation Mode:", 
        ["Optimization (Search)", "Manual Check (Report Mode)"],
        help="Optimization searches for configs. Manual Check provides detailed math for a specific config."
    )
    
    st.divider()
    
    if mode == "Manual Check (Report Mode)":
        st.subheader("Manual Configuration")
        m_n = st.number_input("Number of layers ($n$)", value=5, min_value=2)
        m_ti = st.number_input("Inner layer thick ($t_i$)", value=12)
        m_ts = st.number_input("Plate thickness ($t_s$)", value=4)
        st.info("Input the configuration you wish to verify and document.")
    
    st.divider()
    st.write("Standard: EN 1337-3:2005")
    st.caption("Developed for structural design checking.")

# --- HELPER FUNCTION FOR STYLING ---
def style_status_df(df):
    """Applies red/green background to the 'STATUS' column."""
    def _color_status(val):
        if val == 'PASS': return 'background-color: #28a745; color: white'
        elif val == 'FAIL': return 'background-color: #dc3545; color: white'
        return ''
    if 'STATUS' in df.columns:
        return df.style.applymap(_color_status, subset=['STATUS'])
    return df

# --- MAIN UI ---
st.title("🏗️ EN 1337-3 Bearing Pad Design")
st.markdown("Automated design checking and procedural reporting for laminated elastomeric bearings.")
st.divider()

# --- 1. COMMON INPUT SECTION ---
st.header("1. Design Inputs")
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Geometry")
    a = st.number_input("Overall Width $a$ (mm)", value=560)
    b = st.number_input("Overall Length $b$ (mm)", value=380)
    target_Tb = st.number_input("Target Total Height $T_b$ (mm)", value=73)
    fy = st.number_input("Steel Yield $f_y$ (MPa)", value=235)

with col2:
    st.subheader("Design Loads")
    Fz_d = st.number_input("Max Vertical $F_{z,d}$ (kN)", value=1500) * 1000
    Fz_dmin = st.number_input("Min Vertical $F_{z,min}$ (kN)", value=1000) * 1000
    Fx_d = st.number_input("Horiz Force $F_{x,d}$ (kN)", value=50) * 1000
    Fy_d = st.number_input("Horiz Force $F_{y,d}$ (kN)", value=20) * 1000

with col3:
    st.subheader("Deformations")
    vx_d = st.number_input("Max Disp. $v_{x,d}$ (mm)", value=30)
    vy_d = st.number_input("Max Disp. $v_{y,d}$ (mm)", value=15)
    alpha_ad = st.number_input("Rotation $\\alpha_{a,d}$ (rad)", value=0.005, format="%.4f")
    alpha_bd = st.number_input("Rotation $\\alpha_{b,d}$ (rad)", value=0.002, format="%.4f")

# Standard constants
G, Kf, Kh = 0.9, 0.6, 1.0

# --- 2. EXECUTION LOGIC ---

if mode == "Optimization (Search)":
    if st.button("Run Design Check", type="primary", use_container_width=True):
        configs = engine.find_bearing_configs(a, b, target_Tb, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd)
        
        if configs:
            st.header("2. Design Results")
            st.subheader("Available Configurations")
            df_base = pd.DataFrame(configs)[["n", "ti", "ts"]]
            df_base["Total $T_b$ (mm)"] = target_Tb
            st.dataframe(df_base, use_container_width=True)
            
            st.divider()
            
            # Verification Tabs
            st.header("3. Verification Tabs")
            t1, t2, t3, t4, t5 = st.tabs(["📉 Strains", "🛡️ Stability", "🛷 Sliding", "🔩 Reinforcement", "📡 Actions"])
            
            with t1:
                st.markdown("### Clause 5.3.3.2 - 5.3.3.4: Strain Checks")
                df_strains = pd.DataFrame(configs).rename(columns={
                    "eps_cd": "ε_c,d", "eps_qd": "ε_q,d", "eps_ad": "ε_a,d", "eps_td": "ε_t,d"
                })
                st.dataframe(style_status_df(df_strains), use_container_width=True)
                with st.expander("ℹ️ View Criteria"):
                    st.info(r"$\epsilon_{q,d} \le 1.0$ and $\epsilon_{t,d} \le 7.0$")

            with t2:
                res_stab = engine.check_stability(a, b, target_Tb, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd)
                df_stab = pd.DataFrame(res_stab).rename(columns={"sum_vzd": "Σv_z,d", "uplift": "Uplift", "p_act": "p_act", "p_lim": "p_lim"})
                st.dataframe(style_status_df(df_stab), use_container_width=True)
                with st.expander("ℹ️ View Criteria"):
                    st.info(r"Uplift check: $\sum v_{z,d} - \text{rotation term} \ge 0$. Buckling: $p_{act} < p_{lim}$")
            
        with t3:
            st.markdown("### Clause 5.3.3.6: Non-Sliding Condition")
            res_slide = engine.check_sliding(a, b, target_Tb, Fx_d, Fy_d, Fz_dmin, vx_d, vy_d, Kf=Kf)
            df_slide = pd.DataFrame(res_slide).rename(columns={
                "sigma_m": "σ_m", "mu_e": "μ_e", "F_fric": "F_fric(kN)", "F_hor": "F_hor(kN)"
            })
            st.dataframe(style_status_df(df_slide), use_container_width=True)
            
            with st.expander("ℹ️ View Sliding Criteria"):
                st.info(r"""
                **Acceptance Criteria:**
                1. **Friction Check**: $F_{hor} \le F_{fric}$
                2. **Pressure Check**: $\sigma_m \ge 3.0$ MPa (Required for permanent contact)
                *Where $\mu_e = 0.1 + \frac{1.5 \cdot K_f}{\sigma_m}$*
                """)

        with t4:
            st.markdown("### Clause 5.3.3.5: Reinforcing Plate Thickness")
            res_reinf = engine.check_reinforcement(a, b, target_Tb, Fz_d, vx_d, vy_d, fy=fy, Kh=Kh)
            df_reinf = pd.DataFrame(res_reinf).rename(columns={"ts_prov": "t_s,prov", "ts_req": "t_s,req"})
            st.dataframe(style_status_df(df_reinf), use_container_width=True)
            
            with st.expander("ℹ️ View Reinforcement Criteria"):
                st.info(r"""
                **Acceptance Criteria:**
                1. **Minimum Thickness**: $t_{s,prov} \ge 2.0$ mm
                2. **Strength Check**: $t_{s,prov} \ge t_{s,req}$
                *Where $t_{s,req} = \frac{1.3 \cdot F_{z,d} \cdot (t_1 + t_2) \cdot K_h \cdot \gamma_m}{A_r \cdot f_y}$*
                """)
    else:
        st.error("No configurations found matching target height.")

elif mode == "Manual Check (Report Mode)":
    if st.button("Generate Calculation Report", type="primary", use_container_width=True):
        st.divider()
        st.header(f"Detailed Calculation Report: $n={m_n}$, $t_i={m_ti}$ mm, $t_s={m_ts}$ mm")
        
        # Call the procedural engine
        steps = engine.get_procedural_report(
            a, b, m_n, m_ti, m_ts, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd, Kf, fy
        )
        
        # Display the math steps
        with st.container():
            for step in steps:
                st.markdown(step)
        
        st.divider()
        st.success("Report generated successfully. You can copy this into your design documentation.")