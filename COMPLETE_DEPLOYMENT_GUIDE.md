# Portfolio Performance Dashboard - Complete AWS Deployment Guide

## 🚀 Quick Start: Local Testing (ขั้นที่ 1)

```bash
# 1. Install dependencies
pip install -r requirements_streamlit.txt

# 2. Run locally
streamlit run streamlit_app.py

# Should open: http://localhost:8501
```

---

## 📦 Phase 1: Prepare for AWS (ขั้นที่ 2-3)

### Create Deployment Structure:

```
portfolio-dashboard/
├── streamlit_app.py
├── src/
│   ├── __init__.py
│   ├── portfolio.py
│   ├── data_fetcher.py
│   ├── analyzer.py
│   └── reporter.py
├── requirements_streamlit.txt
├── .streamlit/
│   └── config.toml
├── .ebextensions/
│   └── python.config
└── .gitignore
```

---

## 🔧 Step 1: Create Streamlit Config File

Create `.streamlit/config.toml`:

```toml
[server]
port = 8501
headless = true
runOnSave = true
logger.level = "error"

[client]
showErrorDetails = false

[theme]
primaryColor = "#0066cc"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#31333F"
font = "sans serif"
```

---

## 🗄️ Step 2: Setup AWS RDS (Store Historical Data)

### Create PostgreSQL Database:

```sql
-- Create table for historical data
CREATE TABLE portfolio_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stock_symbol VARCHAR(10),
    current_price FLOAT,
    current_value FLOAT,
    gain_loss_dollars FLOAT,
    gain_loss_percent FLOAT,
    total_portfolio_value FLOAT,
    total_return_percent FLOAT
);

-- Create index for fast queries
CREATE INDEX idx_timestamp ON portfolio_history(timestamp DESC);
```

---

## 📊 Step 3: Enhanced Streamlit App with Database

Update `streamlit_app.py` to include database storage:

```python
import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from src.portfolio import Portfolio
from src.analyzer import PortfolioAnalyzer

# Database connection
@st.cache_resource
def get_db_connection():
    return psycopg2.connect(
        host=st.secrets.get("DB_HOST"),
        database=st.secrets.get("DB_NAME"),
        user=st.secrets.get("DB_USER"),
        password=st.secrets.get("DB_PASSWORD")
    )

def save_to_db(conn, holdings_data, summary):
    """Save current snapshot to RDS"""
    cursor = conn.cursor()
    timestamp = datetime.now()

    for _, holding in holdings_data.iterrows():
        cursor.execute("""
            INSERT INTO portfolio_history
            (timestamp, stock_symbol, current_price, current_value,
             gain_loss_dollars, gain_loss_percent, total_portfolio_value, total_return_percent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            timestamp,
            holding['symbol'],
            holding['current_price'],
            holding['current_value'],
            holding['gain_loss_dollars'],
            holding['gain_loss_percent'],
            summary['total_current_value'],
            summary['total_gain_loss_percent']
        ))

    conn.commit()
    cursor.close()

# ... rest of app
```

---

## 🔑 Step 4: AWS Secrets Manager Setup

Create `secrets.toml` locally (for local testing):

```toml
DB_HOST = "your-rds-instance.xx.rds.amazonaws.com"
DB_NAME = "portfolio_db"
DB_USER = "admin"
DB_PASSWORD = "your-strong-password"
```

**For AWS**: Store in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name portfolio-db-credentials \
  --secret-string '{"DB_HOST":"...", "DB_NAME":"...", "DB_USER":"...", "DB_PASSWORD":"..."}'
```

---

## 🐳 Step 5: Create Docker Image (For Deployment)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements_streamlit.txt .
RUN pip install --no-cache-dir -r requirements_streamlit.txt

# Copy app
COPY . .

# Expose port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "streamlit_app.py"]
```

---

## ☁️ Step 6: AWS Deployment Options

### Option A: Elastic Beanstalk (Recommended for Beginners)

```bash
# 1. Initialize
eb init -p python-3.11 portfolio-dashboard

# 2. Create environment
eb create portfolio-env \
  --instance-type t3.micro \
  --envvars DB_HOST=your-rds.amazonaws.com,DB_USER=admin

# 3. Deploy
eb deploy

# 4. View logs
eb logs --all

# 5. Open in browser
eb open
```

**EB Extensions** - Create `.ebextensions/python.config`:

```yaml
commands:
  01_update:
    command: "source /var/app/venv/*/bin/activate && pip install -r /var/app/current/requirements_streamlit.txt"
    leader_only: true

option_settings:
  aws:elasticbeanstalk:application:environment:
    PYTHONPATH: /var/app/current
  aws:elasticbeanstalk:container:python:
    WSGIPath: streamlit_app.py
```

---

### Option B: ECS Fargate with Auto-Scaling

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name portfolio-dashboard

