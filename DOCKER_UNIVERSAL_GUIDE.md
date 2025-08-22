# 🐳 Universal Docker Setup

## ✨ One Command, Multiple Access Methods

With this setup, **one Docker command** serves both you (localhost) and your colleague (dev tunnels) simultaneously!

---

## 🚀 Quick Start

### Single Command for Both Access Methods:
```bash
docker-compose up --build
```

That's it! Now both of these work simultaneously:

| Access Method | URL | Who Uses |
|---------------|-----|----------|
| **Localhost** | http://localhost:3000 | You (local development) |
| **Dev Tunnels** | https://pmpr6m1k-3000.inc1.devtunnels.ms | Your colleague |

---

## 🔧 How It Works

### Smart URL Detection
The frontend **automatically detects** how it's being accessed:

- **Localhost access** → Uses `http://localhost:8000` for API calls
- **Dev tunnels access** → Uses `https://pmpr6m1k-8000.inc1.devtunnels.ms` for API calls

### No Configuration Needed!
- ✅ No environment variables to change
- ✅ No separate Docker commands
- ✅ No manual URL updates
- ✅ Works for both users simultaneously

---

## 📋 Complete Workflow

### 1. Start Everything
```bash
# Navigate to project root
cd C:\Users\Dhruv Saija\Desktop\Cursor\multi-rag-bot

# Start all services
docker-compose up --build
```

### 2. Access URLs
**You (localhost):**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

**Colleague (dev tunnels):**
- Frontend: https://pmpr6m1k-3000.inc1.devtunnels.ms/
- Backend: https://pmpr6m1k-8000.inc1.devtunnels.ms/ (automatic)

### 3. Development
- Both of you can use the app simultaneously
- All changes are reflected in real-time
- Same backend data for both users

---

## 🔄 Services Started

When you run `docker-compose up --build`, you get:

| Service | Port | Purpose |
|---------|------|---------|
| **Frontend** | 3000 | React app with smart URL detection |
| **Backend** | 8000 | FastAPI with universal CORS |
| **PostgreSQL** | 5432 | Database |
| **Redis** | 6379 | Cache |
| **Qdrant** | 6333 | Vector database |

---

## 🛠️ What's Different

### Traditional Setup:
❌ Separate commands for local vs sharing  
❌ Manual URL configuration  
❌ Environment switching  
❌ CORS headaches  

### This Universal Setup:
✅ One command for everything  
✅ Automatic URL detection  
✅ Universal CORS configuration  
✅ Simultaneous access  
✅ Zero configuration switching  

---

## 🐛 Troubleshooting

### Issue: "Can't connect to backend"
**Check**: Make sure VS Code has ports 3000 and 8000 forwarded as dev tunnels

### Issue: "CORS errors"
**Already handled!** The backend automatically allows both localhost and your dev tunnel domains.

### Issue: "App loads but API calls fail"
**Solution**: 
1. Check that backend container is running: `docker-compose ps`
2. Verify dev tunnels are active in VS Code
3. Test backend directly: visit https://pmpr6m1k-8000.inc1.devtunnels.ms/health

---

## 💡 Pro Tips

### For Development:
- Use `docker-compose up -d` to run in background
- Use `docker-compose logs frontend` to see frontend logs
- Use `docker-compose restart frontend` to restart just frontend

### For Stopping:
```bash
docker-compose down
```

### For Fresh Start:
```bash
docker-compose down -v
docker-compose up --build
```

---

## 🎯 Summary

With this setup:
- **You run**: `docker-compose up --build`
- **You access**: http://localhost:3000
- **Colleague accesses**: https://pmpr6m1k-3000.inc1.devtunnels.ms/
- **Both work simultaneously** with the same backend!

No more switching between different configurations! 🎉
