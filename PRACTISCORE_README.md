# PractiScore Integration

This directory contains tools for integrating PractiScore match data with the IPSC ranking system.

## Components

### 1. PractiScore Client (`practiscore.py`)

A comprehensive client for fetching and parsing match data from PractiScore.

**Features:**
- Fetches match data from PractiScore by match ID
- Parses HTML results into standardized format
- Validates data structure and content
- Handles errors gracefully with detailed logging
- Supports timeout and retry mechanisms

**Usage:**
```python
from practiscore import PractiScoreClient

client = PractiScoreClient()
match_data = client.fetch_match_data('287616')

if match_data:
    print(f"Match: {match_data['match_title']}")
    print(f"Shooters: {len(match_data['production_optics_results'])}")
    client.save_match_data(match_data)
```

### 2. Batch Fetcher (`fetch_practiscore_matches.py`)

Utility script for fetching multiple matches at once.

**Usage:**
```bash
# Fetch single match
python fetch_practiscore_matches.py 287616

# Fetch multiple matches
python fetch_practiscore_matches.py 287616 287617 287618

# Fetch from file list
echo -e "287616\n287617\n287618" > match_ids.txt
python fetch_practiscore_matches.py --list-file match_ids.txt
```

### 3. Data Format

All fetched matches are saved in the `match_data/` directory with the format expected by the ranking system:

```json
{
  "match_id": 287616,
  "match_title": "Match Name",
  "match_date": "2025-01-08T10:00:00",
  "match_level": "Level II",
  "club_name": "Club Name",
  "production_optics_results": [
    {
      "first_name": "John",
      "last_name": "Doe",
      "alias": "",
      "region": "NOR",
      "division": "Production Optics",
      "match_percentage": 85.5,
      "placement": 1
    }
  ],
  "combined_results": [...]
}
```

## Integration with Ranking System

After fetching matches, process them with the existing ranking system:

```bash
# Fetch matches
python fetch_practiscore_matches.py 287616 287617

# Process all matches (including newly fetched ones)
python process_matches.py
```

## Limitations and Notes

1. **HTML Parsing**: PractiScore pages vary in structure. The parser includes multiple fallback methods but may need adjustment for specific match formats.

2. **Rate Limiting**: The client includes delays and error handling to be respectful to PractiScore servers.

3. **Data Validation**: All fetched data is validated for completeness and correctness before saving.

4. **Manual Fallback**: For matches that can't be automatically parsed, manual data entry may be required.

## Troubleshooting

### Common Issues

1. **Empty Results**: 
   - Check if the match ID is correct
   - Verify the match is publicly accessible
   - Some matches may require authentication

2. **Parsing Errors**:
   - Use `debug_practiscore.py` to inspect page structure
   - Check saved HTML files for manual parsing
   - Different match types may need custom parsing logic

3. **Network Issues**:
   - Check internet connectivity
   - PractiScore may have rate limiting
   - Try again later if server is overloaded

### Debug Mode

For debugging parsing issues:

```python
# Enable verbose output
from practiscore import PractiScoreClient
client = PractiScoreClient()
# Check debug_practiscore.html for page structure
```

## Future Enhancements

- Support for different divisions beyond Production Optics
- Integration with PractiScore API (if available)
- Automatic region detection based on shooter data
- Support for team matches and other formats
- Caching mechanism for frequently accessed matches