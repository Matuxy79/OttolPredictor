# Activity Tracking System Analysis

## Current GUI Activities

### Data Operations
- Game switching
- Data refresh (smart/full)
- Loading historical data
- Importing new draws
- Data validation/cleanup

### Prediction Activities
- Strategy selection
- Prediction generation
- Quick picks
- Prediction evaluation
- Strategy performance updates

### Analysis Activities
- Chart generation
- Performance metrics updates
- Statistical analysis runs
- Export operations

## Backend Activities

### Data Manager Events
- PDF parsing
- Data normalization
- Cache updates
- Data validation
- Draw record updates

### Predictor Events
- Strategy evaluation
- Model updates
- Confidence calculations
- Historical analysis
- Performance tracking

### Scraper Events
- Web scraping attempts
- PDF downloads
- Data parsing
- File saves
- Validation checks

## Proposed Integration Matrix

| Activity Type | Frontend Display | Backend Logging | Storage | Priority |
|--------------|------------------|-----------------|---------|-----------|
| Data Load    | Real-time        | Detailed        | DB+Log  | High     |
| Predictions  | Interactive      | Performance     | DB      | High     |
| Analysis     | Background       | Metrics         | Cache   | Medium   |
| Errors       | User-friendly    | Technical       | Log     | High     |
| Maintenance  | Summary          | Detailed        | Log     | Low      |

## Implementation Strategy

1. Core Activity Types:
```python
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
```

2. Integration Points:

- Data Manager:
  ```python
  def load_game_data(self):
      self.log_activity("Loading game data", "data")
      # ... existing code
  ```

- Predictor:
  ```python
  def generate_prediction(self):
      self.log_activity("Generating prediction", "prediction")
      # ... existing code
  ```

3. Activity Flow:
```
Backend Event → Activity Logger → Storage → GUI Update
```

4. Storage Options:
- In-memory queue for recent activities
- SQLite table for historical tracking
- Log files for technical details

5. GUI Updates:
- Real-time for high priority
- Batched for medium priority
- Background for low priority

## Required New Components

1. ActivityLogger class
2. Activity storage system
3. Activity queue manager
4. GUI update coordinator

## Next Steps

1. Create ActivityLogger singleton
2. Add activity points in backend
3. Create storage system
4. Update GUI display system
5. Implement priority handling
