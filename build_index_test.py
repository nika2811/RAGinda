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
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
import faiss
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# Import existing modules
from src.product_finder import config
from src.product_finder.utils.data_io import load_categories_from_file
from src.product_finder.utils.async_utils import read_json_async, write_json_async
from src.product_finder.scraping.zoommer_scraper import zommer_scraper_for_urls
from src.product_finder.core_logic.embedding import build_embedding_text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('build_index.log'),
        logging.StreamHandler()
    ]
)
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
            
    async def load_test_urls(self, filepath: str = "test_categories.json") -> List[str]:
        """
        Load test category URLs from JSON file.
        
        Args:
            filepath: Path to the JSON file containing URLs
            
        Returns:
            List of category URLs
        """
        logger.info(f"Loading test URLs from {filepath}...")
        
        try:
            data = await read_json_async(filepath)
            
            urls = data.get('main_category_urls', [])
            
            if not urls:
                raise ValueError("No URLs found in the file")
                
            logger.info(f"Successfully loaded {len(urls)} test URLs")
            return urls
            
        except Exception as e:
            logger.error(f"Failed to load test URLs: {e}")
            raise
            
    async def scrape_from_urls(self, urls: List[str], limit: int = None) -> List[Dict[str, Any]]:
        """
        Scrape products from a list of category URLs.
        
        Args:
            urls: List of category URLs (relative paths)
            limit: Maximum number of URLs to process (for testing)
            
        Returns:
            List of scraped product dictionaries
        """
        logger.info(f"Starting URL-based scraping for {len(urls)} categories...")
        
        # Limit URLs for testing if specified
        if limit:
            urls = urls[:limit]
            logger.info(f"Limited to {limit} URLs for testing")
        
        # Convert relative URLs to subcategory format
        subcategories = []
        for url in urls:
            # Extract category name from URL (remove /category-c123 format)
            category_name = url.replace('/', '').split('-c')[0]
            subcategories.append({
                "name": category_name,
                "url": url
            })
        
        logger.info(f"Converted {len(subcategories)} URLs to subcategory format")
        
        # Run scraping with concurrency control
        start_time = time.time()
        
        try:
            await zommer_scraper_for_urls(subcategories)
            
            # Load scraped products
            products = await read_json_async(config.SCRAPED_DATA_FILE)
                
            scraping_time = time.time() - start_time
            logger.info(f"URL scraping completed in {scraping_time:.2f}s. Found {len(products)} products")
            
            return products
            
        except Exception as e:
            logger.error(f"URL scraping failed: {e}")
            raise
            
    async def scrape_all_products(self, categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Asynchronously scrape products from all categories.
        
        Args:
            categories: List of category configurations
            
        Returns:
            List of scraped product dictionaries
        """
        logger.info("Starting comprehensive product scraping...")
        
        # Extract all subcategories for scraping
        all_subcategories = []
        for category in categories:
            for subcategory in category.get('subcategories', []):
                all_subcategories.append({
                    "name": subcategory.get('subcategory_name'),
                    "url": subcategory.get('subcategory_url')
                })
        
        logger.info(f"Found {len(all_subcategories)} subcategories to scrape")
        
        # Run scraping with concurrency control
        start_time = time.time()
        
        try:
            await zommer_scraper_for_urls(all_subcategories)
            
            # Load scraped products
            products = await read_json_async(config.SCRAPED_DATA_FILE)
                
            scraping_time = time.time() - start_time
            logger.info(f"Scraping completed in {scraping_time:.2f}s. Found {len(products)} products")
            
            return products
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise
            
    async def generate_embeddings_batch(self, products: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Generate embeddings for all products in optimized batches.
        
        Args:
            products: List of product dictionaries
            
        Returns:
            Tuple of (embeddings_matrix, metadata_list)
        """
        logger.info("Generating embeddings for all products...")
        
        if not products:
            logger.warning("No products to embed")
            return np.array([]), []
        
        vectors = []
        metadata = []
        batch_size = 32  # Optimize based on your hardware
        
        # Process products in batches for memory efficiency
        for i in tqdm(range(0, len(products), batch_size), desc="Processing batches"):
            batch = products[i:i + batch_size]
            batch_texts = []
            batch_metadata = []
            
            for product in batch:
                try:
                    # Build embedding text
                    text = build_embedding_text(product)
                    prefixed_text = config.EMBEDDER_PASSAGE_PREFIX + text
                    batch_texts.append(prefixed_text)
                    batch_metadata.append(product)
                    
                except Exception as e:
                    logger.warning(f"Failed to process product {product.get('title', 'Unknown')}: {e}")
                    continue
            
            if batch_texts:
                # Generate embeddings for the batch
                batch_embeddings = await asyncio.to_thread(
                    self.embedding_model.encode,
                    batch_texts,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                
                vectors.extend(batch_embeddings)
                metadata.extend(batch_metadata)
        
        if not vectors:
            logger.error("No valid embeddings generated")
            return np.array([]), []
            
        embeddings_matrix = np.vstack(vectors).astype('float32')
        logger.info(f"Generated {embeddings_matrix.shape[0]} embeddings with {embeddings_matrix.shape[1]} dimensions")
        
        return embeddings_matrix, metadata
        
    async def build_optimized_faiss_index(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        """
        Build and save an optimized FAISS index for fast similarity search.
        
        Args:
            embeddings: Matrix of product embeddings
            metadata: Corresponding product metadata
        """
        logger.info("Building optimized FAISS index...")
        
        if embeddings.size == 0:
            logger.error("Cannot build index from empty embeddings")
            return
            
        n_vectors, dim = embeddings.shape
        logger.info(f"Building index for {n_vectors} vectors of dimension {dim}")
        
        # Choose index type based on dataset size
        if n_vectors < 1000:
            # For small datasets, use flat index
            index = faiss.IndexFlatL2(dim)
            logger.info("Using IndexFlatL2 for small dataset")
        else:
            # For larger datasets, use IVF index for better performance
            nlist = min(100, int(np.sqrt(n_vectors)))  # Number of clusters
            quantizer = faiss.IndexFlatL2(dim)
            index = faiss.IndexIVFFlat(quantizer, dim, nlist)
            
            # Train the index
            logger.info(f"Training IVF index with {nlist} clusters...")
            await asyncio.to_thread(index.train, embeddings)
            logger.info("Using IndexIVFFlat for large dataset")
        
        # Add vectors to index
        logger.info("Adding vectors to index...")
        await asyncio.to_thread(index.add, embeddings)
        
        # Save index and metadata
        logger.info("Saving FAISS index and metadata...")
        await asyncio.to_thread(faiss.write_index, index, config.FAISS_INDEX_FILE)
        
        await write_json_async(config.FAISS_METADATA_FILE, metadata)
            
        logger.info(f"Successfully saved index with {len(metadata)} products")
        
        # Log index statistics
        total_size_mb = (Path(config.FAISS_INDEX_FILE).stat().st_size + 
                        Path(config.FAISS_METADATA_FILE).stat().st_size) / (1024 * 1024)
        logger.info(f"Total index size: {total_size_mb:.2f} MB")
        
    async def run_test_pipeline(self, test_limit: int = 3) -> None:
        """
        Execute a test pipeline with URL-based scraping.
        
        Args:
            test_limit: Number of URLs to test (default: 3)
        """
        pipeline_start = time.time()
        logger.info(f"Starting test pipeline with {test_limit} URLs...")
        
        try:
            # Step 1: Load test URLs
            urls = await self.load_test_urls()
            
            # Step 2: Scrape from test URLs (background job capable)
            products = await self.scrape_from_urls(urls, limit=test_limit)
            
            # Step 3: Generate embeddings (Phase 2: Chunking + Embedding)
            embeddings, metadata = await self.generate_embeddings_batch(products)
            
            # Step 4: Build and save FAISS index
            await self.build_optimized_faiss_index(embeddings, metadata)
            
            pipeline_time = time.time() - pipeline_start
            logger.info(f"Test pipeline completed successfully in {pipeline_time:.2f}s")
            logger.info(f"Processed {len(products)} products from {test_limit} categories")
            
        except Exception as e:
            logger.error(f"Test pipeline failed: {e}")
            raise

    async def run_full_pipeline(self) -> None:
        """
        Execute the complete offline indexing pipeline.
        """
        pipeline_start = time.time()
        logger.info("Starting full offline indexing pipeline...")
        
        try:
            # Step 1: Load categories
            categories = await self.load_categories()
            
            # Step 2: Scrape all products
            products = await self.scrape_all_products(categories)
            
            # Step 3: Generate embeddings
            embeddings, metadata = await self.generate_embeddings_batch(products)
            
            # Step 4: Build and save FAISS index
            await self.build_optimized_faiss_index(embeddings, metadata)
            
            pipeline_time = time.time() - pipeline_start
            logger.info(f"Pipeline completed successfully in {pipeline_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise


async def main():
    """
    Main entry point for the offline indexing pipeline.
    """
    try:
        builder = OfflineIndexBuilder()
        
        # Check if we want to run test pipeline
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "--test":
            test_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            await builder.run_test_pipeline(test_limit)
        else:
            await builder.run_full_pipeline()
        
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}")
        raise


if __name__ == "__main__":
    """
    Run the offline indexing pipeline.
    
    Usage:
        python build_index.py               # Full pipeline
        python build_index.py --test        # Test with 3 URLs
        python build_index.py --test 5      # Test with 5 URLs
        
    Or as a cron job:
        0 2 * * * /usr/bin/python3 /path/to/build_index.py
    """
    asyncio.run(main())
