# MercuryBot Systemd Service Installation

This guide explains how to set up MercuryBot as a systemd service on Linux, so it runs automatically on system boot and restarts on failure.

## Prerequisites

- Linux system with systemd
- Python 3.10 or higher
- MercuryBot installed and configured

## Installation Steps

### 1. Create Service User (Optional but recommended)

```bash
sudo useradd -r -s /bin/false mercurybot
```

### 2. Set up Installation Directory

```bash
# Create installation directory
sudo mkdir -p /opt/mercurybot

# Copy MercuryBot files
sudo cp -r /path/to/MercuryBot/* /opt/mercurybot/

# Set ownership
sudo chown -R mercurybot:mercurybot /opt/mercurybot
```

### 3. Create Python Virtual Environment

```bash
cd /opt/mercurybot
sudo -u mercurybot python3 -m venv venv
sudo -u mercurybot venv/bin/pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy .env.example to .env
sudo -u mercurybot cp .env.example .env

# Edit .env with your credentials
sudo -u mercurybot nano .env
```

### 5. Install Systemd Service

```bash
# Copy service file to systemd directory
sudo cp mercurybot.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable mercurybot

# Start the service
sudo systemctl start mercurybot
```

## Service Management

### Check Service Status

```bash
sudo systemctl status mercurybot
```

### View Logs

```bash
# View live logs
sudo journalctl -u mercurybot -f

# View recent logs
sudo journalctl -u mercurybot -n 100

# View logs with timestamps
sudo journalctl -u mercurybot --since "1 hour ago"
```

### Restart Service

```bash
sudo systemctl restart mercurybot
```

### Stop Service

```bash
sudo systemctl stop mercurybot
```

### Disable Service (prevent auto-start on boot)

```bash
sudo systemctl disable mercurybot
```

## Web Interface

The web interface will be available at:
- **URL:** `http://localhost:5000` (or your server's IP)
- **Default Port:** 5000

To change the port, edit `main.py` and modify the `web_port` parameter.

### Access from External Network

If you want to access the web interface from outside your server:

1. **Configure Firewall:**
```bash
sudo ufw allow 5000/tcp
```

2. **Use Nginx as Reverse Proxy (recommended):**

Create `/etc/nginx/sites-available/mercurybot`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/mercurybot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Troubleshooting

### Service Won't Start

1. Check logs for errors:
```bash
sudo journalctl -u mercurybot -n 50
```

2. Verify Python environment:
```bash
sudo -u mercurybot /opt/mercurybot/venv/bin/python3 --version
```

3. Test manually:
```bash
sudo -u mercurybot /opt/mercurybot/venv/bin/python3 /opt/mercurybot/main.py
```

### Permission Issues

```bash
# Reset ownership
sudo chown -R mercurybot:mercurybot /opt/mercurybot

# Verify .env file exists and is readable
sudo -u mercurybot cat /opt/mercurybot/.env
```

### High Memory Usage

Adjust memory limits in `mercurybot.service`:

```ini
MemoryMax=512M  # Reduce from 1G
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart mercurybot
```

## Security Recommendations

1. **Use a dedicated user** (don't run as root)
2. **Restrict file permissions:**
```bash
sudo chmod 600 /opt/mercurybot/.env
sudo chmod 755 /opt/mercurybot
```

3. **Enable firewall:**
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 5000/tcp  # Only if web interface is needed externally
```

4. **Use HTTPS** for web interface (with Nginx + Let's Encrypt)
5. **Regular updates:**
```bash
sudo systemctl stop mercurybot
cd /opt/mercurybot
sudo -u mercurybot git pull
sudo -u mercurybot venv/bin/pip install -r requirements.txt --upgrade
sudo systemctl start mercurybot
```

## Monitoring

### Set up Log Rotation

Create `/etc/logrotate.d/mercurybot`:

```
/var/log/mercurybot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 mercurybot mercurybot
}
```

### Monitor Resource Usage

```bash
# CPU and Memory usage
systemctl status mercurybot

# Detailed resource stats
systemd-cgtop -1
```

## Updating MercuryBot

```bash
# Stop the service
sudo systemctl stop mercurybot

# Pull latest changes
cd /opt/mercurybot
sudo -u mercurybot git pull

# Update dependencies
sudo -u mercurybot venv/bin/pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl start mercurybot

# Verify it's running
sudo systemctl status mercurybot
```
