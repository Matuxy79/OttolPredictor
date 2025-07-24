"""
Activity Logger for Lottery Predictor

Handles system-wide activity tracking with:
- Priority-based processing
- Storage management
- GUI update coordination
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from queue import Queue
import sqlite3
import json
import os
from dataclasses import dataclass
from threading import Lock

@dataclass
class Activity:
    """Represents a single system activity"""
    type: str
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    priority: str = 'medium'
    source: str = 'system'

class ActivityLogger:
    """
    Singleton logger for system-wide activity tracking
    
    Features:
    - Priority queue for activities
    - SQLite storage for history
    - Memory cache for recent items
    - GUI update coordination
    """
    
    _instance = None
    _lock = Lock()
    
    ACTIVITY_TYPES = {
        'data': {
            'icon': '📊',
            'color': '#2ecc71',
            'priority': 'high'
        },
        'prediction': {
            'icon': '🎯',
            'color': '#3498db',
            'priority': 'high'
        },
        'analysis': {
            'icon': '📈',
            'color': '#9b59b6',
            'priority': 'medium'
        },
        'error': {
            'icon': '❌',
            'color': '#e74c3c',
            'priority': 'high'
        },
        'maintenance': {
            'icon': '🔧',
            'color': '#95a5a6',
            'priority': 'low'
        }
    }

    def __init__(self):
        """Initialize the activity logger"""
        self.logger = logging.getLogger(__name__)
        self.activity_queue = Queue()
        self.recent_activities: List[Activity] = []
        self.max_recent = 100
        self.gui_callbacks = []
        self.stats = {
            'total_activities': 0,
            'activities_by_type': {},
            'activities_by_priority': {
                'high': 0,
                'medium': 0,
                'low': 0
            }
        }
        
        # Initialize storage
        self._init_storage()
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ActivityLogger()
        return cls._instance

    def _init_storage(self):
        """Initialize SQLite storage"""
        try:
            db_path = os.path.join('data', 'activity.db')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            self.conn = sqlite3.connect(db_path)
            cursor = self.conn.cursor()
            
            # Create activity table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    priority TEXT,
                    source TEXT
                )
            ''')
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to initialize activity storage: {e}")

    def log_activity(self, 
                    message: str,
                    activity_type: str = 'info',
                    details: Optional[Dict[str, Any]] = None,
                    source: str = 'system') -> bool:
        """
        Log a new activity
        
        Args:
            message: Activity description
            activity_type: Type of activity (data/prediction/analysis/error/maintenance)
            details: Optional additional information
            source: Component that generated the activity
            
        Returns:
            bool: Success status
        """
        try:
            # Create activity record
            activity = Activity(
                type=activity_type,
                message=message,
                timestamp=datetime.now(),
                details=details,
                priority=self.ACTIVITY_TYPES.get(activity_type, {}).get('priority', 'medium'),
                source=source
            )
            
            # Add to queue
            self.activity_queue.put(activity)
            
            # Store in database
            self._store_activity(activity)
            
            # Update recent activities
            self._update_recent(activity)
            
            # Update statistics
            self.stats['total_activities'] += 1
            self.stats['activities_by_type'][activity_type] = self.stats['activities_by_type'].get(activity_type, 0) + 1
            self.stats['activities_by_priority'][activity.priority] += 1
            
            # Notify all GUI callbacks
            for callback in self.gui_callbacks:
                try:
                    callback(activity)
                except Exception as e:
                    self.logger.error(f"Error in GUI callback: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log activity: {e}")
            return False

    def _store_activity(self, activity: Activity):
        """Store activity in SQLite database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO activities 
                (timestamp, type, message, details, priority, source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                activity.timestamp.isoformat(),
                activity.type,
                activity.message,
                json.dumps(activity.details) if activity.details else None,
                activity.priority,
                activity.source
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to store activity: {e}")

    def _update_recent(self, activity: Activity):
        """Update recent activities cache"""
        self.recent_activities.insert(0, activity)
        if len(self.recent_activities) > self.max_recent:
            self.recent_activities.pop()

    def get_recent_activities(self, limit: int = 50) -> List[Activity]:
        """Get most recent activities from cache"""
        return self.recent_activities[:limit]

    def register_callback(self, callback) -> None:
        """Register a GUI callback for activity updates"""
        if callback not in self.gui_callbacks:
            self.gui_callbacks.append(callback)

    def unregister_callback(self, callback) -> None:
        """Remove a GUI callback"""
        if callback in self.gui_callbacks:
            self.gui_callbacks.remove(callback)
            
    def get_stats(self) -> Dict[str, Any]:
        """Get activity statistics"""
        return {
            'total': self.stats['total_activities'],
            'by_type': self.stats['activities_by_type'],
            'by_priority': self.stats['activities_by_priority'],
            'recent_count': len(self.recent_activities)
        }
        
    def clear_history(self) -> bool:
        """Clear activity history and reset stats"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM activities')
            self.conn.commit()
            
            self.recent_activities.clear()
            self.stats = {
                'total_activities': 0,
                'activities_by_type': {},
                'activities_by_priority': {
                    'high': 0,
                    'medium': 0,
                    'low': 0
                }
            }
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear activity history: {e}")
            return False
        return self.recent_activities[:limit]

    def get_activities_by_type(self, activity_type: str, limit: int = 50) -> List[Activity]:
        """Get activities of specific type"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM activities 
                WHERE type = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (activity_type, limit))
            
            return [Activity(
                type=row[2],
                message=row[3],
                timestamp=datetime.fromisoformat(row[1]),
                details=json.loads(row[4]) if row[4] else None,
                priority=row[5],
                source=row[6]
            ) for row in cursor.fetchall()]
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve activities: {e}")
            return []

    def clear_old_activities(self, days_to_keep: int = 30):
        """Clear activities older than specified days"""
        try:
            cursor = self.conn.cursor()
            cutoff = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            cursor.execute('DELETE FROM activities WHERE timestamp < ?', (cutoff,))
            self.conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to clear old activities: {e}")

    def format_activity_for_display(self, activity: Activity) -> Dict[str, Any]:
        """Format an activity for GUI display with styling"""
        activity_info = self.ACTIVITY_TYPES.get(activity.type, {
            'icon': '📝',
            'color': '#7f8c8d',
            'priority': 'medium'
        })
        
        formatted = {
            'message': f"{activity_info['icon']} {activity.message}",
            'timestamp': activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'color': activity_info['color'],
            'priority': activity.priority,
            'source': activity.source,
            'type': activity.type,
            'details': activity.details,
            'style': {
                'background': activity_info['color'] + '20',  # 20% opacity
                'border-left': f"4px solid {activity_info['color']}"
            }
        }
        
        return formatted

    def __del__(self):
        """Cleanup on deletion"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
        except:
            pass
