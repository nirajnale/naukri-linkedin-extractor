import csv
import re

INPUT_FILE = "naukri_jobs.csv"
OUTPUT_FILE = "naukri_jobs_clean.csv"

CITY_PATTERNS = [
    "Mumbai", "Navi Mumbai", "Thane", "Pune", "Delhi", "Noida", "Gurgaon",
    "Gurugram", "Hyderabad", "Bangalore", "Bengaluru", "Chennai", "Kolkata",
    "Lucknow", "Bhubaneswar", "Ahmedabad", "Indore", "Jaipur", "Nagpur", "Surat",
    "Chandigarh", "Ambala", "Vadodara", "Coimbatore", "Ranchi", "Gandhinagar",
    "Turbhe", "Delhi Ncr", "Delhi / Ncr"
]

JUNK_KEYWORDS = [
    "Hiring", "Urgent", "Executive", "Specialist", "Associate", "Manager",
    "Lead Generation", "Process", "Sales", "Voice", "Business Development",
    "Telesales", "Internship", "Freshers", "Software Inside"
]

LEFTOVER_FRAGMENTS = ["Navi", "Ncr", "All Areas", "Hybrid", "Remote"]

def clean_company_name(company_raw, job_title=None):
    if not company_raw:
        return "Unknown"

    text = company_raw.strip()

    if job_title:
        text = re.sub(re.escape(job_title), "", text, flags=re.IGNORECASE)

    for kw in JUNK_KEYWORDS:
        text = re.sub(rf"\b{kw}\b", "", text, flags=re.IGNORECASE)

    for city in CITY_PATTERNS:
        text = re.sub(rf"\b{re.escape(city)}\b", "", text, flags=re.IGNORECASE)

    for frag in LEFTOVER_FRAGMENTS:
        text = re.sub(rf"\b{frag}\b", "", text, flags=re.IGNORECASE)

    text = re.sub(r"\b\d+\s*To\s*(\d+)?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\s*-\s*.*$", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    return text if text else "Unknown"

def clean_location(location_raw):
    if not location_raw:
        return "Unknown"
    # Remove parentheses and extra spaces
    text = re.sub(r"\(.*?\)", "", location_raw).strip()
    # Collapse multiple commas/spaces
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r",\s*,", ",", text)
    return text if text else "Unknown"

with open(INPUT_FILE, newline="", encoding="utf-8") as infile, \
     open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as outfile:

    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        row["company"] = clean_company_name(
            row.get("company", ""),
            job_title=row.get("title", "")
        )
        row["location"] = clean_location(row.get("location", ""))
        writer.writerow(row)

print(f"✅ Final cleaned CSV saved to {OUTPUT_FILE}")
