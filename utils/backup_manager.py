# -*- coding: utf-8 -*-
"""
===================================
Backup Management Module
===================================

[Features]
1. Create timestamped zip backups
2. Auto cleanup old backups (keep latest 5)
3. List all backups with timestamps
4. Restore from backup with rollback support

[Backup Naming Convention]
daily_stock_analysis_backup_YYYYMMDDHHMM.zip
- YYYY: Year
- MM: Month
- DD: Day
- HH: Hour
- MM: Minute

[Backup Location]
./backup/

[Retention Policy]
Keep only the latest 5 backups, auto-delete older ones
"""

import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Backup Manager Class
    
    [Core Features]
    1. Create timestamped backups
    2. Auto cleanup old backups
    3. List backups with timestamps
    4. Restore from backup
    """
    
    def __init__(self, project_root: str = None):
        """
        Initialize backup manager
        
        Args:
            project_root: Project root directory path
        """
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backup"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_backups = 5
        
        self.exclude_patterns = [
            '__pycache__',
            '.git',
            '.venv',
            'venv',
            '*.pyc',
            '*.pyo',
            '*.log',
            'backup',
            'openbb_backup',
            'openbb_deps',
            'data',
            'logs',
            '*.db',
            '*.db-journal'
        ]
    
    def create_backup(self, reason: str = "auto") -> Dict[str, str]:
        """
        Create a timestamped backup
        
        Args:
            reason: Backup reason (auto, manual, pre_restore, etc.)
            
        Returns:
            Dict with backup info: {'path': str, 'timestamp': str, 'size': str}
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        backup_name = f"daily_stock_analysis_backup_{timestamp}.zip"
        backup_path = self.backup_dir / backup_name
        
        logger.info(f"Creating backup: {backup_name}")
        print(f"Creating backup: {backup_name}")
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.project_root):
                    dirs[:] = [d for d in dirs if not self._should_exclude(d)]
                    
                    for file in files:
                        if self._should_exclude(file):
                            continue
                        
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(self.project_root)
                        
                        try:
                            zipf.write(file_path, arcname)
                        except Exception as e:
                            logger.warning(f"Failed to backup {file_path}: {e}")
            
            backup_size = backup_path.stat().st_size
            size_mb = backup_size / (1024 * 1024)
            
            logger.info(f"Backup created: {backup_path} ({size_mb:.2f} MB)")
            print(f"Backup created: {backup_path} ({size_mb:.2f} MB)")
            
            self._cleanup_old_backups()
            
            return {
                'path': str(backup_path),
                'timestamp': timestamp,
                'size': f"{size_mb:.2f} MB",
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def _should_exclude(self, name: str) -> bool:
        """
        Check if a file/directory should be excluded from backup
        
        Args:
            name: File or directory name
            
        Returns:
            True if should exclude, False otherwise
        """
        for pattern in self.exclude_patterns:
            if pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False
    
    def _cleanup_old_backups(self) -> int:
        """
        Clean up old backups, keep only latest 5
        
        Returns:
            Number of deleted backups
        """
        backups = self.list_backups()
        
        if len(backups) <= self.max_backups:
            return 0
        
        to_delete = backups[self.max_backups:]
        deleted_count = 0
        
        for backup in to_delete:
            try:
                backup_path = Path(backup['path'])
                if backup_path.exists():
                    backup_path.unlink()
                    logger.info(f"Deleted old backup: {backup['filename']}")
                    print(f"Deleted old backup: {backup['filename']}")
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete backup {backup['filename']}: {e}")
        
        return deleted_count
    
    def list_backups(self) -> List[Dict[str, str]]:
        """
        List all backups sorted by timestamp (newest first)
        
        Returns:
            List of backup info dicts
        """
        backups = []
        
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
        
        return backups
    
    def print_backup_list(self, count: int = 5) -> str:
        """
        Print formatted backup list
        
        Args:
            count: Number of backups to show
            
        Returns:
            Formatted string of backup list
        """
        backups = self.list_backups()[:count]
        
        if not backups:
            return "No backups found"
        
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("Backup List (Latest 5)")
        lines.append("=" * 60)
        
        for i, backup in enumerate(backups, 1):
            lines.append(f"{i}. {backup['filename']}")
            lines.append(f"   Time: {backup['datetime']}")
            lines.append(f"   Size: {backup['size']}")
        
        lines.append("=" * 60)
        
        result = '\n'.join(lines)
        print(result)
        return result
    
    def restore_backup(self, timestamp: str) -> Dict[str, str]:
        """
        Restore from a backup by timestamp
        
        Args:
            timestamp: Backup timestamp (YYYYMMDDHHMM format)
            
        Returns:
            Dict with restore result info
        """
        pre_restore_backup = self.create_backup(reason="pre_restore")
        logger.info(f"Pre-restore backup created: {pre_restore_backup['path']}")
        print(f"Pre-restore backup created: {pre_restore_backup['path']}")
        
        backup_name = f"daily_stock_analysis_backup_{timestamp}.zip"
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")
        
        logger.info(f"Restoring from backup: {backup_name}")
        print(f"Restoring from backup: {backup_name}")
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                for member in zipf.namelist():
                    target_path = self.project_root / member
                    
                    if member.endswith('/'):
                        target_path.mkdir(parents=True, exist_ok=True)
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        with zipf.open(member) as source, open(target_path, 'wb') as target:
                            target.write(source.read())
            
            logger.info(f"Restore completed from: {backup_name}")
            print(f"Restore completed from: {backup_name}")
            
            return {
                'status': 'success',
                'restored_from': backup_name,
                'pre_restore_backup': pre_restore_backup['path'],
                'message': f"Successfully restored from {backup_name}"
            }
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise
    
    def get_backup_by_index(self, index: int) -> Optional[Dict[str, str]]:
        """
        Get backup info by index (1-based)
        
        Args:
            index: Backup index (1 = latest)
            
        Returns:
            Backup info dict or None
        """
        backups = self.list_backups()
        if 1 <= index <= len(backups):
            return backups[index - 1]
        return None


def get_backup_manager(project_root: str = None) -> BackupManager:
    """
    Get backup manager instance
    
    Args:
        project_root: Project root directory path
        
    Returns:
        BackupManager instance
    """
    return BackupManager(project_root)


if __name__ == '__main__':
    manager = get_backup_manager()
    
    print("\n" + "=" * 60)
    print("Backup Manager Test")
    print("=" * 60)
    
    result = manager.create_backup(reason="manual_test")
    print(f"\nBackup created: {result}")
    
    manager.print_backup_list()
