#!/bin/bash
# ==============================================================================
# UTILITY SCRIPT - Manual Deployment Helper
# ==============================================================================
# This script is NOT required for deployment. Render auto-deploys from GitHub.
# Use this only for manual git operations if needed.
#
# Normal deployment: Just push to main branch, Render handles the rest.
# ==============================================================================

echo "🚀 Lock Zone AI Floor Plan Analyzer - Automated Deployment"
echo "=========================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Error: Not a git repository${NC}"
    echo "Please run this script from your project root directory"
    exit 1
fi

# Make build.sh executable
echo -e "${BLUE}📝 Making build.sh executable...${NC}"
chmod +x build.sh

# Check git status
echo -e "${BLUE}📊 Checking git status...${NC}"
git status

# Add all files
echo -e "${BLUE}📦 Adding all files to git...${NC}"
git add .

# Get commit message or use default
echo ""
read -p "Enter commit message (or press Enter for default): " COMMIT_MSG
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Production-ready: Advanced AI detection, tier pricing, and bulletproof error handling"
fi

# Commit changes
echo -e "${BLUE}💾 Committing changes...${NC}"
git commit -m "$COMMIT_MSG"

# Get current branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${BLUE}🌿 Current branch: $BRANCH${NC}"

# Push to GitHub
echo -e "${BLUE}🚀 Pushing to GitHub...${NC}"
git push origin $BRANCH

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ SUCCESS! Changes pushed to GitHub${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Go to your Render dashboard: https://dashboard.render.com"
    echo "2. Your app will automatically deploy"
    echo "3. Wait 3-5 minutes for build to complete"
    echo "4. Test your live app!"
    echo ""
    echo "Your GitHub repo: https://github.com/caesaralt/lockzone-ai-floorplan"
else
    echo -e "${RED}❌ Failed to push to GitHub${NC}"
    echo "Please check your internet connection and git credentials"
    exit 1
fi
