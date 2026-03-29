# Deployment Guide

Complete guide for deploying the Portfolio Performance Dashboard to production.

## 🚀 Quick Deploy (Streamlit Cloud - 5 minutes)

### Step 1: Prepare GitHub Repository

```bash
# 1. Push code to GitHub
git add .
git commit -m "feat: Add DCA simulator and documentation"
git push origin main

# 2. Verify files are on GitHub:
# - streamlit_advanced.py
# - src/ directory
# - requirements_streamlit.txt
# - README.md
```

### Step 2: Create Streamlit Account

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign up with GitHub account
3. Authorize Streamlit to access your GitHub

### Step 3: Deploy

1. Click "Create app" button
2. Select:
   - **GitHub repo**: `yourusername/portfolio-performance-dashboard`
   - **Branch**: `main`
   - **Main file path**: `streamlit_advanced.py`
3. Click "Deploy"

**Wait 1-3 minutes** ⏳ for build & deploy...

### Step 4: Access Live App

Get your URL:
```
https://share.streamlit.io/yourusername/portfolio-performance-dashboard/main/streamlit_advanced.py
```

**New deployments**: https://share.streamlit.io/yourusername/portfolio-performance-dashboard/main/streamlit_advanced.py

**Share this link** with HR/interviewers!

---

## 📋 Streamlit Cloud Setup Checklist

### Before Deploying
- [ ] Code is in GitHub public repository
- [ ] `streamlit_advanced.py` exists in root
- [ ] `requirements_streamlit.txt` has all dependencies
- [ ] `.gitignore` includes `.streamlit/secrets.toml`
- [ ] No hardcoded secrets in code
- [ ] README.md documents the project
- [ ] Local testing passes: `streamlit run streamlit_advanced.py`

### After Deploying
- [ ] App loads without errors (check "Logs" in Streamlit Cloud dashboard)
- [ ] Dashboard tab displays charts
- [ ] Stock prices update when you click "Refresh" button
- [ ] Simulator tab loads without errors
- [ ] Run a test simulation
- [ ] Share URL with interviewers

---

## 🚨 Troubleshooting Deployment

### "ModuleNotFoundError: No module named 'src'"

**Solution**: Ensure `src/__init__.py` exists:
```bash
touch src/__init__.py
git add src/__init__.py
git push
```

### "Failed to fetch prices from Yahoo Finance"

**Cause**: yfinance API temporary outage or network issue
**Solution**: Click "Refresh" button or wait 5 minutes and reload

### "Unable to import streamlit"

**Cause**: `requirements_streamlit.txt` is incorrect
**Solution**: Verify format:
```
streamlit>=1.28.0
plotly>=5.18.0
pandas>=2.2.0
yfinance>=0.2.32
scipy>=1.12.0
requests>=2.31.0
python-dotenv>=1.0.0
numpy>=1.26.0
```

### "Deploy fails, can't see logs"

**Solution**:
1. Go to Streamlit Cloud dashboard
2. Click on your app
3. Click "Settings" → "Advanced settings"
4. Check "Show logs" option
5. Rerun deployment
6. View logs in real-time

---

## 🔑 Secrets Management

### No Secrets Required (For Now)

This app uses only public Yahoo Finance data, so **no secrets needed**.

### If You Add Secrets Later

1. Create `.streamlit/secrets.toml`:
```toml
[database]
host = "your-db.com"
user = "your-username"
password = "your-password"

[api_keys]
api_key_name = "your-secret-key"
```

2. Add to `.gitignore`:
```
.streamlit/secrets.toml
.streamlit/secrets.toml.local
```

3. In Streamlit Cloud dashboard:
   - App → Settings → Secrets
   - Paste contents of secrets.toml
   - Save

4. In code:
```python
import streamlit as st
password = st.secrets["database"]["password"]
```

---

## 🐳 Docker Deployment (Self-Hosted)

### Build Docker Image

Create `Dockerfile` in project root:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY requirements_streamlit.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements_streamlit.txt

# Copy app code
COPY . .

