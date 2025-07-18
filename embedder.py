import os
import json
import faiss
import numpy as np
import google.generativeai as genai
from tqdm import tqdm

# Configure Gemini Pro Embeddings
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # Set this in your .env or shell

# Create Gemini model
embedding_model = genai.GenerativeModel('embedding-001')  # Georgian support is decent


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


def get_gemini_embedding(text):
    response = embedding_model.embed_content(
        content=text,
        task_type="RETRIEVAL_DOCUMENT",
        title="პროდუქტის აღწერა",
    )
    return np.array(response["embedding"], dtype="float32")


def embed_all_products(products):
    vectors = []
    metadata = []

    for p in tqdm(products, desc="📦 ემბედინგი მიმდინარეობს"):
        try:
            text = build_embedding_text(p)
            emb = get_gemini_embedding(text)
            vectors.append(emb)
            metadata.append(p)
        except Exception as e:
            print(f"❌ შეცდომა ემბედინგზე {p.get('title')}: {e}")

    return np.vstack(vectors), metadata


def save_faiss_index(vectors, metadata, index_path="output/index.faiss", meta_path="output/metadata.json"):
    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)
    faiss.write_index(index, index_path)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ შენახულია {len(metadata)} პროდუქტი")


def search_similar(query_text, top_k=5, index_path="output/index.faiss", meta_path="output/metadata.json"):
    query_vector = get_gemini_embedding(query_text).reshape(1, -1)
    index = faiss.read_index(index_path)

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    distances, indices = index.search(query_vector, top_k)
    results = [metadata[i] for i in indices[0]]

    return results


# Example runner
if __name__ == "__main__":
    products = load_products("output/zoommer_scraping.json")
    vectors, metadata = embed_all_products(products)
    save_faiss_index(vectors, metadata)

    print("\n🔍 მაგალითი ძიება:")
    query = "სმარტ საათი, დიდი ბატარიით და NFC-ით"
    results = search_similar(query)

    for r in results:
        print(f"- {r['title']} | {r['price']} ლარი | {r['category']}")