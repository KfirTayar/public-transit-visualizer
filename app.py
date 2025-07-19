import streamlit as st
import pandas as pd
import pydeck as pdk
from utils import load_data, get_vehicle_route_in_muni, color_and_legend

st.set_page_config(
    page_title="City Pulse: Municipality Map",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📍 City Pulse: Real-Time Public Transit Visualization")

# Load data
muni_gdf, gdf_all = load_data()

st.sidebar.title("Filters")

# Municipality selector
muni_names = sorted(muni_gdf["LocNameHeb"].unique())
muni_name  = st.sidebar.selectbox("Municipality", muni_names)


# Time selectbox for 2025-06-18 only
tz = gdf_all["recorded_at"].dt.tz
target_date = pd.Timestamp("2025-06-18", tz=tz)

# Build list of HH:MM:SS strings on that date
times_on_date = (
    gdf_all[
        gdf_all["recorded_at"].dt.normalize() == target_date.normalize()
        ]["recorded_at"]
    .dt.strftime("%H:%M:%S")
    .sort_values()
    .unique()
    .tolist()
)

selected_time = st.sidebar.selectbox(
    "Time on 2025-06-18",
    times_on_date,
    index=0
)

# Parse back into tz-aware Timestamp
h, m, s = map(int, selected_time.split(":"))
t = target_date + pd.Timedelta(hours=h, minutes=m, seconds=s)

# Spatial + temporal filtering
muni_poly = (
    muni_gdf[muni_gdf["LocNameHeb"] == muni_name]
    .geometry
    .union_all()
)
in_muni = gdf_all[gdf_all.within(muni_poly)]
df_cur = in_muni[in_muni["recorded_at"] == t]

#  filter & legend
# Choose which field to filter by
filter_by = st.sidebar.selectbox(
    "filter by",
    ["vehicle_id", "line_id", "speed", "operator_id"]
)

df_disp, color_map, legend_html = color_and_legend(df_cur, filter_by)

st.write(
    f"Displaying {len(df_disp)} vehicles at **{t.strftime('%Y-%m-%d %H:%M:%S%z')}**, "
    f"colored by **{filter_by}**"
)
st.markdown(legend_html, unsafe_allow_html=True)

# Scatter + Text layers
scatter = pdk.Layer(
    "ScatterplotLayer",
    data=df_disp,
    get_position="[longitude, latitude]",
    get_fill_color="color",
    get_radius=50,
    radius_min_pixels=3,
    pickable=True
)
text = pdk.Layer(
    "TextLayer",
    data=df_disp,
    get_position="[longitude, latitude]",
    get_text=filter_by,         # label each dot with the same field
    get_color=[0,0,0,255],
    get_size=12,
    get_alignment_baseline="'bottom'"
)

# Compute map center
if not df_disp.empty:
    lat0, lon0 = df_disp.latitude.mean(), df_disp.longitude.mean()
else:
    centroid = muni_poly.centroid
    lat0, lon0 = centroid.y, centroid.x

view_state = pdk.ViewState(latitude=lat0, longitude=lon0, zoom=12, pitch=0)

# Initial render
deck = pdk.Deck(
    layers=[scatter, text],
    initial_view_state=view_state,
    map_style="light",
    tooltip={"text": f"{filter_by}: {{{filter_by}}}"}
)
map_placeholder = st.empty()
map_placeholder.pydeck_chart(deck)

# Let the user pick a vehicle from the currently displayed dots
sel_vid = st.sidebar.selectbox(
    "Choose vehicle to trace:",
    options=sorted(df_disp["vehicle_id"].unique())
)

# Show button
if st.sidebar.button("Show Route from here"):
    # build the muni polygon
    muni_poly = (
        muni_gdf[muni_gdf["LocNameHeb"] == muni_name]
          .geometry
          .unary_union
    )

    # Get route (all future pings in this muni)
    route_gdf = get_vehicle_route_in_muni(
        db_path="db/citypulse.db",
        vehicle_id=int(sel_vid),
        start_time=t,
        _muni_poly=muni_poly
    )

    if route_gdf.empty:
        st.warning("No further pings found for that vehicle in this municipality.")
    else:
        st.markdown(f"#### 🚍 Full route for **Vehicle {sel_vid}**")

        # Annotate with time_label and keep vehicle_id
        route_gdf["time_label"] = route_gdf["recorded_at"].dt.strftime("%H:%M:%S")

        # Split into start / middle / end
        start = route_gdf.iloc[[0]].copy()
        end   = route_gdf.iloc[[-1]].copy()
        mid   = route_gdf.iloc[1:-1].copy()

        # Build one layer per segment
        start_layer = pdk.Layer(
            "ScatterplotLayer",
            data=start,
            pickable=True,
            get_position="[longitude, latitude]",
            get_fill_color=[0,200,0,255],
            get_radius=80
        )
        mid_layer = pdk.Layer(
            "ScatterplotLayer",
            data=mid,
            pickable=True,
            get_position="[longitude, latitude]",
            get_fill_color=[200,0,0,150],
            get_radius=50
        )
        end_layer = pdk.Layer(
            "ScatterplotLayer",
            data=end,
            pickable=True,
            get_position="[longitude, latitude]",
            get_fill_color=[0,100,200,255],
            get_radius=50
        )

        # Center on start
        lat0, lon0 = start.geometry.y.iloc[0], start.geometry.x.iloc[0]
        view = pdk.ViewState(latitude=lat0, longitude=lon0, zoom=13, pitch=0)

        # Render with hover tooltip showing ID + time
        tooltip = {
            "html": (
                "<b>Vehicle:</b> {vehicle_id}<br/>"
                "<b>Time:</b> {time_label}"
            ),
            "style": {
                "backgroundColor": "rgba(255,0,0,0.7)",
                "color": "white",
                "fontSize": "12px",
                "padding": "8px"
            }
        }
        deck = pdk.Deck(
            layers=[start_layer, mid_layer, end_layer],
            initial_view_state=view,
            map_style="light",
            tooltip=tooltip
        )
        st.pydeck_chart(deck)

# Current Data table
st.dataframe(
    df_disp[
        ["vehicle_id", "line_id", "recorded_at", "operator_id",
         "bearing", "speed", "latitude", "longitude"]
    ].reset_index(drop=True)
)