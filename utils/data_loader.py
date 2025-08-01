import streamlit as st
import pandas as pd
import geopandas as gpd
import sqlite3
from shapely.geometry import Point

@st.cache_data
def load_data(db_path: str = "db/citypulse.db", muni_geojson: str = "data/municipalities_multi.geojson") -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Load municipality polygons and vehicle pings into GeoDataFrames.
    """
    muni = gpd.read_file(muni_geojson)

    # Initialize the SQLite connection
    conn = sqlite3.connect(db_path)

    # Load vehicle_positions via the cached connection
    df = pd.read_sql_query(
        "SELECT * FROM vehicle_locations",
        conn,
        parse_dates=["recorded_at"],
    )
    conn.close()

    df["recorded_at"] = df["recorded_at"].dt.tz_localize(None)

    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs="EPSG:4326",
    )

    return muni, gdf

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