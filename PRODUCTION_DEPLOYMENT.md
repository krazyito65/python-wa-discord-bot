# WeakAuras Discord Bot - Production Deployment Guide

## 🚀 Production Setup Complete

Your WeakAuras Discord Bot is now configured for production deployment with enterprise-grade security, monitoring, and reliability features.

## 🔧 Configuration Summary

### ✅ Completed Components

1. **Security & Configuration**
   - Environment-based secrets management
   - Secure file permissions (600) for sensitive files
   - Production-specific Django settings
   - External data storage outside git repository

2. **Service Management**
   - Systemd services for auto-start and management
   - `weakauras-bot.service` - Discord bot service
   - `weakauras-django.service` - Web interface service
   - Automatic restart on failure

3. **Web Server & SSL**
   - Nginx reverse proxy configuration
   - SSL/TLS ready (requires domain configuration)
   - Security headers and rate limiting
   - Static file serving optimization

4. **Monitoring & Logging**
   - Centralized logging with rotation
   - Health monitoring every 5 minutes
   - Resource usage alerts
   - Service status monitoring

5. **Backup & Recovery**
   - Daily automated backups at 2:30 AM
   - 30-day backup retention
   - Complete system state backup

6. **Security Hardening**
   - UFW firewall configured
   - SSH and HTTP/HTTPS only
   - Dedicated system user
   - Process isolation

## 🔑 Required Manual Configuration

### 1. Discord Bot Token Configuration
Edit `/etc/weakauras-bot/production.env`:
```bash
# Replace with your actual production Discord bot token
DISCORD_BOT_TOKEN=your_production_discord_bot_token_here
DISCORD_CLIENT_ID=your_discord_client_id_here
DISCORD_CLIENT_SECRET=your_discord_client_secret_here
```

### 2. Domain Configuration
Edit `/etc/nginx/sites-available/weakauras-bot`:
```nginx
# Replace your-domain.com with your actual domain
server_name your-domain.com www.your-domain.com;
```

Update allowed hosts in environment file:
```bash
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

### 3. SSL Certificate Setup
```bash
# After configuring your domain, get SSL certificates
certbot --nginx -d your-domain.com -d www.your-domain.com
```

## 🚀 Starting Services

### First-Time Setup
```bash
# 1. Configure production tokens in environment file
vim /etc/weakauras-bot/production.env

# 2. Run Django migrations
cd /root/git_repos/python-wa-discord-bot/web
sudo -u weakauras-bot /root/git_repos/python-wa-discord-bot/.venv/bin/python manage.py migrate --settings=weakauras_web.production

# 3. Collect static files
sudo -u weakauras-bot /root/git_repos/python-wa-discord-bot/.venv/bin/python manage.py collectstatic --noinput --settings=weakauras_web.production

# 4. Start services
systemctl start weakauras-bot weakauras-django nginx
systemctl enable weakauras-bot weakauras-django nginx
```

### Service Management Commands

**Use the provided management scripts (recommended):**
```bash
# Service Management
bin/prod-restart-all      # Restart all services
bin/prod-restart-bot      # Restart Discord bot only
bin/prod-restart-web      # Restart web interface only
bin/prod-status           # Complete production health check

# Log Management
bin/prod-logs-all         # View all service logs
bin/prod-logs-bot         # View Discord bot logs
bin/prod-logs-web         # View web interface logs
bin/prod-logs-status      # Check log rotation and disk usage
```

**Manual systemctl commands (if needed):**
```bash
# Check service status
systemctl status weakauras-bot weakauras-django nginx

# View logs
journalctl -u weakauras-bot -f
journalctl -u weakauras-django -f

# Restart services
systemctl restart weakauras-bot
systemctl restart weakauras-django
systemctl reload nginx

