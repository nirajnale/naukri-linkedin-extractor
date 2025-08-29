import json
import pandas as pd

# Input files
PROFILES_FILE = "linkedin_results_cleaned.json"   # output of profile_cleaner_v2
COMPANIES_FILE = "company_linkedin_pages.json"   # from linkedin_search.py

# Output files
OUTPUT_JSON = "linkedin_profiles_final.json"
OUTPUT_CSV = "linkedin_profiles_final.csv"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    # Load data
    profiles = load_json(PROFILES_FILE)
    companies = load_json(COMPANIES_FILE)

    # Map company details
    company_map = {
        c.get("company_name", "").strip(): {
            "company_website": c.get("website"),
            "company_size": c.get("company_size"),
            "company_linkedin_url": c.get("linkedin_url")
        }
        for c in companies
    }

    merged = []
    for p in profiles:
        company = p.get("company", "").strip()
        details = company_map.get(company, {})
        merged.append({
            "query": p.get("query"),
            "title": p.get("title"),
            "url": p.get("url"),
            "roles": p.get("roles"),
            "company": company,
            "company_website": details.get("company_website"),
            "company_size": details.get("company_size"),
            "company_linkedin_url": details.get("company_linkedin_url")
        })

    # Save JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    # Save CSV
    df = pd.DataFrame(merged)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    print(f"✅ Merged {len(merged)} profiles into '{OUTPUT_JSON}' and '{OUTPUT_CSV}'")

if __name__ == "__main__":
    main()
