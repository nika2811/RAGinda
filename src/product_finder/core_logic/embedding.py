# src/product_finder/core_logic/embedding.py
import json
import time
import faiss
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .. import config

# მოდელი იტვირთება ერთხელ და გამოიყენება მრავალჯერ
embedding_model = SentenceTransformer(config.EMBEDDER_MODEL)

def build_embedding_text_improved(product: dict) -> str:
    """
    აუმჯობესებს პროდუქტის ტექსტურ აღწერას ემბედინგისთვის.
    - შლის "ხმაურიან" და ცარიელ მონაცემებს.
    - ქმნის ერთიან, სუფთა ტექსტს.
    - ფასს არ რთავს, რადგან ის სემანტიკური მახასიათებელი არაა.
    """
    if not isinstance(product, dict):
        return ""

    title = product.get('title', '').strip()
    category = product.get('category', '').strip()
    
    text_parts = [f"სათაური: {title}", f"კატეგორია: {category}"]

    specs = product.get('specs', {})
    if isinstance(specs, dict):
        spec_list = []
        for key, value in specs.items():
            # ვამოწმებთ, რომ მნიშვნელობა არ არის ცარიელი ან ტირე
            if isinstance(value, str) and value.strip() and value.strip() != '-':
                cleaned_key = key.strip().replace(':', '')
                spec_list.append(f"{cleaned_key}: {value.strip()}")
        
        if spec_list:
            text_parts.append("მახასიათებლები: " + ", ".join(spec_list))

    description = product.get('description', '').strip()
    if description:
        text_parts.append(f"აღწერა: {description}")

    # ვაერთებთ წერტილით და ჰარით, რაც უკეთესია მოდელისთვის
    return ". ".join(part for part in text_parts if part)

def embed_all_products_batch(products: list) -> Tuple[np.ndarray, List[dict]]:
    """
    ქმნის ემბედინგებს პაკეტურ რეჟიმში (batch processing) მაქსიმალური სისწრაფისთვის.
    """
    if not products:
        return np.array([]), []

    print("ემბედინგისთვის ტექსტების მომზადება მიმდინარეობს...")
    all_texts = [build_embedding_text_improved(p) for p in products]
    
    # ვამატებთ პრეფიქსს ყველა ტექსტს
    prefixed_texts = [config.EMBEDDER_PASSAGE_PREFIX + text for text in all_texts]

    print(f"მიმდინარეობს {len(prefixed_texts)} პროდუქტის ემბედინგი (Batch Mode)...")
    
    start_time = time.time()
    
    # მოდელი მუშაობს ერთხელ მთელ მონაცემთა ბაზაზე!
    embeddings = embedding_model.encode(
        prefixed_texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        batch_size=32  # შეგიძლიათ შეცვალოთ თქვენი აპარატურის მიხედვით
    )
    
    end_time = time.time()
    print(f"✅ ემბედინგი დასრულდა {end_time - start_time:.2f} წამში.")
    
    # ვინაიდან ტექსტები და პროდუქტები იმავე თანმიმდევრობითაა, მეტამონაცემები უცვლელია.
    return embeddings.astype('float32'), products

def build_and_save_faiss_index_optimized(vectors, metadata, index_path=config.FAISS_INDEX_FILE, meta_path=config.FAISS_METADATA_FILE):
    """
    ქმნის ოპტიმიზირებულ FAISS ინდექსს, რომელიც მასშტაბირებადია.
    """
    if vectors.size == 0:
        print("⚠️ ვექტორები ცარიელია. FAISS ინდექსი არ შეიქმნება.")
        return

    n_vectors, dim = vectors.shape
    print(f"მიმდინარეობს ინდექსის აგება {n_vectors} ვექტორისთვის, განზომილება: {dim}")

    # ვირჩევთ ინდექსის ტიპს მონაცემთა რაოდენობის მიხედვით (საუკეთესო პრაქტიკა)
    if n_vectors < 1000:
        index = faiss.IndexFlatL2(dim)
        print("გამოიყენება IndexFlatL2 (მცირე მონაცემებისთვის).")
    else:
        nlist = min(100, int(np.sqrt(n_vectors))) # კლასტერების რაოდენობა
        quantizer = faiss.IndexFlatL2(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, nlist)
        print("გამოიყენება IndexIVFFlat (დიდი მონაცემებისთვის). ინდექსის ვარჯიში...")
        index.train(vectors)
        print("ვარჯიში დასრულდა.")

    index.add(vectors)
    faiss.write_index(index, index_path)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ FAISS ინდექსი და მეტამონაცემები შენახულია. ინდექსშია {index.ntotal} პროდუქტი.")

class SearchService:
    """
    საძიებო სერვისის კლასი, რომელიც იტვირთავს ინდექსს ერთხელ.
    ეს არის სწორი არქიტექტურული პატერნი API-სთვის.
    """
    def __init__(self, index_path=config.FAISS_INDEX_FILE, meta_path=config.FAISS_METADATA_FILE):
        print("საძიებო სერვისის ინიციალიზაცია...")
        try:
            self.index = faiss.read_index(index_path)
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            print(f"✅ ინდექსი ({self.index.ntotal} ვექტორი) და მეტამონაცემები წარმატებით ჩაიტვირთა.")
        except FileNotFoundError:
            self.index = None
            self.metadata = None
            print("❌ საძიებო ფაილები ვერ მოიძებნა. სერვისი ვერ იმუშავებს.")

    def search(self, query_text: str, top_k: int = config.SEARCH_TOP_K) -> List[dict]:
        if not self.index:
            return []

        query_vector = embedding_model.encode(
            config.EMBEDDER_QUERY_PREFIX + query_text
        ).reshape(1, -1).astype('float32')

        _, indices = self.index.search(query_vector, top_k)
        
        # ინდექსი შეიძლება იყოს ცარიელი
        if len(indices[0]) == 0:
            return []
            
        return [self.metadata[i] for i in indices[0]]

# Backward compatibility functions - შენარჩუნება ძველი კოდისთვის
def build_embedding_text(product):
    """Backward compatibility wrapper for existing code."""
    return build_embedding_text_improved(product)

def get_embedding(text, prefix):
    """Backward compatibility wrapper for existing code."""
    return np.array(embedding_model.encode(prefix + text), dtype="float32")

def embed_all_products(products):
    """Backward compatibility wrapper - redirects to optimized batch version."""
    return embed_all_products_batch(products)

def save_faiss_index(vectors, metadata, index_path=config.FAISS_INDEX_FILE, meta_path=config.FAISS_METADATA_FILE):
    """Backward compatibility wrapper - redirects to optimized version."""
    return build_and_save_faiss_index_optimized(vectors, metadata, index_path, meta_path)

def search_similar(query_text, top_k=config.SEARCH_TOP_K, index_path=config.FAISS_INDEX_FILE, meta_path=config.FAISS_METADATA_FILE):
    """Backward compatibility wrapper - creates temporary SearchService."""
    service = SearchService(index_path, meta_path)
    return service.search(query_text, top_k)