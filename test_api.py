#!/usr/bin/env python3
"""
Test script for the AI Product Search API.
"""

import asyncio
import json
import time
import aiohttp
from typing import Dict, Any

API_BASE_URL = "http://localhost:8000"

async def test_health_check():
    """Test the health check endpoint."""
    print("🔍 Testing health check...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Health check passed")
                    print(f"   Status: {data['status']}")
                    print(f"   Components: {json.dumps(data['components'], indent=2)}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

async def test_search(query: str, max_results: int = 5):
    """Test the search endpoint."""
    print(f"\n🔍 Testing search: '{query}'")
    
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"query": query, "max_results": max_results}
            start_time = time.time()
            
            async with session.post(
                f"{API_BASE_URL}/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    print("✅ Search successful")
                    print(f"   Response time: {response_time:.2f}ms (API reported: {data['response_time_ms']}ms)")
                    print(f"   Selected category: {data['selected_category']['subcategory_name']}")
                    print(f"   Found products: {data['total_results']}")
                    
                    for i, product in enumerate(data['products'][:3], 1):
                        print(f"   {i}. {product['title']} - {product['price']} ლარი")
                        if product.get('similarity_score'):
                            print(f"      Similarity: {product['similarity_score']:.3f}")
                    
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Search failed: {response.status}")
                    print(f"   Error: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Search error: {e}")
            return False

async def test_stats():
    """Test the stats endpoint."""
    print("\n🔍 Testing stats...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Stats retrieved")
                    print(f"   Total products: {data['total_products']}")
                    print(f"   Index dimension: {data['index_dimension']}")
                    print(f"   Index size: {data['index_size']}")
                    print(f"   Embedding model: {data['model_name']}")
                    return True
                else:
                    print(f"❌ Stats failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Stats error: {e}")
            return False

async def run_performance_test(query: str, num_requests: int = 10):
    """Run performance test with multiple concurrent requests."""
    print(f"\n🚀 Performance test: {num_requests} concurrent requests for '{query}'")
    
    async def single_request(session, request_id):
        start_time = time.time()
        try:
            async with session.post(
                f"{API_BASE_URL}/search",
                json={"query": query, "max_results": 5},
                headers={"Content-Type": "application/json"}
            ) as response:
                response_time = (time.time() - start_time) * 1000
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "response_time": response_time,
                        "api_time": data["response_time_ms"],
                        "results": data["total_results"]
                    }
                else:
                    return {"success": False, "response_time": response_time}
        except Exception as e:
            return {"success": False, "error": str(e), "response_time": time.time() - start_time}
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        # Run all requests concurrently
        tasks = [single_request(session, i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        if successful:
            response_times = [r["response_time"] for r in successful]
            api_times = [r["api_time"] for r in successful]
            
            print("✅ Performance test completed")
            print(f"   Total time: {total_time:.2f}s")
            print(f"   Successful requests: {len(successful)}/{num_requests}")
            print(f"   Requests per second: {len(successful)/total_time:.2f}")
            print(f"   Average response time: {sum(response_times)/len(response_times):.2f}ms")
            print(f"   Average API time: {sum(api_times)/len(api_times):.2f}ms")
            print(f"   Min/Max response time: {min(response_times):.2f}ms / {max(response_times):.2f}ms")
        
        if failed:
            print(f"❌ Failed requests: {len(failed)}")

async def main():
    """Run all tests."""
    print("🧪 AI Product Search API Test Suite")
    print("=" * 50)
    
    # Test 1: Health check
    health_ok = await test_health_check()
    
    if not health_ok:
        print("\n❌ Health check failed. Make sure the server is running.")
        return
    
    # Test 2: Basic search tests
    test_queries = [
        "laptop gaming",
        "wireless headphones",
        "smartphone samsung",
        "coffee machine",
    ]
    
    for query in test_queries:
        await test_search(query)
        await asyncio.sleep(0.5)  # Small delay between tests
    
    # Test 3: Stats
    await test_stats()
    
    # Test 4: Performance test
    await run_performance_test("laptop gaming", 10)
    
    print("\n🎉 Test suite completed!")
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("ReDoc Documentation: http://localhost:8000/redoc")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
