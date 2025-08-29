import os
import pandas as pd
import requests
import json
from time import sleep
from dotenv import load_dotenv

# Files
INPUT_CSV = "linkedin_profiles_cleaned.csv"
INPUT_JSON = "company_linkedin_pages.json"
OUTPUT_CSV = "linkedin_profiles_cleaned_updated.csv"

# Load Serper API key
load_dotenv()
SERPER_KEY = os.getenv("SERPER_KEY")
HEADERS = {"X-API-KEY": SERPER_KEY}

# Load CSV
df = pd.read_csv(INPUT_CSV)

# Load JSON
with open(INPUT_JSON, "r", encoding="utf-8") as f:
    company_data = json.load(f)

# Create lookup: company_name (lower) -> {website, company_size}
company_lookup = {
    str(comp.get("company_name", "")).strip().lower(): {
        "website": comp.get("website", ""),
        "company_size": comp.get("company_size", "")
    }
    for comp in company_data
    if comp.get("company_name")
}

def fetch_unknown_company_website(person_name, role):
    """Fallback: Try to find company website for Unknown companies using person's name + role."""
    query = f"{person_name} {role} official company website"
    url = "https://google.serper.dev/search"
    payload = {"q": query, "gl": "us", "hl": "en", "num": 5}

    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "organic" in data:
            for item in data["organic"]:
                link = item.get("link")
                if link:
                    return link
        return ""
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error fetching website for {person_name}: {e}")
        return ""

# Ensure company_size column exists
if "company_size" not in df.columns:
    df["company_size"] = ""

# Pass 1: Fill from company_linkedin_pages.json
for idx, row in df.iterrows():
    company = str(row.get("company_name", "")).strip().lower()
    if company in company_lookup:
        info = company_lookup[company]
        # Fill website if missing
        if (not row.get("company_website")) or row["company_website"] in ["", "Unknown", "unknown"]:
            if info["website"]:
                df.at[idx, "company_website"] = info["website"]
                print(f"✅ Filled from JSON: {row['company_name']} → {info['website']}")
        # Always update company size
        if info["company_size"]:
            df.at[idx, "company_size"] = info["company_size"]

# Pass 2: Handle "Unknown" companies via Google search
unknown_rows = df[df["company_name"].str.lower() == "unknown"]

for idx, row in unknown_rows.iterrows():
    person_name = str(row["title"]).split("-")[0].strip()
    role = row.get("roles", "")
    website = fetch_unknown_company_website(person_name, role)
    if website:
        df.at[idx, "company_website"] = website
        print(f"🌍 Found via Google: {row['title']} → {website}")
    else:
        print(f"❌ Still unknown: {row['title']}")
    sleep(1)  # Avoid rate limiting

# Save full dataset
print(f"💾 Saving {len(df)} total rows (with websites + company size updated)...")
df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Updated dataset saved as {OUTPUT_CSV}")
