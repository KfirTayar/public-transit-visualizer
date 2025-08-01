import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import sqlite3
import shapely.geometry

@st.cache_data(
    hash_funcs={
        shapely.geometry.base.BaseGeometry: lambda geom: geom.wkb
    }
)
def get_vehicle_route_in_muni(db_path: str, vehicle_id: int, start_time: pd.Timestamp, _muni_poly: shapely.geometry.base.BaseGeometry) -> gpd.GeoDataFrame:
    """
    Fetch vehicle pings for a given vehicle from a start time, keep only those inside the municipality polygon, and return a GeoDataFrame sorted by recorded_at.
    """
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM vehicle_locations "
        "WHERE vehicle_id = ? and recorded_at >= ? "
        "ORDER BY recorded_at",
        conn,
        params=[vehicle_id, start_time.strftime("%Y-%m-%d %H:%M:%S%z")],
        parse_dates=["recorded_at"]
    )
    conn.close()

    if df.empty:
        return gpd.GeoDataFrame(columns=df.columns.tolist() + ["geometry"], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs="EPSG:4326"
    )

    poly = _muni_poly.unary_union if hasattr(_muni_poly, "unary_union") else _muni_poly
    result = gdf[gdf.within(poly)].sort_values("recorded_at").reset_index(drop=True)
    return result

def build_route_layers(route_gdf: gpd.GeoDataFrame) -> list:
    """
    Split a route GeoDataFrame into start, mid, and end layers for plotting.
    """
    route = route_gdf.sort_values('recorded_at').copy()
    route['time_label'] = route['recorded_at'].dt.strftime('%H:%M:%S')
    start = route.iloc[[0]]
    end = route.iloc[[-1]]
    mid = route.iloc[1:-1]
    layers = []
    for segment, color, radius in [
        (start, [0,200,0,255], 80),  # green start
        (mid,   [200,0,0,150], 50),  # red mid
        (end,   [0,100,200,255], 50)  # blue end
    ]:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=segment,
                get_position="[longitude, latitude]",
                get_fill_color=color,
                get_radius=radius,
                pickable=True
            )
        )
    return layers