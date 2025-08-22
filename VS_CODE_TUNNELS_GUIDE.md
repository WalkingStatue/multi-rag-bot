# 🚀 VS Code Dev Tunnels Setup Guide

## 📋 Your Current Setup

- **Frontend Tunnel**: https://pmpr6m1k-3000.inc1.devtunnels.ms/
- **Backend Tunnel**: https://pmpr6m1k-8000.inc1.devtunnels.ms/
- **Environment**: Docker + VS Code Dev Tunnels

## 🎯 Quick Start (3 Steps)

### 1. For Your Local Development
```bash
# Frontend (your machine)
cd frontend
npm run dev  # Uses localhost

# Backend runs in Docker with tunnels already setup
```

### 2. For Colleague Access
```bash
# Frontend (configured for tunnels)
cd frontend
npm run dev:tunnels  # Uses dev tunnels URLs

# Backend already accessible via: https://pmpr6m1k-8000.inc1.devtunnels.ms/
```

### 3. Share with Colleague
Send your colleague this URL: **https://pmpr6m1k-3000.inc1.devtunnels.ms/**

---

## 🔧 Simultaneous Usage (You + Colleague)

**✅ YES! You can both use it at the same time!**

### Your Workflow:
```bash
# Terminal 1: Your local frontend
npm run dev

# Your app runs on: http://localhost:3000
# Backend: Docker handles the tunnels automatically
```

### Colleague's Access:
- **Frontend**: https://pmpr6m1k-3000.inc1.devtunnels.ms/
- **Backend API**: https://pmpr6m1k-8000.inc1.devtunnels.ms/ (automatic)

### Both of you can:
- Work simultaneously
- Make different API calls
- Have separate sessions
- Test different features

---

## 🔄 Available Commands

| Command | Purpose | URL |
|---------|---------|-----|
| `npm run dev` | Your local development | http://localhost:3000 |
| `npm run dev:tunnels` | Tunnel-optimized mode | https://pmpr6m1k-3000.inc1.devtunnels.ms |
| `npm run dev:shared` | Legacy shared mode | For manual port forwarding |

---

## ⚙️ Configuration Files

### `.env.local` (Your development)
```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### `.env.devtunnels` (Colleague access)
```bash
VITE_API_URL=https://pmpr6m1k-8000.inc1.devtunnels.ms
VITE_WS_URL=wss://pmpr6m1k-8000.inc1.devtunnels.ms
```

---

## 🐛 Troubleshooting

### Issue: Colleague gets "Connection Refused"
**Solution**: Make sure VS Code has the tunnels active
1. Check VS Code status bar for tunnel indicators
2. Verify backend is running in Docker
3. Test: `curl https://pmpr6m1k-8000.inc1.devtunnels.ms/health`

### Issue: "Mixed Content" errors
**Solution**: Already handled! We use HTTPS tunnels for both frontend and backend.

### Issue: Tunnels expire
**Solution**: VS Code dev tunnels are persistent as long as VS Code is open.

---

## 💡 Best Practices

### For You (Development)
1. Use `npm run dev` for your daily work
2. Only use `npm run dev:tunnels` when testing with colleague
3. Keep VS Code open to maintain tunnels

### For Colleague
1. Always use the tunnel URL: https://pmpr6m1k-3000.inc1.devtunnels.ms/
2. Refresh page if you see connection issues
3. Ask you to restart if tunnels seem down

---

## 🔧 VS Code Tunnel Management

### Check Tunnel Status
In VS Code:
- Look for tunnel indicator in status bar
- Go to Command Palette → "Ports: Focus on Ports View"

### Restart Tunnels
1. Close the forwarded ports in VS Code
2. Re-forward ports 3000 and 8000
3. Update URLs if they change

### New Tunnel URLs
If VS Code generates new tunnel URLs:
1. Update `.env.devtunnels` with new URLs
2. Update `backend/main.py` CORS settings
3. Restart both frontend and backend

---

## 🌟 Advantages of This Setup

✅ **Simultaneous Access**: You both can use it at the same time  
✅ **HTTPS**: Secure tunnels with SSL  
✅ **No Router Config**: No port forwarding needed  
✅ **Easy Sharing**: Just share one URL  
✅ **Docker Integration**: Works perfectly with your Docker setup  
✅ **Persistent**: Tunnels stay active while VS Code is open  

---

## 📞 Need Help?

### Quick Tests
```bash
# Test backend health
curl https://pmpr6m1k-8000.inc1.devtunnels.ms/health

# Should return: {"status": "healthy"}
```

### If something breaks:
1. Check VS Code tunnel status
2. Restart Docker containers
3. Run `npm run dev:tunnels` instead of `npm run dev`
4. Share new tunnel URLs if they changed
