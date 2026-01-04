import geopandas as gpd
import os
import glob
from shapely.geometry import box

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
raw_dir = os.path.join(script_dir, "../raw")

# Map specific Folder Names to Clean Layer Names
folder_map = {
    "routes_nyc_subway_december2025": "subway_lines",
    "stops_nyc_subway_december2025": "subway_stations",
    "bus_routes_nyc_december2025": "bus_routes",
    "bus_stops_nyc_december2025": "bus_stops",
    "routes_LIRR_december2025": "rail_lirr_routes",
    "stops_LIRR_december2025": "rail_lirr_stops",
    "routes_metro_north_december2025": "rail_mnr_routes",
    "stops_metro_north_december2025": "rail_mnr_stops",
    "Rail_Lines_of_NJ_Transit": "rail_njt_routes",
    "NJTransit_Rail_Stations": "rail_njt_stops",
    "NTAD_Amtrak_Routes": "rail_amtrak_routes",
    "NTAD_Amtrak_Stations": "rail_amtrak_stops",
    "PATH_Train_Lines": "rail_path_routes",
    "PATH_Train_Stations": "rail_path_stops"
}

print("🏗️  Building Manhattan-Only Clipping Mask...")

# 1. Load the NYC Census Blocks (You already have this!)
blocks_path = os.path.join(raw_dir, "nycb2020_25d", "nycb2020.shp")

if os.path.exists(blocks_path):
    # Load and filter for Manhattan (BoroCode '1')
    nyc_blocks = gpd.read_file(blocks_path)
    # BoroCode is usually a string '1' or int 1. We check both just in case.
    manhattan_blocks = nyc_blocks[nyc_blocks['BoroCode'].astype(str) == '1']
    
    print("   Dissolving blocks into single island shape...")
    # Combine all blocks into one shape
    manhattan_poly = manhattan_blocks.dissolve().geometry[0]
    
    # Convert to Lat/Lon (EPSG:4326) to match transit data
    # We create a temporary GDF just to transform the geometry
    temp_gdf = gpd.GeoDataFrame({'geometry': [manhattan_poly]}, crs=nyc_blocks.crs)
    temp_gdf = temp_gdf.to_crs(epsg=4326)
    clip_mask = temp_gdf.geometry[0]
    print("✅ Mask Ready: Manhattan, Roosevelt Island, Inwood, Marble Hill.")
else:
    print("❌ Error: Could not find 'nycb2020_25d/nycb2020.shp'. Cannot create mask.")
    exit()

print(f"\n✂️  Processing and CLIPPING data to Manhattan Shape...")

for folder_name, layer_name in folder_map.items():
    folder_path = os.path.join(raw_dir, folder_name)
    
    if not os.path.exists(folder_path):
        continue
    
    shp_files = glob.glob(os.path.join(folder_path, "*.shp"))
    if not shp_files:
        continue
        
    try:
        input_shp = shp_files[0]
        print(f"   --> Loading {layer_name}...")
        gdf = gpd.read_file(input_shp)
        
        # 1. Standardize Projection
        if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)
            
        # 2. CLIP TO MANHATTAN POLYGON
        original_count = len(gdf)
        gdf_clipped = gdf.clip(clip_mask)
        new_count = len(gdf_clipped)
        
        if new_count == 0:
            print(f"       ⚠️  Warning: {layer_name} removed completely (Not in Manhattan)")
        else:
            print(f"       ✂️  Clipped {original_count} -> {new_count} features")

        # 3. Save
        out_path = os.path.join(raw_dir, f"{layer_name}.geojson")
        gdf_clipped.to_file(out_path, driver="GeoJSON")
        print(f"       ✅ Saved {layer_name}.geojson")
        
    except Exception as e:
        print(f"       ❌ Error processing {layer_name}: {e}")

print("\n✨ Done! Files are strictly limited to Manhattan.")