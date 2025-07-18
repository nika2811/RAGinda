import json
import os
from playwright.sync_api import sync_playwright

BASE_URL = "https://zoommer.ge"
OUTPUT_PATH = "output/zoommer_scraping.json"
MAX_PAGES = 1

def clean_price(price_text):
    return float(price_text.replace("₾", "").replace(",", "").strip())

def crawl_product_detail(page, url):
    try:
        page.goto(url, timeout=60000)
        page.wait_for_selector("body", timeout=10000)

        title = page.query_selector("h1")
        title = title.inner_text().strip() if title else ""

        desc_el = page.query_selector("div:has-text('აღწერა')")
        desc = desc_el.inner_text().strip() if desc_el else ""

        specs = {}
        container = page.query_selector("#product-specifications")
        if container:
            tables = container.query_selector_all("table")
            for table in tables:
                rows = table.query_selector_all("tr")
                for row in rows:
                    cells = row.query_selector_all("td")
                    if len(cells) == 2:
                        key_el = cells[0].query_selector("h4")
                        val_el = cells[1].query_selector("h4")
                        key = key_el.inner_text().strip() if key_el else ""
                        val = val_el.inner_text().strip() if val_el else ""
                        if key and val:
                            specs[key] = val

        return {
            "product_title_detail": title,
            "description": desc,
            "specs": specs
        }

    except Exception as e:
        print(f"❌ Failed to crawl detail page {url}: {e}")
        return {}

def crawl_category(playwright, category_name, relative_url):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    detail_page = browser.new_page()
    products = []

    for page_num in range(1, MAX_PAGES + 1):
        url = f"{BASE_URL}{relative_url}?page={page_num}"
        print(f"🔎 Loading {url}")
        page.goto(url, timeout=60000)

        try:
            page.wait_for_selector(".sc-1a03f073-0", timeout=10000)
        except:
            print("⚠️ Timeout waiting for products")
            continue

        cards = page.query_selector_all(".sc-1a03f073-0")
        if not cards:
            print("⚠️ No product cards found")
            break

        for card in cards:
            try:
                title_el = card.query_selector(".sc-1a03f073-11")
                title = title_el.inner_text().strip() if title_el else "N/A"
                link = BASE_URL + title_el.get_attribute("href") if title_el else ""

                price_el = card.query_selector(".sc-1a03f073-8")
                price_text = price_el.inner_text().strip() if price_el else "0"
                price = clean_price(price_text)

                img_el = card.query_selector("img.sc-1a03f073-3")
                img = img_el.get_attribute("src") if img_el else ""

                detail_data = crawl_product_detail(detail_page, link)

                products.append({
                    "category": category_name,
                    "title": title,
                    "price": price,
                    "link": link,
                    "image": img,
                    **detail_data
                })

            except Exception as e:
                print(f"❌ Error parsing product card: {e}")
                continue

        page.wait_for_timeout(1500)

    browser.close()
    return products

# 🆕 Exposed function to call from main.py
def zommer_scraper_for_urls(subcategories):
    all_products = []
    os.makedirs("output", exist_ok=True)

    with sync_playwright() as playwright:
        for subcat in subcategories:
            print(f"\n📦 Crawling: {subcat['name']}")
            items = crawl_category(playwright, subcat['name'], subcat['url'])
            all_products.extend(items)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(all_products)} products to {OUTPUT_PATH}")