import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import re
from urllib.parse import urlparse

INPUT_CSV = "naukri_with_websites.csv"
OUTPUT_JSON = "company_linkedin_pages.json"

def extract_linkedin_from_website(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "linkedin.com/company" in href:
                href = href.split("?")[0]
                if href not in links:
                    links.append(href)
        return links
    except Exception as e:
        print(f"⚠️ Error crawling {url}: {e}")
        return []

def extract_company_size(linkedin_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(linkedin_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        match = re.search(r"([\d,]+)\s+employees", text, re.IGNORECASE)
        if match:
            number = match.group(1).replace(",", "")
            return int(number)
        return None
    except Exception as e:
        print(f"⚠️ Error fetching size from {linkedin_url}: {e}")
        return None

# Load CSV
df = pd.read_csv(INPUT_CSV)
if "website" not in df.columns or "company" not in df.columns:
    raise ValueError("❌ CSV must have 'website' and 'company' columns")

results = []

websites_df = df[["company", "website"]].dropna().drop_duplicates()
websites_list = websites_df.to_dict(orient="records")

for idx, row in enumerate(websites_list, 1):
    website = str(row["website"]).strip()
    company_name = row["company"].strip()
    
    if not website or website.lower() in ["n/a", "not found (only job/social links)", "error"]:
        continue
    
    if not website.startswith("http"):
        website = "https://" + website
    
    print(f"🔎 ({idx}/{len(websites_list)}) Crawling {website}")
    
    linkedin_urls = extract_linkedin_from_website(website)
    
    company_size = None
    if linkedin_urls:
        company_size = extract_company_size(linkedin_urls[0])
    
    results.append({
        "company_name": company_name,
        "website": website,
        "linkedin_urls": linkedin_urls,
        "company_size": company_size,
        "source_url": website
    })
    
    print(f"✅ Found {len(linkedin_urls)} LinkedIn URLs, Company Size: {company_size}")
    time.sleep(1)  # avoid hammering servers

# Save enhanced JSON
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"\n✔ Done. Saved results to '{OUTPUT_JSON}'")
