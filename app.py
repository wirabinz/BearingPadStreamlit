import streamlit as st
import pandas as pd
import engine
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle


# Set page to wide mode for better table visibility
st.set_page_config(page_title="EN 1337-3 Bearing Tool", layout="wide")

# --- SIDEBAR: MODE & SETTINGS ---
with st.sidebar:
    st.title("Settings & Modes")
    # Dropdown menu for operation mode
    mode = st.selectbox(
        "Select Operation Mode:", 
        ["Find Configuration", "Manual Check"],
        help="Find Configuration searches for valid setups. Manual Check provides detailed calculation for a specific config."
    )
    
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

# --- HELPER FUNCTION FOR BUILDING BEARING SECTION ---

def draw_bearing_section(n, ti, ts, a, b):
    """Generates a professional 3/4 isometric section view of the bearing."""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Dimensions
    cover = 2.5
    ec = 4  # side cover
    a_p = a - (2 * ec)
    b_p = b - (2 * ec)
    
    # Isometric Constants
    iso_x = 0.7 
    iso_y = 0.4 
    
    def draw_iso_layer(x0, y0, z0, dx, dy, dz, color, alpha=1.0, is_steel=False):
        safe_alpha = max(0.0, min(1.0, alpha))
        highlight = max(0.0, min(1.0, alpha * 1.2))
        shadow = max(0.0, min(1.0, alpha * 0.8))
        
        # If it's steel, we only see the "cut" faces because it's inside the rubber
        # Front face
        ax.add_patch(Rectangle((x0, z0), dx, dz, color=color, alpha=safe_alpha, ec='black', lw=0.3))
        # Top face
        top = [(x0, z0 + dz), (x0 + dx, z0 + dz), 
               (x0 + dx + dy*iso_x, z0 + dz + dy*iso_y), (x0 + dy*iso_x, z0 + dz + dy*iso_y)]
        ax.add_patch(Polygon(top, color=color, alpha=highlight, ec='black', lw=0.3))
        # Right face
        right = [(x0 + dx, z0), (x0 + dx + dy*iso_x, z0 + dy*iso_y), 
                 (x0 + dx + dy*iso_x, z0 + dz + dy*iso_y), (x0 + dx, z0 + dz)]
        ax.add_patch(Polygon(right, color=color, alpha=shadow, ec='black', lw=0.3))

    current_z = 0
    
    # 1. Bottom Cover (Rubber)
    draw_iso_layer(0, 0, current_z, a, b, cover, '#333333', 0.6)
    current_z += cover
    
    # 2. Main Stack Loop
    # We need n+1 plates and n rubber layers
    for i in range(n + 1):
        # Draw Steel Plate (Recessed by edge cover 'ec')
        # This is shown as a "cut" view
        draw_iso_layer(ec, ec, current_z, a_p, b_p, ts, '#FFD700', 1.0) # Gold color for visibility
        current_z += ts
        
        # Draw Inner Elastomer Layer (Full size)
        if i < n:
            draw_iso_layer(0, 0, current_z, a, b, ti, '#333333', 0.5)
            current_z += ti

    # 3. Top Cover (Rubber)
    draw_iso_layer(0, 0, current_z, a, b, cover, '#333333', 0.6)
    total_h = current_z + cover

    # Axis Setup
    ax.set_xlim(-20, a + b*iso_x + 150)
    ax.set_ylim(-20, total_h + b*iso_y + 50)
    ax.axis('off')
    ax.set_aspect('equal')

    # Professional Legend Box (Points 1 & 2)
    props = dict(boxstyle='round,pad=1', facecolor='#f9f9f9', alpha=0.9, edgecolor='#cccccc')
    legend_text = (
        r"$\bf{BEARING\ SPECIFICATION}$" + "\n\n"
        f"Designation: {a} x {b} x {round(total_h,1)}\n"
        f"Elastomer Layers ($n$): {n} layers\n"
        f"Layer Thickness ($t_i$): {ti} mm\n"
        f"Steel Plates ($n+1$): {n+1} plates\n"
        f"Plate Thickness ($t_s$): {ts} mm\n"
        f"Top/Bot Covers: {cover} mm\n"
        f"Side Cover ($e_c$): {ec} mm\n"
        f"Total Height ($T_b$): {round(total_h,1)} mm"
    )
    ax.text(a + b*iso_x + 20, total_h/2, legend_text, fontsize=11, bbox=props, family='monospace', verticalalignment='center')
    
    # Title and Watermark
    ax.text(0, -15, "3/4 SECTIONAL ISOMETRIC VIEW - NOT TO SCALE", fontsize=9, style='italic', color='#666666')
    
    st.pyplot(fig)
    
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
    fy = st.number_input("Steel Yield $f_y$ (MPa)", value=240)

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

