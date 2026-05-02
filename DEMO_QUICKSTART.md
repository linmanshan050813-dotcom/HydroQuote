# 🚀 HydroQuote AI - Demo Quick Start Guide

## Step-by-Step Instructions to Run the Demo

### Prerequisites Check
✅ Python 3.11+ installed  
✅ Dependencies installed (`pip install -r requirements.txt`)  

---

## ⚠️ IMPORTANT: Module Import Fix

**If you see this error:**
```
ModuleNotFoundError: No module named 'app'
```

**Solution:** Use `python start_backend.py` instead of `python app/main.py`

The `start_backend.py` script properly sets up the Python path to avoid import errors.

✅ `.env` file configured with Watson NLU credentials

---

## 🎬 Method 1: One-Click Demo (Easiest!)

### Windows Users - Double-click this file:
```
start_demo.bat
```
This will automatically open two terminal windows and start both servers!

---

## 🎬 Method 2: Manual Start (Two Terminals)

### Step 1: Open TWO Terminal Windows

**Terminal 1 - Backend API:**
```bash
cd "c:/Users/Jeff Chang/Desktop/OIOteam_IBM_hackathon"
python start_backend.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 - Frontend Server:**
```bash
cd "c:/Users/Jeff Chang/Desktop/OIOteam_IBM_hackathon"
python serve_frontend.py
```

You should see:
```
======================================================================
  🌊 HydroQuote AI - Frontend Demo Server
======================================================================

📁 Serving files from: frontend/
🌐 Frontend URL: http://localhost:3000
🔌 Backend API: http://localhost:8000

⚠️  Make sure the FastAPI backend is running on port 8000!

✓ Browser opened automatically
🚀 Server is running...
```

### Step 2: Browser Opens Automatically
- The demo dashboard will open at `http://localhost:3000`
- If it doesn't open automatically, manually navigate to: `http://localhost:3000`

### Step 3: Use the Demo Dashboard
The dashboard provides:
- 📊 Real-time system status
- 🧪 Interactive API testing
- 📄 JSON response viewer
- 🔍 Watson NLU connection testing

---

## 🎬 Method 3: Manual Testing

### Option A: Test Backend API Directly

1. **Start the backend:**
```bash
python app/main.py
```

2. **Open your browser to:**
- API Root: `http://localhost:8000/`
- Health Check: `http://localhost:8000/health`
- Config Info: `http://localhost:8000/config/info`
- Swagger Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Option B: Use curl/PowerShell

**PowerShell:**
```powershell
# Test root endpoint
Invoke-WebRequest -Uri "http://localhost:8000/" | Select-Object -ExpandProperty Content

# Test health check
Invoke-WebRequest -Uri "http://localhost:8000/health" | Select-Object -ExpandProperty Content

# Test config info
Invoke-WebRequest -Uri "http://localhost:8000/config/info" | Select-Object -ExpandProperty Content
```

**curl (if installed):**
```bash
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/config/info
```

---

## 🎨 Demo Dashboard Features

### 1. System Status Monitor
- Shows if API is healthy
- Displays current configuration
- Watson NLU connection status

### 2. API Testing Buttons
- **Run All Tests**: Execute complete test suite
- **Test Health Check**: Verify API health
- **Test Configuration**: Check config endpoint
- **Test Watson NLU**: Validate Watson connection
- **Clear Results**: Reset test output

### 3. Test Results Panel
- Real-time test execution
- Color-coded results (✓ pass, ✗ fail, ⚠️ warning)
- Timestamps for each test
- Detailed error messages

### 4. JSON Response Viewer
- Pretty-printed JSON responses
- Syntax highlighting
- Scrollable for large responses

### 5. API Documentation Links
- Direct links to Swagger UI
- ReDoc documentation
- OpenAPI schema

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to API"

**Solution:**
1. Make sure backend is running: `python app/main.py`
2. Check if port 8000 is available
3. Verify no firewall blocking localhost:8000

### Problem: "Frontend won't load"

**Solution:**
1. Make sure frontend server is running: `python serve_frontend.py`
2. Check if port 3000 is available
3. Try manually opening: `http://localhost:3000`

