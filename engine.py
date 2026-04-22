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
    """Generates valid physical combinations of n, ti, ts."""
    covers = 5        
    edge_cover = 4    
    valid_ts = {3, 4, 5}
    
    a_prime = a - (2 * edge_cover)
    b_prime = b - (2 * edge_cover)
    A1 = a_prime * b_prime
    lp = 2 * (a_prime + b_prime)
    
    base_matches = []
    for n in range(2, 12):
        for ti in range(5, 25):
            remaining = target_Tb - covers - (n * ti)
            denominator = n - 1
            if remaining <= 0: break
            
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
        T_q = (c['n'] * c['ti']) + 5
        
        e_cd = (1.5 * Fz_d) / (G * Ar * S) if Ar > 0 else 999
        e_qd = v_xyd / T_q
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

def get_procedural_report(a, b, n, ti, ts, G, Fz_d, vx_d, vy_d, alpha_ad, alpha_bd, Kf=0.6, fy=235):
    """
    Generates a step-by-step LaTeX report for a specific configuration.
    """
    # Base Geometry
    edge_cover = 4
    a_p = a - (2 * edge_cover)
    b_p = b - (2 * edge_cover)
    A1 = a_p * b_p
    lp = 2 * (a_p + b_p)
    Ar = A1 * (1 - (vx_d / a_p) - (vy_d / b_p))
    S = A1 / (lp * ti)
    T_q = (n * ti) + 5
    
    report = []
    
    # Section 1: Geometry
    report.append(r"### 1. Effective Geometry")
    report.append(rf"$a' = a - 2 \cdot e_c = {a} - 8 = {a_p}$ mm")
    report.append(rf"$b' = b - 2 \cdot e_c = {b} - 8 = {b_p}$ mm")
    report.append(rf"$A' = a' \cdot b' = {a_p} \cdot {b_p} = {A1}$ $mm^2$")
    report.append(rf"$S = \frac{{A'}}{{l_p \cdot t_i}} = \frac{{{A1}}}{{{lp} \cdot {ti}}} = {round(S, 2)}$")
    
    # Section 2: Strains
    e_cd = (1.5 * Fz_d) / (G * Ar * S)
    report.append(r"### 2. Design Strains (Clause 5.3.3.2)")
    report.append(rf"$\epsilon_{{c,d}} = \frac{{1.5 \cdot F_{{z,d}}}}{{G \cdot A_r \cdot S}} = \frac{{1.5 \cdot {Fz_d}}}{{{G} \cdot {round(Ar,1)} \cdot {round(S,2)}}} = {round(e_cd, 3)}$")
    
    # Section 3: Stability
    Eb = 2000
    v_c = (Fz_d * ti / A1) * (1 / (5 * G * S**2) + 1 / Eb)
    sum_v = n * v_c
    report.append(r"### 3. Stability & Deflection (Clause 5.3.3.6)")
    report.append(rf"$\sum v_{{z,d}} = n \cdot \left[ \frac{{F_{{z,d}} \cdot t_i}}{{A' \cdot (5GS^2)}} \right] = {n} \cdot {round(v_c, 4)} = {round(sum_v, 3)}$ mm")
    
    return report