import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import os

# Gebruik non-interactive backend voor server/script omgevingen
plt.switch_backend('Agg')

def calculate_bimodality_score(flow_series, smooth_window=15, max_rel_pos=0.5, max_p1_rel_pos=0.25):
    """
    Berekent bimodaliteit, score en pieken.
    Bimodaliteit mag alleen in de eerste helft van de melking zitten.
    """
    # 1. Smoothing
    smoothed = flow_series.rolling(
        window=smooth_window, center=True, min_periods=1
    ).mean()
    
    # 2. Peak Detection
    peaks, properties = find_peaks(
        smoothed.values,
        distance=20,
        prominence=10,
        height=40
    )
    
    total_len = len(smoothed)
    num_peaks = len(peaks)
    
    result = {
        'is_bimodal': False,
        'score': 0.0,
        'num_peaks': num_peaks,
        'peaks': peaks,
        'smoothed': smoothed,
        'valley_idx': None,
        'valley_val': None
    }
    
    if num_peaks < 2:
        return result
    
    # 3. Neem de twee meest prominente pieken
    sorted_indices = np.argsort(properties['prominences'])[::-1]
    top_peaks = sorted(peaks[sorted_indices[:2]])
    
    p1_idx, p2_idx = top_peaks
    
    # --- NIEUW: BIOLOGISCHE CONSTRAINTS ---
    p1_rel = p1_idx / total_len
    p2_rel = p2_idx / total_len
    
    # Tweede piek moet in eerste helft zitten
    if p2_rel > max_rel_pos:
        return result
    
    # Eerste piek moet echt vroeg starten
    if p1_rel > max_p1_rel_pos:
        return result
    # ------------------------------------
    
    # 4. Zoek dal tussen de pieken
    valley_relative_idx = np.argmin(smoothed.values[p1_idx:p2_idx])
    valley_idx = p1_idx + valley_relative_idx
    valley_val = smoothed.values[valley_idx]
    
    p1_val = smoothed.values[p1_idx]
    p2_val = smoothed.values[p2_idx]
    min_peak = min(p1_val, p2_val)
    
    if min_peak <= 0:
        return result
    
    ratio = 1 - (valley_val / min_peak)
    
    result.update({
        'is_bimodal': ratio > 0.35,
        'score': round(ratio, 4),
        'valley_idx': valley_idx,
        'valley_val': valley_val
    })
    
    return result

def create_plot_base64(series_raw, res_dict, session_id):
    """Genereert een matplotlib grafiek en returnt base64 string"""
    plt.figure(figsize=(10, 4))
    
    # Ruwe data en smoothed
    plt.plot(series_raw.index.total_seconds(), series_raw.values, 
             color='lightgray', linestyle='None', marker='.', markersize=2, label='Raw')
    
    smoothed = res_dict['smoothed']
    plt.plot(smoothed.index.total_seconds(), smoothed.values,              color='#2c3e50', linewidth=1.5, label='Smoothed')
    
    # Pieken
    peaks = res_dict['peaks']
    if len(peaks) > 0:
        plt.plot(smoothed.index.total_seconds()[peaks], smoothed.values[peaks],                  "x", color='red', markersize=8, markeredgewidth=2, label='Peaks')
        
    # Valley (indien aanwezig)
    if res_dict['valley_idx'] is not None:
        v_idx = res_dict['valley_idx']
        v_val = res_dict['valley_val']
        t_sec = smoothed.index.total_seconds()
        plt.plot(t_sec[v_idx], v_val, "o", color='orange', markersize=8, label='Valley')
        
        # Visuele lijn voor de score (diepte)
        plt.vlines(t_sec[v_idx], v_val, v_val + (res_dict['score'] * v_val), 
                   colors='orange', linestyles='dotted', alpha=0.5)

    color = "green" if res_dict['is_bimodal'] else "gray"
    status = "BIMODAAL" if res_dict['is_bimodal'] else "UNIMODAAL"
    
    plt.title(f"ID: {session_id} | {status} | Score: {res_dict['score']:.2f} | Pieken: {res_dict['num_peaks']}",               color=color, fontweight='bold')

    plt.xlabel("Tijd (s)")
    
    plt.ylabel("Flow")
    
    plt.legend()
    
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save to buffer
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close()
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    return img_str

