import streamlit as st
import pandas as pd
import engine
import aashto_engine
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

# Set page to wide mode for better table visibility
st.set_page_config(page_title="Bridge Bearing Design Tool", layout="wide")

# --- SIDEBAR: MODE & DESIGN STANDARDS ---
with st.sidebar:
    st.title("Settings & Modes")
    
    # 1. Select the governing engineering code standard specification
    standard = st.selectbox(
        "Select Design Standard:",
        ["EN 1337-3:2005", "AASHTO LRFD 2007 METHOD B "],
        help="Swaps verification algorithms, variables, and procedural math formulation metrics."
    )
    
    # 2. Select operation mode
    mode = st.selectbox(
        "Select Operation Mode:", 
        ["Find Configuration", "Manual Check"],
        help="Find Configuration searches for valid setups. Manual Check provides detailed calculation for a specific config."
    )
    
    st.divider()
    st.caption("Developed for multi-standard structural design checking workflows.")

# --- HELPER FUNCTION FOR STYLING ---
def style_status_df(df):
    """Applies red/green background to the 'STATUS' column."""
    def _color_status(val):
        if val == 'PASS': return 'background-color: #28a745; color: white'
        elif val == 'FAIL': return 'background-color: #dc3545; color: white'
        return ''
    
    if 'STATUS' in df.columns:
        return df.style.map(_color_status, subset=['STATUS'])
    return df

# --- HELPER FUNCTION FOR BUILDING BEARING SECTION ---
def draw_bearing_section(n, ti, ts, a, b, top_bottom_cover, edge_cover, is_aashto=False):
    """Generates a professional 3/4 isometric section view of the bearing."""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    cover = top_bottom_cover
    ec = edge_cover
    a_p = a - (2 * ec)
    b_p = b - (2 * ec)
    
    iso_x = 0.7 
    iso_y = 0.4 
    
    def draw_iso_layer(x0, y0, z0, dx, dy, dz, color, alpha=1.0):
        safe_alpha = max(0.0, min(1.0, alpha))
        highlight = max(0.0, min(1.0, alpha * 1.2))
        shadow = max(0.0, min(1.0, alpha * 0.8))
        
        ax.add_patch(Rectangle((x0, z0), dx, dz, color=color, alpha=safe_alpha, ec='black', lw=0.3))
        top_face = [(x0, z0 + dz), (x0 + dx, z0 + dz), 
                    (x0 + dx + dy*iso_x, z0 + dz + dy*iso_y), (x0 + dy*iso_x, z0 + dz + dy*iso_y)]
        ax.add_patch(Polygon(top_face, color=color, alpha=highlight, ec='black', lw=0.3))
        right_face = [(x0 + dx, z0), (x0 + dx + dy*iso_x, z0 + dy*iso_y), 
                      (x0 + dx + dy*iso_x, z0 + dz + dy*iso_y), (x0 + dx, z0 + dz)]
        ax.add_patch(Polygon(right_face, color=color, alpha=shadow, ec='black', lw=0.3))

    current_z = 0
    draw_iso_layer(0, 0, current_z, a, b, cover, '#333333', 0.6)
    current_z += cover
    
    for i in range(n + 1):
        draw_iso_layer(ec, ec, current_z, a_p, b_p, ts, '#FFD700', 1.0) 
        current_z += ts
        if i < n:
            draw_iso_layer(0, 0, current_z, a, b, ti, '#333333', 0.5)
            current_z += ti

    draw_iso_layer(0, 0, current_z, a, b, cover, '#333333', 0.6)
    total_h = current_z + cover

    ax.set_xlim(-20, a + b*iso_x + 150)
    ax.set_ylim(-20, total_h + b*iso_y + 50)
    ax.axis('off')
    ax.set_aspect('equal')

    props = dict(boxstyle='round,pad=1', facecolor='#f9f9f9', alpha=0.9, edgecolor='#cccccc')
    
    # Adapt textual labels based on the chosen code standard
    label_w = "Width $a$" if not is_aashto else "Length $L$"
    label_l = "Length $b$" if not is_aashto else "Width $W$"
    label_h = "$T_b$" if not is_aashto else "$h_{rst}$"
    label_ti = "$t_i$" if not is_aashto else "$h_{ri}$"
    label_ts = "$t_s$" if not is_aashto else "$h_s$"

    legend_text = (
        r"$\bf{BEARING\ SPECIFICATION}$" + f" ({'AASHTO' if is_aashto else 'EN1337'})\n\n"
        f"Designation: {a} x {b} x {round(total_h,1)}\n"
        f"Elastomer Layers ($n$): {n} layers\n"
        f"Layer Thickness ({label_ti}): {ti} mm\n"
        f"Steel Plates ($n+1$): {n+1} plates\n"
        f"Plate Thickness ({label_ts}): {ts} mm\n"
        f"Top/Bot Cover Layer: {cover} mm\n"
        f"Side/Edge Cover Layer ($e_c$): {ec} mm\n"
        f"Total Pad Height ({label_h}): {round(total_h,1)} mm"
    )
    ax.text(a + b*iso_x + 20, total_h/2, legend_text, fontsize=11, bbox=props, family='monospace', verticalalignment='center')
    ax.text(0, -15, " ISOMETRIC VIEW - NOT TO SCALE", fontsize=9, style='italic', color='#666666')
    
    st.pyplot(fig)

