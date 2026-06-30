# aashto_engine.py
import math

def generate_aashto_configs(L, W, target_Tb, top_bottom_cover=2.5, edge_cover=4):
    """
    Generates valid configurations using the AASHTO structural layering convention.
    n elastomer layers require n+1 steel plates.
    """
    covers = 2 * top_bottom_cover    
    valid_ts = {3, 4, 5}
    
    # Internal recessed geometry parameters
    L_prime = L - (2 * edge_cover)
    W_prime = W - (2 * edge_cover)
    
    base_matches = []
    for n in range(2, 12):
        for ti in range(5, 25):
            remaining = target_Tb - covers - (n * ti)
            denominator = n + 1 
            
            if remaining <= 0: 
                continue 
            
            if remaining % denominator == 0:
                ts = remaining // denominator
                if ts in valid_ts:
                    base_matches.append({
                        "n": n, "ti": ti, "ts": ts,
                        "L_prime": L_prime, "W_prime": W_prime, "T_b": target_Tb,
                        "top_bottom_cover": top_bottom_cover,
                        "edge_cover": edge_cover
                    })
    return base_matches

def find_aashto_configs(L, W, target_Tb, G, DL, LL, delta_long, delta_trans, teta_long, teta_trans, fy, F_TH, top_bottom_cover=2.5, edge_cover=4, deck_type="free"):
    """Validates bearing configurations against AASHTO LRFD 2007 Method B guidelines."""
    configs = generate_aashto_configs(L, W, target_Tb, top_bottom_cover=top_bottom_cover, edge_cover=edge_cover)
    delta_max = math.sqrt(delta_long**2 + delta_trans**2)
    results = []

    for c in configs:
        n, ti, ts = c['n'], c['ti'], c['ts']
        
        S_i = (L * W) / (2 * ti * (L + W))
        sig_s = (DL + LL) / (L * W)
        sig_l = LL / (L * W)
        h_rt = (n * ti) + (2 * top_bottom_cover)
        
        # 1. Stress Verification
        limit_s = min(1.66 * G * S_i, 11.0)
        limit_l = 0.66 * G * S_i
        status_s = (sig_s <= limit_s)
        status_l = (sig_l <= limit_l)
        
        # 2. Compressive Deflection
        eps_l = sig_l / (6 * G * S_i**2)
        delt_l = n * eps_l * ti
        status_defl = (delt_l <= 3.175)
        
        # 3. Maximum Shear Deformation 
        status_shear = (h_rt >= 2 * delta_max)
        
        # 4. Longitudinal & Transverse Rotational Boundaries
        rot_factor_long = (teta_long / n) * (L / ti)**2
        uplift_long = 1.0 * G * S_i * rot_factor_long
        shear_long = 1.875 * G * S_i * (1.0 - 0.20 * rot_factor_long)
        status_rot_long = (uplift_long < sig_s < shear_long)
        
        rot_factor_trans = (teta_trans / n) * (W / ti)**2
        uplift_trans = 1.0 * G * S_i * rot_factor_trans
        shear_trans = 1.875 * G * S_i * (1.0 - 0.20 * rot_factor_trans)
        status_rot_trans = (uplift_trans < sig_s < shear_trans)
        
        # 5. Buckling Stability
        L_c, W_c = (W, L) if L > W else (L, W)
        A = (1.92 * h_rt / L_c) / math.sqrt(1.0 + (2.0 * L_c / W_c))
        B = 2.67 / ((S_i + 2.0) * (1.0 + (L_c / (4.0 * W_c))))
        
        if (2.0 * A) <= B:
            status_stab = True
        else:
            denom = (2.0 * A - B) if deck_type == "free" else (A - B)
            if denom <= 0:
                status_stab = True  # Stable independent of stress
            else:
                sig_lim_stab = (G * S_i) / denom
                status_stab = (sig_s <= sig_lim_stab)
            
        # 6. Steel Reinforcement Performance
        ts_req_sls = (3 * ti * sig_s) / fy
        ts_req_fat = (2 * ti * sig_l) / F_TH
        status_reinf = (ts >= ts_req_sls and ts >= ts_req_fat)
        
        is_passed = (status_s and status_l and status_defl and status_shear and status_rot_long and status_rot_trans and status_stab and status_reinf)
        
        results.append({
            "n": n, "ti": ti, "ts": ts, "S": round(S_i, 2),
            "sig_s": round(sig_s, 2), "sig_l": round(sig_l, 2),
            "delt_l": round(delt_l, 2), "h_rt": h_rt,
            "STATUS": "PASS" if is_passed else "FAIL"
        })
    return results

