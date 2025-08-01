import random
import pandas as pd

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