# --- MAIN UI ---
st.title(f"🏗️ {standard} Bridge Bearing Design Suite")
st.markdown(f"Automated design configuration search, code compliance verification and reporting matching **{standard}** specifications.")
st.divider()

# --- 1. DYNAMIC INPUT PARAMETERS MAPPING ---
st.header("1. Design Input Space Parameters")
col1, col2, col3 = st.columns(3)

is_aashto_selected = (standard == "AASHTO LRFD 2007")

with col1:
    st.subheader("Geometric Dimensions")
    label_dim_a = "Overall Width $a$ (mm)" if not is_aashto_selected else "Total Plan Length $L$ (mm)"
    label_dim_b = "Overall Length $b$ (mm)" if not is_aashto_selected else "Total Plan Width $W$ (mm)"
    label_height = "Target Total Height $T_b$ (mm)" if not is_aashto_selected else "Target Total Height $h_{{rst}}$ (mm)"
    
    a = st.number_input(label_dim_a, value=450 if is_aashto_selected else 560)
    b = st.number_input(label_dim_b, value=600 if is_aashto_selected else 380)
    target_Tb = st.number_input(label_height, value=72 if is_aashto_selected else 73)
    
    top_bottom_cover = st.number_input("Protective Cover Layer Thick (mm)", value=6.0 if is_aashto_selected else 2.5, step=0.5, format="%.1f")
    edge_cover = st.number_input("Side/Edge Profile Distance (mm)", value=10.0 if is_aashto_selected else 4.0, step=0.5, format="%.1f")
    fy = st.number_input("Steel Yield Limit $f_y$ (MPa)", value=240)
    if is_aashto_selected:
        F_TH = st.number_input("Fatigue Threshold $\Delta F_{TH}$ (MPa)", value=165)

with col2:
    st.subheader("Service & Ultimate Loading")
    if not is_aashto_selected:
        Fz_d = st.number_input("Max Ultimate Vertical $F_{z,d}$ (kN)", value=1500) * 1000
        Fz_dmin = st.number_input("Min Service Vertical $F_{z,min}$ (kN)", value=1000) * 1000
        Fx_d = st.number_input("Longitudinal Force $F_{x,d}$ (kN)", value=50) * 1000
        Fy_d = st.number_input("Transverse Force $F_{y,d}$ (kN)", value=20) * 1000
    else:
        DL = st.number_input("Service Dead Load $DL$ (kN)", value=1907) * 1000
        LL = st.number_input("Service Live Load $LL$ (kN)", value=766) * 1000
        deck_type = st.selectbox("Bridge Deck Movement", ["free", "fixed"])

