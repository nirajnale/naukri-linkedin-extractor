import os
import requests
import pandas as pd
from dotenv import load_dotenv
from time import sleep
from urllib.parse import urlparse

# Load environment variables
load_dotenv()
SERPER_KEY = os.getenv("SERPER_KEY")

INPUT_FILE = "naukri_jobs_clean.csv"
OUTPUT_FILE = "naukri_with_websites.csv"

BLOCKED_DOMAINS = [
    "naukri.com", "linkedin.com", "glassdoor.com", "indeed.com",
    "monster.com", "shine.com", "timesjobs.com", "instahyre.com",
    "ambitionbox.com", "zippia.com"
]

def is_valid_company_website(url):
    if not url:
        return False
    domain = urlparse(url).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    for bad in BLOCKED_DOMAINS:
        if bad in domain:
            return False
    if any(domain.endswith(tld) for tld in [".com", ".in", ".org", ".net", ".co", ".io"]):
        return True
    return False

def fetch_company_website(company_name):
    if not company_name or company_name.lower() == "unknown":
        return "N/A"

    query = f"{company_name} official website"
    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": SERPER_KEY,
        "Content-Type": "application/json"
    }

    payload = {"q": query, "num": 3}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        if "organic" in data:
            for item in data["organic"]:
                link = item.get("link")
                if is_valid_company_website(link):
                    return link
            return "Not Found (Only job/social links)"
        else:
            return "Not Found"

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error fetching {company_name}: {e}")
        return "Error"

def main():
    df = pd.read_csv(INPUT_FILE)
    if "company" not in df.columns:
        raise ValueError("❌ CSV must have a 'company' column (lowercase)")

    websites = []
    for i, company in enumerate(df["company"], start=1):
        print(f"[{i}/{len(df)}] Fetching website for: {company}")
        website = fetch_company_website(company)
        print(f"   → {website}")
        websites.append(website)
        sleep(1)

    df["website"] = websites
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Done! Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
