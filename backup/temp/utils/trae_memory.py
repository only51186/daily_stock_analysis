# -*- coding: utf-8 -*-
"""
===================================
Trae Memory Management Module
===================================

[Features]
1. Persistent task state storage
2. Context recovery after restart
3. Data cache management
4. Configuration validation

[Memory File]
./trae_memory/task_state.json

[Cache Directory]
./data_cache/
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class TraeMemory:
    """
    Trae Memory Management Class
    
    [Core Features]
    1. Task state persistence
    2. Context recovery
    3. Cache management
    4. Configuration validation
    """
    
    def __init__(self, project_root: str = None):
        """
        Initialize memory manager
        
        Args:
            project_root: Project root directory path
        """
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.project_root = Path(project_root)
        self.memory_dir = self.project_root / "trae_memory"
        self.cache_dir = self.project_root / "data_cache"
        self.backup_dir = self.project_root / "backup"
        
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.memory_dir / "task_state.json"
        
        self.current_task_id = "openbb_integration_v2"
    
    def load_state(self) -> Dict[str, Any]:
        """
        Load task state from file
        
        Returns:
            Task state dictionary
        """
        if not self.state_file.exists():
            return self._create_initial_state()
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            logger.info(f"Loaded task state: {state.get('task_id', 'unknown')}")
            return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return self._create_initial_state()
    
    def save_state(self, state: Dict[str, Any]) -> bool:
        """
        Save task state to file
        
        Args:
            state: Task state dictionary
            
        Returns:
            True if saved successfully
        """
        try:
            state['last_updated'] = datetime.now().isoformat()
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved task state: {state.get('task_id', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            return False
    
    def _create_initial_state(self) -> Dict[str, Any]:
        """
        Create initial task state
        
        Returns:
            Initial state dictionary
        """
        state = {
            "task_id": self.current_task_id,
            "status": "in_progress",
            "completed_steps": [],
            "config": {
                "project_root": str(self.project_root),
                "python_version": "3.11.9",
                "venv_path": str(self.project_root / ".venv"),
                "tushare_token": "",
                "doubao_api_key": "",
                "openbb_version": "4.1.0",
                "backup_list": [],
                "cache_enabled": True
            },
            "data_sources": {
                "priority": ["openbb", "tushare", "akshare", "cache"],
                "last_successful_source": None
            },
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        self.save_state(state)
        return state
    
    def update_step(self, step_name: str, status: str = "completed") -> Dict[str, Any]:
        """
        Update task step status
        
        Args:
            step_name: Step name
            status: Step status
            
        Returns:
            Updated state
        """
        state = self.load_state()
        
        if status == "completed" and step_name not in state['completed_steps']:
            state['completed_steps'].append(step_name)
        
        self.save_state(state)
        return state
    
    def update_config(self, key: str, value: Any) -> Dict[str, Any]:
        """
        Update configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Returns:
            Updated state
        """
        state = self.load_state()
        state['config'][key] = value
        self.save_state(state)
        return state
    
    def get_summary(self) -> str:
        """
        Get task state summary
        
        Returns:
            Formatted summary string
        """
        state = self.load_state()
        
        completed = len(state.get('completed_steps', []))
        total = 10  # Estimated total steps
        status = state.get('status', 'unknown')
        
        config_summary = []
        if state.get('config', {}).get('python_version'):
            config_summary.append(f"Python {state['config']['python_version']}")
        if state.get('config', {}).get('openbb_version'):
            config_summary.append(f"OpenBB {state['config']['openbb_version']}")
        
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("🧠 Trae Memory Summary")
        lines.append("=" * 60)
        lines.append(f"Task ID: {state.get('task_id', 'unknown')}")
        lines.append(f"Status: {status}")
        lines.append(f"Progress: {completed}/{total} steps completed")
        lines.append(f"Config: {', '.join(config_summary)}")
        lines.append(f"Last Updated: {state.get('last_updated', 'N/A')}")
        
        if state.get('completed_steps'):
            lines.append("\nCompleted Steps:")
            for i, step in enumerate(state['completed_steps'], 1):
                lines.append(f"  {i}. {step}")
        
        lines.append("=" * 60)
        
        return '\n'.join(lines)
    
    def validate_environment(self) -> Dict[str, bool]:
        """
        Validate environment configuration
        
        Returns:
            Validation results
        """
        state = self.load_state()
        results = {}
        
        venv_path = Path(state['config'].get('venv_path', ''))
        results['venv_exists'] = venv_path.exists()
        
        python_exe = venv_path / 'Scripts' / 'python.exe'
        results['python_exe_exists'] = python_exe.exists()
        
        env_file = self.project_root / '.env'
        results['env_file_exists'] = env_file.exists()
        
        results['backup_dir_exists'] = self.backup_dir.exists()
        results['cache_dir_exists'] = self.cache_dir.exists()
        
        return results
    
    def get_backup_list(self) -> List[Dict[str, str]]:
        """
        Get list of available backups
        
        Returns:
            List of backup info
        """
        backups = []
        
        if not self.backup_dir.exists():
            return backups
        
        for file in self.backup_dir.glob("daily_stock_analysis_backup_*.zip"):
            try:
                timestamp_str = file.stem.replace("daily_stock_analysis_backup_", "")
                timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M')
                size_mb = file.stat().st_size / (1024 * 1024)
                
                backups.append({
                    'path': str(file),
                    'filename': file.name,
                    'timestamp': timestamp_str,
                    'datetime': timestamp.strftime('%Y-%m-%d %H:%M'),
                    'size': f"{size_mb:.2f} MB"
                })
            except Exception as e:
                logger.warning(f"Invalid backup file: {file.name}")
        
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        
        state = self.load_state()
        state['config']['backup_list'] = [b['filename'] for b in backups[:5]]
        self.save_state(state)
        
        return backups[:5]
    
    def record_data_fetch(self, source: str, symbol: str, success: bool) -> None:
        """
        Record data fetch operation
        
        Args:
            source: Data source name
            symbol: Stock symbol
            success: Whether fetch was successful
        """
        state = self.load_state()
        
        if 'data_fetch_history' not in state:
            state['data_fetch_history'] = []
        
        state['data_fetch_history'].append({
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'symbol': symbol,
            'success': success
        })
        
        if len(state['data_fetch_history']) > 100:
            state['data_fetch_history'] = state['data_fetch_history'][-100:]
        
        if success:
            state['data_sources']['last_successful_source'] = source
        
        self.save_state(state)
    
    def get_cache_path(self, symbol: str, data_type: str = "daily") -> Path:
        """
        Get cache file path for symbol
        
        Args:
            symbol: Stock symbol
            data_type: Data type
            
        Returns:
            Cache file path
        """
        safe_symbol = symbol.replace('.', '_').replace(':', '_')
        return self.cache_dir / f"{safe_symbol}_{data_type}.parquet"
    
    def has_cache(self, symbol: str, data_type: str = "daily", max_age_hours: int = 24) -> bool:
        """
        Check if valid cache exists
        
        Args:
            symbol: Stock symbol
            data_type: Data type
            max_age_hours: Maximum cache age in hours
            
        Returns:
            True if valid cache exists
        """
        cache_path = self.get_cache_path(symbol, data_type)
        
        if not cache_path.exists():
            return False
        
        import time
        file_age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        
        return file_age_hours <= max_age_hours


def get_memory(project_root: str = None) -> TraeMemory:
    """
    Get memory manager instance
    
    Args:
        project_root: Project root directory path
        
    Returns:
        TraeMemory instance
    """
    return TraeMemory(project_root)


if __name__ == '__main__':
    memory = get_memory()
    
    print(memory.get_summary())
    
    validation = memory.validate_environment()
    print("\nEnvironment Validation:")
    for key, value in validation.items():
        status = "✓" if value else "✗"
        print(f"  {status} {key}")
    
    backups = memory.get_backup_list()
    print("\nBackup List:")
    for i, backup in enumerate(backups, 1):
        print(f"  {i}. {backup['filename']} ({backup['datetime']})")