with col3:
    st.subheader("Deformations & Rotations")
    vx_d = st.number_input("Max Shear Displacement $v_{x,d}$ (mm)", value=20.0)
    vy_d = st.number_input("Max Shear Displacement $v_{y,d}$ (mm)", value=10.0)
    alpha_ad = st.number_input("Rotation Plan Direction $\\alpha_{a,d}$ (rad)", value=0.004 if is_aashto_selected else 0.0050, format="%.4f")
    alpha_bd = st.number_input("Rotation Plan Direction $\\alpha_{b,d}$ (rad)", value=0.002 if is_aashto_selected else 0.0020, format="%.4f")

G, Kf, Kh = 0.9, 0.6, 1.0

# --- 2. EXECUTION ENGINE FLOWS ---
if mode == "Find Configuration":
    st.divider()
    if st.button("Execute Multi-Config Design Evaluation", type="primary", use_container_width=True):
        
        if not is_aashto_selected:
            # Route execution to original European standard checking core
            configs = engine.find_bearing_configs(a, b, target_Tb, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd, top_bottom_cover=top_bottom_cover, edge_cover=edge_cover)
        else:
            # Route execution to newly isolated AASHTO specifications toolset
            configs = aashto_engine.find_aashto_configs(a, b, target_Tb, G, DL, LL, vx_d, vy_d, alpha_ad, alpha_bd, fy, F_TH, top_bottom_cover=top_bottom_cover, edge_cover=edge_cover, deck_type=deck_type)
            
        if configs:
            st.header("2. Search Results Grid")
            df_base = pd.DataFrame(configs)[["n", "ti", "ts", "S", "STATUS"]]
            df_base.insert(3, "Total Thickness (mm)", target_Tb)
            st.dataframe(style_status_df(df_base), use_container_width=True)
            
            st.divider()
            st.header("3. Standard Compliance Verification Matrix")
            
            if not is_aashto_selected:
                t1, t2, t3, t4, t5 = st.tabs(["📉 Strain Checks", "🛡️ Stability & Uplift", "🛷 Sliding", "🔩 Shim Plates", "📡 Actions"])
                with t1:
                    df_strains = pd.DataFrame(configs)[["n", "ti", "ts", "eps_cd", "eps_qd", "eps_ad", "eps_td", "STATUS"]].rename(columns={
                        "eps_cd": "ε_c,d", "eps_qd": "ε_q,d", "eps_ad": "ε_a,d", "eps_td": "ε_t,d"
                    })
                    st.dataframe(style_status_df(df_strains), use_container_width=True)
                with t2:
                    res_stab = engine.check_stability(a, b, target_Tb, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd, top_bottom_cover=top_bottom_cover, edge_cover=edge_cover)
                    st.dataframe(style_status_df(pd.DataFrame(res_stab)), use_container_width=True)
                with t3:
                    res_slide = engine.check_sliding(a, b, target_Tb, Fx_d, Fy_d, Fz_dmin, vx_d, vy_d, Kf=Kf, top_bottom_cover=top_bottom_cover, edge_cover=edge_cover)
                    st.dataframe(style_status_df(pd.DataFrame(res_slide)), use_container_width=True)
                with t4:
                    res_reinf = engine.check_reinforcement(a, b, target_Tb, Fz_d, vx_d, vy_d, fy=fy, Kh=Kh, top_bottom_cover=top_bottom_cover, edge_cover=edge_cover)
                    st.dataframe(style_status_df(pd.DataFrame(res_reinf)), use_container_width=True)
                with t5:
                    res_loads = engine.calculate_structure_loads(a, b, target_Tb, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd, top_bottom_cover=top_bottom_cover, edge_cover=edge_cover)
                    st.dataframe(pd.DataFrame(res_loads), use_container_width=True)
            else:
                t1, t2, t3, t4, t5 = st.tabs(["📊 Stress Profiles", "📉 Strain Deflections", "🔄 Rotational Limits", "🔩 Shim Strength & Stability", "🛷 Shear Deformation"])
                with t1:
                    st.markdown("### Article 14.7.5.3.2: Stresses verification")
                    res_stress = aashto_engine.check_aashto_stresses(a, b, target_Tb, G, DL, LL, top_bottom_cover, edge_cover)
                    st.dataframe(style_status_df(pd.DataFrame(res_stress)), use_container_width=True)
                with t2:
                    st.markdown("### Article 14.7.5.3.3: Compressive Deflections")
                    res_defl = aashto_engine.check_aashto_deflections(a, b, target_Tb, G, LL, top_bottom_cover, edge_cover)
                    st.dataframe(style_status_df(pd.DataFrame(res_defl)), use_container_width=True)
                with t3:
                    st.markdown("### Article 14.7.5.3.5: Rotational Capacities boundaries")
                    res_rot = aashto_engine.check_aashto_rotations(a, b, target_Tb, G, DL, LL, alpha_ad, alpha_bd, top_bottom_cover, edge_cover)
                    st.dataframe(style_status_df(pd.DataFrame(res_rot)), use_container_width=True)
                with t4:
                    st.markdown("### Article 14.7.5.3.6 & 14.7.5.3.7: Structural Stability & Steel Shims checks")

                    st.write("**Stability Component Performance:**")
                    res_stab = aashto_engine.check_aashto_stability(a, b, target_Tb, G, DL, LL, top_bottom_cover, edge_cover, deck_type=deck_type)
                    st.dataframe(style_status_df(pd.DataFrame(res_stab)), use_container_width=True)

                    st.write("**Steel Shim Thickness Performance:**")
                    res_reinf = aashto_engine.check_aashto_reinforcement(a, b, target_Tb, DL, LL, fy, F_TH, top_bottom_cover, edge_cover)
                    st.dataframe(style_status_df(pd.DataFrame(res_reinf)), use_container_width=True)
                with t5:
                    st.markdown("### Article 14.7.6.3.4: Maximum Shear Deformation Constraint")
                    res_shear = aashto_engine.check_aashto_shear_deformation(a, b, target_Tb, vx_d, vy_d, top_bottom_cover, edge_cover)
                    st.dataframe(style_status_df(pd.DataFrame(res_shear)), use_container_width=True)
        else:
            st.error("No valid physical configurations can be established matching the target total thickness profile.")

