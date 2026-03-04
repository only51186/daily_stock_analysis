# -*- coding: utf-8 -*-
"""
Trae Memory Test Script
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.trae_memory import get_memory

def main():
    memory = get_memory()
    
    print(memory.get_summary())
    
    print("\nEnvironment Validation:")
    validation = memory.validate_environment()
    for key, value in validation.items():
        status = "OK" if value else "MISSING"
        print(f"  [{status}] {key}")
    
    print("\nBackup List (Latest 5):")
    backups = memory.get_backup_list()
    for i, backup in enumerate(backups, 1):
        print(f"  {i}. {backup['filename']}")
        print(f"     Time: {backup['datetime']}")
        print(f"     Size: {backup['size']}")
    
    print("\nData Source Priority:")
    state = memory.load_state()
    for i, source in enumerate(state['data_sources']['priority'], 1):
        status = state['data_sources'].get(f'{source}_status', 'unknown')
        print(f"  {i}. {source}: {status}")

if __name__ == '__main__':
    main()
