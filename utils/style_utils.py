import random
import pandas as pd
import streamlit as st

def make_time_picker(gdf_all: pd.DataFrame, date_str: str) -> pd.Timestamp:
    """
    Add a sidebar selectbox for selecting a time on a given date_str (YYYY-MM-DD). Returns a tz-aware pandas.Timestamp.
    """
    tz = gdf_all["recorded_at"].dt.tz
    target = pd.Timestamp(date_str, tz=tz).normalize()

    times = (
        gdf_all[gdf_all["recorded_at"].dt.normalize() == target]
        ["recorded_at"]
        .dt.strftime("%H:%M:%S")
        .sort_values()
        .unique()
        .tolist()
    )

    selected = st.sidebar.selectbox(f"Time on {date_str}", times)
    h, m, s = map(int, selected.split(':'))

    return target + pd.Timedelta(hours=h, minutes=m, seconds=s)

def color_and_legend(df: pd.DataFrame, by: str) -> tuple[pd.DataFrame, dict, str]:
    """
    Return a copy of the DataFrame with an RGBA 'color' column, the color_map dict, and an HTML legend snippet.
    """
    df = df.copy()
    unique_vals = sorted(df[by].unique())

    # Build color_map
    color_map = {
        val: [random.randint(50, 255), random.randint(50, 255), random.randint(50, 255), 200]
        for val in unique_vals
    }

    # Assign colors
    df["color"] = df[by].map(color_map)

    # Build legend HTML
    items = "".join([
        f"<span style='margin-right:12px;'>"
        f"<span style='display:inline-block;width:12px;height:12px;"
        f"background-color:#{r:02x}{g:02x}{b:02x};margin-right:4px;'></span>"
        f"{val}</span>"
        for val, (r, g, b, _) in color_map.items()
    ])
    legend_html = f"**Legend:**<br>{items}"

    return df, color_map, legend_html

def vehicle_route_tooltip() -> dict:
    """Return the standardized tooltip dict for vehicle route layers."""
    return {
        "html": "<b>Vehicle:</b> {vehicle_id}<br/><b>Time:</b> {time_label}",
        "style": {
            "backgroundColor": "rgba(255,0,0,0.7)",
            "color": "white",
            "fontSize": "12px",
            "padding": "8px"
        }
    }