def generate_html(results_data):
    """Bouwt de HTML string"""
    
    html_template = """
    <html>
    <head>
        <title>Melkflow Bimodaliteits Rapport</title>

    </head>
    <body>
        <h1>Melkflow Analyse Rapport</h1>
        
        <div class="summary">
            <h2>Samenvatting</h2>
            <p>Totaal Sessies: <strong>{total}</strong> | 
               Bimodaal: <strong>{bimodal_count}</strong> | 
               Ratio: <strong>{ratio:.1f}%</strong>
            </p>
        </div>

        <div class="grid">
            {cards}
        </div>
    </body>
    </html>
    """
    
    cards_html = ""
    bimodal_count = 0
    
    # Sorteer resultaten: Bimodaal eerst, daarna op score (hoog-laag)
    results_data.sort(key=lambda x: (x['is_bimodal'], x['score']), reverse=True)
    
    for res in results_data:
        if res['is_bimodal']: bimodal_count += 1
        
        css_class = "bimodal" if res['is_bimodal'] else "unimodal"
        badge_class = "bg-green" if res['is_bimodal'] else "bg-gray"
        status_text = "BIMODAAL" if res['is_bimodal'] else "UNIMODAAL"
        
        cards_html += f"""
        <div class="card {css_class}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3>Koe {res['cow']} - {res['date']}</h3>
                <span class="badge {badge_class}">{status_text} (Score: {res['score']})</span>
            </div>
            <img src="data:image/png;base64,{res['img']}" />
        </div>
        """
        
    return html_template.format(
        total=len(results_data),
        bimodal_count=bimodal_count,
        ratio=(bimodal_count / len(results_data) * 100) if len(results_data) > 0 else 0,
        cards=cards_html
    )

def process_and_report(file_path):
    # Load logic
    try:
        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # ID Fix
    df['SessionID'] = df['Cow'].astype(str) + "_" + df['ImCvDate'].astype(str) + "_" + df['ImCvTime'].astype(str)
    
    results_for_html = []
    
    print("Analyseren en plotten...")
    groups = list(df.groupby('SessionID'))
    
    for session_id, group in groups:
        # Prep
        group = group.sort_values('ImCvDur').drop_duplicates('ImCvDur')
        group.index = pd.to_timedelta(group['ImCvDur'], unit='s')
        resampled = group['ImCvFlow'].resample('1s').interpolate(method='linear').fillna(0)
        
        # Calc
        analysis = calculate_bimodality_score(resampled)
        
        # Plot
        if not analysis['is_bimodal']: continue
        img_b64 = create_plot_base64(group['ImCvFlow'], analysis, session_id)
        
        results_for_html.append({
            'cow': group['Cow'].iloc[0],
            'date': group['ImCvDate'].iloc[0],
            'is_bimodal': analysis['is_bimodal'],
            'score': analysis['score'],
            'img': img_b64
        })

    # Generate HTML
    full_html = generate_html(results_for_html)
    
    output_file = "milk_flow_report.html"

    style = """        <style>
            body { background-color: #f4f4f9; padding: 20px; }
            h1 { color: #333; }
            .summary { margin-bottom: 20px; padding: 15px; background: white; border-radius: 5px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(600px, 1fr)); gap: 20px; }
            .card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .card.bimodal { border-left: 5px solid #27ae60; }
            .card.unimodal { border-left: 5px solid #95a5a6; }
            img { max-width: 100%; height: auto; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .badge { padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; }
            .bg-green { background-color: #27ae60; }
            .bg-gray { background-color: #95a5a6; }
        </style>"""
    output_file.replace("</head>", style + "\n</head>")
    with open(output_file, "w", encoding='utf-8') as f:
        f.write(full_html)
        
    print(f"Klaar! Rapport gegenereerd: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    # Selecteer bestand
    filename = 'bimodal.xlsx' 
    filename = 'Results.csv'
    if not os.path.exists(filename):
        # Fallback voor testen als xlsx er niet is
        filename = 'Results.xlsx - sheet1.csv'
        
    if os.path.exists(filename):
        process_and_report(filename)
    else:
        print(f"Geen input bestand gevonden ({filename}).")