def check_aashto_stresses(L, W, target_Tb, G, DL, LL, top_bottom_cover, edge_cover):
    configs = generate_aashto_configs(L, W, target_Tb, top_bottom_cover, edge_cover)
    results = []
    for c in configs:
        S_i = (L * W) / (2 * c['ti'] * (L + W))
        sig_s = (DL + LL) / (L * W)
        sig_l = LL / (L * W)
        limit_s = min(1.66 * G * S_i, 11.0)
        limit_l = 0.66 * G * S_i
        
        results.append({
            "n": c['n'], "ti": c['ti'], "ts": c['ts'],
            "sig_s (MPa)": round(sig_s, 2), "Limit_s (MPa)": round(limit_s, 2),
            "sig_l (MPa)": round(sig_l, 2), "Limit_l (MPa)": round(limit_l, 2),
            "STATUS": "PASS" if (sig_s <= limit_s and sig_l <= limit_l) else "FAIL"
        })
    return results

def check_aashto_deflections(L, W, target_Tb, G, LL, top_bottom_cover, edge_cover):
    configs = generate_aashto_configs(L, W, target_Tb, top_bottom_cover, edge_cover)
    results = []
    for c in configs:
        S_i = (L * W) / (2 * c['ti'] * (L + W))
        sig_l = LL / (L * W)
        eps_l = sig_l / (6 * G * S_i**2)
        delt_l = c['n'] * eps_l * c['ti']
        
        results.append({
            "n": c['n'], "ti": c['ti'], "ts": c['ts'],
            "eps_L": round(eps_l, 5), "delt_L (mm)": round(delt_l, 2),
            "Limit (mm)": 3.18,
            "STATUS": "PASS" if (delt_l <= 3.175) else "FAIL"
        })
    return results

def check_aashto_rotations(L, W, target_Tb, G, DL, LL, teta_long, teta_trans, top_bottom_cover, edge_cover):
    configs = generate_aashto_configs(L, W, target_Tb, top_bottom_cover, edge_cover)
    results = []
    sig_s = (DL + LL) / (L * W)
    for c in configs:
        n, ti = c['n'], c['ti']
        S_i = (L * W) / (2 * ti * (L + W))
        
        rot_l = (teta_long / n) * (L / ti)**2
        up_l = 1.0 * G * S_i * rot_l
        sh_l = 1.875 * G * S_i * (1.0 - 0.20 * rot_l)
        pass_l = (up_l < sig_s < sh_l)
        
        results.append({
            "n": n, "ti": ti, "ts": c['ts'],
            "Uplift_L (MPa)": round(up_l, 2), "Acted (MPa)": round(sig_s, 2), "Shear_L (MPa)": round(sh_l, 2),
            "STATUS": "PASS" if pass_l else "FAIL"
        })
    return results

def check_aashto_stability(L, W, target_Tb, G, DL, LL, top_bottom_cover, edge_cover, deck_type="free"):
    configs = generate_aashto_configs(L, W, target_Tb, top_bottom_cover, edge_cover)
    results = []
    sig_s = (DL + LL) / (L * W)
    for c in configs:
        S_i = (L * W) / (2 * c['ti'] * (L + W))
        h_rt = (c['n'] * c['ti']) + (2 * top_bottom_cover)
        L_c, W_c = (W, L) if L > W else (L, W)
        
        A = (1.92 * h_rt / L_c) / math.sqrt(1.0 + (2.0 * L_c / W_c))
        B = 2.67 / ((S_i + 2.0) * (1.0 + (L_c / (4.0 * W_c))))
        
        # Check initial stability rule (Eq. 1)
        if (2.0 * A) <= B:
            status = "PASS"
            sig_lim = float('inf')
        else:
            denom = (2.0 * A - B) if deck_type == "free" else (A - B)
            
            # If denominator <= 0, it's unconditionally stable (negative or infinite limit)
            if denom <= 0:
                status = "PASS"
                sig_lim = float('inf')
            else:
                sig_lim = (G * S_i) / denom
                status = "PASS" if sig_s <= sig_lim else "FAIL"
            
        results.append({
            "n": c['n'], "ti": c['ti'], "ts": c['ts'],
            "2A": round(2*A, 3), "B": round(B, 3), "sig_s": round(sig_s, 2),
            "sig_lim": "inf" if sig_lim == float('inf') else round(sig_lim, 2),
            "STATUS": status
        })
    return results

