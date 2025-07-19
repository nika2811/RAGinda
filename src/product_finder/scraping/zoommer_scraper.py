# src/product_finder/scraping/zoommer_scraper.py

import json
import os
import time
import asyncio
from playwright.async_api import async_playwright, Browser

# ყურადღება: იმპორტები სწორია ახალი სტრუქტურისთვის
from .. import config
from .utils import ScrapingStats, clean_price

# --- სრული კოდი crawl_product_detail ფუნქციისთვის ---
async def crawl_product_detail(browser: Browser, url: str, stats: ScrapingStats):
    start_time = time.perf_counter()
    page = await browser.new_page()
    try:
        await page.route("**/*.{png,jpg,jpeg,webp,css,woff2}", lambda route: route.abort())
        await page.goto(url, timeout=config.SCRAPER_PAGE_TIMEOUT, wait_until='domcontentloaded')

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
        print(f"❌ დეტალური გვერდის {url} სკრეიპინგი ჩაიშალა: {e}")
        await page.close()
        return {}

# --- სრული კოდი crawl_category ფუნქციისთვის ---
async def crawl_category(browser: Browser, category_name: str, relative_url: str, stats: ScrapingStats):
    start_time = time.perf_counter()
    page = await browser.new_page()
    products_base_info = []

    for page_num in range(1, config.SCRAPER_MAX_PAGES_PER_CATEGORY + 1):
        url = f"{config.WEBSITE_BASE_URL}{relative_url}?page={page_num}"
        print(f"🔎 იტვირთება კატეგორიის გვერდი: {url}")
        try:
            await page.goto(url, timeout=config.SCRAPER_PAGE_TIMEOUT, wait_until='domcontentloaded')
            await page.wait_for_selector(".sc-1a03f073-0", timeout=config.SCRAPER_SELECTOR_TIMEOUT)
        except Exception as e:
            print(f"⚠️ გვერდის ჩატვირთვა ვერ მოხერხდა {page_num}: {e}. გადავდივარ შემდეგზე.")
            break

        cards = await page.query_selector_all(".sc-1a03f073-0")
        if not cards:
            print(f"⚠️ პროდუქტები ვერ მოიძებნა გვერდზე {page_num}. ამ კატეგორიის სკრეიპინგი დასრულებულია.")
            break

        for card in cards:
            title_el = await card.query_selector(".sc-1a03f073-11")
            title = (await title_el.inner_text()).strip() if title_el else "N/A"
            link = config.WEBSITE_BASE_URL + await title_el.get_attribute("href") if title_el else ""

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
        print(f"🔗 ნაპოვნია {len(products_base_info)} პროდუქტის ლინკი. დეტალების მოთხოვნა კონკურენტულად...")
        
        semaphore = asyncio.Semaphore(config.SCRAPER_CONCURRENT_REQUESTS)
        
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

# --- სრული კოდი zommer_scraper_for_urls ფუნქციისთვის ---
async def zommer_scraper_for_urls(subcategories):
    all_products = []
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    
    stats = ScrapingStats()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        for subcat in subcategories:
            print(f"\n📦 სკრეიპინგი: {subcat['name']}")
            items = await crawl_category(browser, subcat['name'], subcat['url'], stats)
            all_products.extend(items)
        await browser.close()

    stats.finalize(len(all_products))
    stats.report()

    # Return products directly instead of writing to file
    print(f"\n✅ სკრეიპინგი დასრულდა: {len(all_products)} პროდუქტი")
    return all_products