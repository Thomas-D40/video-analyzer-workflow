# Quick HTTPS Testing Guide

## ✅ HTTPS Configuration Complete!

Your VPS now has full HTTPS support with automatic SSL certificate generation.

## 🚀 Step-by-Step Testing

### 1. Push Changes to VPS

```bash
git push origin main
```

This will trigger GitHub Actions to deploy automatically.

**Wait 2-3 minutes** for deployment to complete.

### 2. Verify Deployment

Check GitHub Actions:
- https://github.com/Thomas-D40/video-analyzer-workflow/actions
- Look for "Deploy to VPS" workflow
- Should show ✅ green checkmark

### 3. Accept Self-Signed Certificate

#### Chrome:
1. Navigate to `https://46.202.128.11`
2. You'll see "Your connection is not private"
3. Click **"Advanced"**
4. Click **"Proceed to 46.202.128.11 (unsafe)"**
5. ✅ Certificate accepted!

#### Firefox:
1. Navigate to `https://46.202.128.11`
2. You'll see "Warning: Potential Security Risk Ahead"
3. Click **"Advanced"**
4. Click **"Accept the Risk and Continue"**
5. ✅ Certificate accepted!

### 4. Test API Endpoint

```bash
# Test health endpoint
curl -k https://46.202.128.11/health

# Expected response:
{"status": "ok"}
```

### 5. Test Chrome Extension

1. Go to `chrome://extensions/`
2. Find "YouTube Argument Analyzer"
3. Click **🔄 Reload**
4. Open YouTube video
5. Click extension icon
6. Click "Analyser"
7. Check console (F12):
   ```
   [Config] Environment: development
   [Config] API URL: http://46.202.128.11:8000/api/analyze
   ```
8. ✅ Should work with HTTP (dev mode)

### 6. Test Firefox Extension

#### Install Extension:
1. Open Firefox
2. Navigate to `about:debugging#/runtime/this-firefox`
3. Click **"Load Temporary Add-on..."**
4. Select `extension/manifest.json`

#### Test Analysis:
1. Open YouTube video
2. Click extension icon
3. Click "Analyser"
4. Check console (F12):
   ```
   [Config] Environment: development
   [Config] API URL: http://46.202.128.11:8000/api/analyze
   ```
5. ✅ Should work!

## 🔍 Troubleshooting

### GitHub Actions Failed

```bash
# SSH to VPS manually
ssh root@46.202.128.11

# Navigate to project
cd /opt/video-analyzer

# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose down
docker compose up -d --build

# Check logs
docker compose logs -f
```

### nginx Container Won't Start

```bash
# SSH to VPS
ssh root@46.202.128.11
cd /opt/video-analyzer

# Check container status
docker compose ps

# View nginx logs
docker compose logs nginx

# Common issues:
# 1. Port 443 in use → sudo lsof -i :443
# 2. Certificate generation failed → check logs
# 3. nginx config error → docker compose logs nginx
```

### Extension Shows ERR_SSL_PROTOCOL_ERROR

**In Development Mode (unpacked):**
- Extension uses HTTP, not HTTPS
- This is normal and expected
- HTTP works fine for local testing

**In Production Mode (published):**
- Extension uses HTTPS
- Need to accept self-signed certificate first
- See step 3 above

### Cannot Accept Certificate

**Chrome:**
- Type `thisisunsafe` anywhere on the warning page
- Chrome will bypass the warning

**Firefox:**
- Ensure you click "Advanced" first
- Then "Accept the Risk"
- If still blocked, check Firefox security settings

## 📊 Expected Results

### Ports Listening:
```bash
# On VPS
sudo netstat -tlnp | grep -E ':(80|443|8000)'

# Expected:
tcp  0.0.0.0:80    LISTEN  (nginx)
tcp  0.0.0.0:443   LISTEN  (nginx)
tcp  0.0.0.0:8000  LISTEN  (nginx)
```

### Container Status:
```bash
docker compose ps

# Expected:
NAME                STATUS
nginx               Up (healthy)
api                 Up
mongo               Up
```

### Extension Console:
```javascript
// Chrome/Firefox (dev mode)
[Config] Environment: development
[Config] API URL: http://46.202.128.11:8000/api/analyze

// Chrome/Firefox (prod mode - if published)
[Config] Environment: production
[Config] API URL: https://46.202.128.11:8000/api/analyze
```

## ✨ Success Checklist

- [ ] GitHub Actions deployment succeeded
- [ ] `https://46.202.128.11` accessible
- [ ] Certificate accepted in Chrome
- [ ] Certificate accepted in Firefox
- [ ] API health check returns `{"status": "ok"}`
- [ ] Chrome extension works
- [ ] Firefox extension works
- [ ] No SSL errors in browser console

## 🎯 What You Should See

### Working Analysis:
1. Extension popup opens
2. "Analyser" button clickable
3. Loading spinner appears
4. Results display with arguments
5. Sources show scientific/web icons
6. Reliability scores displayed

### Console Output:
```
[Config] Environment: development
[Config] API URL: http://46.202.128.11:8000/api/analyze
[Cookies] Extracted 15 YouTube cookies
POST http://46.202.128.11:8000/api/analyze 200 OK
```

## 🆘 Need Help?

1. Check deployment logs: `docker compose logs -f`
2. Verify HTTPS: `curl -k https://46.202.128.11/health`
3. Review HTTPS_SETUP.md for detailed troubleshooting
4. Check extension console (F12) for errors

---

🔧 Generated with Claude Code
