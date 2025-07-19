# src/product_finder/scraping/utils.py
import time
import numpy as np

class ScrapingStats:
    # ... (class content remains unchanged, exactly as it was) ...
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
            print("პროდუქტები ვერ მოიძებნა. რეპორტი ჩაიშალა.")
            print(f"საერთო დრო: {self.total_duration:.2f} წამი")
            return
        products_per_second = self.total_products / self.total_duration if self.total_duration > 0 else 0
        print(f"⏱️ საერთო დრო: {self.total_duration:.2f} წამი")
        print(f"🗃️ დამუშავებული კატეგორია: {self.total_categories}")
        print(f"📦 ჯამური პროდუქტი: {self.total_products}")
        print(f"🚀 საშუალო დამუშავება: {products_per_second:.2f} პროდუქტი/წამში")
        print("-" * 50)
        print("\n🕒 კატეგორიების მიხედვით:")
        for cat in sorted(self.category_times, key=lambda x: x['duration'], reverse=True):
            print(f"  - {cat['name']} ({cat['products']} პროდ.): {cat['duration']:.2f} წამი")
        if self.detail_page_times:
            avg_detail_time = np.mean(self.detail_page_times)
            min_detail_time = np.min(self.detail_page_times)
            max_detail_time = np.max(self.detail_page_times)

            print("\n" + "-"*50)

            print("📄 პროდუქტის დეტალური გვეშის მონაცემები:")
            print(f"  - საშუალო დრო: {avg_detail_time:.2f} წამი")
            print(f"  - უსწრაფესი: {min_detail_time:.2f} წამი")
            print(f"  - უმელესი: {max_detail_time:.2f} წამი")

        print("="*50)


def clean_price(price_text):
    return float(price_text.replace("₾", "").replace(",", "").strip())