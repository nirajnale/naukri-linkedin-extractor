import json
import re

INPUT_FILE = "linkedin_results.json"
OUTPUT_FILE = "linkedin_results_cleaned.json"

def clean_profiles():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    seen_urls = {}
    cleaned = []

    for entry in data:
        url = entry["url"]
        role = entry["role"]
        company = entry["company"].lower()
        title = entry["title"].lower()

        # ✅ Relevance check: role or company name must be in title
        if role.lower() not in title and company not in title:
            continue

        if url in seen_urls:
            # Merge roles if same person shows in multiple searches
            seen_urls[url]["roles"].add(role)
        else:
            seen_urls[url] = {
                "query": entry["query"],
                "company": entry["company"],
                "url": entry["url"],
                "title": entry["title"],
                "roles": {role}
            }

    # Flatten roles into comma-separated string
    for v in seen_urls.values():
        v["roles"] = ", ".join(sorted(v["roles"]))
        cleaned.append(v)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)

    print(f"✅ Cleaned {len(cleaned)} unique profiles (from {len(data)} raw results).")
    print(f"📂 Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    clean_profiles()