# Expose port
EXPOSE 8501

# Run streamlit
CMD ["streamlit", "run", "streamlit_advanced.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Build & Run

```bash
# Build image
docker build -t portfolio-dashboard:latest .

# Run container
docker run -p 8501:8501 portfolio-dashboard:latest

# Access at: http://localhost:8501
```

### Push to Docker Hub

```bash
# Tag image
docker tag portfolio-dashboard:latest yourusername/portfolio-dashboard:latest

# Login to Docker Hub
docker login

# Push
docker push yourusername/portfolio-dashboard:latest

# Others can run:
docker run -p 8501:8501 yourusername/portfolio-dashboard:latest
```

---

## ☁️ AWS Deployment

### Option 1: AWS Elastic Beanstalk (Easy)

1. **Install EB CLI**:
```bash
pip install awsebcli
```

2. **Initialize project**:
```bash
eb init -p python-3.10 portfolio-dashboard
```

3. **Create environment**:
```bash
eb create portfolio-dashboard-env
```

4. **Deploy**:
```bash
eb deploy
```

5. **Open app**:
```bash
eb open
```

### Option 2: AWS EC2 (More Control)

1. **Launch EC2 instance** (Ubuntu 20.04+)
2. **SSH into instance**:
```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

3. **Install dependencies**:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
```

4. **Clone repo**:
```bash
git clone https://github.com/yourusername/portfolio-performance-dashboard.git
cd portfolio-performance-dashboard
```

5. **Setup Streamlit**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_streamlit.txt
```

6. **Configure Streamlit** (`~/.streamlit/config.toml`):
```toml
[server]
port = 8501
headless = true
runOnSave = true

[browser]
gatherUsageStats = false
```

7. **Run with systemd** (auto-restart):
```bash
sudo tee /etc/systemd/system/streamlit.service > /dev/null << EOF
[Unit]
Description=Streamlit Portfolio Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/portfolio-performance-dashboard
Environment="PATH=/home/ubuntu/portfolio-performance-dashboard/venv/bin"
ExecStart=/home/ubuntu/portfolio-performance-dashboard/venv/bin/streamlit run streamlit_advanced.py --server.port 8501 --server.address 0.0.0.0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable streamlit
sudo systemctl start streamlit
```

8. **Using nginx as reverse proxy**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Option 3: AWS Lambda + API Gateway (Serverless)

Not recommended for Streamlit apps (better suited for stateless functions).

---

## 🌐 Google Cloud Deployment

### Cloud Run (Easiest)

1. **Install Google Cloud SDK**:
```bash
# macOS
brew install google-cloud-sdk

# Linux/Windows: https://cloud.google.com/sdk/docs/install
```

2. **Authenticate**:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

3. **Create `cloudbuild.yaml`**:
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/portfolio-dashboard', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/portfolio-dashboard']
  - name: 'gcr.io/cloud-builders/gke-deploy'
    args: ['run', '--filename=k8s/']
```

4. **Deploy**:
```bash
gcloud run deploy portfolio-dashboard \
  --source . \
  --platform managed \
  --region us-central1
```

---

## 🔄 Continuous Deployment (CD)

### GitHub Actions Auto-Deploy

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Streamlit Cloud

on:
  push:
    branches: [main]
    paths:
      - 'streamlit_advanced.py'
      - 'src/**'
      - 'requirements_streamlit.txt'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Trigger Streamlit Cloud deploy
        env:
          STREAMLIT_SDK_API_TOKEN: ${{ secrets.STREAMLIT_SDK_API_TOKEN }}
        run: |
          curl -X POST https://api.streamlit.cloud/api/deploy \
            -H "X-Streamlit-Token: $STREAMLIT_SDK_API_TOKEN" \
            -d '{"appId": "yourusername/portfolio-performance-dashboard"}'
```

---

## 📊 Monitoring & Logging

### Streamlit Cloud Logs

```
Dashboard → Your App → Settings → Logs
```

View real-time logs as app runs.

### Local Testing Before Deploy

```bash
# Simulate Streamlit Cloud environment
streamlit run streamlit_advanced.py \
  --logger.level=warning \
  --client.showErrorDetails=false
```

### Monitor App Performance

- **Load time**: Should be < 3 seconds
- **Refresh time**: Should update prices within 5 seconds
- **Error rate**: Monitor Streamlit Cloud dashboard

### Uptime Monitoring

Use external service like:
- **UptimeRobot**: https://uptimerobot.com
- **Pingdom**: https://www.pingdom.com
- **StatusCake**: https://www.statuscake.com

Setup to ping your app's public URL every 5 minutes.

---

## 🔒 Security Best Practices

### Before Deploying to Production

- [ ] Never commit secrets (API keys, passwords)
- [ ] Use `.gitignore` to exclude `.streamlit/secrets.toml`
- [ ] Verify no hardcoded passwords in code
- [ ] Use HTTPS (Streamlit Cloud provides free SSL)
- [ ] Keep dependencies updated: `pip install --upgrade -r requirements_streamlit.txt`
- [ ] Review GitHub repository permissions (public vs private)
- [ ] Add LICENSE file (MIT recommended)

### Network Security

- [ ] Use HTTPS/SSL (automatic on Streamlit Cloud)
- [ ] Use VPN for database connections if needed
- [ ] Implement rate limiting for public APIs
- [ ] Use secrets manager for production API keys

---

## 🚨 Rollback & Updates

### If Deployment Breaks

1. **Identify last working commit**:
```bash
git log --oneline
```

2. **Revert to previous version**:
```bash
git revert HEAD  # Creates new commit that undoes changes
git push origin main
```

3. **Streamlit Cloud auto-redeploys** within 2 minutes

### Update Safely

1. **Test locally first**:
```bash
streamlit run streamlit_advanced.py
```

2. **Run tests**:
```bash
pytest tests/
```

3. **Push to feature branch for feedback**:
```bash
git checkout -b feature/my-update
git push origin feature/my-update
# Wait for code review
```

4. **Merge to main** only after approval
5. **Streamlit Cloud auto-deploys**

---

## 📈 Scaling Considerations

### Current Setup (Suitable For)
- ✅ Personal portfolio tracking
- ✅ Interview demonstrations
- ✅ Small team of users
- ✅ Educational purposes

### When You Need to Scale

1. **Multi-user app** → Add authentication (Streamlit Enterprise)
2. **High traffic** → Use Streamlit Sharing with reserved resources
3. **Large datasets** → Add database (PostgreSQL, MongoDB)
4. **Real-time updates** → Use WebSockets or polling
5. **Complex logic** → Separate backend API from frontend

### Recommended Architecture for Scale
```
Client (React/Vue) → REST API (FastAPI) → Database (PostgreSQL)
                  ↓
             Cache (Redis)
```

---

## 📞 Support & Troubleshooting

### Common Issues & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing dependency | Add to `requirements_streamlit.txt` |
| Connection timeout | Network issue | Check internet, retry |
| `SessionState` error | Streamlit version | Upgrade: `pip install --upgrade streamlit` |
| CORS error | Frontend/backend mismatch | Not applicable for Streamlit |
| Port already in use | Another app on port | `streamlit run ... --server.port 8502` |

### Get Help

- **Streamlit Docs**: https://docs.streamlit.io/
- **Stack Overflow**: Tag `streamlit`
- **GitHub Issues**: Report bugs here
- **Streamlit Community**: https://discuss.streamlit.io/

---

## 🎯 Post-Deployment Checklist

- [ ] App loads at public URL
- [ ] Dashboard tab displays all charts
- [ ] Stock prices update correctly
- [ ] Simulator runs without errors
- [ ] Performance acceptable (< 3s page load)
- [ ] No console errors
- [ ] README renders correctly
- [ ] Share link with team/interviewers
- [ ] Monitor uptime for first week
- [ ] Collect user feedback

---

**Your app is now live! 🎉**

Share the URL:
```
https://share.streamlit.io/yourusername/portfolio-performance-dashboard/main/streamlit_advanced.py
```
