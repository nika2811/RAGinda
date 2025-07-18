# embedder.py

import os
import json
import faiss
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import config # Import the configuration file

# Use config for model name
embedding_model = SentenceTransformer(config.EMBEDDER_MODEL)

def load_products(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_embedding_text(product):
    specs = product.get("specs", {})
    spec_str = ", ".join(f"{k.strip()}: {v}" for k, v in specs.items())
    return f"""
სათაური: {product.get('title')}
კატეგორია: {product.get('category')}
ფასი: {product.get('price')} ლარი
მახასიათებლები: {spec_str}
აღწერა: {product.get('description', '')}
    """

def get_embedding(text):
    # Use config for model-specific prefix
    return np.array(embedding_model.encode(config.EMBEDDER_PASSAGE_PREFIX + text), dtype="float32")

def embed_all_products(products):
    vectors = []
    metadata = []

    for p in tqdm(products, desc="📦 ემბედინგი მიმდინარეობს"):
        try:
            text = build_embedding_text(p)
            emb = get_embedding(text)
            vectors.append(emb)
            metadata.append(p)
        except Exception as e:
            print(f"❌ შეცდომა ემბედინგზე {p.get('title')}: {e}")

    return np.vstack(vectors), metadata

# Use config for default file paths
def save_faiss_index(vectors, metadata, index_path=config.FAISS_INDEX_FILE, meta_path=config.FAISS_METADATA_FILE):
    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)
    faiss.write_index(index, index_path)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ შენახულია {len(metadata)} პროდუქტი")

# Use config for default parameters and paths
def search_similar(query_text, top_k=config.SEARCH_TOP_K, index_path=config.FAISS_INDEX_FILE, meta_path=config.FAISS_METADATA_FILE):
    # Use config for model-specific prefix
    query_vector = get_embedding(config.EMBEDDER_QUERY_PREFIX + query_text).reshape(1, -1)
    index = faiss.read_index(index_path)

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    distances, indices = index.search(query_vector, top_k)
    results = [metadata[i] for i in indices[0]]

    return results

# Example runner
if __name__ == "__main__":
    # Use config for file path
    products = load_products(config.SCRAPED_DATA_FILE)
    vectors, metadata = embed_all_products(products)
    save_faiss_index(vectors, metadata)

    print("\n🔍 მაგალითი ძიება:")
    query = "სმარტ საათი, დიდი ბატარიით და NFC-ით"
    results = search_similar(query)

    for r in results:
        print(f"- {r['title']} | {r['price']} ლარი | {r['category']}")