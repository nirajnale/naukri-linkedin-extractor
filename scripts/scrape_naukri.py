import asyncio
from playwright.async_api import async_playwright
import csv
import re
import urllib.parse

SEARCH_QUERY = "Lead Generation"
LOCATION = "India"
MAX_PAGES = 50

COMPANY_SUFFIXES = ["Pvt Ltd", "Ltd", "Limited", "Services", "Solutions", 
                    "Technologies", "Group", "Enterprises", "India"]
JUNK_COMPANY_KEYWORDS = ["Years", "Confidential", "Unknown"]

def clean_company_name(name: str) -> str:
    if not name:
        return "Unknown"
    name = name.strip()
    for suf in COMPANY_SUFFIXES:
        name = re.sub(rf'\b{suf}\b', '', name, flags=re.I).strip()
    if not name or any(j.lower() in name.lower() for j in JUNK_COMPANY_KEYWORDS):
        return "Unknown"
    return re.sub(r'\s+', ' ', name)

def extract_company_from_link(link: str) -> str:
    if not link:
        return "Unknown"
    try:
        parts = urllib.parse.urlparse(link).path.split("-")
        if len(parts) > 3:
            company_parts = parts[2:-3]
            company = " ".join(company_parts).title()
            return clean_company_name(company)
    except:
        return "Unknown"
    return "Unknown"

async def scrape_naukri():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        all_jobs = []

        for page_number in range(1, MAX_PAGES + 1):
            url = f"https://www.naukri.com/{SEARCH_QUERY.lower().replace(' ','-')}-jobs-in-{LOCATION.lower()}-{page_number}"
            print(f"🌐 Scraping page: {url}")
            await page.goto(url, wait_until="networkidle")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            jobs = await page.query_selector_all(".jobTuple, .cust-job-tuple")
            if not jobs:
                print(f"⚠️ No jobs found on page {page_number}.")
                continue

            for job in jobs:
                # Title and link
                title_el = await job.query_selector("a.title")
                title = await title_el.inner_text() if title_el else ""
                link = await title_el.get_attribute("href") if title_el else ""

                # Location
                location_el = await job.query_selector(".locWdth, .location")
                location = await location_el.inner_text() if location_el else ""

                # Company extraction
                company = ""
                if link:
                    try:
                        detail_page = await browser.new_page()
                        await detail_page.goto(link, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(1)

                        about_selectors = [
                            "section.about-company",
                            ".job-desc-about-company",
                            ".jd-header-comp-name",
                            "div.aboutCompany div:nth-child(1)"
                        ]

                        about_text = ""
                        for sel in about_selectors:
                            el = await detail_page.query_selector(sel)
                            if el:
                                about_text = await el.inner_text()
                                if about_text.strip():
                                    break

                        if about_text:
                            company_line = about_text.strip().split("\n")[0]
                            company = company_line.strip()
                        await detail_page.close()
                    except Exception as e:
                        print(f"⚠️ Could not load detail page {link}: {e}")

                # Fallback to job card or URL
                if not company or any(j.lower() in company.lower() for j in JUNK_COMPANY_KEYWORDS):
                    company_el = await job.query_selector(".company a, .company span, .subTitle, .jd-header-comp-name")
                    company = await company_el.inner_text() if company_el else ""
                    company = re.sub(r'(\d+|years|yrs|0 to \d+)', '', company, flags=re.I).strip()
                    if not company or any(j.lower() in company.lower() for j in JUNK_COMPANY_KEYWORDS):
                        company = extract_company_from_link(link)

                company = clean_company_name(company)

                # Skip duplicates
                if any(j["link"] == link for j in all_jobs):
                    continue

                all_jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": location.strip(),
                    "link": link
                })

        await browser.close()

        # Save to CSV (without posted column)
        with open("naukri_jobs.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title","company","location","link"])
            writer.writeheader()
            writer.writerows(all_jobs)

        print(f"✅ Saved {len(all_jobs)} jobs to CSV")

if __name__ == "__main__":
    asyncio.run(scrape_naukri())
