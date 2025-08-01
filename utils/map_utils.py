import pandas as pd
import geopandas as gpd


def compute_centroid(gdf: pd.DataFrame, muni_poly: gpd.GeoSeries) -> tuple[float, float]:
    """
    Return the average latitude/longitude of gdf, or the muni_poly centroid if gdf is empty.
    """
    if not gdf.empty:
        lat0, lon0 = gdf.latitude.mean(), gdf.longitude.mean()
    else:
        centroid = muni_poly.centroid
        lat0, lon0 = centroid.y, centroid.x

    return lat0, lon0

def spatial_filter(gdf: gpd.GeoDataFrame, poly) -> gpd.GeoDataFrame:
    """
    Quick-cut with bounding box, then precise within().
    """
    minx, miny, maxx, maxy = poly.bounds
    box_cut = gdf.cx[minx:maxx, miny:maxy]
    return box_cut[box_cut.within(poly)]


def get_muni_poly(muni_gdf: gpd.GeoDataFrame, muni_name: str) -> gpd.GeoSeries:
    """
    Return the unioned polygon for a given municipality name.
    """
    return muni_gdf.loc[muni_gdf["LocNameHeb"] == muni_name, "geometry"].unary_union