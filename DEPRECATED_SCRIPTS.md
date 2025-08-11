# Deprecated Scripts (2025-08-11)

These scripts are no longer needed with the new single source of truth approach:

## ❌ Deprecated Files
- `update_website.py` - Complex copying logic, replaced by `update_rankings.py`
- `sync_dev_prod.py` - No longer needed, dev and prod are identical
- `docs/` folder - Duplicate files, now everything in `rankings/`

## ✅ Use Instead
- `update_rankings.py` - Simple, single source of truth
- `rankings/` folder - One place for everything

## Why Deprecated
The old approach had multiple sources of truth:
- `results/` folder (some files)
- `data/` folder (other files)  
- `docs/` folder (production copies)

This caused:
- Missing files (Combined junior error)
- Dev/prod inconsistencies
- Complex synchronization logic

## Migration Complete
All functionality moved to simpler system. Old files kept for reference but should not be used.