elif mode == "Manual Check":
    st.divider()
    st.header("2. Manual Configuration Specification Mode")
    m_col1, m_col2, m_col3 = st.columns(3)
    
    with m_col1:
        m_n = st.number_input("Number of inner elastomer layers ($n$)", value=3, min_value=1)
    with m_col2:
        m_ti = st.number_input("Thickness of individual inner layer (mm)", value=16 if is_aashto_selected else 10, min_value=2)
    with m_col3:
        m_ts = st.number_input("Thickness of steel shim plates (mm)", value=3 if is_aashto_selected else 3, min_value=1)
        
    if st.button("Generate Extended Math Procedural Report", type="primary", use_container_width=True):
        st.divider()
        st.header("Detailed Calculation Report Execution Output")
        
        st.subheader("Dynamic Visual Section View Diagram")
        draw_bearing_section(m_n, m_ti, m_ts, a, b, top_bottom_cover, edge_cover, is_aashto=is_aashto_selected)
        
        if not is_aashto_selected:
            steps = engine.get_procedural_report(
                a, b, m_n, m_ti, m_ts, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd, Kf, fy,
                Fz_dmin=Fz_dmin, Fx_d=Fx_d, Fy_d=Fy_d, 
                top_bottom_cover=top_bottom_cover, edge_cover=edge_cover
            )
        else:
            steps = aashto_engine.get_aashto_procedural_report(
                a, b, m_n, m_ti, m_ts, G, DL, LL, vx_d, vy_d, alpha_ad, alpha_bd, fy, F_TH,
                top_bottom_cover=top_bottom_cover, edge_cover=edge_cover, deck_type=deck_type
            )
            
        with st.container():
            for step in steps:
                colored_step = step.replace("**PASS**", ":green[**PASS**]").replace("**FAIL**", ":red[**FAIL**]")
                st.markdown(colored_step)
        st.divider()