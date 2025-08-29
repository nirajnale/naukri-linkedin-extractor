import requests
import json
import os
import time
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SERPER_KEY = os.getenv("SERPER_KEY")  # Your Serper.dev API key

CSV_FILE = "naukri_with_websites.csv"
COMPANY_JSON = "company_linkedin_pages.json"
OUTPUT_JSON = "linkedin_results.json"
NO_RESULTS_JSON = "no_results.json"

ROLES = ["Founder", "Co-Founder", "CEO", "Marketing Head", "Head of Marketing", "Business Development Head"]
MAX_QUERIES = 1000  # Limit number of queries per run

# 🔹 Load company names in CSV row order
def load_companies():
    companies = []

    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        if "company" in df.columns:
            valid_companies = df["company"].dropna().astype(str)
            valid_companies = valid_companies[valid_companies.str.lower() != "unknown"]
            companies.extend(valid_companies.tolist())

    if os.path.exists(COMPANY_JSON):
        with open(COMPANY_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            for comp in data:
                if "company" in comp and comp["company"] and comp["company"] not in companies:
                    companies.append(comp["company"])

    companies = [c.strip() for c in companies if c.strip()]
    return companies

# 🔹 Generate LinkedIn search queries
def generate_linkedin_queries(companies):
    queries = []
    for company in companies:
        for role in ROLES:
            queries.append({
                "query": f"{role} at {company}",
                "company": company,
                "role": role
            })
    return queries

# 🔹 Search LinkedIn profiles via Serper.dev
def search_linkedin_profiles(query_obj):
    company = query_obj["company"]
    role = query_obj["role"]

    search_patterns = [
        f'site:linkedin.com/in "{role} at {company}"',
        f'site:linkedin.com/in {role} {company}',
        f'site:linkedin.com/in {company} {role} LinkedIn'
    ]

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}

    profiles = []

    for pattern in search_patterns:
        data = {"q": pattern, "num": 5}
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            results = response.json()

            for result in results.get("organic", []):
                link = result.get("link", "")
                title = result.get("title", "")
                if "linkedin.com/in/" in link:
                    profiles.append({
                        "query": query_obj["query"],
                        "role": role,
                        "company": company,
                        "title": title,
                        "url": link
                    })
            if profiles:  # Stop if we already got something
                break

        except requests.exceptions.RequestException as e:
            print(f"❌ Error for query '{pattern}': {e}")
            continue

    return profiles

# 🔹 Load previous results to continue from last point
def load_previous_results():
    all_results = []
    failed_queries = []

    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            all_results = json.load(f)

    if os.path.exists(NO_RESULTS_JSON):
        with open(NO_RESULTS_JSON, "r", encoding="utf-8") as f:
            failed_queries = json.load(f)

    return all_results, failed_queries

# 🔹 Main runner
if __name__ == "__main__":
    if not SERPER_KEY:
        print("❌ SERPER_KEY is missing in .env file")
        exit()

    companies = load_companies()
    queries = generate_linkedin_queries(companies)

    all_results, failed_queries = load_previous_results()

    # Determine queries to run
    processed_queries = {q['query'] for q in all_results + failed_queries}
    queries_to_run = [q for q in queries if q['query'] not in processed_queries]

    # Apply max queries limit
    queries_to_run = queries_to_run[:MAX_QUERIES]

    print(f"\n🔍 Total queries to run this session: {len(queries_to_run)}\n")

    for i, q in enumerate(queries_to_run, start=1):
        print(f"🔎 [{i}/{len(queries_to_run)}] Searching: {q['query']}")
        profiles = search_linkedin_profiles(q)
        if profiles:
            all_results.extend(profiles)
            print(f"✅ Found {len(profiles)} profiles.")
        else:
            failed_queries.append(q)
            print("⚠️ No results found.")

        # Save partial results after each query
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        with open(NO_RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(failed_queries, f, indent=2)

        time.sleep(2)  # avoid rate limits

    print(f"\n✔ Done. Saved {len(all_results)} results to '{OUTPUT_JSON}'.")
    print(f"❌ {len(failed_queries)} queries failed. Saved to '{NO_RESULTS_JSON}'.")
