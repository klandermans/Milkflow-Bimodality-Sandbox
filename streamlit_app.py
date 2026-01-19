import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from scipy.signal import find_peaks
from streamlit_drawable_canvas import st_canvas

# =========================
# BIMODALITEITSLOGICA
# =========================

def calculate_bimodality_score(
    flow_series,
    smooth_window=15,
    max_rel_pos=0.5,
    max_p1_rel_pos=0.25,
    ratio_threshold=0.45
):
    smoothed = flow_series.rolling(
        window=smooth_window, center=True, min_periods=1
    ).mean()

    peaks, properties = find_peaks(
        smoothed.values,
        distance=30,
        prominence=20,
        height=20
    )

    result = {
        "is_bimodal": False,
        "score": 0.0,
        "num_peaks": len(peaks),
        "peaks": peaks,
        "smoothed": smoothed,
        "valley_idx": None,
        "valley_val": None,
    }

    if len(peaks) < 2:
        return result

    sorted_idx = np.argsort(properties["prominences"])[::-1]
    p1_idx, p2_idx = sorted(peaks[sorted_idx[:2]])
    total_len = len(smoothed)

    if p2_idx / total_len > max_rel_pos:
        return result
    if p1_idx / total_len > max_p1_rel_pos:
        return result

    valley_rel = np.argmin(smoothed.values[p1_idx:p2_idx])
    valley_idx = p1_idx + valley_rel
    valley_val = smoothed.values[valley_idx]

    min_peak = min(
        smoothed.values[p1_idx],
        smoothed.values[p2_idx]
    )

    if min_peak <= 0:
        return result

    ratio = 1 - (valley_val / min_peak)

    result.update({
        "is_bimodal": ratio > ratio_threshold,
        "score": round(float(ratio), 4),
        "valley_idx": valley_idx,
        "valley_val": float(valley_val)
    })

    return result


def create_plot(series, res):
    plt.figure(figsize=(10, 4))
    t = series.index.total_seconds()

    plt.plot(t, series.values, ".", color="lightgray", label="Raw")
    plt.plot(t, res["smoothed"].values, linewidth=2, label="Smoothed")

    if len(res["peaks"]) > 0:
        plt.plot(t[res["peaks"]],
                 res["smoothed"].values[res["peaks"]],
                 "x", color="red", label="Peaks")

    if res["valley_idx"] is not None:
        plt.plot(t[res["valley_idx"]],
                 res["valley_val"],
                 "o", color="orange", label="Valley")

    title = "BIMODAAL" if res["is_bimodal"] else "UNIMODAAL"
    plt.title(f"{title} | score={res['score']}")
    plt.xlabel("Tijd (s)")
    plt.ylabel("Flow")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=120)
    plt.close()
    buf.seek(0)
    return buf


# =========================
# STREAMLIT UI
# =========================

st.set_page_config(layout="wide")
st.title("🧪 Milkflow Bimodality Sandbox")

st.markdown("Teken een melkflow.")

canvas = st_canvas(
    fill_color="rgba(0,0,0,0)",
    stroke_width=2,
    stroke_color="black",
    background_color="#ffffff",
    height=300,
    width=900,
    drawing_mode="freedraw",
    key="canvas",
)

if canvas.json_data and "objects" in canvas.json_data:
    paths = [
        obj["path"]
        for obj in canvas.json_data["objects"]
        if obj["type"] == "path"
    ]

    if paths:
        points = []
        for path in paths:
            for cmd in path:
                if len(cmd) >= 3:
                    points.append((cmd[1], cmd[2]))

        if len(points) > 20:
            arr = np.array(points)

            # INVERTEER FLOW-AS
            arr[:, 1] = arr[:, 1].max() - arr[:, 1]

            df = pd.DataFrame(arr, columns=["x", "flow"])
            

            df["t"] = (df["x"] - df["x"].min()) / (df["x"].max() - df["x"].min())
            df["t"] = df["t"] * 600  # 5 minuten melking

            df = df.groupby("t").mean().reset_index()
            df.index = pd.to_timedelta(df["t"], unit="s")

            flow_series = df["flow"]

            res = calculate_bimodality_score(flow_series)
            img = create_plot(flow_series, res)

            st.subheader("Resultaat")
            st.image(img)
            st.json({
                "bimodaal": res["is_bimodal"],
                "score": res["score"],
                "pieken": res["num_peaks"]
            })
