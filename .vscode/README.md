# VS Code Debug Configuration

This directory contains VS Code debugging and task configurations for the WeakAuras Discord Bot project.

## 🚀 Available Debug Configurations

### Discord Bot Debugging
- **Debug Discord Bot (Dev)** - Debug Discord bot in development mode with Django running in background
- **Debug Discord Bot (Prod)** - Debug Discord bot in production mode with Django running in background
- **Debug Discord Bot Launcher** - Debug the run-bot.py launcher script with Django running in background
- **Debug Discord Bot (Dev) - No Background Services** - Debug bot without managing other services

### Django Web Server Debugging
- **Debug Django Web Server** - Debug Django web interface with Discord bot running in background
- **Debug Django Shell** - Debug Django management shell with bot running in background
- **Debug Django Tests** - Debug Django test suite with bot running in background
- **Debug Django Web Server - No Background Services** - Debug Django without managing other services

### General
- **Python Debugger: Current File** - Debug any currently open Python file

## 🔧 How It Works

### Automatic Service Management
When you start debugging:

1. **Bot Debug Sessions**: Stop all services, then start Django server in background for web interface access
2. **Django Debug Sessions**: Stop all services, then start Discord bot in background for full functionality
3. **Background Services**: Run with logging to `bot.log` and `django.log` files
4. **Clean State**: Every debug session starts with a clean slate by stopping all services first

### Pre-Launch Tasks
- **Stop All and Start Django Background**: Kills all services, starts Django in background (for bot debugging)
- **Stop All and Start Bot Background**: Kills all services, starts bot in background (for Django debugging)
- **Stop All Services**: Kills both services (useful for manual cleanup)

### Utility Tasks
- **View Bot Logs**: Monitor background bot logs (`tail -f bot.log`)
- **View Django Logs**: Monitor background Django logs (`tail -f django.log`)

## 📋 Usage Instructions

### 1. Normal Debugging (Recommended)
1. Open VS Code in the project root
2. Set breakpoints in your code
3. Press F5 or go to Run > Start Debugging
4. Select the appropriate debug configuration
5. The other service will automatically start in background

### 2. Manual Service Management
Use VS Code Command Palette (Ctrl+Shift+P):
- `Tasks: Run Task` > Select task to run
- `Tasks: Terminate Task` to stop running tasks

### 3. Viewing Background Logs
- Use the "View Bot Logs" or "View Django Logs" tasks
- Or manually: `tail -f bot.log` / `tail -f django.log`

### 4. Cleanup
Run the "Stop All Services" task to kill all background processes.

## ⚙️ Configuration Files

- **launch.json**: Debug configurations with pre-launch tasks
- **tasks.json**: Background service management tasks
- **settings.json**: VS Code workspace settings optimized for the project
- **README.md**: This documentation file

## 🔍 Debugging Tips

1. **Set Breakpoints**: Click in the gutter next to line numbers
2. **Watch Variables**: Add variables to the Watch panel
3. **Inspect Call Stack**: View function call hierarchy
4. **Step Through Code**: Use F10 (step over), F11 (step into), Shift+F11 (step out)
5. **Debug Console**: Execute Python expressions in the debug context

## 🔧 Troubleshooting

### Port Conflicts
If you get "port already in use" errors:
1. Run "Stop All Services" task
2. Or manually kill processes: `pkill -f 'python.*manage.py'` or `pkill -f 'python.*main.py'`

### Import Errors
The configurations set proper `PYTHONPATH` variables, but if you still get import errors:
1. Check that you're using the project's virtual environment (`.venv/bin/python`)
2. Verify the working directory is correct in launch.json

### Background Services Not Starting
Check the task output in VS Code terminal and the log files for error messages.
