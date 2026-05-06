import os
import psutil

try:
    import winreg
except ImportError:
    winreg = None

def get_steam_path():
    if winreg is None:
        return os.path.expanduser("~/.local/share/Steam")
    try:
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(hkey, "SteamPath")
        winreg.CloseKey(hkey)
        return steam_path
    except Exception:
        return r"C:\Program Files (x86)\Steam"

def is_steam_running():
    for p in psutil.process_iter(['name']):
        if p.info['name'] and p.info['name'].lower() == 'steam.exe':
            return True
    return False

def kill_steam():
    killed = False
    target_processes = ['steam.exe', 'steamwebhelper.exe', 'steamservice.exe']
    for p in psutil.process_iter(['name']):
        if p.info['name'] and p.info['name'].lower() in target_processes:
            try:
                p.kill()
                p.wait()
                killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    return killed
