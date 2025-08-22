# 🚀 Development Guide

This guide explains how to run the frontend for both local development and sharing with colleagues via port forwarding.

## 📋 Setup

### For Local Development (Default)
```bash
# Uses localhost:8000 for API calls
npm run dev
```
This will use the `.env.local` file which points to `localhost:8000` for the backend.

### For Sharing with Colleagues (Port Forwarding)
1. **First, get your public IP or use a tool like ngrok:**
   ```bash
   # Option 1: Find your public IP
   curl ifconfig.me
   
   # Option 2: Use ngrok (recommended for easier setup)
   npx ngrok http 8000  # For backend
   npx ngrok http 3000  # For frontend (in separate terminal)
   ```

2. **Update the `.env.shared` file with your public IP or ngrok URL:**
   ```bash
   # Replace with your actual public IP or ngrok URL
   VITE_API_URL=http://YOUR_PUBLIC_IP:8000
   VITE_WS_URL=ws://YOUR_PUBLIC_IP:8000
   
   # Or if using ngrok:
   VITE_API_URL=https://abc123.ngrok.io
   VITE_WS_URL=wss://abc123.ngrok.io
   ```

3. **Run in shared mode:**
   ```bash
   npm run dev:shared
   ```

## 🔧 Environment Files

- `.env.local` - Used for local development (localhost)
- `.env.shared` - Used for sharing with colleagues (public IP/ngrok)

## 🌐 Port Forwarding Setup

### Method 1: Router Port Forwarding
1. Forward port 3000 (frontend) and 8000 (backend) in your router
2. Update `.env.shared` with your public IP
3. Share your public IP with colleagues

### Method 2: ngrok (Easier)
1. Install ngrok: `npm install -g ngrok`
2. Forward backend: `ngrok http 8000`
3. Forward frontend: `ngrok http 3000` (in new terminal)
4. Update `.env.shared` with ngrok URLs
5. Share the frontend ngrok URL with colleagues

## 🔄 Switching Between Modes

```bash
# Local development
npm run dev

# Shared development (for colleagues)
npm run dev:shared
```

## 🐛 Troubleshooting

### "Connection Refused" Error
- Make sure your backend is running on port 8000
- Verify the API URLs in your environment files
- Check if your firewall is blocking the ports

### Frontend Works but API Calls Fail
- Check that `.env.shared` has the correct public IP/URLs
- Verify backend is accessible from external networks
- Test API endpoint directly: `curl http://YOUR_PUBLIC_IP:8000/health`

### Ngrok Session Expired
- Free ngrok URLs expire after 8 hours
- Restart ngrok and update `.env.shared` with new URLs