if mode == "Find Configuration":
    st.divider()
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
                with st.expander("ℹ️ View Strain Criteria"):
                    st.info(r"""
                    **Acceptance Criteria:**
                    1. **Shear Strain**: $\epsilon_{q,d} \le 1.0$ (Clause 5.3.3.3)
                    2. **Total Strain**: $\epsilon_{t,d} \le 7.0$ (Clause 5.3.3.2)
                    *Where $\epsilon_{t,d} = K_L(\epsilon_{c,d} + \epsilon_{q,d} + \epsilon_{a,d})$*
                    """)

            with t2:
                st.markdown("### Clause 5.3.3.6: Rotational and Buckling Limit")
                res_stab = engine.check_stability(a, b, target_Tb, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd)
                df_stab = pd.DataFrame(res_stab).rename(columns={"sum_vzd": "Σv_z,d", "uplift": "Uplift", "p_act": "p_act", "p_lim": "p_lim"})
                st.dataframe(style_status_df(df_stab), use_container_width=True)
                with st.expander("ℹ️ View Stability Criteria"):
                    st.info(r"""
                    **Acceptance Criteria:**
                    1. **Rotational Limitation (Uplift)**: $\sum v_{z,d} - \frac{a' \alpha_a + b' \alpha_b}{K_{rd}} \ge 0$
                    2. **Buckling Stability**: $p_{act} < p_{lim}$ 
                    *Where $p_{lim} = \frac{2 \cdot a' \cdot G \cdot S}{3 \cdot T_e}$*
                    """)
            
            with t3:
                st.markdown("### Clause 5.3.3.6: Non-Sliding Condition")
                res_slide = engine.check_sliding(a, b, target_Tb, Fx_d, Fy_d, Fz_dmin, vx_d, vy_d, Kf=Kf)
                df_slide = pd.DataFrame(res_slide).rename(columns={"sigma_m": "σ_m", "mu_e": "μ_e", "F_fric": "F_fric(kN)", "F_hor": "F_hor(kN)"})
                st.dataframe(style_status_df(df_slide), use_container_width=True)
                with st.expander("ℹ️ View Sliding Criteria"):
                    st.info(r"""
                    **Acceptance Criteria:**
                    1. **Friction Check**: $F_{hor} \le F_{fric}$
                    2. **Pressure Check**: $\sigma_m \ge 3.0$ MPa
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
                    """)
            
            with t5:
                st.markdown("### Clause 5.3.3.7: Forces/Moments Exerted on Structure")
                res_loads = engine.calculate_structure_loads(a, b, target_Tb, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd)
                df_loads = pd.DataFrame(res_loads).rename(columns={"Rxy_kN": "R_xy(kN)", "Ma_kNm": "M_a(kNm)", "Mb_kNm": "M_b(kNm)"})
                st.dataframe(df_loads, use_container_width=True)
        else:
            st.error("No configurations found matching target height.")

elif mode == "Manual Check":
    st.divider()
    st.header("2. Manual Configuration")
    m_col1, m_col2, m_col3 = st.columns(3)
    
    with m_col1:
        m_n = st.number_input("Number of layers ($n$)", value=5, min_value=2)
    with m_col2:
        m_ti = st.number_input("Inner layer thick ($t_i$) (mm)", value=10,min_value=5)
    with m_col3:
        m_ts = st.number_input("Plate thickness ($t_s$) (mm)", value=3, min_value=2)
        
    if st.button("Generate Calculation Report", type="primary", use_container_width=True):
        st.divider()
        st.header(f"Detailed Calculation Report: ")
        
        # 2. Section Cut Graph
        st.subheader("Bearing Pad Section Cut")
        draw_bearing_section(m_n, m_ti, m_ts, a,b)
        
        # 1. Procedural Engine with Colored Status
        steps = engine.get_procedural_report(a, b, m_n, m_ti, m_ts, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd, Kf, fy)
        
        with st.container():
            for step in steps:
                # Add color to PASS/FAIL
                colored_step = step.replace("**PASS**", ":green[**PASS**]").replace("**FAIL**", ":red[**FAIL**]")
                st.markdown(colored_step)
        
        st.divider()
        # st.success("Report generated successfully.")