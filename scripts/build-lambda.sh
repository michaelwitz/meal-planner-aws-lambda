#!/bin/bash

# Exit on error
set -e

echo "🚀 Building Lambda package (removing /backend prefix)..."

# Variables
BUILD_DIR=".build"
ZIP_FILE=".serverless/lambda-package.zip"

# Clean up previous builds
rm -rf $BUILD_DIR $ZIP_FILE
mkdir -p $BUILD_DIR/app .serverless

# Copy app files from backend/app to build/app
echo "📦 Copying app files (backend/app -> app)..."
cp -r backend/app/* $BUILD_DIR/app/

# Clean up unnecessary files
echo "🧹 Cleaning up test files and caches..."
find $BUILD_DIR -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find $BUILD_DIR -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find $BUILD_DIR -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find $BUILD_DIR -name "*.pyc" -delete 2>/dev/null || true
find $BUILD_DIR -name ".DS_Store" -delete 2>/dev/null || true

# Copy requirements.txt to build root for serverless-python-requirements
cp backend/app/requirements.txt $BUILD_DIR/

# Install dependencies using Docker (for ARM64 Lambda)
echo "🐳 Installing dependencies with Docker..."
docker run --rm \
  -v $(pwd)/$BUILD_DIR:/var/task \
  -w /var/task \
  --entrypoint /bin/sh \
  public.ecr.aws/lambda/python:3.11-arm64 \
  -c "pip install --no-cache-dir -r requirements.txt -t . --upgrade --platform manylinux2014_aarch64 --only-binary :all: 2>/dev/null || pip install --no-cache-dir -r requirements.txt -t . --upgrade"

# Remove requirements.txt from build (not needed in package)
rm -f $BUILD_DIR/requirements.txt
rm -f $BUILD_DIR/app/requirements.txt

# Create serverless-wsgi config (app at root, no backend)
echo '{"app":"app:create_app()"}' > $BUILD_DIR/.serverless-wsgi

# Copy serverless_wsgi.py
cp node_modules/serverless-wsgi/serverless_wsgi.py $BUILD_DIR/

# Create wsgi_handler.py
cat > $BUILD_DIR/wsgi_handler.py << 'EOF'
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lambda WSGI handler - imports app from root (no backend prefix)
"""
import json
import os
import serverless_wsgi

def load_config():
    root = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(root, ".serverless-wsgi"), "r") as f:
        return json.loads(f.read())

# Import app - it's at /app in our package
from app import create_app
wsgi_app = create_app()

def handler(event, context):
    """Lambda event handler"""
    return serverless_wsgi.handle_request(wsgi_app, event, context)
EOF

# Create the ZIP package
echo "📦 Creating ZIP package..."
cd $BUILD_DIR
zip -rq ../$ZIP_FILE . -x "*.pyc" -x "*__pycache__*" -x "*.dist-info/*" -x "*.egg-info/*"
cd ..

# Verify package structure
echo ""
echo "✅ Package structure (first 30 files):"
unzip -l $ZIP_FILE | grep -v "/$" | head -30

# Check for any 'backend' references
echo ""
echo "🔍 Checking for 'backend' references in package:"
if unzip -l $ZIP_FILE | grep -i backend > /dev/null 2>&1; then
    echo "❌ WARNING: Found 'backend' in package structure!"
    unzip -l $ZIP_FILE | grep -i backend
else
    echo "✅ No 'backend' references found in package!"
fi

# Get package size
PACKAGE_SIZE=$(ls -lh $ZIP_FILE | awk '{print $5}')
echo ""
echo "📊 Package size: $PACKAGE_SIZE"
echo "📍 Package location: $ZIP_FILE"
echo ""
echo "✅ Build complete! Package ready for deployment."
