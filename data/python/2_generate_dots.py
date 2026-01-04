import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point
import random
import os
import sys

# --- CONFIGURATION ---
DOT_SCALE = 5 
script_dir = os.path.dirname(os.path.abspath(__file__))

# FILES
SHAPEFILE_PATH = os.path.join(script_dir, "../raw/nycb2020_25d/nycb2020.shp")
# UPDATED: Use the new detailed CSV
CSV_PATH = os.path.join(script_dir, "nyc_demographics_detailed.csv") 
# OLD ETHNICITY CSV (Still needed for Race data!)
ETH_CSV_PATH = os.path.join(script_dir, "../raw/nyc_demographics_2020.csv")

OUTPUT_PATH = os.path.join(script_dir, "../census_dots_full.geojson")

# --- LOAD DATA ---
print("Loading Shapefile...")
gdf = gpd.read_file(SHAPEFILE_PATH).to_crs(epsg=2263)

print("Loading Detailed Demographics...")
df_detailed = pd.read_csv(CSV_PATH, dtype={'GEOID': str})

print("Loading Ethnicity Data...")
df_eth = pd.read_csv(ETH_CSV_PATH, dtype={'GEOID': str})

# MERGE ALL
print("Merging Data...")
merged = gdf.merge(df_eth, on="GEOID", how="inner")
merged = merged.merge(df_detailed, on="GEOID", how="inner", suffixes=('', '_dtl'))

# Filter for Manhattan (061) for speed/size
merged = merged[merged['COUNTY'] == 61]
print(f"Processing {len(merged)} blocks...")

# --- GENERATOR ---
def get_random_points(polygon, num):
    points = []
    minx, miny, maxx, maxy = polygon.bounds
    while len(points) < num:
        p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if p.within(polygon):
            points.append(p)
    return points

dot_geoms = []
dot_props = {'ethnicity': [], 'sex': [], 'age_group': []}

print("Generating Synthetic Population Dots...")

for idx, row in merged.iterrows():
    # 1. Ethnicity Counts (From original Logic)
    eth_counts = {
        'Asian': row['Asian'],
        'Black': row['Black'],
        'Hispanic': row['Hispanic'],
        'White': row['White'],
        'Other': max(0, row['TotalPop'] - (row['Asian'] + row['Black'] + row['Hispanic'] + row['White']))
    }
    
    # 2. Probability Distributions for this Block
    total = row['TotalPop']
    if total <= 0: continue

    # Sex Probabilities
    prob_female = row['Pop_Female'] / total
    prob_male = 1.0 - prob_female
    
    # Age Probabilities
    age_labels = ['0-4', '5-17', '18-34', '35-59', '60+']
    age_counts = [row['Age_0_4'], row['Age_5_17'], row['Age_18_34'], row['Age_35_59'], row['Age_60_Plus']]
    
    # Normalize age probs (handle slight data mismatches in Census)
    age_sum = sum(age_counts)
    if age_sum > 0:
        age_probs = [x / age_sum for x in age_counts]
    else:
        age_probs = [0.2] * 5 # Fallback equal distribution

    # 3. Generate Dots
    for eth, count in eth_counts.items():
        if pd.isna(count) or count <= 0: continue
        
        num_dots = int(count // DOT_SCALE)
        if num_dots > 0:
            new_pts = get_random_points(row.geometry, num_dots)
            
            # Assign Attributes Probabilistically
            # "Synthetic Population": We assume independence between Race/Age/Sex for standard blocks
            sexes = np.random.choice(['Male', 'Female'], size=num_dots, p=[prob_male, prob_female])
            ages = np.random.choice(age_labels, size=num_dots, p=age_probs)
            
            dot_geoms.extend(new_pts)
            dot_props['ethnicity'].extend([eth] * num_dots)
            dot_props['sex'].extend(sexes)
            dot_props['age_group'].extend(ages)

# --- SAVE ---
print(f"Saving {len(dot_geoms)} dots...")
gdf_out = gpd.GeoDataFrame(dot_props, geometry=dot_geoms, crs="EPSG:2263")
gdf_out = gdf_out.to_crs(epsg=4326)
gdf_out.to_file(OUTPUT_PATH, driver="GeoJSON")
print("✅ Done! Upload 'census_dots_full.geojson' to Mapbox.")