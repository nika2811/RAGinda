#!/usr/bin/env python3
"""
Validation script to check the refactored architecture for common issues.
"""

import os
import sys
import json
from pathlib import Path

def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists and report."""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} MISSING: {filepath}")
        return False

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("\n🔍 Checking Dependencies...")
    
    package_mappings = {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'pydantic': 'pydantic',
        'aiofiles': 'aiofiles',
        'aiohttp': 'aiohttp',
        'sentence-transformers': 'sentence_transformers',
        'faiss-cpu': 'faiss',
        'numpy': 'numpy',
        'tqdm': 'tqdm',
        'requests': 'requests',
        'python-dotenv': 'dotenv',
        'playwright': 'playwright',
        'scikit-learn': 'sklearn'
    }
    
    missing = []
    for package_name, import_name in package_mappings.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - MISSING")
            missing.append(package_name)
    
    if missing:
        print(f"\n⚠️ Install missing packages: pip install {' '.join(missing)}")
        return False
    return True

def check_project_structure():
    """Check if the project structure is correct."""
    print("\n🔍 Checking Project Structure...")
    
    base_path = "c:\\Users\\nikan\\Downloads\\Scrap"
    
    # Critical files
    critical_files = [
        (os.path.join(base_path, "build_index.py"), "Offline Indexing Pipeline"),
        (os.path.join(base_path, "server.py"), "FastAPI Server"),
        (os.path.join(base_path, "requirements.txt"), "Requirements File"),
        (os.path.join(base_path, "src", "product_finder", "config.py"), "Configuration"),
        (os.path.join(base_path, "src", "product_finder", "utils", "async_utils.py"), "Async Utilities"),
        (os.path.join(base_path, "data", "categories.json"), "Categories Data"),
    ]
    
    all_exist = True
    for filepath, description in critical_files:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    # Check directories
    directories = [
        (os.path.join(base_path, "output"), "Output Directory"),
        (os.path.join(base_path, "data"), "Data Directory"),
        (os.path.join(base_path, "src", "product_finder"), "Source Directory"),
    ]
    
    for dirpath, description in directories:
        if Path(dirpath).exists():
            print(f"✅ {description}: {dirpath}")
        else:
            print(f"❌ {description} MISSING: {dirpath}")
            all_exist = False
    
    return all_exist

def check_environment():
    """Check environment variables."""
    print("\n🔍 Checking Environment Configuration...")
    
    env_file = "c:\\Users\\nikan\\Downloads\\Scrap\\.env"
    if Path(env_file).exists():
        print(f"✅ Environment file found: {env_file}")
        with open(env_file, 'r') as f:
            content = f.read()
            if "GEMINI_API_KEY" in content:
                print("✅ GEMINI_API_KEY configured")
                return True
            else:
                print("❌ GEMINI_API_KEY not found in .env file")
                return False
    else:
        print(f"❌ Environment file missing: {env_file}")
        print("   Create a .env file with: GEMINI_API_KEY=your_api_key")
        return False

def check_code_syntax():
    """Check for basic syntax errors in main files."""
    print("\n🔍 Checking Code Syntax...")
    
    base_path = "c:\\Users\\nikan\\Downloads\\Scrap"
    files_to_check = [
        os.path.join(base_path, "build_index.py"),
        os.path.join(base_path, "server.py"),
        os.path.join(base_path, "run_server.py"),
        os.path.join(base_path, "test_api.py"),
    ]
    
    all_valid = True
    for filepath in files_to_check:
        if Path(filepath).exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    compile(f.read(), filepath, 'exec')
                print(f"✅ Syntax OK: {Path(filepath).name}")
            except SyntaxError as e:
                print(f"❌ Syntax Error in {Path(filepath).name}: Line {e.lineno} - {e.msg}")
                all_valid = False
            except Exception as e:
                print(f"⚠️ Could not check {Path(filepath).name}: {e}")
        else:
            print(f"❌ File not found: {filepath}")
            all_valid = False
    
    return all_valid

def check_config_values():
    """Check configuration values."""
    print("\n🔍 Checking Configuration...")
    
    try:
        sys.path.append("c:\\Users\\nikan\\Downloads\\Scrap")
        from src.product_finder import config
        
        # Check critical config values
        configs_to_check = [
            ('EMBEDDER_MODEL', config.EMBEDDER_MODEL),
            ('RETRIEVER_MODEL', config.RETRIEVER_MODEL),
            ('FAISS_INDEX_FILE', config.FAISS_INDEX_FILE),
            ('FAISS_METADATA_FILE', config.FAISS_METADATA_FILE),
            ('CATEGORIES_FILE', config.CATEGORIES_FILE),
            ('SCRAPED_DATA_FILE', config.SCRAPED_DATA_FILE),
        ]
        
        for name, value in configs_to_check:
            if value:
                print(f"✅ {name}: {value}")
            else:
                print(f"❌ {name}: Not configured")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Could not load config: {e}")
        return False

def print_usage_instructions():
    """Print usage instructions."""
    print("\n" + "="*60)
    print("📋 USAGE INSTRUCTIONS")
    print("="*60)
    
    print("\n1️⃣ FIRST RUN (Offline Pipeline):")
    print("   python build_index.py")
    print("   (This will scrape data and build the search index)")
    
    print("\n2️⃣ START THE API SERVER:")
    print("   python run_server.py")
    print("   OR")
    print("   python -m uvicorn server:app --host 0.0.0.0 --port 8000")
    
    print("\n3️⃣ TEST THE API:")
    print("   python test_api.py")
    print("   OR visit: http://localhost:8000/docs")
    
    print("\n4️⃣ DOCKER DEPLOYMENT:")
    print("   docker-compose up --build")
    
    print("\n5️⃣ PERIODIC INDEX UPDATES:")
    print("   Set up a cron job to run build_index.py daily")
    print("   Example: 0 2 * * * cd /path/to/project && python build_index.py")

def main():
    """Run all validation checks."""
    print("🧪 ARCHITECTURE VALIDATION")
    print("="*50)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure), 
        ("Environment", check_environment),
        ("Code Syntax", check_code_syntax),
        ("Configuration", check_config_values),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name} check failed: {e}")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 ALL CHECKS PASSED! The architecture looks good.")
        print_usage_instructions()
    else:
        print("⚠️ SOME CHECKS FAILED. Please fix the issues above.")
        print("\n💡 Common fixes:")
        print("   - Run: pip install -r requirements.txt")
        print("   - Create .env file with GEMINI_API_KEY")
        print("   - Ensure all files are in the correct locations")
    
    print("\n📚 Documentation: README_NEW.md")
    print("🔗 API Docs (when running): http://localhost:8000/docs")

if __name__ == "__main__":
    main()