def check_aashto_reinforcement(L, W, target_Tb, DL, LL, fy, F_TH, top_bottom_cover, edge_cover):
    configs = generate_aashto_configs(L, W, target_Tb, top_bottom_cover, edge_cover)
    results = []
    sig_s = (DL + LL) / (L * W)
    sig_l = LL / (L * W)
    for c in configs:
        ts_req_sls = (3 * c['ti'] * sig_s) / fy
        ts_req_fat = (2 * c['ti'] * sig_l) / F_TH
        max_req = max(ts_req_sls, ts_req_fat)
        
        results.append({
            "n": c['n'], "ti": c['ti'], "ts_prov": c['ts'],
            "ts_req (SLS)": round(ts_req_sls, 2), "ts_req (Fatigue)": round(ts_req_fat, 2),
            "STATUS": "PASS" if c['ts'] >= max_req else "FAIL"
        })
    return results

def check_aashto_shear_deformation(L, W, target_Tb, delta_long, delta_trans, top_bottom_cover, edge_cover):
    configs = generate_aashto_configs(L, W, target_Tb, top_bottom_cover, edge_cover)
    delta_max = math.sqrt(delta_long**2 + delta_trans**2)
    results = []
    for c in configs:
        h_rt = (c['n'] * c['ti']) + (2 * top_bottom_cover)
        passed = (h_rt >= 2 * delta_max)
        results.append({
            "n": c['n'], "ti": c['ti'], "ts": c['ts'],
            "Resultant Delta_s (mm)": round(delta_max, 2),
            "Min Required h_rt (mm)": round(2 * delta_max, 2),
            "Provided h_rt (mm)": h_rt,
            "STATUS": "PASS" if passed else "FAIL"
        })
    return results

