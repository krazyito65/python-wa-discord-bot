# WeakAuras Discord Bot - Production Maintenance Guide

## 🚨 Situations When You'll Need to Act Manually

### 1. **SSL Certificate Issues** (Most Common)

**When this happens:**
- Certificate expires and auto-renewal fails
- Domain changes or DNS issues
- Email notifications about certificate problems

**Symptoms:**
- Browser shows "Not Secure" or SSL errors
- Users can't access the web interface
- Email warnings from Let's Encrypt

**What to do:**
```bash
# Check certificate status
certbot certificates

# Test renewal
certbot renew --dry-run

# Force renewal if needed
certbot renew --force-renewal

# If DNS changed, get new certificate
certbot --nginx -d bot.weakauras.wtf --email your-email@example.com --agree-tos --no-eff-email

# Check nginx after renewal
nginx -t && systemctl reload nginx
```

### 2. **Discord Bot Token Issues**

**When this happens:**
- Discord revokes/changes bot tokens
- Bot appears offline in Discord
- Authentication errors in logs

**Symptoms:**
- Bot shows as offline in Discord servers
- Commands don't respond
- "Unauthorized" errors in logs

**What to do:**
```bash
# Update token in environment file
vim /etc/weakauras-bot/production.env
# Change DISCORD_BOT_TOKEN=new_token_here

# Restart bot service
systemctl restart weakauras-bot

# Check status
systemctl status weakauras-bot
journalctl -u weakauras-bot -f
```

### 3. **Server Crashes or Reboots**

**When this happens:**
- Power outage, server restart, system updates
- Services may not start automatically

**What to check after reboot:**
```bash
# Check all services are running
systemctl status weakauras-bot weakauras-django nginx

# Start any stopped services
systemctl start weakauras-bot weakauras-django nginx

# Check logs for errors
journalctl -u weakauras-bot -u weakauras-django --since "1 hour ago"
```

### 4. **Database Corruption or Issues**

**When this happens:**
- Sudden shutdowns, disk full, hardware issues
- Web interface shows errors or missing data

**Symptoms:**
- Django shows database errors
- Statistics not loading
- Server data appears empty

**What to do:**
```bash
# Check database file
ls -la /var/lib/weakauras-bot/statistics.db

# Restore from backup if needed
cd /var/backups/weakauras-bot/
ls -la  # Find latest backup
tar -xzf weakauras-bot-backup-YYYYMMDD_HHMMSS.tar.gz

# Restore database
cp backup-folder/server_data/statistics.db /var/lib/weakauras-bot/
chown weakauras-bot:weakauras-bot /var/lib/weakauras-bot/statistics.db

# Restart services
systemctl restart weakauras-django
```

### 5. **Disk Space Full**

**When this happens:**
- Logs grow too large, backups accumulate, database grows

**Symptoms:**
- Services crash or won't start
- "No space left on device" errors
- Poor performance

**What to do:**
```bash
# Check disk usage
df -h

# Clean up logs
journalctl --vacuum-time=7d  # Keep only 7 days of system logs
find /var/log/weakauras-bot/ -name "*.log.*" -mtime +14 -delete

# Clean old backups (keep only 30 days - already automated)
find /var/backups/weakauras-bot/ -name "*.tar.gz" -mtime +30 -delete

# Check what's using space
du -sh /var/lib/weakauras-bot/*
du -sh /var/log/*
```

### 6. **High Memory/CPU Usage**

**When this happens:**
- Bot gets very busy, memory leaks, or attacks

**Symptoms:**
- System becomes slow or unresponsive
- Services crash frequently
- High load averages

**What to do:**
```bash
# Check resource usage
htop
systemctl status weakauras-bot weakauras-django

# Restart services to clear memory
systemctl restart weakauras-bot weakauras-django

# Check for unusual activity in logs
tail -f /var/log/nginx/weakauras-bot-access.log
grep ERROR /var/log/weakauras-bot/*.log
```

### 7. **Code Updates**

**When this happens:**
- You want to update the bot with new features or fixes

**Safe update process:**
```bash
# 1. Create backup first
/usr/local/bin/backup-weakauras-bot

# 2. Stop services
systemctl stop weakauras-bot weakauras-django

# 3. Update code
cd /root/git_repos/python-wa-discord-bot
git stash  # Save any local changes
git pull origin main

# 4. Update dependencies if needed
uv sync

# 5. Run database migrations
sudo -u weakauras-bot .venv/bin/python web/manage.py migrate --settings=weakauras_web.production

# 6. Collect static files
sudo -u weakauras-bot .venv/bin/python web/manage.py collectstatic --noinput --settings=weakauras_web.production

# 7. Restart services
systemctl start weakauras-bot weakauras-django

# 8. Verify everything works
systemctl status weakauras-bot weakauras-django
```

## 🔍 Regular Health Checks (Monthly)

```bash
# Check service status
systemctl status weakauras-bot weakauras-django nginx

# Check disk space
df -h

# Check recent errors
grep -i error /var/log/weakauras-bot/*.log | tail -20

# Check certificate expiration (should auto-renew at 30 days)
certbot certificates

# Verify backups are working
ls -la /var/backups/weakauras-bot/ | tail -5

# Check monitoring
/usr/local/bin/monitor-weakauras-bot
```

## 📞 Emergency Contacts & Information

**Server Details:**
- Server IP: `[Your Server IP]`
- Domain: `bot.weakauras.wtf`
- SSH Access: `ssh root@[server-ip]`

**Important File Locations:**
- Configuration: `/etc/weakauras-bot/production.env`
- Server Data: `/var/lib/weakauras-bot/`
- Logs: `/var/log/weakauras-bot/`
- Backups: `/var/backups/weakauras-bot/`
- Nginx Config: `/etc/nginx/sites-available/weakauras-bot`

**Service Commands:**
```bash
# Service management
systemctl start|stop|restart|status weakauras-bot
systemctl start|stop|restart|status weakauras-django
systemctl start|stop|restart|status nginx

# View logs in real-time
journalctl -u weakauras-bot -f
journalctl -u weakauras-django -f
tail -f /var/log/weakauras-bot/bot.log
```

**Discord Bot Settings:**
- Bot ID: `270716626469519372`
- Permissions: Application Commands, Send Messages
- OAuth URL: `https://discord.com/oauth2/authorize?client_id=270716626469519372&scope=bot+applications.commands&permissions=2048`

## 🆘 "Everything is Broken" Recovery

If everything goes wrong and you're not sure what's happening:

1. **Check if services are running:**
   ```bash
   systemctl status weakauras-bot weakauras-django nginx
   ```

2. **Restart everything:**
   ```bash
   systemctl restart weakauras-bot weakauras-django nginx
   ```

3. **Check logs for errors:**
   ```bash
   journalctl -u weakauras-bot -u weakauras-django --since "30 minutes ago"
   ```

4. **Restore from backup if needed:**
   ```bash
   cd /var/backups/weakauras-bot/
   # Find latest backup and restore as shown in Database section above
   ```

5. **Contact support or check documentation:**
   - Discord.py documentation
   - Django documentation
   - Nginx documentation
   - This server's `/root/PRODUCTION_DEPLOYMENT.md`

Remember: **Always create a backup before making changes!**