# Stop all services
systemctl stop weakauras-bot weakauras-django
```

## 📊 Monitoring & Maintenance

### Log Management & Rotation

**Automatic Log Rotation (Configured):**
- **SystemD Journal**: 100MB max total, 30-day retention, weekly rotation
- **Nginx Logs**: 10MB per file, 7-day retention, daily rotation
- **Compression**: Enabled for space efficiency

**Log Locations:**
- **SystemD Journal**: `/var/log/journal/[machine-id]/` (binary format)
- **Nginx Logs**: `/var/log/nginx/weakauras-bot-*.log` (text format)
- **Log Configuration**: `/etc/systemd/journald.conf.d/10-weakauras.conf`
- **Rotation Config**: `/etc/logrotate.d/weakauras-bot`

**Viewing Logs:**
```bash
# Use management scripts (recommended)
bin/prod-logs-all         # View all service logs
bin/prod-logs-status      # Check log sizes and rotation

# View logs in vim (text editor friendly)
journalctl -u weakauras-bot --since "1 hour ago" > /tmp/logs.txt && vim /tmp/logs.txt

# Manual systemd journal access
journalctl -u weakauras-bot -f
journalctl -u weakauras-django -f
```

### Backup Management
```bash
# Manual backup
/usr/local/bin/backup-weakauras-bot

# View backups
ls -la /var/backups/weakauras-bot/

# Restore from backup (example)
cd /var/backups/weakauras-bot/
tar -xzf weakauras-bot-backup-YYYYMMDD_HHMMSS.tar.gz
# Then manually restore files as needed
```

### Health Monitoring
```bash
# Manual health check
/usr/local/bin/monitor-weakauras-bot

# Check firewall status
ufw status verbose

# System resource usage
htop
df -h
free -h
```

## 🛡️ Security Features

- **Firewall**: Only SSH (22), HTTP (80), and HTTPS (443) allowed
- **SSL/TLS**: Forced HTTPS with security headers
- **Process Isolation**: Services run as dedicated `weakauras-bot` user
- **Secure Storage**: Sensitive files protected with 600 permissions
- **Rate Limiting**: API endpoint protection via nginx
- **Secret Management**: Environment-based configuration

## 📁 File Locations

### Configuration Files
- Environment variables: `/etc/weakauras-bot/production.env`
- Systemd services: `/etc/systemd/system/weakauras-*.service`
- Nginx configuration: `/etc/nginx/sites-available/weakauras-bot`
- Backup script: `/usr/local/bin/backup-weakauras-bot`
- Monitor script: `/usr/local/bin/monitor-weakauras-bot`

### Data Directories
- Server data: `/var/lib/weakauras-bot/`
- Static files: `/var/www/weakauras-bot/static/`
- Logs: `/var/log/weakauras-bot/`
- Backups: `/var/backups/weakauras-bot/`

## 🔄 Updates & Maintenance

### Updating the Bot
```bash
# 1. Create backup
/usr/local/bin/backup-weakauras-bot

# 2. Stop services
systemctl stop weakauras-bot weakauras-django

# 3. Update code
cd /root/git_repos/python-wa-discord-bot
git pull origin main

# 4. Update dependencies if needed
uv sync

# 5. Run migrations
sudo -u weakauras-bot .venv/bin/python web/manage.py migrate --settings=weakauras_web.production

# 6. Collect static files
sudo -u weakauras-bot .venv/bin/python web/manage.py collectstatic --noinput --settings=weakauras_web.production

# 7. Restart services
systemctl start weakauras-bot weakauras-django
```

## ⚠️ Important Notes

1. **Production Token Required**: You must configure a valid Discord production bot token
2. **Domain Required**: SSL certificates require a valid domain name
3. **External Storage**: Data is stored outside git repository for safety
4. **Regular Backups**: Automated daily backups with 30-day retention
5. **Monitoring**: Health checks run every 5 minutes with alerting

## 🆘 Troubleshooting

### Services Won't Start
1. Check environment file: `/etc/weakauras-bot/production.env`
2. Verify Discord tokens are valid
3. Check logs: `journalctl -u weakauras-bot -u weakauras-django`
4. Ensure database is accessible

### SSL Certificate Issues
1. Verify domain DNS points to this server
2. Check nginx configuration syntax: `nginx -t`
3. Run certbot manually: `certbot --nginx -d your-domain.com`

### Performance Issues
1. Check system resources: `htop`, `df -h`, `free -h`
2. Review monitoring logs: `/var/log/weakauras-bot/monitor.log`
3. Analyze nginx access patterns
4. Consider enabling additional caching

Your WeakAuras Discord Bot is now production-ready! 🎉