# 2. Build and push Docker image
docker build -t portfolio-dashboard .
docker tag portfolio-dashboard:latest <aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/portfolio-dashboard:latest
docker push <aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/portfolio-dashboard:latest

# 3. Create ECS cluster
aws ecs create-cluster --cluster-name portfolio-cluster

# 4. Setup CloudFormation or use AWS Console for task definition
```

---

### Option C: AWS Lambda + API Gateway (Serverless Update)

Create `lambda_handler.py`:

```python
import json
import boto3
import pandas as pd
from src.portfolio import Portfolio
from src.analyzer import PortfolioAnalyzer

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('portfolio-snapshots')

def lambda_handler(event, context):
    """Triggered hourly by CloudWatch Events"""

    portfolio = Portfolio("AWS Portfolio")
    portfolio.add_holding("AAPL", 10, 150.00, "2023-01-15")
    portfolio.add_holding("MSFT", 5, 300.00, "2023-03-20")
    portfolio.add_holding("GOOGL", 3, 2800.00, "2023-06-10")
    portfolio.add_holding("AMZN", 2, 3200.00, "2023-08-05")

    analyzer = PortfolioAnalyzer(portfolio)
    summary = analyzer.calculate_portfolio_summary()
    holdings = analyzer.calculate_current_value()

    # Save to DynamoDB
    table.put_item(Item={
        'timestamp': int(time.time()),
        'summary': json.loads(json.dumps(summary, default=str)),
        'holdings': json.loads(holdings.to_json(orient='table'))
    })

    return {'statusCode': 200, 'body': 'Success'}
```

Deploy to Lambda:

```bash
pip install -r requirements.txt -t package/
cd package
zip -r ../lambda-deployment.zip .
cd ..
zip -r lambda-deployment.zip src/ lambda_handler.py

aws lambda create-function \
  --function-name portfolio-updater \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT-ID:role/lambda-role \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://lambda-deployment.zip
```

---

## ⏰ Step 7: Auto-Refresh with CloudWatch Events

### Schedule Lambda to run every hour:

```bash
aws events put-rule \
  --name portfolio-update-schedule \
  --schedule-expression "rate(1 hour)"

aws events put-targets \
  --rule portfolio-update-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT-ID:function:portfolio-updater"
```

---

## 📱 Step 8: Real-time Updates on Cloud

### Add Auto-Refresh to Streamlit:

```python
import streamlit as st
import time

# Auto-refresh every 60 seconds
st.set_page_config(
    page_title="Portfolio Dashboard",
    initial_sidebar_state="expanded",
    layout="wide"
)

# Add refresh button
col1, col2 = st.columns([0.9, 0.1])
with col2:
    if st.button("🔄 Refresh"):
        st.rerun()

# Auto-refresh every 5 minutes
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 300:  # 5 minutes
    st.rerun()
    st.session_state.last_refresh = time.time()

# Display live timestamp
st.sidebar.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
```

---

## 📊 Step 9: Add Monitoring Dashboard

```bash
# Create CloudWatch Dashboard
aws cloudwatch put-dashboard \
  --dashboard-name PortfolioDashboard \
  --dashboard-body file://dashboard-config.json
```

---

## 💰 AWS Cost Breakdown (Estimated Monthly):

| Service | Usage | Cost |
|---------|-------|------|
| Elastic Beanstalk | t3.micro instance | $5-15 |
| RDS PostgreSQL | db.t3.micro | $15-20 |
| Lambda | ~730 calls/month | $0-1 |
| CloudWatch | Logs + Events | $2-5 |
| Data Transfer | ~1GB | $0-2 |
| **Total** | - | **$22-43/month** |

---

## ✅ Deployment Checklist:

- [ ] Test locally: `streamlit run streamlit_app.py`
- [ ] Create `.streamlit/config.toml`
- [ ] Setup RDS database
- [ ] Store credentials in AWS Secrets Manager
- [ ] Prepare Docker image (if using Fargate)
- [ ] Choose deployment option (EB recommended)
- [ ] Run `eb init` and `eb create`
- [ ] Deploy: `eb deploy`
- [ ] Setup CloudWatch auto-refresh
- [ ] Monitor logs: `eb logs`
- [ ] Setup domain (optional Route 53)

---

## 🔗 Useful AWS CLI Commands:

```bash
# Check deployment status
eb status

# View environment variables
eb printenv

# SSH to instance
eb ssh

# View real-time logs
eb logs --all --stream

# Terminate environment
eb terminate portfolio-env

# Scale instances
eb scale 2
```

---

## 🎯 Next Steps to Deploy:

1. **Today**: Test locally
2. **Tomorrow**: Setup AWS RDS
3. **Soon**: Run `eb init` and deploy
4. **Production**: Setup auto-refresh + monitoring

Ready to deploy? Let me know which option you prefer! 🚀
