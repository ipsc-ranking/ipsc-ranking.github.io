Read the README.md file to understand the project.

* We use nix.
* Make sure to never create several copies of the same file, clean up after yourself.

## Website Structure (Updated 2025-08-11)

The website uses a **single source of truth** approach:
- All files are in the `rankings/` directory
- No copying between folders needed
- Development and production are identical

### Key files:
- `rankings/` - Main website directory (served by GitHub Pages)
- `rankings/data/` - All ranking JSON files and metadata
- `update_rankings.py` - Simple update script (replaces old complex scripts)

### Workflow:
1. Generate rankings: `python generate_all_rankings.py`
2. Update website: `python update_rankings.py`
3. Test: `jekyll serve`
4. Deploy: `git commit && git push` 