#!/usr/bin/env python3
"""
Create a standalone HTML version for local testing (no Jekyll needed)
"""

import os
from pathlib import Path

def create_standalone_html():
    """Create a standalone index.html that can be served directly"""
    
    # Get the script directory and find rankings from there
    script_dir = Path(__file__).parent
    rankings_dir = script_dir / "rankings"
    
    if not rankings_dir.exists():
        print(f"❌ Rankings directory not found: {rankings_dir}")
        return False
    
    # Read the Jekyll template files
    try:
        with open(rankings_dir / "index.html", "r") as f:
            content = f.read()
        
        with open(rankings_dir / "_layouts/default.html", "r") as f:
            layout = f.read()
            
        with open(rankings_dir / "_includes/header.html", "r") as f:
            header = f.read()
            
        with open(rankings_dir / "_includes/footer.html", "r") as f:
            footer = f.read()
    except FileNotFoundError as e:
        print(f"❌ Could not read template files: {e}")
        return False
    
    # Remove Jekyll front matter from content
    if content.startswith("---\n"):
        lines = content.split("\n")
        # Find the end of front matter
        end_idx = 1
        for i in range(1, len(lines)):
            if lines[i] == "---":
                end_idx = i + 1
                break
        content = "\n".join(lines[end_idx:])
    
    # Replace Jekyll variables in layout
    title = "Svenska IPSC Ranking"
    layout = layout.replace("{% if page.title %}{{ page.title }} - {{ site.title }}{% else %}{{ site.title }}{% endif %}", title)
    layout = layout.replace("{{ '/styles.css' | relative_url }}", "styles.css")
    layout = layout.replace("{{ '/script.js' | relative_url }}", "script.js")
    layout = layout.replace("{% include header.html %}", header)
    layout = layout.replace("{% include footer.html %}", footer)
    layout = layout.replace("{{ content }}", content)
    
    # Write standalone version
    standalone_path = rankings_dir / "index_standalone.html"
    with open(standalone_path, "w") as f:
        f.write(layout)
    
    print(f"✅ Created {standalone_path}")
    print("🚀 Test locally with:")
    print(f"   python -m http.server 8000 --directory rankings")
    print(f"   Then visit: http://localhost:8000/index_standalone.html")
    
    return True

if __name__ == "__main__":
    create_standalone_html()