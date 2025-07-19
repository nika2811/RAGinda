# AI-Powered Product Search System (RAGinda)

ზღვარდაუკვეთ მაღალი წარმადობის მქონე ორ-ნაწილიანი AI-powered e-commerce პროდუქტების ძიების სისტემა, რომელიც იყენებს FastAPI, FAISS ვექტორულ ბაზას და semantic embeddings-ს.

## 🏗️ არქიტექტურის მიმოხილვა

სისტემა დაყოფილია ორ მთავარ კომპონენტად:

1. **Offline Indexing Pipeline** (`build_index.py`) - პერიოდულად მუშაობს მონაცემების მომზადებისთვის
2. **Online Serving API** (`server.py`) - რეალურ დროში უზრუნველყოფს ძიებას millisecond-level response time-ით

### 🔄 სამუშაო პრინციპი

```
📊 ფაზა 1: Offline Data Preparation
scraping → embedding generation → FAISS index building → metadata storage

⚡ ფაზა 2: Online Search Serving  
user query → vector search + category LLM → result fusion → response
```

## ✨ ფუნქციები

- 🚀 **მაღალი წარმადობა**: millisecond response times pre-built indexes-ით
- 🔍 **Semantic Search**: გაუმჯობესებული similarity search sentence transformers-ით
- 🧠 **AI-Enhanced**: LLM-გაძლიერებული კატეგორიების შერჩევა Gemini API-ით
- 📊 **მასშტაბირებადი**: ოპტიმიზებული FAISS indexes დიდი product catalogs-ისთვის
- 🔄 **Async Architecture**: asyncio-ზე აგებული მაღალი concurrency-სთვის
- 📱 **API-First**: RESTful API OpenAPI დოკუმენტაციით
- 🐳 **კონტეინერიზებული**: Docker support მარტივი deployment-ისთვის
- 🌍 **მრავალენოვანი**: ქართული და ინგლისური ენების მხარდაჭერა

## 🚀 სწრაფი დაწყება

### 1. ინსტალაცია

```bash
# Repository-ის კლონირება
git clone https://github.com/nika2811/RAGinda.git
cd RAGinda

# Dependencies-ების ინსტალაცია
pip install -r requirements.txt

# Playwright browsers-ების ინსტალაცია (scraping-ისთვის)
playwright install chromium
```

### 2. კონფიგურაცია

შექმენით `.env` ფაილი project root-ში:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Index-ის აგება (Offline Pipeline)

გაუშვით offline indexing pipeline მონაცემების მომზადებისთვის:

```bash
# სრული pipeline ყველა კატეგორიისთვის
python build_index.py

# ტესტისთვის მხოლოდ 3 კატეგორია
python build_index.py --test 3
```

ეს ოპერაცია:
- ასკრეიპებს პროდუქტებს ყველა კატეგორიიდან
- აგენერირებს embeddings-ს ყველა პროდუქტისთვის
- აშენებს და ინახავს FAISS index-ს
- ინახავს metadata-ს სწრაფი lookup-ისთვის

### 4. API Server-ის გაშვება

```bash
# მეთოდი 1: პირდაპირი გაშვება
python server.py

# მეთოდი 2: uvicorn-ის გამოყენება
python -m uvicorn server:app --host 0.0.0.0 --port 8000

# მეთოდი 3: Docker-ის გამოყენება
docker-compose up --build
```

### 5. API-ის ტესტირება

```bash
# Health check
curl http://localhost:8000/health

# პროდუქტების ძიება
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "gaming laptop", "max_results": 5}'

# ქართული query
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "ყურსასმენი", "max_results": 3}'
```

## 🔧 როგორ მუშაობს სისტემა

### Offline Pipeline (build_index.py)

1. **Data Collection**: Async scraping with Playwright
   ```
   URL List → Parallel Scraping → Raw JSON Storage
   ```

2. **Embedding Generation**: Batch processing
   ```
   Products → Text Building → SentenceTransformer → Vector Embeddings
   ```

3. **Index Building**: FAISS optimization
   ```
   Embeddings → FAISS Index (IndexFlatL2/IndexIVFFlat) → Storage
   ```

### Online API (server.py)

1. **Server Startup**: Component pre-loading
   ```
   FastAPI Lifespan → Model Loading → Index Loading → Ready to Serve
   ```

2. **Search Request Flow**:
   ```
   User Query → Query Preprocessing → Parallel Execution:
                                     ├── Vector Search (FAISS)
                                     └── Category Selection (LLM)
                                     → Result Fusion → Response
   ```

3. **Enhanced Search Features**:
   - **Query Expansion**: "ლეპტოპი" → "ლეპტოპი laptop კომპიუტერი"
   - **Category Boost**: 20% score boost for category-matching products
   - **Term Matching**: 10% boost per matching query term
   - **Result Diversification**: Different categories and brands

## 📊 Performance მონაცემები

