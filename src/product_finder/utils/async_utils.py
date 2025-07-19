"""
Async utilities for file operations and other helper functions.
"""

import json
import aiofiles
from typing import Any, List, Dict
from pathlib import Path


async def read_json_async(file_path: str) -> Any:
    """
    Asynchronously read and parse a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Parsed JSON data
    """
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
        content = await f.read()
        return json.loads(content)


async def write_json_async(file_path: str, data: Any, indent: int = 2) -> None:
    """
    Asynchronously write data to a JSON file.
    
    Args:
        file_path: Path to the JSON file
        data: Data to write
        indent: JSON indentation level
    """
    # Ensure parent directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        json_str = json.dumps(data, ensure_ascii=False, indent=indent)
        await f.write(json_str)


def file_exists_async(file_path: str) -> bool:
    """
    Check if a file exists.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if file exists, False otherwise
    """
    return Path(file_path).exists()
