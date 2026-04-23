# engine.py
import math

def get_ks(ratio):
    """Interpolation for Ks (Table 4) based on b'/a'."""
    table_4 = {
        0.5: 137, 0.75: 100, 1.0: 86.2, 1.2: 80.4, 1.25: 79.3, 1.3: 78.4,
        1.4: 76.7, 1.5: 75.3, 1.6: 74.1, 1.7: 73.1, 1.8: 72.2, 1.9: 71.5,
        2.0: 70.8, 2.5: 68.3, 10.0: 61.9, 1000: 60
    }
    ratios = sorted(table_4.keys())
    if ratio <= ratios[0]: return table_4[ratios[0]]
    if ratio >= ratios[-1]: return table_4[ratios[-1]]
    
    for i in range(len(ratios) - 1):
        if ratios[i] <= ratio <= ratios[i+1]:
            r1, r2 = ratios[i], ratios[i+1]
            k1, k2 = table_4[r1], table_4[r2]
            return k1 + (k2 - k1) * (ratio - r1) / (r2 - r1)
    return 70.0

def generate_base_configs(a, b, target_Tb):
    """Generates valid physical combinations of n, ti, ts using n+1 plate rule."""
    covers = 5        # 2.5mm top + 2.5mm bottom
    edge_cover = 4    
    valid_ts = {3, 4, 5}
    
    a_prime = a - (2 * edge_cover)
    b_prime = b - (2 * edge_cover)
    A1 = a_prime * b_prime
    lp = 2 * (a_prime + b_prime)
    
    base_matches = []
    for n in range(2, 12):
        for ti in range(5, 25):
            # T_b = (n * ti) + ((n + 1) * ts) + covers
            remaining = target_Tb - covers - (n * ti)
            
            # Logic Update: n elastomer layers need n+1 plates for external plate config
            denominator = n + 1 
            
            if remaining <= 0: continue # Check other n values
            
            if remaining % denominator == 0:
                ts = remaining // denominator
                if ts in valid_ts:
                    base_matches.append({
                        "n": n, "ti": ti, "ts": ts,
                        "a_prime": a_prime, "b_prime": b_prime,
                        "A1": A1, "lp": lp, "T_b": target_Tb
                    })
    return base_matches

def find_bearing_configs(a, b, target_Tb, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd, K_L=1.0):
    configs = generate_base_configs(a, b, target_Tb)
    v_xyd = math.sqrt(vx_d**2 + vy_d**2)
    results = []

    for c in configs:
        Ar = c['A1'] * (1 - (vx_d / c['a_prime']) - (vy_d / c['b_prime']))
        S = c['A1'] / (c['lp'] * c['ti'])
        
        # T_q is total elastomer thickness: (n * ti) + covers
        T_q = (c['n'] * c['ti']) + 5 
        
        e_cd = (1.5 * Fz_d) / (G * Ar * S) if Ar > 0 else 999
        e_qd = v_xyd / T_q
        
        # sum_ti3 must include the covers as individual layers
        sum_ti3 = (c['n'] * (c['ti']**3)) + (2 * (2.5**3))
        
        e_ad = (((c['a_prime']**2 * alpha_ad) + (c['b_prime']**2 * alpha_bd)) * c['ti']) / (2 * sum_ti3)
        e_td = K_L * (e_cd + e_qd + e_ad)
        
        results.append({
            "n": c['n'], "ti": c['ti'], "ts": c['ts'], "S": round(S, 2),
            "eps_cd": round(e_cd, 3), "eps_qd": round(e_qd, 3),
            "eps_ad": round(e_ad, 3), "eps_td": round(e_td, 3),
            "STATUS": "PASS" if (e_qd <= 1.0 and e_td <= 7.0) else "FAIL"
        })
    return results

def check_stability(a, b, target_Tb, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd, K_rd=3.0):
    configs = generate_base_configs(a, b, target_Tb)
    results = []
    Eb_bulk = 2000

    for c in configs:
        Ar = c['A1'] * (1 - (vx_d / c['a_prime']) - (vy_d / c['b_prime']))
        S = c['A1'] / (c['lp'] * c['ti'])
        Te = (c['n'] * c['ti']) + 5
        v_c_single = (Fz_d * c['ti'] / c['A1']) * (1 / (5 * G * S**2) + 1 / Eb_bulk)
        sum_vzd = c['n'] * v_c_single
        uplift = sum_vzd - ((c['a_prime'] * alpha_ad + c['b_prime'] * alpha_bd) / K_rd)
        p_act = Fz_d / Ar if Ar > 0 else 999
        p_lim = (2 * c['a_prime'] * G * S) / (3 * Te)
        
        results.append({
            "n": c['n'], "ti": c['ti'], "ts": c['ts'],
            "sum_vzd": round(sum_vzd, 2), "uplift": round(uplift, 2),
            "p_act": round(p_act, 2), "p_lim": round(p_lim, 2),
            "STATUS": "PASS" if (uplift >= 0 and p_act < p_lim) else "FAIL"
        })
    return results

