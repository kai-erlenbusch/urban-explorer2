import pandas as pd
import requests
import os
import time

# --- CONFIGURATION ---
API_KEY = "87652936fa56e45af8b1926027381b6d600d298f" 

# NYC Counties: Bronx (005), Kings (047), New York (061), Queens (081), Richmond (085)
NYC_COUNTIES = "005,047,061,081,085"

# --- CENSUS DHC VARIABLES (Table P12: Sex by Age) ---
# We fetch all relevant columns to calculate the buckets manually
# P12_002N = Total Male, P12_026N = Total Female
# MALE Age Cols: 003 (<5) to 025 (85+)
# FEMALE Age Cols: 027 (<5) to 049 (85+)
# We will construct the API call dynamically to keep code clean.

def fetch_county_data(county_code):
    # 1. Define the Variables needed
    # Basic
    vars_list = ["P12_001N", "P12_002N", "P12_026N"] # Total, Male, Female
    
    # 2. Add Age Columns (Male 003-025, Female 027-049)
    # Note: Census API allows ~50 variables per call. This is close (~49), so it should fit.
    for i in range(3, 26): vars_list.append(f"P12_{i:03d}N") # Male Ages
    for i in range(27, 50): vars_list.append(f"P12_{i:03d}N") # Female Ages
    
    var_string = ",".join(vars_list)
    
    # 3. Call API (Using 'dec/dhc' endpoint instead of 'pl')
    url = f"https://api.census.gov/data/2020/dec/dhc?get={var_string}&for=block:*&in=state:36&in=county:{county_code}&key={API_KEY}"
    print(f"Fetching DHC data for county {county_code}...")
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: {response.text}")
        return None
        
    data = response.json()
    return pd.DataFrame(data[1:], columns=data[0])

# --- EXECUTION ---
all_data = []

for county in NYC_COUNTIES.split(','):
    df = fetch_county_data(county)
    if df is not None:
        all_data.append(df)
        time.sleep(1) # Be nice to the API

final_df = pd.concat(all_data)

# Convert all number columns to integers
cols_to_numeric = [c for c in final_df.columns if c.startswith("P12")]
final_df[cols_to_numeric] = final_df[cols_to_numeric].apply(pd.to_numeric)

# --- CALCULATE BUCKETS ---
print("Calculating Demographics Buckets...")

# 1. Sex
final_df['Pop_Male'] = final_df['P12_002N']
final_df['Pop_Female'] = final_df['P12_026N']

# 2. Age Groups
# Helper to sum male+female columns for a range
def sum_cols(df, male_idxs, female_idxs):
    m_cols = [f"P12_{i:03d}N" for i in male_idxs]
    f_cols = [f"P12_{i:03d}N" for i in female_idxs]
    return df[m_cols + f_cols].sum(axis=1)

# 0-4 Years (Index 3 and 27)
final_df['Age_0_4'] = sum_cols(final_df, [3], [27])

# 5-17 Years (Indexes 4-6 and 28-30)
final_df['Age_5_17'] = sum_cols(final_df, range(4, 7), range(28, 31))

# 18-34 Years (Indexes 7-12 and 31-36)
final_df['Age_18_34'] = sum_cols(final_df, range(7, 13), range(31, 37))

# 35-59 Years (Indexes 13-17 and 37-41)
final_df['Age_35_59'] = sum_cols(final_df, range(13, 18), range(37, 42))

# 60+ Years (Indexes 18-25 and 42-49)
final_df['Age_60_Plus'] = sum_cols(final_df, range(18, 26), range(42, 50))

# Create GEOID
final_df["GEOID"] = final_df["state"] + final_df["county"] + final_df["tract"] + final_df["block"]

# Keep only what we need
output_df = final_df[["GEOID", "P12_001N", "Pop_Male", "Pop_Female", "Age_0_4", "Age_5_17", "Age_18_34", "Age_35_59", "Age_60_Plus"]]
output_df = output_df.rename(columns={"P12_001N": "TotalPop"})

output_path = "nyc_demographics_detailed.csv"
output_df.to_csv(output_path, index=False)
print(f"✅ Saved detailed demographics to {output_path}")