ტესტის შედეგები 69 პროდუქტზე:
- **Response Time**: 980-1500ms
- **Vector Search**: ~100ms (memory-based)
- **LLM Category Selection**: ~600-800ms
- **Index Size**: 0.19MB (69 products)
- **Model Memory**: ~500MB (SentenceTransformers)

## 📝 API დოკუმენტაცია

### ძირითადი Endpoints

#### `GET /health`
სისტემის ჯანმრთელობის შემოწმება - ყველა კომპონენტის ჩატვირთვის სტატუსი.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-19T15:27:13.993744",
  "components": {
    "embedding_model": "loaded",
    "hybrid_retriever": "loaded", 
    "faiss_index": "loaded",
    "product_metadata": "69 products"
  }
}
```

#### `POST /search`
მთავარი search endpoint პროდუქტების საპოვნელად.

**Request:**
```json
{
  "query": "gaming laptop",
  "max_results": 5
}
```

**Response:**
```json
{
  "query": "gaming laptop",
  "selected_category": {
    "category_name": "Gaming",
    "subcategory_name": "Gaming ლეპტოპები",
    "subcategory_url": "/gaming-gaming-leptopebi-c838s"
  },
  "products": [
    {
      "title": "Asus ROG Ally X RC72LA Z1 Extreme",
      "price": "2699.0",
      "category": "skhva-konsolebi",
      "link": "https://zoommer.ge/gaming/asus-rog-ally-x-rc72la-z1-extreme-handheld-video-game-console-24gb-ram-1tb-black-p43722",
      "image": "/_next/image?url=https%3A%2F%2Fs3.zoommer.ge%2Fsite%2Fcfe525d9-45d1-458d-a266-5c84a586ba90_Thumb.jpeg&w=384&q=50",
      "product_title_detail": "Asus ROG Ally X RC72LA Z1 Extreme Handheld Video Game Console 24GB RAM 1TB Black",
      "description": "",
      "specs": {
        "ბრენდი:": "Asus",
        "პროცესორი:": "AMD Ryzen Z1 Extreme",
        "მეხსიერება:": "24 GB",
        "შენახვის ტიპი:": "SSD",
        "ეკრანის ზომა:": "7 inches",
        "რეზოლუცია:": "1920 x 1080 (FHD)",
        "გრაფიკული ჩიპი:": "AMD Radeon",
        "ელემენტის ხანგრძლივობა:": "Up To 2.4 h",
        "წონა:": "678 g",
        "ფერი:": "Black"
      },
      "similarity_score": 1.0
    }
  ],
  "total_results": 3,
  "response_time_ms": 856.47,
  "timestamp": "2025-07-19T14:53:02.273740"
}
```

**რესპონსის ველების აღწერა:**

**პროდუქტის ინფორმაცია (products):**
- `title`: პროდუქტის მოკლე სახელწოდება
- `price`: ფასი (ლარებში, string ფორმატში)
- `category`: პროდუქტის კატეგორია
- `link`: პროდუქტის გვერდის პირდაპირი ლინკი zoommer.ge-ზე
- `image`: პროდუქტის ფოტოს URL
- `product_title_detail`: დეტალური პროდუქტის სახელწოდება
- `description`: პროდუქტის აღწერა
- `specs`: დეტალური ტექნიკური მახასიათებლები (ქართულ ენაზე)
- `similarity_score`: საძიებო მოთხოვნასთან მსგავსების ხარისხი (0-1)

**კატეგორიის ინფორმაცია (selected_category):**
- `category_name`: მთავარი კატეგორია
- `subcategory_name`: ქვეკატეგორია
- `subcategory_url`: კატეგორიის URL

#### `GET /stats`
ჩატვირთული მონაცემების სტატისტიკა.

**Response:**
```json
{
  "total_products": 69,
  "index_dimension": 384,
  "index_size": 69,
  "model_name": "intfloat/multilingual-e5-small",
  "retriever_model": "paraphrase-multilingual-MiniLM-L12-v2"
}
```

### Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 💻 გამოყენების მაგალითები

### Python Client

```python
import requests
import json

# პროდუქტების ძიება
response = requests.post(
    "http://localhost:8000/search",
    json={"query": "ყურსასმენი", "max_results": 5}
)

if response.status_code == 200:
    data = response.json()
    print(f"ნაპოვნია {data['total_results']} პროდუქტი {data['response_time_ms']}ms-ში")
    print(f"კატეგორია: {data['selected_category']['subcategory_name']}")
    
    for i, product in enumerate(data['products'], 1):
        print(f"{i}. {product['title']} - {product['price']} ლარი")
        print(f"   Similarity: {product['similarity_score']:.3f}")
else:
    print(f"შეცდომა: {response.status_code}")
```

### JavaScript/Frontend

```javascript
// ძიების ფუნქცია
async function searchProducts(query, maxResults = 10) {
    try {
        const response = await fetch('http://localhost:8000/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                query: query, 
                max_results: maxResults 
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log(`ნაპოვნია ${data.total_results} პროდუქტი`);
            console.log(`Response time: ${data.response_time_ms}ms`);
            return data;
        } else {
            console.error('ძიება ვერ მოხერხდა:', response.status);
        }
    } catch (error) {
        console.error('ძიების შეცდომა:', error);
    }
}

