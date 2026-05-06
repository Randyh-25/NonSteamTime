import os
import subprocess
import vdf
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

from steam_utils import get_steam_path, is_steam_running, kill_steam
from vdf_utils import get_all_users, parse_shortcuts_vdf, safe_get_apps, get_playtime, save_playtime

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Steam Non-Game Playtime Manager")
        
        self.steam_path = get_steam_path()
        self.all_users = get_all_users(self.steam_path)
        
        if not self.all_users:
            ctk.CTkLabel(self, text="Could not find any Steam users.").pack(pady=50)
            return

        self.user_id = None
        for u in self.all_users:
            if u['recent']:
                self.user_id = u['account_id']
                break
        
        if not self.user_id:
            self.user_id = self.all_users[0]['account_id']
            
        self.games = []
        self.current_view = "List"
        self.images = [] # keep references to avoid garbage collection
        
        self.setup_ui()
        self.load_user_data(self.user_id) # Load data initially
        
    def load_user_data(self, account_id):
        self.user_id = account_id
        self.userdata_dir = os.path.join(self.steam_path, "userdata", self.user_id, "config")
        self.shortcuts_file = os.path.join(self.userdata_dir, "shortcuts.vdf")
        self.localconfig_file = os.path.join(self.userdata_dir, "localconfig.vdf")
        self.grid_dir = os.path.join(self.userdata_dir, "grid")
        self.cmd_load_file()
        
    def setup_ui(self):
        # Top Menu Bar
        self.top_bar = ctk.CTkFrame(self, height=50, corner_radius=0)
        self.top_bar.pack(fill="x", side="top")
        
        # Menu Buttons
        btn_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        btn_frame.pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(btn_frame, text="Load File", width=80, command=self.cmd_load_file).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Save File", width=80, command=self.cmd_save_file).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Kill Steam", width=80, fg_color="#c0392b", hover_color="#e74c3c", command=self.cmd_kill_steam).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Launch Steam", width=80, fg_color="#27ae60", hover_color="#2ecc71", command=self.cmd_launch_steam).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Tutorial", width=80, fg_color="#2980b9", hover_color="#27ae60", command=self.show_tutorial).pack(side="left", padx=5)
        
        # User Selection Dropdown
        user_options = [f"{u['name']} ({u['account_id']})" for u in self.all_users]
        
        current_value = user_options[0]
        for opt in user_options:
            if self.user_id in opt:
                current_value = opt
                break
                
        def on_user_change(choice):
            account_id = choice.split("(")[1].strip(")")
            self.load_user_data(account_id)

        self.user_dropdown = ctk.CTkOptionMenu(self.top_bar, values=user_options, command=on_user_change)
        self.user_dropdown.set(current_value)
        self.user_dropdown.pack(side="right", padx=10, pady=10)

        # View Toggle
        self.view_toggle = ctk.CTkSegmentedButton(self.top_bar, values=["List View", "Grid View"], command=self.switch_view)
        self.view_toggle.set("List View")
        self.view_toggle.pack(side="right", padx=10, pady=10)
        
        # Main content area
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def cmd_load_file(self):
        self.games = parse_shortcuts_vdf(self.shortcuts_file)
        
        self.localconfig_apps = {}
        if os.path.exists(self.localconfig_file):
            with open(self.localconfig_file, 'r', encoding='utf-8') as f:
                data = vdf.load(f)
            self.localconfig_apps = safe_get_apps(data)
            
        self.render_games()
        
    def cmd_save_file(self):
        # TODO: global save structure if applying multiple changes, currently edits save immediately
        messagebox.showinfo("Wait", "Changes are saved automatically when editing playtime.")

    def cmd_kill_steam(self):
        if kill_steam():
            messagebox.showinfo("Success", "Steam process terminated.")
        else:
            messagebox.showinfo("Info", "Steam is not running.")

    def cmd_launch_steam(self):
        if is_steam_running():
            messagebox.showinfo("Info", "Steam is already running.")
        else:
            steam_exe = os.path.join(self.steam_path, "steam.exe")
            if os.path.exists(steam_exe):
                subprocess.Popen([steam_exe, "-offline"])
            else:
                messagebox.showerror("Error", f"Could not find steam.exe at {steam_exe}")

    def show_tutorial(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Tutorial: Edit Playtime Safely")
        dialog.geometry("500x350")
        dialog.transient(self)
        dialog.grab_set()

        tutorial_text = (
            "How to Safely Edit Playtime (Without Steam Resetting It)\n\n"
            "Warning: Steam Cloud Sync will overwrite local changes if you do this while online.\n\n"
            "1. Kill Steam: Click the red 'Kill Steam' button to fully close Steam.\n"
            "2. Edit Playtime: Click 'Edit Playtime', enter desired hours, and Save.\n"
            "3. Disconnect Internet (CRUCIAL): Turn off Wi-Fi or unplug Ethernet.\n"
            "4. Launch Steam: Click 'Launch Steam'. Choose 'Start in Offline Mode' on the error.\n"
            "5. Verify: Check your Library to ensure the new playtime is displayed.\n"
            "6. Go Online: Reconnect internet. Click 'Steam' (top-left) -> 'Go Online...' -> 'Leave Offline Mode'.\n\n"
            "Your new playtime is now permanently saved and synced with Steam!"
        )

        textbox = ctk.CTkTextbox(dialog, wrap="word", font=("Arial", 13))
        textbox.pack(fill="both", expand=True, padx=20, pady=20)
        textbox.insert("0.0", tutorial_text)
        textbox.configure(state="disabled")

        ctk.CTkButton(dialog, text="Got it!", command=dialog.destroy).pack(pady=10)

    def switch_view(self, value):
        self.current_view = value.split()[0]
        self.render_games()
        
    def get_game_artwork(self, appid, is_logo=False):
        if is_logo:
            paths = [f"{appid}_logo.png", f"{appid}_logo.jpg", f"{appid}p.png", f"{appid}p.jpg"]
        else:
            paths = [f"{appid}p.png", f"{appid}p.jpg"]
            
        for path in paths:
            full_path = os.path.join(self.grid_dir, path)
            if os.path.exists(full_path):
                return full_path
        return None

    def render_games(self):
        # clear existing widgets
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.images.clear()
            
        if not self.games:
            ctk.CTkLabel(self.scroll_frame, text="No Non-Steam games found.").pack(pady=20)
            return

        if self.current_view == "Grid":
            self._render_grid_view()
        else:
            self._render_list_view()

    def _render_list_view(self):
        for game in self.games:
            appid_unsigned = game['appid_unsigned']
            appid_signed = game['appid_signed']
            playtime = get_playtime(self.localconfig_apps, appid_signed)
            hours = playtime / 60.0
            
            card = ctk.CTkFrame(self.scroll_frame)
            card.pack(fill="x", pady=5)
            
            # Use columns with weights to push edit button right
            card.grid_columnconfigure(2, weight=1)
            
            artwork_path = self.get_game_artwork(appid_unsigned, is_logo=True)
            if artwork_path:
                try:
                    img = Image.open(artwork_path)
                    if artwork_path.endswith('p.png') or artwork_path.endswith('p.jpg'):
                        # fallback artwork, scale to 2:3 to avoid stretching horizontally
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(40, 60))
                        lbl_img = ctk.CTkLabel(card, image=ctk_img, text="", width=120)
                    else:
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 60))
                        lbl_img = ctk.CTkLabel(card, image=ctk_img, text="")
                    self.images.append(ctk_img)
                except Exception:
                    lbl_img = ctk.CTkLabel(card, text="No Image", width=120, height=60, fg_color="gray")
            else:
                lbl_img = ctk.CTkLabel(card, text="No Image", width=120, height=60, fg_color="gray")
                
            lbl_img.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
            
            ctk.CTkLabel(card, text=game['app_name'], font=("Arial", 16, "bold")).grid(row=0, column=1, sticky="w", padx=10, pady=(10, 0))
            ctk.CTkLabel(card, text=f"{hours:.1f} hours").grid(row=1, column=1, sticky="nw", padx=10)
            
            btn_edit = ctk.CTkButton(card, text="Edit Playtime", width=120, command=lambda g=game, p=playtime: self.handle_edit_request(g, p))
            btn_edit.grid(row=0, column=3, rowspan=2, sticky="e", padx=20)

    def _render_grid_view(self):
        # 3 items per row roughly depending on window size
        columns = 3
        
        for i in range(columns):
            self.scroll_frame.grid_columnconfigure(i, weight=1, uniform="col")

        row, col = 0, 0
        for game in self.games:
            appid_unsigned = game['appid_unsigned']
            appid_signed = game['appid_signed']
            playtime = get_playtime(self.localconfig_apps, appid_signed)
            hours = playtime / 60.0
            
            card = ctk.CTkFrame(self.scroll_frame)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            artwork_path = self.get_game_artwork(appid_unsigned, is_logo=False)
            if artwork_path:
                try:
                    img = Image.open(artwork_path)
                    # Use 2:3 ratio (160x240)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 240))
                    self.images.append(ctk_img)
                    lbl_img = ctk.CTkLabel(card, image=ctk_img, text="")
                except Exception:
                    lbl_img = ctk.CTkLabel(card, text="No Image", width=160, height=240, fg_color="gray")
            else:
                lbl_img = ctk.CTkLabel(card, text="No Image", width=160, height=240, fg_color="gray")
                
            lbl_img.pack(pady=10)
            
            ctk.CTkLabel(card, text=game['app_name'], font=("Arial", 14, "bold"), wraplength=180).pack(pady=5)
            ctk.CTkLabel(card, text=f"{hours:.1f} hours").pack(pady=5)
            
            btn_edit = ctk.CTkButton(card, text="Edit Playtime", command=lambda g=game, p=playtime: self.handle_edit_request(g, p))
            btn_edit.pack(side="bottom", pady=15)
            
            col += 1
            if col >= columns:
                col = 0
                row += 1

    def handle_edit_request(self, game, current_playtime):
        if is_steam_running():
            ans = messagebox.askyesno(
                "Steam is running", 
                "Steam is currently running. You must close Steam to modify playtime. Kill Steam now?"
            )
            if not ans:
                return
            
            kill_steam()
            
        self.open_edit_dialog(game, current_playtime)

    def open_edit_dialog(self, game, current_playtime):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Edit {game['app_name']}")
        dialog.geometry("300x200")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=f"Edit Playtime for {game['app_name']}").pack(pady=10)
        
        hours_input = ctk.CTkEntry(dialog, placeholder_text="Hours (e.g. 5.5)")
        hours_input.pack(pady=10)
        hours_input.insert(0, str(round(current_playtime / 60.0, 1)))
        
        def save():
            try:
                new_hours = float(hours_input.get())
                new_mins = int(new_hours * 60)
                
                # Double check steam wasn't relaunched while dialog was open
                if is_steam_running():
                    kill_steam()
                    
                save_playtime(self.localconfig_file, game['appid_signed'], new_mins)
                self.cmd_load_file() # reload data into memory then render
                dialog.destroy()
            except ValueError:
                print("Invalid input for hours")
                
        ctk.CTkButton(dialog, text="Save Changes", command=save).pack(pady=20)