def check_sliding(a, b, target_Tb, Fx_d, Fy_d, Fz_dmin, vx_d, vy_d, Kf=0.6):
    configs = generate_base_configs(a, b, target_Tb)
    Fxy_d = math.sqrt(Fx_d**2 + Fy_d**2)
    results = []

    for c in configs:
        Ar = c['A1'] * (1 - (vx_d / c['a_prime']) - (vy_d / c['b_prime']))
        sigma_m = Fz_dmin / Ar if Ar > 0 else 0.1
        mu_e = 0.1 + (1.5 * Kf / sigma_m)
        F_fric = mu_e * Fz_dmin
        
        results.append({
            "n": c['n'], "ti": c['ti'], "ts": c['ts'],
            "sigma_m": round(sigma_m, 2), "mu_e": round(mu_e, 3),
            "F_fric": round(F_fric / 1000, 2), "F_hor": round(Fxy_d / 1000, 2),
            "STATUS": "PASS" if (Fxy_d <= F_fric and sigma_m >= 3.0) else "FAIL"
        })
    return results

def check_reinforcement(a, b, target_Tb, Fz_d, vx_d, vy_d, fy=235, Kh=1, gamma_m=1.00):
    configs = generate_base_configs(a, b, target_Tb)
    results = []

    for c in configs:
        Ar = c['A1'] * (1 - (vx_d / c['a_prime']) - (vy_d / c['b_prime']))
        ts_req = (1.3 * Fz_d * (2 * c['ti']) * Kh * gamma_m) / (Ar * fy) if Ar > 0 else 99
        results.append({
            "n": c['n'], "ti": c['ti'], "ts_prov": c['ts'],
            "ts_req": round(max(2.0, ts_req), 2),
            "STATUS": "PASS" if c['ts'] >= ts_req and c['ts'] >= 2.0 else "FAIL"
        })
    return results

def calculate_structure_loads(a, b, target_Tb, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd):
    configs = generate_base_configs(a, b, target_Tb)
    ks = get_ks((b - 8) / (a - 8))
    v_xy = math.sqrt(vx_d**2 + vy_d**2)
    results = []

    for c in configs:
        Te = (c['n'] * c['ti']) + 5
        Rxy = ((a * b) * G * v_xy) / Te
        denom_m = c['n'] * (c['ti']**3) * ks
        Ma = (G * alpha_ad * (c['a_prime']**5) * c['b_prime']) / denom_m
        Mb = (G * alpha_bd * (c['b_prime']**5) * c['a_prime']) / denom_m
        results.append({
            "n": c['n'], "ti": c['ti'], "ts": c['ts'],
            "Rxy_kN": round(Rxy / 1000, 2), "Ma_kNm": round(Ma / 1e6, 2), "Mb_kNm": round(Mb / 1e6, 2)
        })
    return results

