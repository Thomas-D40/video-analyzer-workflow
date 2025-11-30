# HTTPS Configuration & Testing Guide

This project includes **automatic HTTPS support** via Nginx reverse proxy with self-signed SSL certificates.

## Architecture

```
Browser Extension → HTTPS:8000/8443 (Nginx) → HTTP:8000 (FastAPI) → MongoDB
```

### Components
1. **Nginx** - Reverse proxy handling HTTPS
2. **Self-signed SSL Certificate** - Auto-generated on first run
3. **FastAPI** - Internal HTTP (not exposed externally)

## Port Configuration

**Note**: VPS Hostinger uses ports 80 and 443 for the control panel, so we use alternative ports.

| Port | Protocol | Purpose |
|------|----------|---------|
| 8000 | HTTPS    | Main HTTPS endpoint (extension uses this) |
| 8443 | HTTPS    | Alternative HTTPS endpoint |

## Quick Setup

### 1. Deploy to VPS

```bash
# Push changes (triggers GitHub Actions)
git push origin main

# Or manually on VPS:
cd /opt/video-analyzer
git pull origin main
docker compose down
docker compose up -d --build
```

Wait 2-3 minutes for deployment to complete.

### 2. Verify Deployment

Check GitHub Actions:
- https://github.com/Thomas-D40/video-analyzer-workflow/actions
- Look for "Deploy to VPS" workflow
- Should show ✅ green checkmark

### 3. Accept Self-Signed Certificate

#### Chrome
1. Navigate to `https://46.202.128.11:8000`
2. You'll see "Your connection is not private"
3. Click **"Advanced"**
4. Click **"Proceed to 46.202.128.11 (unsafe)"**
5. ✅ Certificate accepted!

**Pro tip**: Type `thisisunsafe` anywhere on the warning page to bypass.

#### Firefox
1. Navigate to `https://46.202.128.11:8000`
2. You'll see "Warning: Potential Security Risk Ahead"
3. Click **"Advanced"**
4. Click **"Accept the Risk and Continue"**
5. ✅ Certificate accepted!

## SSL Certificate Details

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

## Custom Certificate (Optional)

### Option 1: Let's Encrypt (Requires Domain)

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

## Security Features

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

## Testing

### 1. Test HTTPS Endpoint

```bash
# Test health endpoint (port 8000)
curl -k https://46.202.128.11:8000/health

# Expected response:
{"status": "ok"}

# Alternative: port 8443
curl -k https://46.202.128.11:8443/health
```

### 2. Test API Endpoint

```bash
# Test with API key
curl -k -X POST https://46.202.128.11:8000/api/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### 3. Test Chrome Extension

1. Go to `chrome://extensions/`
2. Find "YouTube Argument Analyzer"
3. Click **🔄 Reload**
4. Open YouTube video
5. Click extension icon
6. Click "Analyser"
7. Check console (F12):
   ```
   [Config] Environment: development
   [Config] API URL: https://46.202.128.11:8000/api/analyze
   ```
8. ✅ Should work with HTTPS

### 4. Test Firefox Extension

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
   [Config] API URL: https://46.202.128.11:8000/api/analyze
   ```
5. ✅ Should work with HTTPS!

### 5. Check Certificate

```bash
# View certificate details (port 8000)
openssl s_client -connect 46.202.128.11:8000 -showcerts

# Or port 8443
openssl s_client -connect 46.202.128.11:8443 -showcerts
```

### 6. Check Ports

```bash
# Check which ports are listening
sudo netstat -tlnp | grep -E ':(8000|8443)'

# Expected:
tcp  0.0.0.0:8000  LISTEN  (docker-proxy)
tcp  0.0.0.0:8443  LISTEN  (docker-proxy)
```

## Monitoring

### Nginx Logs

```bash
# Access logs
docker compose logs -f nginx

# Error logs
docker compose exec nginx tail -f /var/log/nginx/error.log
```

### Container Status

```bash
docker compose ps

# Expected:
NAME                STATUS
nginx               Up (healthy)
api                 Up
mongo               Up
```

## Troubleshooting

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
# 1. Port in use → sudo lsof -i :8000
# 2. Certificate generation failed → check logs
# 3. nginx config error → docker compose logs nginx
```

### Ports Already in Use

**Symptom**: nginx fails to start with "port already allocated"

**Solution**: This is already handled in our config.
- Ports 80/443 are used by Hostinger control panel (expected)
- We use ports 8000 and 8443 instead
- If 8000 or 8443 are also in use:
```bash
# Check what's using these ports
sudo lsof -i :8000
sudo lsof -i :8443
```

### Extension Shows SSL Errors

**Check**:
1. Certificate has been accepted in browser (navigate to https://46.202.128.11:8000 first)
2. Extension permissions include https://46.202.128.11:8000/* in manifest.json
3. Check browser console for specific SSL errors

### Extension Shows ERR_SSL_PROTOCOL_ERROR

**In Development Mode (unpacked):**
- Extension uses HTTP, not HTTPS
- This is normal and expected
- HTTP works fine for local testing

**In Production Mode (published):**
- Extension uses HTTPS
- Need to accept self-signed certificate first
- See "Accept Self-Signed Certificate" section above

## Success Checklist

- [ ] GitHub Actions deployment succeeded
- [ ] `https://46.202.128.11:8000` accessible
- [ ] Certificate accepted in Chrome
- [ ] Certificate accepted in Firefox
- [ ] API health check returns `{"status": "ok"}`
- [ ] Chrome extension works
- [ ] Firefox extension works
- [ ] No SSL errors in browser console
- [ ] Hostinger control panel still accessible on ports 80/443

## Expected Results

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
[Config] API URL: https://46.202.128.11:8000/api/analyze
[Cookies] Extracted 15 YouTube cookies
POST https://46.202.128.11:8000/api/analyze 200 OK
```

## Additional Resources

- [Nginx SSL Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Let's Encrypt](https://letsencrypt.org/)
- [SSL Labs Test](https://www.ssllabs.com/ssltest/)
