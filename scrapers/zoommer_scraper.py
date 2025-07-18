import json
import os
import time
import asyncio
import numpy as np
from playwright.async_api import async_playwright, Browser

BASE_URL = "https://zoommer.ge"
OUTPUT_PATH = "output/zoommer_scraping.json"
MAX_PAGES = 1
CONCURRENT_DETAILS_LIMIT = 10


class ScrapingStats:
    """A class to hold and report scraping performance statistics."""

    def __init__(self):
        self.total_start_time = time.perf_counter()
        self.total_duration = 0
        self.total_products = 0
        self.total_categories = 0
        self.category_times = []
        self.detail_page_times = []

    def add_detail_page_time(self, duration: float):
        self.detail_page_times.append(duration)

    def add_category_snapshot(self, name: str, duration: float, product_count: int):
        self.category_times.append({"name": name, "duration": duration, "products": product_count})
        self.total_categories += 1

    def finalize(self, total_products: int):
        self.total_duration = time.perf_counter() - self.total_start_time
        self.total_products = total_products

    def report(self):

        print("\n" + "="*50)
        print("📊 სკრეიპინგის პერფორმანსის რეპორტი 📊")
        print("="*50)

        if not self.total_products:
            print("პროდუქტები ვერ მოიძებნა. რეპორტი ცარიელია.")
            print(f"საერთო დრო: {self.total_duration:.2f} წამი")
            return
        products_per_second = self.total_products / self.total_duration if self.total_duration > 0 else 0
        print(f"⏱️ საერთო დრო: {self.total_duration:.2f} წამი")
        print(f"🗃️ დამუშავებული კატეგორია: {self.total_categories}")
        print(f"📦 ჯამური პროდუქტი: {self.total_products}")
        print(f"🚀 საშუალო წარმადობა: {products_per_second:.2f} პროდუქტი/წამში")
        print("-" * 50)
        print("\n🕒 კატეგორიების მიხედვით:")
        for cat in sorted(self.category_times, key=lambda x: x['duration'], reverse=True):
            print(f"  - {cat['name']} ({cat['products']} პროდ.): {cat['duration']:.2f} წამი")
        if self.detail_page_times:
            avg_detail_time = np.mean(self.detail_page_times)
            min_detail_time = np.min(self.detail_page_times)
            max_detail_time = np.max(self.detail_page_times)

            print("\n" + "-"*50)

            print("📄 პროდუქტის დეტალური გვერდის დამუშავება:")
            print(f"  - საშუალო დრო: {avg_detail_time:.2f} წამი")
            print(f"  - უსწრაფესი: {min_detail_time:.2f} წამი")
            print(f"  - უნელესი: {max_detail_time:.2f} წამი")

        print("="*50)


def clean_price(price_text):
    return float(price_text.replace("₾", "").replace(",", "").strip())


async def crawl_product_detail(browser: Browser, url: str, stats: ScrapingStats):
    start_time = time.perf_counter()
    page = await browser.new_page()
    try:
        await page.route("**/*.{png,jpg,jpeg,webp,css,woff2}", lambda route: route.abort())
        await page.goto(url, timeout=60000, wait_until='domcontentloaded')

        title_el = await page.query_selector("h1")
        title = (await title_el.inner_text()).strip() if title_el else ""

        desc_el = await page.query_selector("div.description_block")
        desc = (await desc_el.inner_text()).strip() if desc_el else ""

        specs = {}
        container = await page.query_selector("#product-specifications")
        if container:
            tables = await container.query_selector_all("table")
            for table in tables:
                rows = await table.query_selector_all("tr")
                for row in rows:
                    cells = await row.query_selector_all("td")
                    if len(cells) == 2:
                        key_el = await cells[0].query_selector("h4")
                        val_el = await cells[1].query_selector("h4")
                        key = (await key_el.inner_text()).strip() if key_el else ""
                        val = (await val_el.inner_text()).strip() if val_el else ""
                        if key and val:
                            specs[key] = val



        duration = time.perf_counter() - start_time
        stats.add_detail_page_time(duration)
        await page.close()
        return {
            "product_title_detail": title,
            "description": desc,
            "specs": specs
        }
    except Exception as e:
        print(f"❌ Failed to crawl detail page {url}: {e}")
        await page.close()
        return {}


async def crawl_category(browser: Browser, category_name: str, relative_url: str, stats: ScrapingStats):
    start_time = time.perf_counter()
    page = await browser.new_page()
    products_base_info = []

    for page_num in range(1, MAX_PAGES + 1):
        url = f"{BASE_URL}{relative_url}?page={page_num}"
        print(f"🔎 Loading category page {url}")
        try:
            await page.goto(url, timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_selector(".sc-1a03f073-0", timeout=10000)
        except Exception as e:
            print(f"⚠️ Could not load or find products on page {page_num}: {e}. Moving on.")
            break

        cards = await page.query_selector_all(".sc-1a03f073-0")
        if not cards:
            print(f"⚠️ No product cards found on page {page_num}. Ending crawl for this category.")
            break

        for card in cards:
            title_el = await card.query_selector(".sc-1a03f073-11")
            title = (await title_el.inner_text()).strip() if title_el else "N/A"
            link = BASE_URL + await title_el.get_attribute("href") if title_el else ""


            price_el = await card.query_selector(".sc-1a03f073-8")
            price_text = await price_el.inner_text() if price_el else "0"
            price = clean_price(price_text)

            img_el = await card.query_selector("img.sc-1a03f073-3")
            img = await img_el.get_attribute("src") if img_el else ""
            
            if link:
                products_base_info.append({"category": category_name, "title": title, "price": price, "link": link, "image": img})

    await page.close()
    
    final_products = []
    if products_base_info:
        print(f"🔗 Found {len(products_base_info)} product links. Fetching details concurrently...")
        
        semaphore = asyncio.Semaphore(CONCURRENT_DETAILS_LIMIT)
        

        async def fetch_with_semaphore(prod_info):
            async with semaphore:
                detail_data = await crawl_product_detail(browser, prod_info['link'], stats)
                return {**prod_info, **detail_data}

        tasks = [fetch_with_semaphore(prod) for prod in products_base_info]
        results = await asyncio.gather(*tasks)
        final_products.extend(results)

    duration = time.perf_counter() - start_time
    stats.add_category_snapshot(category_name, duration, len(final_products))
    return final_products


async def zommer_scraper_for_urls(subcategories):
    all_products = []
    os.makedirs("output", exist_ok=True)
    
    stats = ScrapingStats()


    stats = ScrapingStats()


    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        for subcat in subcategories:
            print(f"\n📦 Crawling: {subcat['name']}")
            items = await crawl_category(browser, subcat['name'], subcat['url'], stats)
            all_products.extend(items)
        await browser.close()

    stats.finalize(len(all_products))
    stats.report()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(all_products)} products to {OUTPUT_PATH}")