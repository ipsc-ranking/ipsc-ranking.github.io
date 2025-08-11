# Simple Deployment - Single Source of Truth

## New Structure ✨

Everything lives in one place now:

```
rankings/
├── index.html              # Main page
├── ranking.html            # Ranking display page  
├── styles.css              # All styling
├── script.js               # JavaScript
├── _config.yml             # Jekyll config
├── _layouts/               # Jekyll layouts
├── _includes/              # Jekyll includes
└── data/                   # All ranking data
    ├── metadata.json
    ├── ipsc_ranking_combined.json
    ├── ipsc_ranking_combined_junior.json  # No more missing files!
    └── ... (all other ranking files)
```

## Development & Production are Identical

- **Development**: `python -m http.server 8000 --directory rankings`
- **Production**: GitHub Pages serves from `rankings/` folder
- **No more copying between folders!**

## Simple Workflow

1. **Generate rankings** (your existing scripts)
2. **Update website**: `python update_rankings.py`  
3. **Test locally** (choose one):
   - **Simple**: `python create_standalone.py` then `python -m http.server 8000 --directory rankings`
     Visit: http://localhost:8000/index_standalone.html
   - **Jekyll**: `./serve_local.sh` (includes live reload!)
     Visit: http://localhost:4000
4. **Deploy**: `git add rankings/ && git commit && git push`

## What Changed

### ✅ Fixed
- Combined junior category now works (file exists in single location)
- Development and production are identical
- No more file synchronization issues
- Simplified deployment process

### 🗑️ Eliminated
- `docs/` folder (confusing duplicate)
- `update_website.py` (complex copying logic)
- Multiple sources of truth
- File sync scripts

### 📁 Old vs New
```bash
# OLD (complex)
data/ → docs/data/    # Copy with potential misses  
results/ → docs/data/ # Copy with conflicts
# Different folder structures

# NEW (simple)  
rankings/data/        # Single source of truth
# One folder, no copying needed
```

## Troubleshooting

**Q: Combined junior still shows error?**
A: Run `python update_rankings.py` to ensure all files are present

**Q: Development differs from production?**  
A: Impossible now - they use the same files!

**Q: Missing ranking files?**
A: Check `rankings/data/` - that's the only place they should be