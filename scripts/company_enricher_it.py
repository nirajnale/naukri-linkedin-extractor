import os
import json
import time
import requests
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup

# ==============================
# CONFIG
# ==============================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INPUT_FILE = "linkedin_profiles_enriched.json"
OUTPUT_FILE = "companies_classified.json"
PARTIAL_FILE = "companies_classified_partial.json"
SAVE_EVERY = 5  # save partial results after N companies
LIMIT = None  # set for testing

# ==============================
# HELPERS
# ==============================
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def fetch_website_text(url):
    """Fetch website content as plain text."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            texts = soup.stripped_strings
            return " ".join(texts)[:20000]  # limit to 20k chars
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
    return ""

def llm_enrich_company(name, website_text, existing_entry):
    """Call LLM to enrich company details from website."""
    try:
        prompt = {
            "role": "system",
            "content": (
                "You are a company analyst. Given a company name and website content, "
                "return a JSON object (respond only in JSON format) with these fields:\n"
                "- is_it_services: true/false based on website\n"
                "- industry_summary: max 3 words describing the industry\n"
                "- company_summary: exactly 10 words describing the company\n"
                "- technologies_used: list of technologies mentioned in website; if none, infer from summary\n"
                "- company_size: number or estimate (like 51-200)\n"
                "- company_linkedin_url: official LinkedIn URL; null if not found\n"
            )
        }

        user_msg = {
            "role": "user",
            "content": json.dumps({
                "company": name,
                "website_text": website_text or "No website data",
                "existing": existing_entry
            })
        }

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[prompt, user_msg],
            response_format={"type": "json_object"},
            temperature=0
        )
        result = response.choices[0].message.content
        return json.loads(result)

    except Exception as e:
        print(f"❌ LLM enrichment error for {name}: {e}")
        return {
            "is_it_services": None,
            "industry_summary": None,
            "company_summary": None,
            "technologies_used": existing_entry.get("technologies_used", []),
            "company_size": existing_entry.get("company_size"),
            "company_linkedin_url": existing_entry.get("company_linkedin_url")
        }

# ==============================
# MAIN SCRIPT
# ==============================
def main():
    data = load_json(INPUT_FILE)
    print(f"📂 Loaded {len(data)} profiles")

    results = []
    cache = {}  # cache enrichment per website

    for i, entry in enumerate(data, start=1):
        if LIMIT and i > LIMIT:
            break

        company_name = entry.get("company", "")
        website = entry.get("company_website")
        cache_key = website or company_name

        print(f"🔎 Enriching {company_name} ({i}/{len(data)})...")

        # Check cache to avoid duplicate calls
        if cache_key in cache:
            enriched = cache[cache_key]
        else:
            website_text = fetch_website_text(website) if website else ""
            enriched = llm_enrich_company(company_name, website_text, entry)
            cache[cache_key] = enriched
            time.sleep(0.2)  # gentle on requests

        # Update entry, only overwrite null/empty values
        if enriched.get("is_it_services") is not None:
            entry["is_it_services"] = enriched["is_it_services"]
        if enriched.get("industry_summary"):
            entry["industry"] = enriched["industry_summary"]
        if enriched.get("company_summary"):
            entry["company_summary"] = enriched["company_summary"]
        if enriched.get("technologies_used"):
            entry["technologies_used"] = enriched["technologies_used"]
        if not entry.get("company_size") and enriched.get("company_size"):
            entry["company_size"] = enriched["company_size"]
        if not entry.get("company_linkedin_url") and enriched.get("company_linkedin_url"):
            entry["company_linkedin_url"] = enriched["company_linkedin_url"]

        results.append(entry)

        # Partial save
        if i % SAVE_EVERY == 0:
            save_json(PARTIAL_FILE, results)
            print(f"💾 Partial save after {i} companies")

    # Final save
    save_json(OUTPUT_FILE, results)
    print(f"✅ Enrichment complete. Saved {len(results)} companies to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
