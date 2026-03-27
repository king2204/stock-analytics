# 🚀 Portfolio Dashboard - AWS Deployment Checklist

## Phase 1: Pre-Deployment (Local Setup)
- [ ] Clone/pull latest code
- [ ] Create Python virtual environment: `python -m venv venv`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements_streamlit.txt`
- [ ] Test locally: `streamlit run streamlit_app.py` (should open at http://localhost:8501)
- [ ] Verify all reports display correctly
- [ ] Test data fetching from Yahoo Finance

## Phase 2: AWS Account Preparation
- [ ] Create AWS account (if needed)
- [ ] Setup AWS credentials: `aws configure`
- [ ] Verify credentials: `aws sts get-caller-identity`
- [ ] Install AWS CLI: `pip install awsebcli`

## Phase 3: AWS Database Setup (Optional but Recommended)
- [ ] Create security group for RDS
- [ ] Create PostgreSQL instance: `db.t3.micro`
- [ ] Note RDS endpoint and credentials
- [ ] Store credentials in AWS Secrets Manager
- [ ] Create DynamoDB table for historical data (alternative)

## Phase 4: Elastic Beanstalk Setup
- [ ] Initialize EB: `eb init -p python-3.11 portfolio-dashboard`
- [ ] Choose region (recommend `us-east-1`)
- [ ] Create `.ebextensions/python.config` ✅ (Already created)
- [ ] Create `.streamlit/config.toml` ✅ (Already created)
- [ ] Create `Dockerfile` ✅ (Already created)

## Phase 5: First Deployment
- [ ] Review `requirements_streamlit.txt` for all dependencies
- [ ] Update `streamlit_app.py` with AWS configs if using database
- [ ] Run: `eb create portfolio-env --instance-type t3.micro`
- [ ] Wait 5-10 minutes for environment to be ready
- [ ] Run: `eb open` to verify deployment
- [ ] Check logs: `eb logs --all`

## Phase 6: Post-Deployment Configuration
- [ ] Set environment variables: `eb setenv DB_HOST=... DB_USER=... DB_PASSWORD=...`
- [ ] Test dashboard loads correctly
- [ ] Verify data is fetching in real-time
- [ ] Check error logs: `eb health`

## Phase 7: Auto-Refresh Setup
- [ ] Create Lambda function: `lambda_handler.py` ✅ (Already created)
- [ ] Package Lambda function
- [ ] Create CloudWatch Event Rule: `rate(1 hour)`
- [ ] Add Lambda as target
- [ ] Test: Trigger manually and verify execution

## Phase 8: Monitoring & Maintenance
- [ ] Setup CloudWatch alarms for errors
- [ ] Enable EB auto-scaling (optional)
- [ ] Configure RDS backups (if using RDS)
- [ ] Setup CloudWatch dashboard
- [ ] Enable logging to CloudWatch Logs

## Phase 9: Custom Domain (Optional)
- [ ] Register domain in Route 53 (or use existing)
- [ ] Create SSL certificate in ACM
- [ ] Update EB listener to use HTTPS
- [ ] Point domain to EB endpoint

## Phase 10: Production Hardening
- [ ] Remove debug logging
- [ ] Add authentication to dashboard (optional)
- [ ] Enable WAF (Web Application Firewall)
- [ ] Setup DDoS protection
- [ ] Review and update security groups

---

## 🎯 Quick Start Commands

### Test Locally:
```bash
streamlit run streamlit_app.py
```

### Initialize EB:
```bash
eb init -p python-3.11 portfolio-dashboard
```

### Deploy:
```bash
eb create portfolio-env --instance-type t3.micro
```

### View Live:
```bash
eb open
```

### Monitor:
```bash
eb logs --all --stream
```

---

## 💾 File Structure Ready for Deployment:

```
✅ portfolio-dashboard/
   ├── streamlit_app.py (Updated for cloud)
   ├── src/
   │   ├── __init__.py
   │   ├── portfolio.py
   │   ├── data_fetcher.py
   │   ├── analyzer.py
   │   └── reporter.py
   ├── requirements_streamlit.txt ✅
   ├── .streamlit/
   │   └── config.toml ✅
   ├── .ebextensions/
   │   └── python.config ✅
   ├── Dockerfile ✅
   ├── lambda_handler.py ✅
   ├── deploy.sh ✅
   └── AWS_SETUP_COMMANDS.sh ✅
```

---

## 📊 Deployment Timeline:

| Step | Time | Notes |
|------|------|-------|
| Local testing | 10 min | Verify everything works |
| AWS setup | 15 min | Create credentials |
| RDS setup (optional) | 10-15 min | Can skip for MVP |
| EB deployment | 5-10 min | Environment creation |
| Lambda setup | 5 min | Scheduling automation |
| **Total** | **45-55 min** | First deployment ready! |

---

## 🔗 Useful Resources:

- AWS Elastic Beanstalk: https://aws.amazon.com/elasticbeanstalk/
- EB CLI Reference: https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3.html
- Streamlit Deployment: https://docs.streamlit.io/deploy
- AWS Lambda: https://aws.amazon.com/lambda/
- AWS RDS: https://aws.amazon.com/rds/

---

## ❓ Common Issues & Solutions:

### Issue: "ModuleNotFoundError: No module named 'src'"
**Solution:** Ensure `.ebextensions/python.config` installs dependencies

### Issue: "Streamlit is not allocated port"
**Solution:** Update `serverConfig` in `.streamlit/config.toml`

### Issue: "403 Access Denied to RDS"
**Solution:** Check security group allows your IP/EB instance

### Issue: "Lambda timeout"
**Solution:** Increase timeout to 60 seconds in Lambda configuration

---

## 🎉 Success Criteria:

- ✅ Streamlit app loads in browser
- ✅ Real-time stock prices display
- ✅ Portfolio metrics calculate correctly
- ✅ Charts render properly
- ✅ Auto-refresh works (every hour via Lambda)
- ✅ Data persists in database
- ✅ No errors in CloudWatch logs

---

**Ready to deploy? Run the AWS_SETUP_COMMANDS.sh next!**
