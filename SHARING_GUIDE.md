# 🌐 Share Your App with Colleagues - Complete Guide

Your public IP: **14.194.54.150**

## 🚀 Quick Start (3 Steps)

### Step 1: Start Backend
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Start Frontend in Shared Mode
```bash
cd frontend
npm run dev:shared
```

### Step 3: Share URLs with Colleague
- **Frontend**: http://14.194.54.150:3000
- **Backend API**: http://14.194.54.150:8000

---

## 🔧 Detailed Setup

### For Local Development (You)
```bash
# Frontend - Uses localhost
npm run dev

# Backend - Local only
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### For Sharing (Colleagues)
```bash
# Frontend - Accessible from internet
npm run dev:shared

# Backend - Accessible from internet  
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📋 Port Forwarding Checklist

### 1. Router Configuration
- [ ] Forward port **3000** (Frontend) to your machine
- [ ] Forward port **8000** (Backend) to your machine
- [ ] Set up port forwarding for your local IP (check with `ipconfig`)

### 2. Windows Firewall
```powershell
# Allow ports through Windows Firewall
netsh advfirewall firewall add rule name="Frontend Port" dir=in action=allow protocol=TCP localport=3000
netsh advfirewall firewall add rule name="Backend Port" dir=in action=allow protocol=TCP localport=8000
```

### 3. Test Local Connectivity
```bash
# Test if backend is accessible locally
curl http://localhost:8000/health

# Test if backend is accessible from network
curl http://14.194.54.150:8000/health
```

---

## 🐛 Troubleshooting

### Issue: "Connection Refused"
**Problem**: Colleague can't reach your backend API

**Solutions**:
1. Make sure backend is running with `--host 0.0.0.0`
2. Check Windows Firewall settings
3. Verify router port forwarding
4. Test with: `curl http://14.194.54.150:8000/health`

### Issue: "CORS Error"
**Problem**: Browser blocks API requests

**Solution**: Already fixed! Backend now allows your public IP.

### Issue: "Can't Load Page"
**Problem**: Colleague can't access frontend

**Solutions**:
1. Make sure you're using `npm run dev:shared`
2. Check router forwards port 3000
3. Test with: `curl http://14.194.54.150:3000`

---

## 🔄 Easy Mode Switch

```bash
# Local development (for you)
npm run dev           # Frontend
# Backend runs on localhost

# Shared development (for colleague)
npm run dev:shared    # Frontend  
# Backend runs on 0.0.0.0
```

---

## 🌟 Alternative: Use ngrok (Easier!)

If port forwarding is too complex:

```bash
# Install ngrok
npm install -g ngrok

# Terminal 1: Backend tunnel
npx ngrok http 8000

# Terminal 2: Frontend tunnel  
npx ngrok http 3000

# Update frontend/.env.shared with ngrok URLs
```

Then share the ngrok frontend URL with your colleague!

---

## 📞 Need Help?

If something doesn't work:
1. Check this guide step by step
2. Test each step individually
3. Use ngrok as fallback option

**Your URLs to share:**
- Frontend: http://14.194.54.150:3000
- API: http://14.194.54.150:8000
