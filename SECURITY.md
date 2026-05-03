# Security Best Practices for HydroQuote AI

## 🔒 Overview

This document outlines security best practices for managing sensitive credentials and API keys in the HydroQuote AI project.

---

## 🚨 Critical Security Rules

### ❌ NEVER Do These Things

1. **NEVER commit `.env` files to Git**
   - The `.env` file contains your actual API keys and secrets
   - Always use `.env.example` as a template instead

2. **NEVER hardcode API keys in source code**
   ```python
   # ❌ BAD - Don't do this!
   api_key = "your_actual_api_key_here"
   
   # ✅ GOOD - Use environment variables
   from app.core.config import settings
   api_key = settings.watsonx_api_key
   ```

3. **NEVER log sensitive information**
   ```python
   # ❌ BAD - Don't log secrets!
   logger.info(f"API Key: {settings.watsonx_api_key}")
   
   # ✅ GOOD - Log that it's configured
   logger.info("API Key: [CONFIGURED]")
   ```

4. **NEVER expose secrets in API responses**
   ```python
   # ❌ BAD - Don't return secrets!
   return {"api_key": settings.watsonx_api_key}
   
   # ✅ GOOD - Return status only
   return {"api_key_configured": True}
   ```

5. **NEVER commit files with "secret", "key", or "credential" in the name**
   - These are automatically ignored by `.gitignore`
   - Double-check before committing

---

## ✅ Secure Configuration Setup

### Step 1: Initial Setup

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual credentials:**
   ```bash
   # Use a text editor (NOT in a public place!)
   notepad .env  # Windows
   nano .env     # Linux/Mac
   ```

3. **Add your IBM watsonx.ai credentials:**
   ```env
   WATSONX_API_KEY=your_actual_api_key_here
   WATSONX_PROJECT_ID=your_actual_project_id_here
   ```

4. **Verify `.env` is in `.gitignore`:**
   ```bash
   git check-ignore .env
   # Should output: .env
   ```

### Step 2: Verify Security

1. **Check what files Git will track:**
   ```bash
   git status
   ```
   - `.env` should NOT appear in the list
   - Only `.env.example` should be tracked

2. **Test the configuration:**
   ```bash
   python -c "from app.core.config import settings; print('Config loaded successfully')"
   ```

3. **Verify no secrets in Git history:**
   ```bash
   git log --all --full-history --source -- .env
   # Should return nothing
   ```

---

## 🔐 Environment Variable Management

### Local Development

**Option 1: Using `.env` file (Recommended)**
```bash
# Create .env file
cp .env.example .env

# Edit with your credentials
# The app will automatically load it
python app/main.py
```

**Option 2: Using shell environment variables**
```bash
# Windows PowerShell
$env:WATSONX_API_KEY="your_key"
$env:WATSONX_PROJECT_ID="your_project"
python app/main.py

# Linux/Mac
export WATSONX_API_KEY="your_key"
export WATSONX_PROJECT_ID="your_project"
python app/main.py
```

### Docker Deployment

**Option 1: Using `.env` file**
```bash
docker run --env-file .env -p 8000:8000 hydroquote-ai
```

**Option 2: Using environment variables**
```bash
docker run \
  -e WATSONX_API_KEY="your_key" \
  -e WATSONX_PROJECT_ID="your_project" \
  -p 8000:8000 \
  hydroquote-ai
```

**Option 3: Using Docker secrets (Production)**
```yaml
# docker-compose.yml
services:
  api:
    image: hydroquote-ai
    environment:
      - WATSONX_API_KEY_FILE=/run/secrets/watsonx_api_key
    secrets:
      - watsonx_api_key

secrets:
  watsonx_api_key:
    external: true
```

### Cloud Deployment

**AWS (Elastic Beanstalk / ECS)**
```bash
# Use AWS Systems Manager Parameter Store
aws ssm put-parameter \
  --name "/hydroquote/watsonx_api_key" \
  --value "your_key" \
  --type "SecureString"
```

**Azure (App Service)**
```bash
# Use Application Settings
az webapp config appsettings set \
  --name hydroquote-api \
  --settings WATSONX_API_KEY="your_key"
```

**Google Cloud (Cloud Run)**
```bash
# Use Secret Manager
gcloud secrets create watsonx-api-key --data-file=-
# Then reference in Cloud Run service
```

---

## 🛡️ Additional Security Measures

### 1. API Key Rotation

Regularly rotate your API keys:

```bash
# 1. Generate new API key in IBM Cloud
# 2. Update .env file with new key
# 3. Restart the application
# 4. Revoke old API key in IBM Cloud
```

### 2. Access Control

Limit who can access production credentials:

- **Development**: Each developer has their own API keys
- **Staging**: Shared staging credentials (limited permissions)
- **Production**: Restricted to DevOps team only

### 3. Monitoring

Monitor for suspicious activity:

```python
# Log API usage (without exposing keys)
logger.info(f"API call made by user: {user_id}")
logger.info(f"Endpoint: {endpoint}")
logger.info(f"Status: {status_code}")
```

### 4. Rate Limiting

Implement rate limiting to prevent abuse:

```python
from fastapi import FastAPI
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

@app.get("/api/quotation")
@limiter.limit("10/minute")
async def generate_quotation():
    pass
```

---

## 🔍 Security Checklist

Before committing code, verify:

- [ ] No `.env` file in Git staging area
- [ ] No hardcoded API keys in source code
- [ ] No sensitive data in log statements
- [ ] No secrets in API responses
- [ ] `.env.example` has placeholder values only
- [ ] `.gitignore` includes all sensitive file patterns
- [ ] Configuration validation is in place
- [ ] Error messages don't leak sensitive info

---

## 🚨 What to Do If Credentials Are Exposed

If you accidentally commit credentials to Git:

### Immediate Actions

1. **Revoke the exposed credentials immediately**
   ```bash
   # Go to IBM Cloud Console
   # Navigate to API Keys
   # Delete the exposed key
   ```

2. **Generate new credentials**
   ```bash
   # Create new API key in IBM Cloud
   # Update .env with new credentials
   ```

3. **Remove from Git history**
   ```bash
   # Use BFG Repo-Cleaner or git-filter-repo
   git filter-repo --path .env --invert-paths
   
   # Force push (if repository is not public yet)
   git push origin --force --all
   ```

4. **Notify your team**
   - Inform team members about the incident
   - Update all deployment environments
   - Review access logs for suspicious activity

### Prevention

- Use pre-commit hooks to scan for secrets:
  ```bash
  pip install pre-commit detect-secrets
  pre-commit install
  ```

- Enable GitHub secret scanning (if using GitHub)
- Use tools like `git-secrets` or `truffleHog`

---

## 📚 Additional Resources

- [IBM Cloud Security Best Practices](https://cloud.ibm.com/docs/security)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [12-Factor App Configuration](https://12factor.net/config)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)

---

## 📞 Security Contact

If you discover a security vulnerability:

1. **DO NOT** create a public GitHub issue
2. Email: security@hydroquote-ai.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

---

**Last Updated**: 2024-05-02  
**Version**: 1.0.0