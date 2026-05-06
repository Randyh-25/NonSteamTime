import os
import vdf
from tkinter import messagebox

def get_all_users(steam_path):
    loginusers_path = os.path.join(steam_path, "config", "loginusers.vdf")
    if not os.path.exists(loginusers_path):
        return []
    
    with open(loginusers_path, 'r', encoding='utf-8') as f:
        data = vdf.load(f)
        
    users = data.get("users", {})
    user_list = []
    for steam_id, info in users.items():
        user_list.append({
            'steam_id64': steam_id,
            'account_id': str(int(steam_id) & 0xFFFFFFFF),
            'name': info.get("PersonaName", "Unknown"),
            'recent': info.get("MostRecent") == "1"
        })
    return user_list

def parse_shortcuts_vdf(filepath):
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'rb') as f:
        raw_data = f.read()

    try:
        data = vdf.binary_loads(raw_data)
        shortcuts = data.get('shortcuts', {})
        res = []
        for key, val in shortcuts.items():
            if isinstance(val, dict) and 'AppName' in val:
                appid = val.get('appid')
                if appid:
                    raw_id = int(appid)
                    unsigned_id = raw_id & 0xFFFFFFFF
                    unsigned_id_str = str(unsigned_id)
                    
                    signed_id = unsigned_id
                    if signed_id >= 0x80000000:
                        signed_id -= 0x100000000
                    signed_id_str = str(signed_id)
                    
                    res.append({
                        'app_name': val['AppName'],
                        'appid_unsigned': unsigned_id_str,
                        'appid_signed': signed_id_str,
                        'exe': val.get('exe', '')
                    })
        return res
    except Exception as e:
        print("Failed parsing shortcuts.vdf:", e)
        return []

def safe_get_apps(data):
    try:
        store = data.get('UserLocalConfigStore', {})
        software = store.get('Software', {})
        valve = software.get('Valve', {})
        steam = valve.get('Steam', {})
        
        # vdf keys can be case sensitive and vary
        apps = steam.get('Apps')
        if apps is None:
            apps = steam.get('apps', {})
            
        return apps
    except AttributeError:
        return {}

def get_playtime(apps, appid):
    app_data = apps.get(str(appid), {})
    
    # fallback to 0 if not exist
    return int(app_data.get('Playtime', 0))

def get_case_insensitive_key(d, target_key):
    for k in d.keys():
        if k.lower() == target_key.lower():
            return k
    return target_key

def save_playtime(localconfig_path, appid, new_minutes):
    if not os.path.exists(localconfig_path):
        messagebox.showwarning("Warning", "localconfig.vdf not found!")
        return
    with open(localconfig_path, 'r', encoding='utf-8') as f:
        data = vdf.load(f)
    
    try:
        d = data
        for part in ['UserLocalConfigStore', 'Software', 'Valve', 'Steam', 'Apps']:
            key = get_case_insensitive_key(d, part)
            if key not in d:
                d[key] = {}
            d = d[key]
            
        apps = d
        appid_str = str(appid)
        if appid_str not in apps:
            apps[appid_str] = {}
            
        apps[appid_str]['Playtime'] = str(new_minutes)
        apps[appid_str]['Playtime2wks'] = str(new_minutes)
        
        with open(localconfig_path, 'w', encoding='utf-8') as f:
            vdf.dump(data, f, pretty=True)
            
    except Exception as e:
        print("Failed to save localconfig:", e)
