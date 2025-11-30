# Firefox Installation Guide

This extension is now compatible with **both Chrome and Firefox**.

## Prerequisites

Before installing the extension on Firefox, ensure your backend API is configured with HTTPS.

### HTTPS Configuration Required

⚠️ **Important**: Firefox enforces stricter mixed-content policies than Chrome. You **must** use HTTPS for the API endpoint.

The extension is configured to use: `https://46.202.128.11:8000/api/analyze`

If you're using a self-signed certificate, you'll need to accept it in Firefox first.

## Installation Steps

### 1. Accept Self-Signed Certificate (if applicable)

If your VPS uses a self-signed certificate:

1. Open Firefox
2. Navigate to `https://46.202.128.11:8000/health` (or your API URL)
3. Click "Advanced" when you see the security warning
4. Click "Accept the Risk and Continue"

This only needs to be done once per Firefox profile.

### 2. Load the Extension

#### Option A: Temporary Installation (Development)

1. Open Firefox
2. Navigate to `about:debugging#/runtime/this-firefox`
3. Click **"Load Temporary Add-on..."**
4. Navigate to the `extension` folder
5. Select the `manifest.json` file
6. The extension will be loaded (valid until Firefox restart)

#### Option B: Permanent Installation (Requires Signing)

Firefox requires extensions to be signed for permanent installation. Options:

1. **Self-distribution (recommended for personal use)**:
   - Package the extension as a `.zip` file
   - Submit to [addons.mozilla.org](https://addons.mozilla.org/developers/) for signing
   - Download the signed `.xpi` file
   - Install via `about:addons` → Install Add-on From File

2. **Developer Edition (unsigned)**:
   - Install [Firefox Developer Edition](https://www.mozilla.org/firefox/developer/)
   - Set `xpinstall.signatures.required` to `false` in `about:config`
   - Load the extension permanently

## Configuration

### API Key Setup

1. Click the extension icon on any YouTube video page
2. Enter your API key when prompted
3. The key is stored locally in Firefox's storage

### Cookie Support

The extension extracts YouTube cookies to support age-restricted videos:
- Cookies are only sent to your backend API
- They're converted to Netscape format automatically
- No third-party services receive your cookies

## Differences from Chrome

The Firefox version includes these cross-browser compatibility features:

1. **Browser API Polyfill** (`js/polyfill.js`):
   - Normalizes `chrome.*` and `browser.*` APIs
   - Uses Promises instead of callbacks

2. **Firefox-specific Manifest Fields**:
   - `browser_specific_settings.gecko.id`: Required for Firefox
   - `browser_specific_settings.gecko.strict_min_version`: Minimum Firefox version (109.0)

3. **HTTPS Enforcement**:
   - API endpoint uses HTTPS by default
   - Self-signed certificates must be manually accepted

## Troubleshooting

### Extension Won't Load

**Error**: "This add-on could not be installed because it appears to be corrupt."

**Solution**: Ensure all files are present:
- `manifest.json`
- All `.js` files in `js/` folder
- `popup.html`
- Icon files (icon16.png, icon48.png, icon128.png)

### Mixed Content Errors

**Error**: "Blocked loading mixed active content"

**Solution**:
1. Check that `api.js` uses `https://` not `http://`
2. Ensure your VPS has HTTPS configured
3. Accept the self-signed certificate if applicable

### Cookies Not Working

**Error**: "Transcription introuvable ou trop courte" on age-restricted videos

**Solutions**:
1. Ensure you're logged into YouTube in Firefox
2. Check extension has `cookies` permission in `about:addons`
3. Try refreshing the YouTube page and reopening the extension

### API Connection Failed

**Error**: Network request failed or CORS error

**Solutions**:
1. Verify VPS is accessible: `curl -k https://46.202.128.11:8000/health`
2. Check CORS settings in `app/api.py` include Firefox origin
3. Ensure firewall allows HTTPS (port 8000)

## Updating API Endpoint

To use a different API endpoint:

1. Edit `extension/js/api.js`:
   ```javascript
   const API_URL = 'https://your-domain.com/api/analyze';
   ```

2. Edit `extension/popup.js` (if using standalone popup):
   ```javascript
   const API_URL = 'https://your-domain.com/api/analyze';
   ```

3. Update `manifest.json` host_permissions:
   ```json
   "host_permissions": [
       "https://your-domain.com/*"
   ]
   ```

## Security Notes

### HTTPS Requirement

Firefox blocks:
- HTTP requests from HTTPS pages (mixed content)
- Cross-origin requests without proper CORS headers
- Extensions accessing HTTP APIs from secure contexts

**Recommendation**: Use a valid SSL certificate from Let's Encrypt instead of self-signed.

### Setting Up Let's Encrypt (Optional)

```bash
# On your VPS
sudo apt-get install certbot
sudo certbot certonly --standalone -d yourdomain.com
```

Then update your `docker-compose.yml` or Nginx config to use the certificate.

## Development

### Testing Changes

After modifying extension code:

1. Go to `about:debugging#/runtime/this-firefox`
2. Find "YouTube Argument Analyzer"
3. Click **Reload** button

### Debugging

1. Click **Inspect** next to the extension in `about:debugging`
2. Console logs appear in the debugger
3. Check Network tab for API requests

## Support

For issues specific to Firefox compatibility:
1. Check browser console (F12) for error messages
2. Verify HTTPS certificate is accepted
3. Test API endpoint directly in Firefox
4. Review CORS configuration on backend

## Version Compatibility

- **Minimum Firefox Version**: 109.0
- **Manifest Version**: 3
- **Required Permissions**: activeTab, scripting, storage, cookies
