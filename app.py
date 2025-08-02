import streamlit as st
import pydeck as pdk
from utils.data_loader import load_data
from utils.route_utils import get_vehicle_route_in_muni, build_route_layers
from utils.style_utils import make_time_picker, color_and_legend, vehicle_route_tooltip
from utils.map_utils import compute_centroid, get_muni_poly, spatial_filter

st.set_page_config(page_title="City Pulse: Municipality Map", layout="wide", initial_sidebar_state="expanded")
st.title("📍 Public Transit Visualizer")

# Load data
muni_gdf, gdf_all = load_data(db_path="db_demo/siri_demo.db")

st.sidebar.image("assets/Bus_Tracking_Map.png", use_container_width=True)
st.sidebar.title("Filters")

# Municipality selector
muni_names = sorted(muni_gdf["LocNameHeb"].unique())
muni_name  = st.sidebar.selectbox("Municipality", muni_names)

# Time selectbox for 2025-06-18 only
t = make_time_picker(gdf_all, "2025-06-18")

# Spatial + temporal filtering
muni_poly = get_muni_poly(muni_gdf, muni_name)
in_muni = spatial_filter(gdf_all, muni_poly)
gdf_cur = in_muni[in_muni["recorded_at"] == t]

#  filter & legend
filter_by = st.sidebar.selectbox("filter by", ["vehicle_id", "line_id", "speed", "operator_id"])
gdf_disp, cmap, legend_html = color_and_legend(gdf_cur, filter_by)
st.write(f"Displaying {len(gdf_disp)} records at **{t.strftime('%Y-%m-%d %H:%M:%S%z')}**, "f"colored by **{filter_by}**")
st.markdown(legend_html, unsafe_allow_html=True)

# ─── Base map ───────────────────────────────────────────────────
# Scatter + Text layers
scatter = pdk.Layer("ScatterplotLayer", data=gdf_disp, get_position="[longitude, latitude]", get_fill_color="color", get_radius=50, radius_min_pixels=3, pickable=True)
text = pdk.Layer("TextLayer", data=gdf_disp, get_position="[longitude, latitude]",get_text=filter_by, get_color=[0,0,0,255], get_size=12, get_alignment_baseline="'bottom'")
# Compute map center
lat0, lon0 = compute_centroid(gdf_disp, muni_poly)
view_state = pdk.ViewState(latitude=lat0, longitude=lon0, zoom=12, pitch=0)
# Initial render
deck = pdk.Deck(layers=[scatter, text], initial_view_state=view_state, map_style="light", tooltip={"text": f"{filter_by}: {{{filter_by}}}"})
map_placeholder = st.empty()
map_placeholder.pydeck_chart(deck)

# ─── Vehicle route tracing ───────────────────────────────────────────────────
sel_vid = st.sidebar.selectbox("Choose vehicle to trace:", options=sorted(gdf_disp["vehicle_id"].unique()))

if st.sidebar.button("Show Route from here"):
    route = get_vehicle_route_in_muni(db_path="db_demo/siri_demo.db", vehicle_id=int(sel_vid), start_time=t, _muni_poly=muni_poly)

    if route.empty:
        st.warning("No further pings found for that vehicle in this municipality.")
    else:
        st.markdown(f"#### 🚍 Full route for **Vehicle {sel_vid}**")
        layers = build_route_layers(route)
        start_pt = route.geometry.iloc[0]
        view_rt = pdk.ViewState(latitude=start_pt.y, longitude=start_pt.x, zoom=13, pitch=0)
        deck_rt = pdk.Deck(layers=layers, initial_view_state=view_rt, map_style="light", tooltip=vehicle_route_tooltip())
        st.pydeck_chart(deck_rt)

# ─── Current Data table ───────────────────────────────────────────────────────────────
st.dataframe(gdf_disp.reset_index(drop=True)[["vehicle_id","line_id","recorded_at","operator_id","bearing","speed","latitude","longitude"]])