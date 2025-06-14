# Deployment Guide - Svenska IPSC Ranking Website

## Overview

This guide explains how to deploy the Svenska IPSC Ranking website to GitHub Pages.

## Quick Start

1. **Enable GitHub Pages**
   - Go to your repository settings
   - Navigate to "Pages" section
   - Select "Deploy from a branch"
   - Choose "main" branch and "/docs" folder
   - Save the settings

2. **Update Data**
   ```bash
   # Generate new rankings (run your ranking scripts)
   python combined_skill.py
   
   # Update website data
   python update_website.py --stats
   
   # Commit and push
   git add docs/data/
   git commit -m "Update ranking data"
   git push
   ```

3. **Access Website**
   - Your site will be available at: `https://username.github.io/repository-name`
   - It may take a few minutes for changes to appear

## File Structure

```
docs/
├── index.html              # Main landing page
├── ranking.html           # Individual ranking pages
├── styles.css             # All styling
├── script.js              # JavaScript functionality
├── _config.yml            # Jekyll configuration
├── README.md              # Documentation
├── DEPLOYMENT.md          # This file
└── data/                  # JSON data files
    ├── ipsc_ranking_combined.json
    ├── ipsc_ranking_classic.json
    ├── ipsc_ranking_open.json
    ├── ipsc_ranking_production.json
    ├── ipsc_ranking_production_optics.json
    ├── ipsc_ranking_standard.json
    ├── ipsc_ranking_revolver.json
    ├── ipsc_ranking_pistol_caliber_carbine.json
    └── metadata.json
```

## Automated Deployment

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that:

- Automatically deploys on pushes to main branch
- Can be triggered manually
- Runs daily to update rankings (if configured)
- Validates data before deployment

## Manual Deployment Steps

### 1. Prepare Data

```bash
# Ensure your ranking data is up to date
python combined_skill.py

# Copy data to website
python update_website.py --stats
```

### 2. Test Locally

```bash
# Start local server
python -m http.server 8000 --directory docs

# Visit http://localhost:8000 in your browser
```

### 3. Deploy

```bash
# Add all changes
git add docs/

# Commit with descriptive message
git commit -m "Update rankings for $(date +%Y-%m-%d)"

# Push to GitHub
git push origin main
```

## Configuration

### GitHub Pages Settings

1. **Source**: Deploy from a branch
2. **Branch**: main
3. **Folder**: /docs
4. **Custom domain**: (optional) your-domain.com

### Jekyll Configuration

The `_config.yml` file contains:
- Site metadata
- Build settings
- Plugin configuration
- SEO settings

### Data Updates

The `update_website.py` script:
- Copies JSON files from `results/` to `docs/data/`
- Validates data integrity
- Updates metadata timestamps
- Shows statistics

## Troubleshooting

### Common Issues

1. **Site not updating**
   - Check GitHub Actions tab for build errors
   - Ensure you're pushing to the correct branch
   - Wait 5-10 minutes for changes to propagate

2. **Data not loading**
   - Verify JSON files are valid
   - Check browser console for errors
   - Ensure file paths are correct

3. **Styling issues**
   - Clear browser cache
   - Check CSS file is loading correctly
   - Verify responsive design on different devices

### Validation

```bash
# Validate data files only
python update_website.py --validate-only

# Check file sizes and counts
python update_website.py --stats
```

## Performance Optimization

### Data Files
- JSON files are compressed by GitHub Pages
- Large files (>1MB) may load slowly on mobile
- Consider pagination for very large datasets

### Caching
- Static files are cached by browsers
- Update metadata.json to force cache refresh
- Use versioned filenames for major updates

### Mobile Performance
- Responsive design works on all devices
- Tables scroll horizontally on small screens
- Search functionality works on touch devices

## Security

### GitHub Pages Security
- HTTPS is enforced automatically
- No server-side code execution
- Static files only

### Data Privacy
- No personal data collection
- No tracking scripts
- Public ranking data only

## Monitoring

### Analytics (Optional)
Add Google Analytics or similar:

```html
<!-- Add to <head> in HTML files -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

### Error Monitoring
- Check GitHub Actions for build failures
- Monitor browser console for JavaScript errors
- Test on multiple devices and browsers

## Backup

### Data Backup
- JSON files are version controlled in Git
- GitHub provides automatic backups
- Consider external backup for critical data

### Site Backup
- Full site is in Git repository
- Can be deployed to multiple platforms
- Export data regularly

## Custom Domain (Optional)

1. **Add CNAME file**
   ```bash
   echo "your-domain.com" > docs/CNAME
   ```

2. **Configure DNS**
   - Add CNAME record pointing to `username.github.io`
   - Or A records pointing to GitHub Pages IPs

3. **Enable HTTPS**
   - GitHub Pages automatically provides SSL
   - May take up to 24 hours to activate

## Support

For issues with:
- **GitHub Pages**: Check GitHub documentation
- **Jekyll**: See Jekyll documentation
- **Ranking System**: Create issue in this repository
- **Website Bugs**: Create issue with browser/device details

## Updates

To update the website framework:

1. **Backup current version**
2. **Test changes locally**
3. **Deploy to staging branch first**
4. **Monitor for issues**
5. **Deploy to production**

Remember to update this documentation when making significant changes to the deployment process.