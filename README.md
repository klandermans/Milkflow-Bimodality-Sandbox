# 🐄 Milkflow Bimodality Sandbox

Interactieve webapp om melkflow-curves te tekenen en te analyseren op bimodaliteit met dezelfde logica als het batch-script. Ideaal voor onderzoek, demonstraties en threshold-tuning.

---

## 🎯 Features

* Teken vrije melkflow-curves met je muis of touchpad
* Real-time analyse van bimodaliteit:

  * Detecteert pieken en dalen
  * Berekent score en aantal pieken
  * Toont of de curve biologisch plausibel bimodaal is
* Grafische weergave van ruwe en gesmoothde data
* Volledige Python-native oplossing via `streamlit-drawable-canvas`
* Optionele inversie van de y-as zodat flow correct wordt geïnterpreteerd

---

## 🛠️ Vereisten

* Python 3.12+
* Streamlit
* Numpy
* Pandas
* Matplotlib
* SciPy
* streamlit-drawable-canvas

---

## ⚡ Installatie

1. Clone de repo:

```bash
git clone <repo-url>
cd melkflow
```

2. Maak een virtuele omgeving:

```bash
python -m venv venv
source venv/bin/activate  # macOS / Linux
venv\Scripts\activate     # Windows
```

3. Installeer dependencies:

```bash
pip install -r requirements.txt
```

> Voor de minimale versie:
>
> ```bash
> pip install streamlit numpy pandas matplotlib scipy streamlit-drawable-canvas
> ```

---

## 🚀 Run de app

```bash
streamlit run streamlit_app.py
```

Open daarna je browser op [http://localhost:8501](http://localhost:8501).

---

## 🖌️ Gebruik

1. Teken een melkflow-curve met de muis.
2. Klik op **Analyseer**.
3. Bekijk de grafiek met:

   * Ruwe en gesmoothde flow
   * Gedetecteerde pieken (rood)
   * Dal (oranje)
4. Controleer de JSON-output voor score, aantal pieken en bimodaliteit.

> Tip: teken minimaal 20 punten voor betrouwbare analyse.

---

## 📐 Logica achter de analyse

* Smoothing via rolling mean
* Detectie van pieken via `scipy.signal.find_peaks`
* Bimodaliteit:

  * Minimaal 2 pieken in de **eerste helft van de melking**
  * Dal tussen pieken moet diep genoeg zijn (`ratio > 0.45`)
* Output: `is_bimodal`, `score`, `num_peaks`

---

## ⚙️ Aanpassingen

* Pas thresholds aan in `calculate_bimodality_score` (parameters `ratio_threshold`, `max_rel_pos`, `max_p1_rel_pos`)
* Inverteren van de y-as gebeurt automatisch voor correcte flow-interpretatie

---

## 📂 Structuur

```
melkflow/
│
├─ streamlit_app.py      # Hoofdapplicatie
├─ requirements.txt      # Python dependencies
├─ README.md             # Deze file
└─ (optioneel) data/     # Voor CSV/XLSX testdata
```

---

## 🧪 Toekomstige verbeteringen

* Overlay van echte melkflow-data voor vergelijking
* Meerdere curves tegelijk analyseren
* Interactieve sliders voor thresholds
* Export van analyse-resultaten (JSON / CSV / HTML-rapport)

---

## 📜 Licentie

MIT License — vrij te gebruiken en aan te passen.
