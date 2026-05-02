# HydroQuote AI - Setup Guide

## 🚀 Quick Start Guide

This guide will help you set up the HydroQuote AI application with secure credential management.

---

## 📋 Prerequisites

- Python 3.11 or higher
- Docker (optional, for containerized deployment)
- IBM watsonx.ai account with API credentials
- Git

---

## 🔧 Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/hydroquote-ai.git
cd hydroquote-ai
```

### 2. Set Up Environment Variables

**IMPORTANT**: Never commit your `.env` file to Git!

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual credentials
# Windows:
notepad .env

# Linux/Mac:
nano .env
# or
vim .env
```

**Required Configuration** (in `.env` file):
```env
# Replace these with your actual IBM watsonx.ai credentials
WATSONX_API_KEY=your_actual_api_key_here
WATSONX_PROJECT_ID=your_actual_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL=ibm/granite-13b-chat-v2
```

### 3. Get IBM watsonx.ai Credentials

1. **Log in to IBM Cloud**: https://cloud.ibm.com/
2. **Navigate to watsonx.ai**: 
   - Go to the IBM Cloud dashboard
   - Search for "watsonx.ai"
   - Create a new instance if you don't have one
3. **Get API Key**:
   - Go to "Manage" → "Access (IAM)" → "API keys"
   - Click "Create an IBM Cloud API key"
   - Copy the API key (you won't be able to see it again!)
4. **Get Project ID**:
   - Go to your watsonx.ai project
   - Click on "Manage" tab
   - Copy the Project ID

### 4. Install Dependencies

**Option A: Using pip (Local Development)**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Option B: Using Docker (Recommended for Production)**
```bash
# Build the Docker image
docker build -t hydroquote-ai .

# Or use docker-compose
docker-compose build
```

### 5. Verify Configuration

```bash
# Test that configuration loads correctly
python -c "from app.core.config import settings; print('✅ Configuration loaded successfully')"

# If you see an error about missing API key, check your .env file
```

### 6. Run the Application

**Option A: Direct Python Execution**
```bash
# Make sure virtual environment is activated
python app/main.py

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Option B: Using Docker**
```bash
# Run with docker-compose (recommended)
docker-compose up

# Or run Docker directly
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  --name hydroquote-api \
  hydroquote-ai
```

### 7. Verify Installation

Open your browser and navigate to:

- **API Root**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs
- **Configuration Info**: http://localhost:8000/config/info

You should see:
```json
{
  "status": "healthy",
  "app": "HydroQuote AI",
  "version": "2.0.0",
  "environment": "development",
  "watsonx_configured": true
}
```

---

## 🔒 Security Verification

Before proceeding, verify that your setup is secure:

### ✅ Security Checklist

Run these commands to verify:

```bash
# 1. Verify .env is NOT tracked by Git
git check-ignore .env
# Should output: .env

# 2. Check Git status
git status
# .env should NOT appear in the list

# 3. Verify .env.example has no real credentials
cat .env.example | grep "your_"
# Should show placeholder values only

# 4. Check that .gitignore includes .env
grep "^\.env$" .gitignore
# Should output: .env
```

### 🚨 If You See Issues

**Problem**: `.env` appears in `git status`
```bash
# Solution: Make sure .gitignore includes .env
echo ".env" >> .gitignore
git rm --cached .env  # Remove from Git tracking
```

**Problem**: Configuration validation fails
```bash
# Solution: Check your .env file has correct values
cat .env | grep WATSONX_API_KEY
# Should show your actual API key (not the placeholder)
```

---

## 🧪 Testing the Setup

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "app": "HydroQuote AI",
  "version": "2.0.0",
  "environment": "development",
  "watsonx_configured": true
}
```

### Test 2: Configuration Info
```bash
curl http://localhost:8000/config/info
```

Expected response (note: no API keys exposed):
```json
{
  "app_name": "HydroQuote AI",
  "app_version": "2.0.0",
  "environment": "development",
  "features": {
    "pi_download": true,
    "file_logging": false,
    "swagger_docs": true
  },
  "llm_config": {
    "model": "ibm/granite-13b-chat-v2",
    "temperature": 0.0,
    "max_tokens": 2000,
    "top_p": 1.0
  },
  "security": {
    "api_key_required": false,
    "cors_enabled": true
  }
}
```

### Test 3: API Documentation
Open http://localhost:8000/docs in your browser to see the interactive API documentation.

---

## 🐳 Docker Deployment

### Development Mode
```bash
# Start with hot reload
docker-compose up

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Production Mode
```bash
# Build production image
docker build -t hydroquote-ai:latest .

# Run with environment variables
docker run -d \
  -e WATSONX_API_KEY="your_key" \
  -e WATSONX_PROJECT_ID="your_project" \
  -e APP_ENV="production" \
  -p 8000:8000 \
  --name hydroquote-api \
  hydroquote-ai:latest

# Check logs
docker logs -f hydroquote-api

# Stop
docker stop hydroquote-api
docker rm hydroquote-api
```

---

## 🌐 Cloud Deployment

### Deploy to AWS (Elastic Beanstalk)

1. **Install EB CLI**:
   ```bash
   pip install awsebcli
   ```

2. **Initialize EB**:
   ```bash
   eb init -p docker hydroquote-ai
   ```

3. **Set environment variables**:
   ```bash
   eb setenv WATSONX_API_KEY="your_key" \
            WATSONX_PROJECT_ID="your_project" \
            APP_ENV="production"
   ```

4. **Deploy**:
   ```bash
   eb create hydroquote-prod
   eb open
   ```

### Deploy to Azure (App Service)

```bash
# Login to Azure
az login

# Create resource group
az group create --name hydroquote-rg --location eastus

# Create App Service plan
az appservice plan create \
  --name hydroquote-plan \
  --resource-group hydroquote-rg \
  --is-linux \
  --sku B1

# Create web app
az webapp create \
  --name hydroquote-api \
  --resource-group hydroquote-rg \
  --plan hydroquote-plan \
  --deployment-container-image-name hydroquote-ai:latest

# Set environment variables
az webapp config appsettings set \
  --name hydroquote-api \
  --resource-group hydroquote-rg \
  --settings \
    WATSONX_API_KEY="your_key" \
    WATSONX_PROJECT_ID="your_project" \
    APP_ENV="production"
```

### Deploy to Google Cloud (Cloud Run)

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/hydroquote-ai

# Deploy to Cloud Run
gcloud run deploy hydroquote-api \
  --image gcr.io/PROJECT_ID/hydroquote-ai \
  --platform managed \
  --region us-central1 \
  --set-env-vars WATSONX_API_KEY="your_key",WATSONX_PROJECT_ID="your_project",APP_ENV="production"
```

---

## 🔧 Troubleshooting

### Issue: "Missing required configuration"

**Cause**: Environment variables not loaded

**Solution**:
```bash
# Check if .env file exists
ls -la .env

# Verify .env has correct values
cat .env | grep WATSONX_API_KEY

# Make sure you're in the correct directory
pwd
```

### Issue: "Import errors" or "Module not found"

**Cause**: Dependencies not installed

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or rebuild Docker image
docker-compose build --no-cache
```

### Issue: "Port 8000 already in use"

**Cause**: Another process is using port 8000

**Solution**:
```bash
# Find process using port 8000
# Windows:
netstat -ano | findstr :8000

# Linux/Mac:
lsof -i :8000

# Kill the process or use a different port
uvicorn app.main:app --port 8001
```

### Issue: Docker container exits immediately

**Cause**: Configuration error or missing dependencies

**Solution**:
```bash
# Check container logs
docker logs hydroquote-api

# Run container interactively to debug
docker run -it --env-file .env hydroquote-ai /bin/bash
```

---

## 📚 Next Steps

1. **Read the Security Guide**: See [SECURITY.md](SECURITY.md) for security best practices
2. **Review the Architecture**: See [ARCHITECTURE_REDESIGN_PLAN.md](ARCHITECTURE_REDESIGN_PLAN.md)
3. **Explore the API**: Visit http://localhost:8000/docs
4. **Implement Prompts**: Add your LLM prompts in `app/prompts/`
5. **Test the System**: Run tests with `pytest`

---

## 📞 Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review [SECURITY.md](SECURITY.md) for security-related issues
3. Check application logs: `docker logs hydroquote-api`
4. Open an issue on GitHub (without exposing credentials!)

---

**Last Updated**: 2024-05-02  
**Version**: 1.0.0