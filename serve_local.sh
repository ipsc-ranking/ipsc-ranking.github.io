#!/bin/bash
# Simple script to serve the rankings locally with Jekyll

echo "🚀 Starting Jekyll server for local development..."
echo "📂 Serving from: rankings/"
echo "🌐 Visit: http://localhost:4000"
echo "⏹️  Stop with: Ctrl+C"
echo ""

jekyll serve --source rankings --destination _site --incremental --livereload