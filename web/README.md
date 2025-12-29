# MercuryBot Web Interface

A Flask-based web interface for managing and configuring MercuryBot.

## Features

### 🎨 Dashboard
- View bot statistics (connected servers, active stores, total deals)
- Configure platform emojis for Discord notifications
- Monitor active stores and their status

### 📨 Test Notifications
- Send test notifications to any configured server
- Select specific stores to test
- Verify notification setup before going live

### 📝 Message Templates
- View documentation for customizing notification messages
- Examples and best practices for template editing

## Access

Once the bot is running, access the web interface at:

```
http://localhost:5000
```

Or from external network (if configured):
```
http://YOUR_SERVER_IP:5000
```

## Authentication

The web interface uses simple admin authentication:
- **Login:** Enter your Discord Admin User ID (configured in `.env` as `DISCORD_ADMIN_ACC`)
- Only the configured admin can access the interface

## Configuration

Set these environment variables in your `.env` file:

```env
# Discord Admin Account (for web interface authentication)
DISCORD_ADMIN_ACC=YOUR_DISCORD_USER_ID

# Web Interface Configuration
WEB_PORT=5000                # Port to run the web server on
WEB_HOST=0.0.0.0            # Host to bind to (0.0.0.0 = all interfaces)
FLASK_SECRET_KEY=RANDOM_SECRET_KEY_CHANGE_THIS  # Session secret key
```

## Security Recommendations

1. **Change the default secret key:**
   ```bash
   python -c "import os; print(os.urandom(24).hex())"
   ```
   Use the output as your `FLASK_SECRET_KEY`

2. **Use a reverse proxy (Nginx/Apache) with HTTPS** for production
3. **Restrict access** using firewall rules or IP whitelisting
4. **Run behind a VPN** if accessing from external networks

## API Endpoints

The web interface exposes these API endpoints (requires authentication):

### GET `/api/stats`
Get bot statistics
```json
{
  "guilds": 150,
  "stores": 5,
  "total_deals": 12
}
```

### GET/POST `/api/config/emojis`
Get or update emoji configuration

### POST `/api/test-notification`
Send a test notification
```json
{
  "server_id": 123456789,
  "store_name": "epic"
}
```

## Development

### Running in Development Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot (includes web server)
python main.py
```

The web interface will start automatically on the configured port.

### File Structure

```
web/
├── app.py                  # Main Flask application
├── templates/              # HTML templates
│   ├── base.html          # Base template with navbar
│   ├── login.html         # Login page
│   ├── dashboard.html     # Main dashboard
│   ├── test_notification.html  # Test notifications
│   └── templates.html     # Template documentation
├── static/                # Static files (currently unused)
│   ├── css/
│   └── js/
└── README.md              # This file
```

## Troubleshooting

### Web interface won't start

1. **Check if port is already in use:**
   ```bash
   sudo lsof -i :5000
   ```

2. **Try a different port:**
   Edit `.env` and change `WEB_PORT=5000` to another port (e.g., 8080)

3. **Check logs:**
   Look for Flask startup messages in the bot logs

### Can't access from external network

1. **Check firewall:**
   ```bash
   sudo ufw allow 5000/tcp
   ```

2. **Verify binding:**
   Make sure `WEB_HOST=0.0.0.0` in `.env` (not `127.0.0.1`)

3. **Check router/network configuration:**
   Port forwarding may be required

### Authentication fails

1. **Verify admin ID:**
   - Get your Discord User ID (Right-click your profile → Copy ID)
   - Ensure it matches `DISCORD_ADMIN_ACC` in `.env`

2. **Check session configuration:**
   - Ensure `FLASK_SECRET_KEY` is set
   - Try clearing browser cookies

## Production Deployment

For production use, consider:

1. **Use Gunicorn or uWSGI** instead of Flask's built-in server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 web.app:app
   ```

2. **Set up Nginx reverse proxy** with SSL/TLS
3. **Enable rate limiting** to prevent abuse
4. **Use environment-specific configs** (production vs development)
5. **Set up monitoring and logging**

## Future Enhancements

Planned features:
- [ ] Advanced template editor with live preview
- [ ] User permission system (multiple admins)
- [ ] Server-specific configuration management
- [ ] Analytics and statistics dashboard
- [ ] Webhook integration for external services
- [ ] Dark/Light theme toggle