// გამოყენება
searchProducts('gaming laptop').then(data => {
    if (data && data.products) {
        data.products.forEach((product, index) => {
            console.log(`${index + 1}. ${product.title} - ${product.price} ლარი`);
        });
    }
});

// ქართული ძიება
searchProducts('ყურსასმენი', 3).then(data => {
    console.log('ყურსასმენების ძიების შედეგი:', data);
});
```

### cURL მაგალითები

```bash
# ყურსასმენების ძიება
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "ყურსასმენი", "max_results": 3}'

# Gaming კონსოლების ძიება  
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "gaming console", "max_results": 4}'

# System სტატისტიკა
curl "http://localhost:8000/stats"

# Health check
curl "http://localhost:8000/health"
```

## 🚀 Deployment

### Production Deployment

1. **Docker Deployment:**
```bash
# Build და run Docker Compose-ით
docker-compose up -d

# Logs-ების შემოწმება
docker-compose logs -f search-api
```

2. **Manual Deployment:**
```bash
# Dependencies-ების ინსტალაცია
pip install -r requirements.txt

# Index-ის აგება
python build_index.py

# Production settings-ით server-ის გაშვება
python -m uvicorn server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --access-log \
  --log-level info
```

### Index განახლებისთვის Cron Job

crontab-ში დაამატეთ ყოველდღიური index-ის განახლება:

```bash
# crontab-ის რედაქტირება
crontab -e

# ყოველდღე 2 საათზე გაშვება
0 2 * * * cd /path/to/RAGinda && python build_index.py >> /var/log/build_index.log 2>&1
```

## ⚡ Performance ოპტიმიზაცია

### Index ოპტიმიზაცია
- Dataset < 1000 products: იყენებს `IndexFlatL2`
- დიდი datasets: იყენებს `IndexIVFFlat` ავტომატური clustering-ით
- Embeddings ინახება `float32` format-ში memory efficiency-სთვის

### API ოპტიმიზაცია
- ყველა კომპონენტი pre-loaded memory-ში startup-ის დროს
- CPU-bound tasks სრულდება thread pools-ში `asyncio.to_thread`-ით
- Parallel execution category finding და product search-ის
- CORS enabled frontend integration-ისთვის

### მონიტორინგი
- Comprehensive logging timestamps-ით
- Response time tracking
- Health check endpoints
- Component status monitoring

## 🛠️ პრობლემების გადაჭრა

### ხშირი პრობლემები

1. **"Components not initialized" შეცდომა:**
   - დარწმუნდით რომ `build_index.py` წარმატებით იყო გაშვებული
   - შეამოწმეთ რომ `output/index.faiss` და `output/metadata.json` არსებობს

2. **ნელი startup:**
   - ნორმალურია პირველი startup-ისთვის (models loading იღებს დროს)
   - შემდეგი requests უნდა იყოს სწრაფი (< 1000ms)

3. **ცარიელი search შედეგები:**
   - შეამოწმეთ რომ categories.json სწორადაა კონფიგურირებული
   - დაადასტურეთ რომ Gemini API key სწორადაა დაყენებული

### Performance Tuning

- **Memory:** გაზარდეთ RAM დიდი datasets-ისთვის
- **CPU:** გამოიყენეთ მეტი uvicorn workers მაღალი concurrency-სთვის  
- **Storage:** გამოიყენეთ SSD სწრაფი index loading-ისთვის

## 🔧 Development

### Project Structure
```
├── build_index.py          # Offline indexing pipeline
├── server.py              # FastAPI server  
├── requirements.txt       # Dependencies
├── Dockerfile            # Docker container setup
├── docker-compose.yml    # Docker Compose configuration
├── test_categories.json  # Test URL list
├── src/
│   └── product_finder/   # Core modules
├── output/               # Generated indexes and metadata
└── data/                 # Configuration files
```

### ტექნოლოგიები
- **FastAPI**: Modern async web framework
- **FAISS**: Vector similarity search
- **SentenceTransformers**: Multilingual embeddings
- **Playwright**: Async web scraping
- **Gemini API**: LLM-enhanced category selection
- **Docker**: Containerization

## 📊 ტესტის შედეგები

ტესტირება 69 პროდუქტზე:
```
✅ Health Check: ყველა კომპონენტი ჩატვირთული
✅ English Search: "laptop" → 1495ms 
✅ Georgian Search: "ყურსასმენი" → 1040ms
✅ Gaming Search: "gaming console" → 982ms
✅ Similarity Scores: 0.30-1.0 range
✅ Category Detection: მაღალი სიზუსტე
```

## 📄 ლიცენზია

ეს პროექტი ლიცენზირებულია MIT License-ით - იხილეთ LICENSE ფაილი დეტალებისთვის.

---

**შექმნილი**: 2025 წელი  
**ავტორი**: nika2811  
**Repository**: [RAGinda](https://github.com/nika2811/RAGinda)
