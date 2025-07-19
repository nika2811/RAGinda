#!/usr/bin/env python3
"""
Offline Indexing Pipeline (build_index.py)

This script is designed to be run periodically (e.g., daily via cron job) 
to prepare all data in advance for fast online serving.

Features:
- Asynchronous scraping of all product categories
- Batch embedding generation with optimized FAISS index
- Saves pre-computed artifacts for instant API responses
"""

import asyncio
import time
import logging
import argparse  # REFACTOR: Using argparse for a better CLI
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
import faiss
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

from src.product_finder import config
from src.product_finder.utils.data_io import load_categories_from_file
from src.product_finder.utils.async_utils import write_json_async, read_json_async
# REFACTOR: Scraper now returns data directly, not writing to a file inside its own logic
from src.product_finder.scraping.zoommer_scraper import zommer_scraper_for_urls
from src.product_finder.core_logic.embedding import build_embedding_text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("build_index.log"), logging.StreamHandler()])
logger = logging.getLogger(__name__)


class OfflineIndexBuilder:
    """
    Handles the complete offline indexing pipeline for product search system.
    """
    
    def __init__(self):
        """Initialize the index builder with necessary models and configurations."""
        logger.info("Initializing OfflineIndexBuilder...")
        
        # Load embedding model
        self.embedding_model = SentenceTransformer(config.EMBEDDER_MODEL)
        logger.info(f"Loaded embedding model: {config.EMBEDDER_MODEL}")
        
        # Ensure output directory exists
        Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
    async def load_categories(self) -> List[Dict[str, Any]]:
        """
        Load product categories from configuration file.
        
        Returns:
            List of category dictionaries
            
        Raises:
            FileNotFoundError: If categories file doesn't exist
            ValueError: If categories file is empty or invalid
        """
        logger.info("Loading product categories...")
        
        try:
            categories = await asyncio.to_thread(
                load_categories_from_file, 
                config.CATEGORIES_FILE
            )
            
            if not categories:
                raise ValueError("Categories file is empty or invalid")
                
            logger.info(f"Successfully loaded {len(categories)} categories")
            return categories
            
        except Exception as e:
            logger.error(f"Failed to load categories: {e}")
            raise
            
    # REFACTOR: Consolidated scraping logic into a single method.
    async def scrape_products(self, categories: List[Dict[str, Any]], test_limit: int = 0) -> List[Dict[str, Any]]:
        """Asynchronously scrapes products from specified categories."""
        all_subcategories = []
        for category in categories:
            for subcategory in category.get('subcategories', []):
                all_subcategories.append({
                    "name": subcategory.get('subcategory_name'),
                    "url": subcategory.get('subcategory_url')
                })
        
        if test_limit > 0:
            logger.info(f"Running in test mode, limiting to {test_limit} categories.")
            all_subcategories = all_subcategories[:test_limit]

        if not all_subcategories:
            logger.warning("No subcategories found to scrape.")
            return []

        logger.info(f"Starting scraping for {len(all_subcategories)} subcategories...")
        start_time = time.time()
        
        # REFACTOR: Scraper now returns products directly. No intermediate file I/O.
        products = await zommer_scraper_for_urls(all_subcategories)
        
        scraping_time = time.time() - start_time
        logger.info(f"Scraping completed in {scraping_time:.2f}s. Found {len(products)} products.")
        return products
    async def generate_embeddings_batch(self, products: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """Generates embeddings for all products in optimized batches."""
        logger.info("Generating embeddings...")
        if not products:
            logger.warning("No products to embed.")
            return np.array([]), []

        batch_size = config.PIPELINE_EMBEDDING_BATCH_SIZE
        texts_to_embed = [config.EMBEDDER_PASSAGE_PREFIX + build_embedding_text(p) for p in products]

        # Use the model's built-in batch processing
        embeddings = await asyncio.to_thread(
            self.embedding_model.encode,
            texts_to_embed,
            show_progress_bar=True,
            convert_to_numpy=True,
            batch_size=batch_size
        )
        embeddings_matrix = embeddings.astype('float32')
        logger.info(f"Generated {embeddings_matrix.shape[0]} embeddings with {embeddings_matrix.shape[1]} dimensions.")
        return embeddings_matrix, products  # Metadata is just the product list itself
    async def build_optimized_faiss_index(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]):
        """Builds and saves an optimized FAISS index."""
        logger.info("Building optimized FAISS index...")
        if embeddings.size == 0:
            logger.error("Cannot build index from empty embeddings.")
            return

        n_vectors, dim = embeddings.shape
        nlist = min(100, int(np.sqrt(n_vectors)))
        quantizer = faiss.IndexFlatL2(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, nlist) if n_vectors >= 1000 else faiss.IndexFlatL2(dim)

        logger.info(f"Using {'IndexIVFFlat' if n_vectors >= 1000 else 'IndexFlatL2'} for {n_vectors} vectors.")
        if isinstance(index, faiss.IndexIVFFlat):
            await asyncio.to_thread(index.train, embeddings)

        await asyncio.to_thread(index.add, embeddings)
        logger.info("Adding vectors to index completed.")

        # Save index and metadata in parallel
        save_index_task = asyncio.to_thread(faiss.write_index, index, config.FAISS_INDEX_FILE)
        save_meta_task = write_json_async(config.FAISS_METADATA_FILE, metadata)
        await asyncio.gather(save_index_task, save_meta_task)
        logger.info(f"Successfully saved FAISS index and metadata for {len(metadata)} products.")

    async def run_pipeline(self, test_limit: int = 0):
        """Executes the complete offline indexing pipeline."""
        pipeline_start = time.time()
        mode = "TEST" if test_limit > 0 else "FULL"
        logger.info(f"--- Starting {mode} offline indexing pipeline ---")
        
        try:
            categories = await asyncio.to_thread(load_categories_from_file, config.CATEGORIES_FILE)
            if not categories:
                raise ValueError("Categories file is empty or invalid.")

            products = await self.scrape_products(categories, test_limit)
            embeddings, metadata = await self.generate_embeddings_batch(products)
            await self.build_optimized_faiss_index(embeddings, metadata)
            
            pipeline_time = time.time() - pipeline_start
            logger.info(f"--- {mode} pipeline completed successfully in {pipeline_time:.2f}s ---")
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise

async def main():
    # REFACTOR: Using argparse for proper command-line argument handling
    parser = argparse.ArgumentParser(description="Offline Indexing Pipeline for AI Product Search.")
    parser.add_argument(
        "--test",
        type=int,
        nargs='?',
        const=3,  # Default value if --test is provided without a number
        default=0,
        help="Run in test mode, limiting to a number of categories. Defaults to 3 if no number is given."
    )
    args = parser.parse_args()

    try:
        builder = OfflineIndexBuilder()
        await builder.run_pipeline(test_limit=args.test)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user.")
    except Exception as e:
        logger.error(f"Pipeline failed with unhandled error: {e}")
        # Exit with a non-zero status code to indicate failure for cron jobs etc.
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
