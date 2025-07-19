import streamlit as st
import pandas as pd
import geopandas as gpd
import sqlite3
import random
from shapely.geometry import Point

# Cache the DB connection as a “resource”
@st.cache_resource
def init_db(db_path: str = "db/citypulse.db") -> sqlite3.Connection:
    """
    Initialize (and cache) the SQLite connection.
    """
    conn = sqlite3.connect(db_path)
    return conn

# Cache the data load as “data”
@st.cache_data
def load_data(muni_geojson: str = "data/municipalities_multi.geojson") -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Load municipality polygons and vehicle pings into GeoDataFrames.
    """
    # load muni polygons
    muni = gpd.read_file(muni_geojson)
    # Load vehicle_positions via the cached connection
    conn = init_db()
    df = pd.read_sql_query(
        "SELECT * FROM vehicle_locations",
        conn,
        parse_dates=["recorded_at"],
    )

    df["recorded_at"] = df["recorded_at"].dt.tz_localize(None)

    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df.longitude, df.latitude)],
        crs="EPSG:4326",
    )
    return muni, gdf

@st.cache_data
def get_vehicle_route_in_muni(db_path: str, vehicle_id: int, start_time: pd.Timestamp, _muni_poly: gpd.GeoSeries) -> gpd.GeoDataFrame:
    """
    Query vehicle_locations for all pings of `vehicle_id`
    at or after `start_time`, then filter to those within
    the given municipality polygon.

    Returns a GeoDataFrame sorted by recorded_at.
    """
    # Load raw pings from DB
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM vehicle_locations WHERE vehicle_id = ? AND recorded_at >= ? ORDER BY recorded_at",
        conn,
        params=(vehicle_id, start_time.isoformat()),
        parse_dates=["recorded_at"]
    )
    conn.close()

    if df.empty:
        return gpd.GeoDataFrame(columns=df.columns.tolist() + ["geometry"], crs="EPSG:4326")

    # Make GeoDataFrame and filter spatially
    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df.longitude, df.latitude)],
        crs="EPSG:4326"
    )
    # Ensure muni_poly is a single Shapely polygon
    poly = _muni_poly.unary_union if hasattr(_muni_poly, "unary_union") else _muni_poly
    gdf = gdf[gdf.within(poly)]

    # Final sort and return
    gdf = gdf.sort_values("recorded_at").reset_index(drop=True)
    return gdf


def color_and_legend(df: pd.DataFrame, by: str) -> tuple[pd.DataFrame, dict, str]:
    """
    Given a DataFrame and a column name to color by:
     - returns a copy of df with a 'color' column (RGBA lists)
     - a color_map dict {value: [r,g,b,a], ...}
     - an HTML snippet for the horizontal legend
    """
    df = df.copy()
    unique_vals = sorted(df[by].unique())

    # build color_map
    color_map = {
        val: [random.randint(50, 255), random.randint(50, 255), random.randint(50, 255), 200]
        for val in unique_vals
    }

    # assign colors
    df["color"] = df[by].map(color_map)

    # build legend HTML
    items = "".join([
        f"<span style='margin-right:12px;'>"
        f"<span style='display:inline-block;width:12px;height:12px;"
        f"background-color:#{r:02x}{g:02x}{b:02x};margin-right:4px;'></span>"
        f"{val}</span>"
        for val, (r, g, b, _) in color_map.items()
    ])
    legend_html = f"**Legend:**<br>{items}"

    return df, color_map, legend_html