### Problem: "Watson NLU tests fail"

**Solution:**
1. Check `.env` file has valid credentials:
   ```
   WATSON_NLU_API_KEY=your_actual_key
   WATSON_NLU_URL=your_actual_url
   ```
2. Verify credentials in IBM Cloud console
3. Check internet connection

### Problem: "Port already in use"

**Solution:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual number)
taskkill /PID <PID> /F

# Or change port in .env file
API_PORT=8001
```

---

## 📸 What You Should See

### Backend Terminal Output:
```
2024-05-02 02:46:46 - __main__ - INFO - Starting HydroQuote AI v2.0.0
2024-05-02 02:46:46 - __main__ - INFO - Environment: development
2024-05-02 02:46:46 - __main__ - INFO - Log Level: INFO
2024-05-02 02:46:46 - __main__ - INFO - API Port: 8000
2024-05-02 02:46:46 - __main__ - INFO - Watsonx Model: ibm/granite-13b-chat-v2
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Frontend Terminal Output:
```
======================================================================
  🌊 HydroQuote AI - Frontend Demo Server
======================================================================

📁 Serving files from: frontend/
🌐 Frontend URL: http://localhost:3000
🔌 Backend API: http://localhost:8000

✓ Browser opened automatically
🚀 Server is running...
```

### Browser Dashboard:
- Purple gradient background
- "HydroQuote AI" header
- Green "System Healthy" badge
- Three info cards showing API status, configuration, and Watson NLU
- Testing buttons and results panel
- JSON viewer at bottom

---

## 🎯 Demo Workflow

### Basic Demo Flow:

1. **Show System Status**
   - Point out the green "System Healthy" badge
   - Show API information card
   - Show configuration card

2. **Run Health Check Test**
   - Click "Test Health Check" button
   - Show the test result (should be green ✓)
   - Show JSON response in viewer

3. **Run Configuration Test**
   - Click "Test Configuration" button
   - Show configuration details
   - Point out security features (no secrets exposed)

4. **Run Watson NLU Test**
   - Click "Test Watson NLU" button
   - Show successful connection
   - Demonstrate real API integration

5. **Run All Tests**
   - Click "Run All Tests" button
   - Watch tests execute in sequence
   - Show comprehensive test results

6. **Show API Documentation**
   - Click on Swagger docs link: `http://localhost:8000/docs`
   - Show interactive API documentation
   - Demonstrate "Try it out" feature

---

## 🔗 Important URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend Dashboard** | http://localhost:3000 | Interactive demo interface |
| **Backend API** | http://localhost:8000 | FastAPI backend |
| **API Root** | http://localhost:8000/ | API information |
| **Health Check** | http://localhost:8000/health | System health status |
| **Configuration** | http://localhost:8000/config/info | Non-sensitive config |
| **Swagger UI** | http://localhost:8000/docs | Interactive API docs |
| **ReDoc** | http://localhost:8000/redoc | Alternative API docs |
| **OpenAPI Schema** | http://localhost:8000/openapi.json | API schema JSON |

---

## 🛑 Stopping the Demo

### Stop Backend (Terminal 1):
Press `Ctrl+C`

### Stop Frontend (Terminal 2):
Press `Ctrl+C`

---

## 💡 Pro Tips

1. **Keep both terminals visible** during demo to show real-time logs
2. **Use the "Run All Tests" button** for impressive automated testing
3. **Show the JSON viewer** to demonstrate API responses
4. **Open Swagger docs** to show interactive API documentation
5. **Refresh the dashboard** to see updated system status

---

## 📞 Need Help?

- Check `TESTING_GUIDE.md` for detailed testing instructions
- Check `BUG_REPORT.md` for known issues and fixes
- Check `README.md` for project overview
- Check `.env.example` for configuration template

---

**Ready to Demo!** 🎉

**Option 1 - One-Click (Windows):**
Double-click `start_demo.bat`

**Option 2 - Manual (Two Terminals):**
```bash
# Terminal 1
python start_backend.py

# Terminal 2
python serve_frontend.py
```

Then open http://localhost:3000 in your browser!