def get_aashto_procedural_report(L, W, n, ti, ts, G, DL, LL, delta_long, delta_trans, teta_long, teta_trans, fy, F_TH, top_bottom_cover=2.5, edge_cover=4, deck_type="free"):
    """Generates an automated, fully expanded step-by-step math report for AASHTO LRFD."""
    h_rt = (n * ti) + (2 * top_bottom_cover)
    S_i = (L * W) / (2 * ti * (L + W))
    sig_s = (DL + LL) / (L * W)
    sig_l = LL / (L * W)
    
    report = []
    
    report.append(r"## 1. Geometric Parameter Strategy & Shape Factors")
    report.append(rf"* Total Protective Layer Thickness $h_{{rt}} = n \cdot t_i + 2 \cdot h_{{cover}} = {n} \cdot {ti} + 2 \cdot {top_bottom_cover} = {h_rt}$ mm")
    report.append(rf"* Internal Layer Shape Factor: $S_i = \frac{{L \cdot W}}{{2 \cdot h_{{ri}} \cdot (L + W)}} = \frac{{{L} \cdot {W}}}{{2 \cdot {ti} \cdot ({L} + {W})}} = {round(S_i, 2)}$")

    report.append(r"## 2. Compressive Stress Performance (Article 14.7.5.3.2)")
    limit_s = min(1.66 * G * S_i, 11.0)
    limit_l = 0.66 * G * S_i
    status_s = "PASS" if sig_s <= limit_s else "FAIL"
    status_l = "PASS" if sig_l <= limit_l else "FAIL"
    report.append(rf"* Service Total Stress: $\sigma_s = \frac{{P_{{DL}} + P_{{LL}}}}{{L \cdot W}} = {round(sig_s, 2)}$ MPa vs Limit: ${round(limit_s, 2)}$ MPa $\rightarrow$ **{status_s}**")
    report.append(rf"* Service Live Stress: $\sigma_L = \frac{{P_{{LL}}}}{{L \cdot W}} = {round(sig_l, 2)}$ MPa vs Limit: ${round(limit_l, 2)}$ MPa $\rightarrow$ **{status_l}**")

    report.append(r"## 3. Instantaneous Live Load Deflection (Article 14.7.5.3.3)")
    eps_l = sig_l / (6 * G * S_i**2)
    delt_l = n * eps_l * ti
    status_defl = "PASS" if delt_l <= 3.175 else "FAIL"
    report.append(rf"* Live Load Strain Parameter: $\varepsilon_L = \frac{{\sigma_L}}{{6 \cdot G \cdot S_i^2}} = {round(eps_l, 5)}$")
    report.append(rf"* Cumulative Deflection: $\delta_L = n \cdot \varepsilon_L \cdot t_i = {n} \cdot {round(eps_l,5)} \cdot {ti} = {round(delt_l, 2)}$ mm vs Max 3.18mm $\rightarrow$ **{status_defl}**")

    report.append(r"## 4. Rotational Boundary Limits (Article 14.7.5.3.5)")
    rot_l = (teta_long / n) * (L / ti)**2
    up_l = 1.0 * G * S_i * rot_l
    sh_l = 1.875 * G * S_i * (1.0 - 0.20 * rot_l)
    status_rot = "PASS" if (up_l < sig_s < sh_l) else "FAIL"
    report.append(rf"* Uplift Boundary limit $\sigma_{{uplift}} = 1.0 \cdot G \cdot S_i \cdot \theta_{{fact}} = {round(up_l, 2)}$ MPa")
    report.append(rf"* Rotational Shear limit $\sigma_{{shear}} = 1.875 \cdot G \cdot S_i \cdot (1 - 0.20 \theta_{{fact}}) = {round(sh_l, 2)}$ MPa")
    report.append(rf"* Criteria Evaluation: ${round(up_l, 2)} < {round(sig_s, 2)} < {round(sh_l, 2)} \rightarrow$ **{status_rot}**")

    report.append(r"## 5. Structural Buckling Stability (Article 14.7.5.3.6)")
    L_c, W_c = (W, L) if L > W else (L, W)
    A = (1.92 * h_rt / L_c) / math.sqrt(1.0 + (2.0 * L_c / W_c))
    B = 2.67 / ((S_i + 2.0) * (1.0 + (L_c / (4.0 * W_c))))
    
    report.append(rf"* Empirical Geometry Metrics: $2A = {round(2*A, 3)}$ vs $B = {round(B, 3)}$")
    
    if (2.0 * A) <= B:
        status_stab = "PASS"
        report.append(r"* Buckling Safe Constraint: Initial geometry check satisfied ($2A \le B$). Stable independent of load stress per Equation (14.7.5.3.6-1).")
    else:
        # Dynamically map the correct AASHTO formula and cross-reference
        if deck_type == "free":
            formula_tex = r"\sigma_s \le \frac{GS}{2A - B}"
            eq_num = "14.7.5.3.6-4"
            denom = (2.0 * A - B)
        else:
            formula_tex = r"\sigma_s \le \frac{GS}{A - B}"
            eq_num = "14.7.5.3.6-5"
            denom = (A - B)
            
        if denom <= 0:
            status_stab = "PASS"
            report.append(rf"* Buckling Safe Constraint: Governing Formula: ${formula_tex}$ (Eq. {eq_num}). Because the denominator (${round(denom, 3)}$) $\le 0$, the bearing is unconditionally stable independent of $\sigma_s$. $\rightarrow$ **PASS**")
        else:
            sig_lim_stab = (G * S_i) / denom
            status_stab = "PASS" if sig_s <= sig_lim_stab else "FAIL"
            report.append(rf"* Buckling Safe Constraint: Governing Formula: ${formula_tex}$ (Eq. {eq_num})")
            report.append(rf"  Substitution: $\sigma_{{lim}} = \frac{{{G} \cdot {round(S_i, 2)}}}{{{round(denom, 3)}}} = {round(sig_lim_stab, 2)}$ MPa vs Acted $\sigma_s = {round(sig_s, 2)}$ MPa $\rightarrow$ **{status_stab}**")

    report.append(r"## 6. Reinforcement Steel Shims Strength (Article 14.7.5.3.7)")
    ts_req_sls = (3 * ti * sig_s) / fy
    ts_req_fat = (2 * ti * sig_l) / F_TH
    max_req = max(ts_req_sls, ts_req_fat)
    status_reinf = "PASS" if ts >= max_req else "FAIL"
    report.append(rf"* Minimum Thickness Required (SLS Demand): $t_{{s,sls}} = \frac{{3 \cdot t_i \cdot \sigma_s}}{{f_y}} = {round(ts_req_sls, 2)}$ mm")
    report.append(rf"* Minimum Thickness Required (Fatigue Demand): $t_{{s,fat}} = \frac{{2 \cdot t_i \cdot \sigma_L}}{{\Delta F_{{TH}}}} = {round(ts_req_fat, 2)}$ mm")
    report.append(rf"* Provided Shim Profile: $t_s = {ts}$ mm vs Required: {round(max_req, 2)} mm $\rightarrow$ **{status_reinf}**")

    return report