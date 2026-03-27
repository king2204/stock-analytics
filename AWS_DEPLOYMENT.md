streamlit run dashboard.py# 🚀 Portfolio Dashboard - AWS Deployment Guide

## Step 1: Setup Local Environment (ทดสอบก่อน)

```bash
# Install Streamlit
pip install streamlit

# Run locally
streamlit run streamlit_app.py
```

Visit: http://localhost:8501

---

## Step 2: Deploy to AWS Elastic Beanstalk (Recommended)

### Prerequisites:
```bash
# Install EB CLI
pip install awsebcli

# Configure AWS credentials
aws configure
```

### Deploy Steps:

```bash
# 1. Initialize Elastic Beanstalk
eb init -p python-3.11 portfolio-dashboard

# 2. Create environment
eb create portfolio-env

# 3. Deploy
eb deploy

# 4. Open in browser
eb open
```

Your app will be live at: `http://portfolio-env-xxxx.us-east-1.elasticbeanstalk.com`

---

## Step 3: Alternative - AWS Lambda + API Gateway

### Create Lambda Function:
```bash
# 1. Package the app
zip -r lambda-deployment.zip src/ requirements_streamlit.txt main.py

# 2. Upload to Lambda
# 3. Set timeout to 60 seconds
# 4. Add API Gateway trigger
```

---

## Step 4: Store Historical Data (Optional)

Enable DynamoDB or RDS to store historical results:

```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('portfolio-history')

# Save snapshot
table.put_item(Item={
    'date': str(datetime.now()),
    'total_value': summary['total_current_value'],
    'return_pct': summary['total_gain_loss_percent']
})
```

---

## AWS Cost Estimate (Monthly):

| Option | Cost | Notes |
|--------|------|-------|
| Elastic Beanstalk | $5-40 | Always running |
| Lambda | $0-5 | Pay per execution |
| EC2 | $10-50 | Full control |
| DynamoDB | $0-25 | Per request |

---

## Environment Variables (Config for AWS):

Create `.env` file or set in EB:
```bash
eb setenv YAHOO_FINANCE_API_KEY=your_key
```

---

## Monitoring & Logs:

```bash
# View logs
eb logs

# Monitor health
eb health

# SSH to instance
eb ssh
```

---

## Auto-Refresh with CloudWatch Events:

Set Lambda to trigger every hour:
```
Rate(1 hour)
```

This will update your portfolio data automatically! ⏰

---

**Questions?** Check AWS documentation or ask for help with specific steps! 🎯
