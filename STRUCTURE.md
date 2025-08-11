# IPSC Ranking System - Project Structure

This document describes the reorganized folder structure of the IPSC ranking system.

## Directory Structure

```
ipsc-ranking/
├── src/                          # Main source code
│   ├── __init__.py
│   ├── data_sources/            # Data source iterators
│   │   ├── __init__.py          # Factory functions and common interface
│   │   ├── base.py              # MatchDataIterator base class
│   │   ├── ssi.py               # SSI (Shoot'n Score It) iterator
│   │   ├── practiscore.py       # Practiscore iterator  
│   │   └── ipscresults.py       # IPSCResults.org iterator
│   ├── ranking/                 # Ranking system logic
│   │   ├── __init__.py
│   │   └── processor.py         # IPSCRankingSystem (match processing)
│   └── utils/                   # Utility modules
│       ├── __init__.py
│       └── division_normalizer.py
├── scripts/                     # Legacy scripts and scrapers
│   ├── scrapers/                # Data scraping scripts
│   └── legacy/                  # Legacy processing scripts
├── examples/                    # Example and demo scripts
├── tests/                       # Test scripts
├── data/                        # Data storage
│   └── matches/                 # Match data files (JSON)
├── docs/                        # Documentation and website
├── results/                     # Generated rankings (JSON/CSV)
├── config/                      # Configuration files
├── ranking_system.py            # Main entry point
└── test_structure.py            # Structure validation test
```

## Main Components

### Data Sources (`src/data_sources/`)
- **base.py**: Abstract base class and common functionality
- **ssi.py**: Iterator for SSI (shootnscoreit.com) data
- **practiscore.py**: Iterator for Practiscore data  
- **ipscresults.py**: Iterator for IPSCResults.org data
- **__init__.py**: Factory functions for creating iterators

### Ranking System (`src/ranking/`)
- **processor.py**: Main ranking processor using OpenSkill rating system

### Utilities (`src/utils/`)
- **division_normalizer.py**: Division name normalization utilities

## Usage

### Basic Usage
```python
# Main entry point
python3 ranking_system.py
```

### Using the API
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_sources import create_iterator
from ranking import IPSCRankingSystem

# Create iterator for all sources
iterator = create_iterator('all', 'file', match_data_dir='./data/matches/')

# Process matches
ranking_system = IPSCRankingSystem()
matches = ranking_system.load_matches()
for match in matches:
    ranking_system.process_match(match)

# Generate rankings
rankings = ranking_system.generate_ranking()
```

### Creating Specific Iterators
```python
from data_sources import create_iterator

# File-based iterators
ssi_iterator = create_iterator('ssi', 'file')
practiscore_iterator = create_iterator('practiscore', 'file')
ipscresults_iterator = create_iterator('ipscresults', 'file')
combined_iterator = create_iterator('all', 'file')

# Live data iterators  
live_ssi = create_iterator('ssi', 'live', start_match_id=1000, end_match_id=2000)
live_practiscore = create_iterator('practiscore', 'live', match_ids=['287616', '287617'])
live_ipscresults = create_iterator('ipscresults', 'live', filter_levels=[3, 4, 5])
```

## Migration from Old Structure

The old flat structure has been reorganized for better maintainability:

| Old Location | New Location |
|--------------|--------------|
| `match_data_iterator.py` | `src/data_sources/base.py` |
| `ssi_iterator.py` | `src/data_sources/ssi.py` |
| `practiscore_iterator.py` | `src/data_sources/practiscore.py` |
| `ipscresults_iterator.py` | `src/data_sources/ipscresults.py` |
| `process_matches.py` | `src/ranking/processor.py` |
| `division_normalizer.py` | `src/utils/division_normalizer.py` |
| `match_data/` | `data/matches/` |
| Various scrapers | `scripts/scrapers/` |
| Example scripts | `examples/` |
| Test scripts | `tests/` |
| Result files | `results/` |

## Benefits of New Structure

1. **Modularity**: Clear separation of concerns with dedicated packages
2. **Maintainability**: Related functionality grouped together
3. **Extensibility**: Easy to add new data sources or ranking algorithms
4. **Testing**: Isolated components are easier to test
5. **Documentation**: Structure is self-documenting
6. **Imports**: Cleaner import paths and reduced coupling

## Testing

Run the structure validation test:
```bash
python3 test_structure.py
```

This validates that:
- All imports work correctly
- Iterators can be created
- Ranking system functions properly
- Data can be loaded from files