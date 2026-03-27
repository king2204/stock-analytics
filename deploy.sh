#!/bin/bash

# Portfolio Dashboard - AWS Deployment Script
# This script automates the Elastic Beanstalk deployment

set -e

echo "🚀 Portfolio Dashboard - AWS Deployment Setup"
echo "=============================================="

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Install it first:"
    echo "   pip install awsebcli"
    exit 1
fi

if ! command -v eb &> /dev/null; then
    echo "❌ EB CLI not found. Install it first:"
    echo "   pip install awsebcli"
    exit 1
fi

# Configuration
APP_NAME="portfolio-dashboard"
ENV_NAME="portfolio-env"
REGION="us-east-1"  # Change this to your region
INSTANCE_TYPE="t3.micro"

echo ""
echo "📝 Configuration:"
echo "   App Name: $APP_NAME"
echo "   Environment: $ENV_NAME"
echo "   Region: $REGION"
echo "   Instance Type: $INSTANCE_TYPE"
echo ""

# Step 1: Initialize EB (if not already done)
if [ ! -d ".elasticbeanstalk" ]; then
    echo "1️⃣  Initializing Elastic Beanstalk..."
    eb init -p python-3.11 "$APP_NAME" --region "$REGION"
else
    echo "✅ Elastic Beanstalk already initialized"
fi

echo ""

# Step 2: Create environment
if [ -z "$(eb list | grep $ENV_NAME)" ]; then
    echo "2️⃣  Creating environment: $ENV_NAME"
    eb create "$ENV_NAME" \
        --instance-type "$INSTANCE_TYPE" \
        --envvars PYTHONPATH=/var/app/current

    echo "⏳ This may take 5-10 minutes. Waiting for environment to be ready..."
    eb health --refresh
else
    echo "✅ Environment already exists: $ENV_NAME"
fi

echo ""

# Step 3: Deploy
echo "3️⃣  Deploying application..."
eb deploy "$ENV_NAME"

echo ""

# Step 4: Get URL
echo "4️⃣  Getting URL..."
URL=$(eb open --print-url)
echo "✅ Dashboard URL: $URL"

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📊 Dashboard is now live at: $URL"
echo ""
echo "🔧 Useful commands:"
echo "   eb logs --all --stream       # View live logs"
echo "   eb health --refresh          # Check environment health"
echo "   eb open                      # Open in browser"
echo "   eb terminate $ENV_NAME       # Delete environment"
echo "   eb scale 2                   # Scale to 2 instances"
echo ""