def get_procedural_report(a, b, n, ti, ts, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd, Kf=0.6, fy=235, Fz_dmin=1000000, Fx_d=50000, Fy_d=20000):
    """
    Generates a full step-by-step LaTeX report with formula, 
    value substitution, results, and units for all EN 1337-3 checks.
    """
    import math
    
    # --- Pre-calculations ---
    edge_cover = 4
    a_p = a - (2 * edge_cover)
    b_p = b - (2 * edge_cover)
    A1 = a_p * b_p
    lp = 2 * (a_p + b_p)
    S = A1 / (lp * ti)
    Ar = A1 * (1 - (vx_d / a_p) - (vy_d / b_p))
    T_q = (n * ti) + 5
    v_xyd = math.sqrt(vx_d**2 + vy_d**2)
    Fxy_d = math.sqrt(Fx_d**2 + Fy_d**2)
    
    report = []

    # --- Section 1: Geometry ---
    report.append(r"## 1. Effective Geometry")
    report.append(rf"* Effective Width: $a' = a - 2 \cdot e_c = {a} - 8 = {a_p}$ mm")
    report.append(rf"* Effective Length: $b' = b - 2 \cdot e_c = {b} - 8 = {b_p}$ mm")
    report.append(rf"* Effective Plan Area: $A' = a' \cdot b' = {a_p} \cdot {b_p} = {A1}$ mm²")
    report.append(rf"* Shape Factor: $S = \frac{{A'}}{{l_p \cdot t_i}} = \frac{{{A1}}}{{{lp} \cdot {ti}}} = {round(S, 2)}$")
    report.append(rf"* Reduced Area: $A_r = A' \cdot (1 - \frac{{v_{{x,d}}}}{{a'}} - \frac{{v_{{y,d}}}}{{b'}}) = {A1} \cdot (1 - \frac{{{vx_d}}}{{{a_p}}} - \frac{{{vy_d}}}{{{b_p}}}) = {round(Ar, 2)}$ mm²")

    # --- Section 2: Design Strains ---
    report.append(r"## 2. Design Strains (Clause 5.3.3.2 - 5.3.3.4)")
    
    e_cd = (1.5 * Fz_d) / (G * Ar * S) if Ar > 0 else 0
    report.append(rf"* Compressive Strain: $\epsilon_{{c,d}} = \frac{{1.5 \cdot F_{{z,d}}}}{{G \cdot A_r \cdot S}} = \frac{{1.5 \cdot {Fz_d}}}{{{G} \cdot {round(Ar,1)} \cdot {round(S,2)}}} = {round(e_cd, 3)}$")
    
    e_qd = v_xyd / T_q
    report.append(rf"* Shear Strain: $\epsilon_{{q,d}} = \frac{{v_{{xy,d}}}}{{T_q}} = \frac{{{round(v_xyd, 2)}}}{{{T_q}}} = {round(e_qd, 3)}$")
    
    sum_ti3 = (n * (ti**3)) + (2 * (2.5**3))
    e_ad = (((a_p**2 * alpha_ad) + (b_p**2 * alpha_bd)) * ti) / (2 * sum_ti3)
    report.append(rf"* Rotational Strain: $\epsilon_{{a,d}} = \frac{{(a'^2 \alpha_a + b'^2 \alpha_b) \cdot t_i}}{{2 \cdot \sum t_i^3}} = \frac{{({a_p}^2 \cdot {alpha_ad} + {b_p}^2 \cdot {alpha_bd}) \cdot {ti}}}{{2 \cdot {round(sum_ti3, 1)}}} = {round(e_ad, 3)}$")
    
    e_td = 1.0 * (e_cd + e_qd + e_ad)
    status_strain = "PASS" if (e_qd <= 1.0 and e_td <= 7.0) else "FAIL"
    report.append(rf"* **Total Design Strain**: $\epsilon_{{t,d}} = K_L(\epsilon_{{c,d}} + \epsilon_{{q,d}} + \epsilon_{{a,d}}) = 1.0 \cdot ({round(e_cd, 3)} + {round(e_qd, 3)} + {round(e_ad, 3)}) = {round(e_td, 3)}$")
    report.append(rf"  Criteria: $\epsilon_{{q,d}} \le 1.0$ and $\epsilon_{{t,d}} \le 7.0 \rightarrow$ **{status_strain}**")

    # --- Section 3: Stability ---
    report.append(r"## 3. Stability & Uplift (Clause 5.3.3.6)")
    Eb = 2000
    v_c = (Fz_d * ti / A1) * (1 / (5 * G * S**2) + 1 / Eb)
    sum_v = n * v_c
    rot_term = (a_p * alpha_ad + b_p * alpha_bd) / 3.0
    uplift = sum_v - rot_term
    
    p_act = Fz_d / Ar if Ar > 0 else 0
    p_lim = (2 * a_p * G * S) / (3 * T_q)
    status_stab = "PASS" if (uplift >= 0 and p_act < p_lim) else "FAIL"
    
    report.append(rf"* Deflection: $\sum v_{{z,d}} = n \cdot v_c = {n} \cdot {round(v_c, 4)} = {round(sum_v, 3)}$ mm")
    report.append(rf"* Uplift Check: $\sum v_{{z,d}} - \frac{{a' \alpha_a + b' \alpha_b}}{{K_{{rd}}}} = {round(sum_v, 3)} - {round(rot_term, 3)} = {round(uplift, 3)}$")
    report.append(rf"* Buckling: $p_{{act}} = \frac{{F_{{z,d}}}}{{A_r}} = {round(p_act, 2)}$ MPa vs $p_{{lim}} = \frac{{2 a' G S}}{{3 T_e}} = {round(p_lim, 2)}$ MPa")
    report.append(rf"  Criteria: Uplift $\ge 0$ and $p_{{act}} < p_{{lim}} \rightarrow$ **{status_stab}**")

    # --- Section 4: Non-Sliding ---
    report.append(r"## 4. Non-Sliding Condition (Clause 5.3.3.6)")
    sigma_m = Fz_dmin / Ar if Ar > 0 else 0
    mu_e = 0.1 + (1.5 * Kf / sigma_m) if sigma_m > 0 else 0
    F_fric = mu_e * Fz_dmin
    status_slide = "PASS" if (Fxy_d <= F_fric and sigma_m >= 3.0) else "FAIL"
    
    report.append(rf"* Average Stress: $\sigma_m = \frac{{F_{{z,min}}}}{{A_r}} = \frac{{{Fz_dmin}}}{{{round(Ar,1)}}} = {round(sigma_m, 2)}$ MPa")
    report.append(rf"* Friction Resistance: $F_{{fric}} = \mu_e \cdot F_{{z,min}} = {round(mu_e, 3)} \cdot {Fz_dmin/1000} = {round(F_fric/1000, 2)}$ kN")
    report.append(rf"* Resultant Load: $F_{{xy,d}} = \sqrt{{F_{{x,d}}^2 + F_{{y,d}}^2}} = {round(Fxy_d/1000, 2)}$ kN")
    report.append(rf"  Criteria: $F_{{xy,d}} \le F_{{fric}}$ and $\sigma_m \ge 3.0$ MPa $\rightarrow$ **{status_slide}**")

    # --- Section 5: Reinforcement ---
    report.append(r"## 5. Reinforcement (Clause 5.3.3.5)")
    ts_req = (1.3 * Fz_d * (2 * ti) * 1.0 * 1.0) / (Ar * fy) if Ar > 0 else 0
    status_reinf = "PASS" if (ts >= ts_req and ts >= 2.0) else "FAIL"
    
    report.append(rf"* Min. Thickness: $t_{{s,req}} = \frac{{1.3 \cdot F_{{z,d}} \cdot (2 t_i) \cdot K_h \cdot \gamma_m}}{{A_r \cdot f_y}} = \frac{{1.3 \cdot {Fz_d} \cdot {2*ti} \cdot 1 \cdot 1}}{{{round(Ar,0)} \cdot {fy}}} = {round(ts_req, 2)}$ mm")
    report.append(rf"* Provided: $t_s = {ts}$ mm vs required {round(ts_req, 2)} mm $\rightarrow$ **{status_reinf}**")

    # --- Section 6: Structural Actions ---
    report.append(r"## 6. Actions on Structure (Clause 5.3.3.7)")
    ks_a = get_ks(b_p/a_p)
    ks_b = get_ks(a_p/b_p)
    Rxy = ((a * b) * G * v_xyd) / T_q
    Ma = (G * alpha_ad * (a_p**5) * b_p) / (n * ti**3 * ks_a)
    Mb = (G * alpha_bd * (b_p**5) * a_p) / (n * ti**3 * ks_b)
    
    report.append(rf"* Resultant Horizontal Force: $R_{{xy}} = \frac{{A \cdot G \cdot v_{{xy}}}}{{T_q}} = \frac{{{a} \cdot {b} \cdot {G} \cdot {round(v_xyd, 2)}}}{{{T_q}}} = {round(Rxy/1000, 2)}$ kN")
    report.append(rf"* Restoring Moment $M_a$: $\frac{{G \alpha_a a'^5 b'}}{{n t_i^3 K_{{s,a}}}} = \frac{{{G} \cdot {alpha_ad} \cdot {a_p}^5 \cdot {b_p}}}{{{n} \cdot {ti}^3 \cdot {ks_a}}} = {round(Ma/1e6, 2)}$ kNm")
    report.append(rf"* Restoring Moment $M_b$: $\frac{{G \alpha_b b'^5 a'}}{{n t_i^3 K_{{s,b}}}} = \frac{{{G} \cdot {alpha_bd} \cdot {b_p}^5 \cdot {a_p}}}{{{n} \cdot {ti}^3 \cdot {ks_b}}} = {round(Mb/1e6, 2)}$ kNm")

    return report