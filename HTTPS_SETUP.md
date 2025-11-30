# HTTPS Configuration Guide

This project now includes **automatic HTTPS support** via Nginx reverse proxy with self-signed SSL certificates.

## 🔒 What's Configured

### Architecture
```
Browser Extension → HTTPS:443/8000 (Nginx) → HTTP:8000 (FastAPI) → MongoDB
```

### Components
1. **Nginx** - Reverse proxy handling HTTPS
2. **Self-signed SSL Certificate** - Auto-generated on first run
3. **FastAPI** - Internal HTTP (not exposed externally)

## 🚀 Quick Start

### 1. Deploy to VPS

```bash
# Push changes
git push origin main

# GitHub Actions will automatically deploy
# Or manually on VPS:
cd /opt/video-analyzer
git pull
docker compose down
docker compose up -d --build
```

### 2. Accept Self-Signed Certificate

#### Chrome
1. Navigate to `https://46.202.128.11`
2. Click "Advanced"
3. Click "Proceed to 46.202.128.11 (unsafe)"
4. Certificate accepted for this browser

#### Firefox
1. Navigate to `https://46.202.128.11`
2. Click "Advanced"
3. Click "Accept the Risk and Continue"
4. Certificate accepted for this browser

### 3. Test Extension

The extension will automatically use HTTPS in production mode.

## 📡 Ports Configuration

| Port | Protocol | Purpose |
|------|----------|---------|
| 80   | HTTP     | Redirects to HTTPS |
| 443  | HTTPS    | Main HTTPS endpoint |
| 8000 | HTTPS    | Legacy endpoint (maps to 443) |

**Why port 8000?** For backward compatibility with existing extension configurations.

## 🔐 SSL Certificate Details

### Auto-Generated Certificate
- **Type**: Self-signed X.509
- **Validity**: 365 days
- **Algorithm**: RSA 2048-bit
- **Subject**: CN=46.202.128.11
- **SAN**: IP:46.202.128.11, DNS:localhost

### Certificate Location
- **Path**: `nginx/ssl/cert.pem` and `nginx/ssl/key.pem`
- **Auto-generated**: On first container start
- **Persisted**: Via Docker volume mount

### Regenerate Certificate

```bash
# On VPS
cd /opt/video-analyzer
docker compose down
rm -rf nginx/ssl/*.pem
docker compose up -d --build
```

## 🔧 Custom Certificate (Optional)

### Option 1: Use Let's Encrypt (Requires Domain)

If you have a domain pointing to your VPS:

```bash
# Install certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem

# Restart services
docker compose restart nginx
```

### Option 2: Use Your Own Certificate

```bash
# Copy your certificate files
cp your-cert.pem nginx/ssl/cert.pem
cp your-key.pem nginx/ssl/key.pem

# Restart nginx
docker compose restart nginx
```

## 🛡️ Security Features

### Enabled
- ✅ TLS 1.2 and 1.3
- ✅ Strong cipher suites
- ✅ HSTS (Strict-Transport-Security)
- ✅ X-Frame-Options: DENY
- ✅ X-Content-Type-Options: nosniff
- ✅ XSS Protection
- ✅ HTTP → HTTPS redirect

### CORS Configuration
- Allows all origins (for extension compatibility)
- Allows POST, GET, OPTIONS methods
- Allows Content-Type and X-API-Key headers

## 🧪 Testing

### Check HTTPS is Working

```bash
# Test HTTPS endpoint
curl -k https://46.202.128.11/health

# Test with API key
curl -k -X POST https://46.202.128.11/api/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### Check Certificate

```bash
# View certificate details
openssl s_client -connect 46.202.128.11:443 -showcerts
```

### Check Redirect

```bash
# HTTP should redirect to HTTPS
curl -I http://46.202.128.11
# Should return: HTTP/1.1 301 Moved Permanently
# Location: https://46.202.128.11/
```

## 📊 Monitoring

### Nginx Logs

```bash
# Access logs
docker compose logs -f nginx

# Error logs
docker compose exec nginx tail -f /var/log/nginx/error.log
```

### Test Extension Connection

1. Load extension in Chrome/Firefox
2. Open browser console (F12)
3. Click extension icon on YouTube video
4. Check console output:
   ```
   [Config] Environment: production
   [Config] API URL: https://46.202.128.11:8000/api/analyze
   ```

## 🔄 Troubleshooting

### Certificate Not Trusted

**Symptom**: Browser shows "Your connection is not private"

**Solution**: This is expected with self-signed certificates. Click "Advanced" and accept the risk.

**Better Solution**: Use a valid domain + Let's Encrypt

### ERR_SSL_PROTOCOL_ERROR

**Symptom**: Cannot connect via HTTPS

**Check**:
```bash
# Ensure nginx is running
docker compose ps

# Check nginx logs
docker compose logs nginx

# Verify certificate exists
docker compose exec nginx ls -la /etc/nginx/ssl/
```

### Port 443 Already in Use

**Symptom**: nginx fails to start

**Solution**:
```bash
# Check what's using port 443
sudo lsof -i :443

# Stop conflicting service
sudo systemctl stop apache2  # or nginx, if installed globally
```

### Extension Still Uses HTTP

**Check**:
1. Extension is loaded as "unpacked" (development mode)
2. Development mode uses HTTP, production uses HTTPS
3. For testing HTTPS locally, publish extension or modify config.js

## 🎯 Production Checklist

- [ ] HTTPS accessible on port 443
- [ ] HTTP redirects to HTTPS
- [ ] Certificate accepted in browser
- [ ] Extension works in Chrome
- [ ] Extension works in Firefox
- [ ] API key authentication works
- [ ] MongoDB accessible internally
- [ ] Logs are clean (no SSL errors)

## 📚 Additional Resources

- [Nginx SSL Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Let's Encrypt](https://letsencrypt.org/)
- [SSL Labs Test](https://www.ssllabs.com/ssltest/)

---

🔧 Generated with Claude Code
