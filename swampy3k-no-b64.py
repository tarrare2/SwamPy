import sys
import os
import json
import requests
import zipfile
import shutil
import psutil
import base64
import random
import re
import ctypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from urllib.parse import urljoin
import csv
import subprocess
import platform
import xml.etree.ElementTree as ET

if sys.platform.startswith('win32'):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('tarrare2.SwamPy.0.1')

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
ICON_B64 = ""
CANCEL_B64 = ""
AGLIA_B64 = ""
BONK_B64 = ""
PESCE_B64 = ""
PLACEHOLDER_B64 = ""
REMOTE_API_URL = "https://api.crocdb.net/"
if getattr(sys, 'frozen', False):
    if hasattr(sys, '_MEIPASS'):
        # One file mode: files extracted to temp folder
        BASE_DIR = Path(sys._MEIPASS)
    else:
        # One folder mode: files are next to the .exe
        BASE_DIR = Path(sys.executable).parent
else:
    # Running as script
    BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
try:
    from mangrove import app as flask_app
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Warning: crocapi module not found. Local server option will be disabled.")
from PySide6.QtCore import QStandardPaths
DATA_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR = DATA_DIR / "SwamPy"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
ROMSET_DIR = CONFIG_DIR / "romsets"
ROMSET_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / ".swampy_config.json"
DEFAULT_SETTINGS = {
    "download_path": str(Path.cwd() / "swamp"),
    "use_es_folders": True,
    "remove_demos": True,
    "cache_size_mb": 50,
    "create_m3u_folders": True,
    "extract_zips": False,
    "decrypt_psv_pkg": True,
    "vita3k_path": "",          # path to Vita3K executable
    "auto_install_vita3k": False,
    "delete_after_vita3k_install": False,
    "show_vita3k_compat": True,
    "vita3k_compat_filter": [], # empty is no filter
    "vita3k_compat_filter_enabled": False, # Vita3K compatibility filter
    "api_mode": "remote",  
    "local_server_port": 5000,
    "local_server_host": "127.0.0.1",
    "start_local_on_launch": False,
    "start_fullscreen": True,
    "window_geometry": "",
    "theme": "system"
}
M3U_PLATFORMS = {"ps1", "dc", "sat"}#Platforms that support the .m3u folder trick (for ES-DE)
# CrocDB Platform to ES-DE folder mapping
PLATFORM_FOLDERS = {
    "32x": "sega32x",
    "3do": "3do",
    "3ds": "n3ds",
    "a26": "atari2600",
    "a52": "atari5200",
    "a78": "atari7800",
    "cdi": "cdimono1",
    "cv": "colecovision",
    "dc": "dreamcast",
    "dsi": "nds",
    "fds": "fds",
    "fmt": "fmtowns",
    "gb": "gb",
    "gba": "gba",
    "gbc": "gbc",
    "gc": "gc",
    "gg": "gamegear",
    "intv": "intellivision",
    "jag": "atarijaguar",
    "jcd": "atarijaguarcd",
    "lynx": "atarilynx",
    "mame": "mame",
    "min": "pokemini",
    "n3ds": "n3ds",
    "n64": "n64",
    "ndd": "n64dd",
    "nds": "nds",
    "nes": "nes",
    "ngcd": "neogeocd",
    "pc98": "pc98",
    "pcfx": "pcfx",
    "pip": "",
    "ps1": "psx",
    "ps2": "ps2",
    "ps3": "ps3",
    "psp": "psp",
    "psv": "psvita",
    "sat": "saturn",
    "scd": "segacd",
    "smd": "genesis",
    "sms": "mastersystem",
    "snes": "snes",
    "tg16": "tg16",
    "tgcd": "tg-cd",
    "vb": "virtualboy",
    "wii": "wii",
    "wiiu": "wiiu",
    "x360": "xbox360",
    "xbox": "xbox"
}
class Vita3KCompatibility:
    COMPAT_URL = "https://github.com/Vita3K/compatibility/releases/download/compat_db/app_compat_db.xml"
    CACHE_FILE = CONFIG_DIR / "vita3k_compat.json"
    #STATUS_OPTIONS = ["Nothing", "Bootable", "Intro", "Menu", "Ingame-", "Ingame+", "Playable", "Unknown"]
    # Mapping of numeric label IDs to readable strings from assimil8.py
    LABEL_MAP = {
        1260231569: "Nothing",
        1344750319: "Bootable",
        1260231381: "Intro",
        1344751053: "Menu",
        1344752299: "Ingame-",
        1260231985: "Ingame+",
        920344019: "Playable",
        # Issues (prefixed with "-")
        1267246426: "-savedata bug",
        5696848242: "-online-only",
        920343647: "-graphics bug",
        920343454: "-crash",
        920343850: "-networking bug",
        920344210: "-softlock bug",
        4225080103: "-ngs freeze",
        920343248: "-audio bug",
        3011534157: "-camera",
        1658005199: "-regression",
        1267247113: "-unity",
        5173295989: "-vulkan issue",
        5505522409: "-dynarmic error",
        1658033591: "-video player bug",
        5553374478: "-motion missing",
        2713149354: "-function missing",
        5173295657: "-vulkan crash",
        3011533277: "-touchscreen issues",
        2176340004: "-blackscreen",
        2978717191: "-color bug",
        3824743245: "-audio speed",
        920343736: "-input bug",
        1260342271: "-shader bug",
        2563026562: "-audio missing",
        3347588318: "-text missing",
        1392167868: "-video missing",
        1387705360: "-ngs crash",
        1294598815: "-NID missing",
        2988735957: "-screen flashing",
        3824734717: "-frame jumping",
        3819783597: "-outdated",
        3579431535: "-dynarmic crash",
        927870278: "-gamemaker",
        1391359723: "-unicorn error",
        5229654123: "-vulkan error",
        920348168: "-module loading bug",
        5171985847: "-controller-issue",
        3044690321: "-sensor missing",
        2662666120: "-too fast",
        1371536201: "-slow",
        3824740901: "-audio quality",
        1267246507: "-trophy bug",
        4250205569: "-upscaling issue",
    }

    def __init__(self):
        self.data = {}  # title_id -> list of strings
        self.load_cache()

    def load_cache(self):
        """Load cached compatibility data if it exists."""
        if self.CACHE_FILE.exists():
            try:
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                print(f"Loaded Vita3K compatibility data for {len(self.data)} titles")
            except Exception as e:
                print(f"Failed to load Vita3K cache: {e}")

    def save_cache(self):
        """Save compatibility data to cache."""
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
            print("Saved Vita3K compatibility cache")
        except Exception as e:
            print(f"Failed to save Vita3K cache: {e}")

    def fetch(self):
        """Download and parse the compatibility XML."""
        try:
            response = requests.get(self.COMPAT_URL, timeout=10)
            if not response.ok:
                print(f"Failed to fetch compatibility XML: {response.status_code}")
                return False
            root = ET.fromstring(response.content)
            new_data = {}
            for app in root.findall('app'):
                title_id = app.get('title_id')
                if not title_id:
                    continue
                labels = []
                for label_elem in app.findall('.//label'):
                    try:
                        label_id = int(label_elem.text)
                        label_str = self.LABEL_MAP.get(label_id, f"unknown-{label_id}")
                        labels.append(label_str)
                    except:
                        continue
                new_data[title_id] = labels
            self.data = new_data
            self.save_cache()
            return True
        except Exception as e:
            print(f"Error fetching compatibility: {e}")
            return False

    def get_status(self, title_id: str) -> Optional[List[str]]:
        """Return list of status strings for a title ID, or None if unknown."""
        return self.data.get(title_id)

    def get_status_summary(self, title_id: str) -> str:
        """Return a human-readable summary (e.g., 'Playable (2 issues)')."""
        labels = self.get_status(title_id)
        if not labels:
            return "Unknown"
        main_status = None
        issues = []
        for label in labels:
            if label.startswith('-'):
                issues.append(label[1:])  # remove leading dash
            else:
                main_status = label
        if not main_status:
            main_status = "Unknown"
        if issues:
            return f"{main_status} ({len(issues)} issue{'s' if len(issues)!=1 else ''})"
        else:
            return main_status
class PSVitaSettingsDialog(QDialog):
    def __init__(self, main_window, settings):
        super().__init__(main_window)  # parent is main window
        self.main_window = main_window
        self.settings = settings.copy()
        self.setWindowTitle("PSVita / Vita3K Settings")
        self.setFixedSize(500, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Vita3K executable
        exe_layout = QHBoxLayout()
        exe_layout.addWidget(QLabel("Vita3K executable:"))
        self.vita3k_edit = QLineEdit(self.settings.get("vita3k_path", ""))
        self.vita3k_edit.setReadOnly(True)
        exe_browse = QPushButton("Browse...")
        exe_browse.clicked.connect(self._browse_vita3k)
        exe_layout.addWidget(self.vita3k_edit)
        exe_layout.addWidget(exe_browse)
        layout.addLayout(exe_layout)

        # Auto-install checkbox
        self.auto_install_cb = QCheckBox("Automatically install PSV games to Vita3K")
        self.auto_install_cb.setChecked(self.settings.get("auto_install_vita3k", False))
        self.auto_install_cb.setToolTip("After downloading a PKG, run Vita3K to install it.")
        layout.addWidget(self.auto_install_cb)

        # Decrypt PKG checkbox
        self.decrypt_cb = QCheckBox("Automatically decrypt PSV PKG files (requires pkg2zip)")
        self.decrypt_cb.setChecked(self.settings.get("decrypt_psv_pkg", True))
        self.decrypt_cb.setToolTip("Convert PKG to ZIP (useful for manual installation).")
        layout.addWidget(self.decrypt_cb)

        # Delete after install checkbox
        self.delete_cb = QCheckBox("Delete original file after Vita3K installation")
        self.delete_cb.setChecked(self.settings.get("delete_after_vita3k_install", False))
        layout.addWidget(self.delete_cb)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)

        # Compatibility info section
        compat_group = QGroupBox("Compatibility Info")
        compat_layout = QVBoxLayout()

        self.show_compat_cb = QCheckBox("Show compatibility status on game cards")
        self.show_compat_cb.setChecked(self.settings.get("show_vita3k_compat", True))
        compat_layout.addWidget(self.show_compat_cb)

        self.refresh_compat_btn = QPushButton("Refresh compatibility database")
        self.refresh_compat_btn.clicked.connect(self._refresh_compat)
        compat_layout.addWidget(self.refresh_compat_btn)
        # Compatibility filter group
        filter_group = QGroupBox("Filter by Compatibility")
        filter_layout = QVBoxLayout()
        self.enable_filter_cb = QCheckBox("Enable compatibility filtering")
        self.enable_filter_cb.setChecked(self.settings.get("vita3k_compat_filter_enabled", False))
        filter_layout.addWidget(self.enable_filter_cb)
        filter_layout.addWidget(QLabel("Include games with status:"))
        self.compat_list = QListWidget()
        self.compat_list.setSelectionMode(QAbstractItemView.MultiSelection)
        statuses = ["Playable", "Ingame+", "Ingame-", "Menu", "Intro", "Bootable", "Nothing"]
        for status in statuses:
            item = QListWidgetItem(status)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.compat_list.addItem(item)
        # Pre-select from settings
        selected = self.settings.get("vita3k_compat_filter", [])
        for i in range(self.compat_list.count()):
            item = self.compat_list.item(i)
            if item.text() in selected:
                item.setCheckState(Qt.Checked)
        filter_layout.addWidget(self.compat_list)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        self.compat_status_label = QLabel("")
        compat_layout.addWidget(self.compat_status_label)
        compat_group.setLayout(compat_layout)
        layout.addWidget(compat_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self._update_compat_status()

    def _browse_vita3k(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Vita3K executable",
            "", "Executable files (*.exe);;All files (*)"
        )
        if path:
            self.vita3k_edit.setText(path)

    def _refresh_compat(self):
        self.refresh_compat_btn.setEnabled(False)
        self.compat_status_label.setText("Downloading compatibility data...")
        QApplication.processEvents()
        success = self.main_window.vita3k_compat.fetch()
        if success:
            self.compat_status_label.setText(f"Updated: {len(self.main_window.vita3k_compat.data)} titles")
        else:
            self.compat_status_label.setText("Update failed")
        self.refresh_compat_btn.setEnabled(True)

    def _update_compat_status(self):
        count = len(self.main_window.vita3k_compat.data) if hasattr(self.main_window, 'vita3k_compat') else 0
        self.compat_status_label.setText(f"Loaded {count} titles")

    def get_settings(self):
        selected_statuses = []
        for i in range(self.compat_list.count()):
            if self.compat_list.item(i).checkState() == Qt.Checked:
                selected_statuses.append(self.compat_list.item(i).text())
        return {
            "vita3k_path": self.vita3k_edit.text(),
            "auto_install_vita3k": self.auto_install_cb.isChecked(),
            "decrypt_psv_pkg": self.decrypt_cb.isChecked(),
            "delete_after_vita3k_install": self.delete_cb.isChecked(),
            "show_vita3k_compat": self.show_compat_cb.isChecked(),
            "vita3k_compat_filter_enabled": self.enable_filter_cb.isChecked(),
            "vita3k_compat_filter": selected_statuses,
        }

class RomsetManagerDialog(QDialog):
    """Dialog to view and load existing romsets."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Romsets")
        self.setFixedSize(400, 300)
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # List of romsets
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(QLabel("Available romsets:"))
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load Selected")
        self.load_btn.clicked.connect(self.accept)
        self.load_btn.setEnabled(False)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.list_widget.itemClicked.connect(lambda: self.load_btn.setEnabled(True))

    def _refresh_list(self):
        self.list_widget.clear()
        for file in ROMSET_DIR.glob("*.txt"):
            item = QListWidgetItem(file.stem)
            item.setData(Qt.UserRole, str(file))
            self.list_widget.addItem(item)

    def get_selected_romset(self) -> Optional[Path]:
        """Return the path of the selected romset, or None."""
        if self.result() != QDialog.Accepted:
            return None
        item = self.list_widget.currentItem()
        if item:
            return Path(item.data(Qt.UserRole))
        return None
class RomsetDialog(QDialog):
    """Dialog to save to an existing romset or create a new one"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add to Romset")
        self.setFixedSize(400, 300)
        self._setup_ui()
        self._load_romsets()
        self._update_ok_button()          # initial state

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Label
        layout.addWidget(QLabel("Select existing romset or enter a new name:"))

        # List of existing romsets
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

        # New name entry
        form = QFormLayout()
        self.new_name_edit = QLineEdit()
        self.new_name_edit.setPlaceholderText("e.g., my_favorites")
        self.new_name_edit.textChanged.connect(self._update_ok_button)
        form.addRow("New romset name:", self.new_name_edit)
        layout.addLayout(form)

        # Buttons
        buttons = QHBoxLayout()
        self.ok_btn = QPushButton("Add")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(self.ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def _load_romsets(self):
        """Scan ROMSET_DIR for .txt files and add them to the list"""
        self.list_widget.clear()
        for file in ROMSET_DIR.glob("*.txt"):
            item = QListWidgetItem(file.stem)
            item.setData(Qt.UserRole, str(file))
            self.list_widget.addItem(item)

    def _on_item_clicked(self, item):
        """When an existing romset is clicked, clear the new name field and update button"""
        self.new_name_edit.clear()
        self._update_ok_button()

    def _update_ok_button(self):
        """Enable OK if a list item is selected OR the new name field is not empty"""
        has_selection = self.list_widget.currentItem() is not None
        has_text = bool(self.new_name_edit.text().strip())
        self.ok_btn.setEnabled(has_selection or has_text)

    def get_selected_romset(self) -> Optional[Path]:
        """Return the chosen romset file path, or None if cancelled."""
        if self.result() != QDialog.Accepted:
            return None

        # If an item in the list is selected, use that
        selected = self.list_widget.currentItem()
        if selected:
            return Path(selected.data(Qt.UserRole))

        # Otherwise use the new name (if not empty)
        new_name = self.new_name_edit.text().strip()
        if new_name:
            # Sanitise filename (remove path separators, etc.)
            safe_name = "".join(c for c in new_name if c.isalnum() or c in "._- ").strip()
            if not safe_name:
                safe_name = "romset"
            return ROMSET_DIR / f"{safe_name}.txt"

        return None
    
from werkzeug.serving import make_server
import threading

class LocalServerThread(QThread):
    started = Signal(str)
    error   = Signal(str)
    stopped = Signal()

    def __init__(self, host='127.0.0.1', port=5000):
        super().__init__()
        self.host = host
        self.port = port
        self.server_url = f"http://{host}:{port}/"
        self.stop_event = threading.Event()
        self.server = None
    def run(self):
        if not FLASK_AVAILABLE:
            self.error.emit("CrocAPI module not available (Put app.py+api.py in a folder named 'mangrove')")
            return
        try:
            self.server = make_server(self.host, self.port, flask_app, threaded=True)
            self.server.timeout = 0.5 
            self.started.emit(self.server_url)
            # Serve one request at a time, checking stop_event
            while not self.stop_event.is_set():
                self.server.handle_request()
            self.server.server_close()
        except Exception as e:
            if self.stop_event.is_set():
                pass  # normal shutdown
            else:
                self.error.emit(str(e))
        finally:
            self.stopped.emit()

    def stop(self):
        """Signal the server to stop and wait for thread to finish."""
        self.stop_event.set()
        # Send a dummy request to unblock handle_request()
        try:
            requests.get(self.server_url, timeout=0.1)
        except:
            pass
        self.wait(2000)   # give it up to 2 seconds

class LocalServerDialog(QDialog):
    """Dialog for local server configuration and status."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self._set_icon()
        self.setWindowTitle("Local API Server")
        self.setFixedSize(450, 300)
        self.setup_ui()
        # Connect to the main window's server state signal
        self.main_window.server_state.connect(self._on_server_state_changed)
        # Initial refresh
        self._refresh_ui_from_state()

    def _set_icon(self):
        """Set dialog icon from embedded base64."""
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(ICON_B64))
        self.setWindowIcon(QIcon(pixmap))

    def setup_ui(self):
        layout = QVBoxLayout(self)
        # Server config
        config_group = QGroupBox("Server Configuration")
        config_layout = QGridLayout()
        config_layout.addWidget(QLabel("Host:"), 0, 0)
        self.host_combo = QComboBox()
        self.host_combo.setEditable(True)
        self.host_combo.addItems(["127.0.0.1", "localhost", "0.0.0.0"])
        self.host_combo.setCurrentText(
            self.main_window.settings.get("local_server_host", "127.0.0.1")
        )
        self.host_combo.setToolTip("0.0.0.0 allows connections from other devices")
        config_layout.addWidget(self.host_combo, 0, 1)
        config_layout.addWidget(QLabel("Port:"), 1, 0)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(
            self.main_window.settings.get("local_server_port", 5000)
        )
        config_layout.addWidget(self.port_spin, 1, 1)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Server status
        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("Server not running")
        self.status_label.setStyleSheet("color: #888; font-weight: bold;")
        status_layout.addWidget(self.status_label)

        self.url_label = QLabel("URL: -")
        self.url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        status_layout.addWidget(self.url_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # CrocAPI availability warning
        if not FLASK_AVAILABLE:
            error_label = QLabel(
                "⚠️ crocapi module not found!\nLocal server functionality is disabled."
            )
            error_label.setStyleSheet(
                "color: #e74c3c; padding: 10px; background: #2d2d2d; border-radius: 4px;"
            )
            error_label.setWordWrap(True)
            layout.addWidget(error_label)

        # Control buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Server")
        self.start_btn.clicked.connect(self.start_server)
        self.start_btn.setEnabled(FLASK_AVAILABLE)

        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        self.test_btn.setEnabled(FLASK_AVAILABLE)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)


    # UI state management
    def _refresh_ui_from_state(self):
        """Read current server state from main window and update UI."""
        thread = self.main_window.local_server_thread
        if thread and thread.isRunning():
            self._set_state_running(thread.server_url)
        else:
            self._set_state_stopped()

    def _on_server_state_changed(self, state: str):
        """Slot for main_window.server_state signal."""
        if state == "running":
            url = self.main_window.local_server_thread.server_url
            self._set_state_running(url)
        elif state == "stopped":
            self._set_state_stopped()
        elif state == "starting":
            self._set_state_starting()
        elif state == "error":
            self._set_state_error()

    def _set_state_stopped(self):
        self.status_label.setText("Server stopped")
        self.status_label.setStyleSheet("color: #888; font-weight: bold;")
        self.url_label.setText("URL: -")
        self.start_btn.setText("Start Server")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.test_btn.setEnabled(True)

    def _set_state_starting(self):
        self.status_label.setText("Starting server...")
        self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        self.url_label.setText("URL: -")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.test_btn.setEnabled(False)

    def _set_state_running(self, url: str):
        self.status_label.setText("Server running")
        self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        self.url_label.setText(f"URL: {url}")
        self.start_btn.setText("Restart Server")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.test_btn.setEnabled(True)

    def _set_state_error(self, error_msg: str = None):
        self.status_label.setText("Server error")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.url_label.setText("URL: -")
        self.start_btn.setText("Start Server")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.test_btn.setEnabled(True)

    # Server control
    def start_server(self):
        """Start the local server via main window."""
        if not FLASK_AVAILABLE:
            QMessageBox.critical(self, "Error", "crocapi module not available")
            return
        host = self.host_combo.currentText().strip()
        port = self.port_spin.value()
        self.main_window.start_server(host, port)

    def stop_server(self):
        """Stop the local server via main window."""
        self.main_window.stop_server()

    def test_connection(self):
        """Test the connection to the (supposedly) running server."""
        # Use the URL that is currently displayed
        thread = self.main_window.local_server_thread
        if thread and thread.isRunning():
            url = thread.server_url
        else:
            host = self.host_combo.currentText().strip()
            port = self.port_spin.value()
            url = f"http://{host}:{port}/"
        try:
            response = requests.get(urljoin(url, "info"), timeout=5)
            if response.ok:
                QMessageBox.information(
                    self,
                    "Connection Test",
                    f"✓ Server is responding!\n\nURL: {url}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Connection Test",
                    f"Server responded with error: {response.status_code}"
                )
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(
                self,
                "Connection Test",
                f"✗ Could not connect to server at:\n{url}\n\n"
                "Make sure the server is running."
            )
        except Exception as e:
            QMessageBox.critical(self, "Connection Test", f"Error: {str(e)}")

    def closeEvent(self, event):
        """Override close event – do NOT stop the server when dialog closes."""
        event.accept()

@dataclass
class Game:
    """Data class for game information"""
    id: str
    title: str
    platform: str
    region: str
    size_str: Optional[str] = None
    rom_id: Optional[str] = None
    zrif: Optional[str] = None
    cover_url: Optional[str] = None
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    download_path: Optional[str] = None
    selected_format: Optional[str] = None
    disc_number: int = field(default=1)
    base_game_name: Optional[str] = None
    is_multi_disc: bool = field(default=False)

@dataclass
class DownloadTask:
    """Data class for download tasks"""
    game: Game
    status: str = "queued"
    progress: float = 0.0
    error_message: Optional[str] = None

class ImageCache:
    """Simple LRU image cache"""
    def __init__(self, max_size_mb: int = 50):
        self.max_size = max_size_mb * 1024 * 1024
        self.cache: Dict[str, Tuple[QPixmap, int]] = {}
        self.access_order: List[str] = []
        self._current_size = 0
    
    def get(self, url: str) -> Optional[QPixmap]:
        if url in self.cache:
            self.access_order.remove(url)
            self.access_order.append(url)
            return self.cache[url][0]
        return None
    
    def put(self, url: str, pixmap: QPixmap):
        size = pixmap.width() * pixmap.height() * 4
        if url in self.cache:
            old_size = self.cache[url][1]
            self._current_size -= old_size
            self.access_order.remove(url)
        while self._current_size + size > self.max_size and self.access_order:
            old_url = self.access_order.pop(0)
            old_size = self.cache[old_url][1]
            self._current_size -= old_size
            del self.cache[old_url]
        self.cache[url] = (pixmap, size)
        self.access_order.append(url)
        self._current_size += size
    
    def clear(self):
        self.cache.clear()
        self.access_order.clear()
        self._current_size = 0

class ImageLoader(QThread):
    """Thread for async image loading"""
    loaded = Signal(str, QPixmap)
    error = Signal(str, str)
    
    def __init__(self):
        super().__init__()
        self.queue: List[Tuple[str, str]] = []
        self._running = True
        self._lock = threading.Lock()
    
    def add(self, url: str, game_id: str):
       if url and url.startswith('http'):
            with self._lock:
                self.queue.append((url, game_id))
            if not self.isRunning():
                self.start()
    def clear(self):
        with self._lock:
            self.queue.clear()
    
    def run(self):
        while self._running:
            with self._lock:
                if self.queue:
                    url, game_id = self.queue.pop(0)
                else:
                    url, game_id = None, None
            if url is None:
                self.msleep(100)
                continue
            try:
                response = requests.get(url, timeout=10)
                if response.ok:
                    image = QImage()
                    if image.loadFromData(response.content):
                        pixmap = QPixmap.fromImage(image)
                        if not pixmap.isNull():
                            self.loaded.emit(game_id, pixmap)
                            continue
                self.error.emit(game_id, "Failed to load image")
            except Exception as e:
                self.error.emit(game_id, str(e))
    
    def stop(self):
        self._running = False
        self.wait()

class DownloadManager(QThread):
    """Thread for managing downloads"""
    progress = Signal(str, float)
    complete = Signal(str, str)
    error = Signal(str, str)
    
    def __init__(self, base_path: str = "", use_es_folders: bool = True, create_m3u: bool = True, psv_helper=None, decrypt_psv_pkg=True, extract_zips=False, auto_install_vita3k=False, vita3k_path="", delete_after_vita3k_install=False):
        super().__init__()
        #print(f"DownloadManager.__init__: decrypt_psv_pkg = {decrypt_psv_pkg}")
        self.base_path = base_path
        self.use_es_folders = use_es_folders
        self.create_m3u = create_m3u
        self.psv_helper = psv_helper
        self.extract_zips = extract_zips
        self.decrypt_psv_pkg = decrypt_psv_pkg
        self.auto_install_vita3k = auto_install_vita3k
        self.delete_after_vita3k_install = delete_after_vita3k_install
        self.vita3k_path = vita3k_path
        self.queue: List[Game] = []
        self.current: Optional[Game] = None
        self._running = True
        self._active = False
        self._cancel = False
        self._paused = False
        self.queue_lock = threading.Lock()

    def pause(self):
        """Pause by canceling current download."""
        self._paused = True
        if self.current:
            self.cancel_current()
    
    def resume(self):
        """Resume downloads."""
        self._paused = False
        if not self._active:
            self._active = True
            self.start()
    
    def is_paused(self):
        return self._paused
    
    def move_to_top(self, game_id: str):
        """Move a queued game to the position after current."""
        with self.queue_lock:
            for i, game in enumerate(self.queue):
                if game.id == game_id:
                    game_to_move = self.queue.pop(i)
                    self.queue.insert(0, game_to_move)
                    return True
        return False
    
    def remove_from_queue(self, game_id: str):
        """Remove a game from queue. Cancel if current."""
        with self.queue_lock:
            self.queue = [g for g in self.queue if g.id != game_id]
        if self.current and self.current.id == game_id:
            self.cancel_current()
            
    def _process_multi_disc_chd(self, game: Game, current_path: str) -> str:
        """Process multi-disc CHD file for .m3u creation."""
        try:
            from pathlib import Path
            import shutil
            
            file_path = Path(current_path)
            download_dir = file_path.parent
            
            # Create safe base name for folder
            if hasattr(game, 'base_game_name') and game.base_game_name:
                safe_base = "".join(c for c in game.base_game_name if c.isalnum() or c in " ._-")
            else:
                # Fallback to title without disc info
                safe_base = "".join(c for c in game.title if c.isalnum() or c in " ._-")
                # Remove "Disc X" part
                safe_base = re.sub(r'\s+[Dd]isc\s+\d+', '', safe_base)
            
            # Create .m3u folder
            m3u_folder_name = f"{safe_base}.m3u"
            m3u_folder = download_dir / m3u_folder_name
            m3u_folder.mkdir(exist_ok=True)
            
            # Move file to .m3u folder
            target_path = m3u_folder / file_path.name
            
            # Handle filename conflicts
            if target_path.exists():
                # Add disc number to filename
                stem = file_path.stem
                suffix = file_path.suffix
                target_path = m3u_folder / f"{stem}_disc{game.disc_number}{suffix}"
            
            if file_path != target_path:
                shutil.move(str(file_path), str(target_path))
                #print(f"DEBUG: Moved to .m3u folder: {target_path.name}")
            
            # Create or update .m3u file
            m3u_file = m3u_folder / f"{safe_base}.m3u"
            self._update_m3u_file(m3u_file, target_path.name, game.disc_number)
            
            return str(target_path)
            
        except Exception as e:
            print(f"Error processing multi-disc: {e}")
            import traceback
            traceback.print_exc()
            return current_path

    def _update_m3u_file(self, m3u_path: Path, filename: str, disc_number: int):
        """Update .m3u file with disc entry."""
        import re
        entries = []
        # Read existing entries
        if m3u_path.exists():
            with open(m3u_path, 'r') as f:
                entries = [line.strip() for line in f if line.strip()]
        # Remove existing entry for this disc number if exists
        disc_pattern = re.compile(r'disc\s*' + str(disc_number), re.IGNORECASE)
        entries = [e for e in entries if not disc_pattern.search(e)]
        # Add new entry
        entries.append(filename)
        # Sort by disc number
        def extract_disc_num(fname):
            match = re.search(r'[Dd]isc\s*(\d+)', fname)
            return int(match.group(1)) if match else 999
        entries.sort(key=extract_disc_num)
        # Write back
        with open(m3u_path, 'w') as f:
            for entry in entries:
                f.write(f"{entry}\n")
    
    def add(self, game: Game):
        with self.queue_lock:
            # Avoid duplicates
            for g in self.queue:
                if g.id == game.id:
                    return
            self.queue.append(game)
        if not self._active:
            self._active = True
            self.start()
    
    def get_path(self, game: Game) -> str:
        if self.use_es_folders:
            folder = PLATFORM_FOLDERS.get(game.platform.lower(), game.platform)
            download_dir = Path(self.base_path) / folder
        else:
            download_dir = Path(self.base_path)
        download_dir.mkdir(parents=True, exist_ok=True)
        safe_title = "".join(c for c in game.title if c.isalnum() or c in " ._-")
        if game.download_url:
            clean_url = game.download_url.split('?')[0]
            filename = safe_title + Path(clean_url).suffix
        else:
            filename = safe_title + ".zip"
        return str(download_dir / filename)
    
    def check_space(self, required_bytes: int) -> bool:
        try:
            path = Path(self.base_path)
            if not path.exists():
                path = path.parent
            usage = psutil.disk_usage(str(path))
            return usage.free >= int(required_bytes * 1.1)
        except:
            return True
    
    def extract_zip(self, zip_path: str) -> Optional[str]:
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                files = [f for f in zip_ref.namelist() if not f.endswith('/')]
                if len(files) != 1:
                    return None
                single_file = files[0]
                zip_dir = os.path.dirname(zip_path)
                zip_ref.extractall(zip_dir)
            extracted = os.path.join(zip_dir, single_file)
            final = os.path.join(zip_dir, os.path.basename(single_file))
            if extracted != final:
                shutil.move(extracted, final)
                self._clean_dirs(os.path.dirname(extracted))
            try:
                os.remove(zip_path)
            except:
                pass
            return final
        except:
            return None
    
    def _clean_dirs(self, directory: str):
        try:
            path = Path(directory)
            if path.exists() and path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                self._clean_dirs(str(path.parent))
        except:
            pass
    
    def run(self):
        while self._running: #and self.queue:
            while self._paused and self._running:
                self.msleep(100)
            if not self._running:
                break
            if not self.queue:
                self._active = False
                break
            with self.queue_lock:
                if not self.queue:
                    self._active = False
                    break
                game = self.queue.pop(0)
            self._cancel = False
            #game = self.queue.pop(0)
            self.current = game
            try:
                if not game.download_url:
                    raise ValueError("No download URL")
                path = self.get_path(game)
                game.download_path = path
                with requests.Session() as session:# Check size and space
                    head = session.head(game.download_url, timeout=10)
                    if head.headers.get('content-length'):
                        size = int(head.headers['content-length'])
                        game.file_size = size
                        if not self.check_space(size):
                            raise OSError("Insufficient disk space")
                    response = session.get(game.download_url, stream=True, timeout=30)
                    response.raise_for_status()
                    total = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    if os.path.exists(path):
                        os.remove(path)
                    with open(path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if self._cancel:
                                raise InterruptedError("Download cancelled")
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total > 0:
                                    self.progress.emit(game.id, downloaded / total)
                skip_extract = False
                # PSVita special handling
                if game.platform.lower() == 'psv' and self.psv_helper and game.rom_id:
                    is_pkg = path.lower().endswith('.pkg') or (game.selected_format and game.selected_format.lower() == 'pkg')
                    installed = False          # becomes True if game is installed in Vita3K
                    zrif = None
                    if is_pkg:
                        # Fetch zRIF if needed
                        if self.decrypt_psv_pkg or self.auto_install_vita3k:
                            zrif = self.psv_helper.get_zrif(game.rom_id)

                        if not zrif and (self.decrypt_psv_pkg or self.auto_install_vita3k):
                            self.error.emit(game.id, "No zRIF available for this PSV game")
                            try:
                                os.remove(path)
                            except:
                                pass
                            self.current = None
                            continue
                        # Install PKG directly if auto-install enabled
                        if self.auto_install_vita3k and self.vita3k_path and zrif:
                            cmd = [self.vita3k_path, "--pkg", path, "--zrif", zrif]
                            success, stdout, stderr = self._run_vita3k_install(cmd)
                            if success:
                                installed = True
                                print("PKG installed successfully")
                                if self.delete_after_vita3k_install:
                                    try:
                                        os.remove(path)
                                        print(f"Deleted installed PKG: {path}")
                                    except Exception as e:
                                        print(f"Failed to delete {path}: {e}")
                            else:
                                error_msg = f"Vita3K PKG installation failed.\n\nCommand: {' '.join(cmd)}\n\nError:\n{stderr}\n\nOutput:\n{stdout}"
                                self.error.emit(game.id, error_msg)
                                try:
                                    os.remove(path)
                                except:
                                    pass
                                self.current = None
                                continue

                        # Decrypt PKG to ZIP if enabled
                        elif self.decrypt_psv_pkg and zrif:
                            output_dir = str(Path(path).parent)
                            zip_path = self.psv_helper.decrypt_pkg(path, zrif, output_dir)
                            if zip_path:
                                try:
                                    os.remove(path)
                                except:
                                    pass
                                path = zip_path
                                skip_extraction = True   # don't extract this ZIP later
                                installed = False         # game not installed in Vita3K, but ZIP exists
                            else:
                                self.error.emit(game.id, "Failed to decrypt PSV PKG")
                                try:
                                    os.remove(path)
                                except:
                                    pass
                                self.current = None
                                continue
                        # Keep PKG as is
                        else:
                            installed = False

                    else:  # Not a PKG (already a ZIP)
                        if path.lower().endswith('.zip'):
                            # Don't auto-install ZIPs
                            installed = False
                            skip_extraction = False   # extraction setting will decide

                    # Create .psvita marker if ES-DE folders enabled and game is installed in Vita3K
                    if self.use_es_folders and installed:
                        platform_folder = PLATFORM_FOLDERS.get('psv', 'psvita')
                        marker_dir = Path(self.base_path) / platform_folder
                        marker_dir.mkdir(parents=True, exist_ok=True)
                        safe_title = "".join(c for c in game.title if c.isalnum() or c in " ._-").strip()
                        if not safe_title:
                            safe_title = game.id
                        marker_path = marker_dir / f"{safe_title}.psvita"
                        try:
                            with open(marker_path, 'w', encoding='utf-8') as f:
                                f.write(game.rom_id)
                            print(f"Created .psvita marker: {marker_path}")
                        except Exception as e:
                            print(f"Error creating .psvita file: {e}")

                if not skip_extract and self.extract_zips and path.lower().endswith('.zip'):# Downloaded and extracted TODO: Is this optimal?
                    extracted = self.extract_zip(path)
                    if extracted:
                        path = extracted
                if (self.create_m3u and hasattr(game, 'is_multi_disc') and game.is_multi_disc and 
                hasattr(game, 'selected_format') and game.selected_format == "chd" and
                hasattr(game, 'platform') and game.platform.lower() in M3U_PLATFORMS):
                
                    print(f"DEBUG: Processing multi-disc CHD for .m3u: {game.title}")
                    path = self._process_multi_disc_chd(game, path)
                self.complete.emit(game.id, path)
            except Exception as e:
                self.error.emit(game.id, str(e))
                if 'path' in locals() and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass
            self.current = None
        self._active = False
        
    def _run_vita3k_install(self, cmd):
        """
        Run Vita3K with given command.
        Returns (success, stdout, stderr)
        """
        try:
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            #print(f"Running Vita3K command: {' '.join(cmd)}") #debug
            # Increase timeout and capture output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes for large installs
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )

            if result.returncode == 0:
                print(f"Vita3K successfully installed package")
                return True, result.stdout, result.stderr
            else:
                print(f"Vita3K failed (code {result.returncode}):\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}")
                return False, result.stdout, result.stderr

        except subprocess.TimeoutExpired as e:
            print(f"Vita3K timed out after 5 minutes")
            return False, "", "Timeout expired"
        except Exception as e:
            print(f"Error running Vita3K: {e}")
            return False, "", str(e)
    def stop(self):
        """Stop the download thread and wait for it to finish."""
        self._running = False
        self.wait()

class GameCard(QFrame):
    """Widget for displaying a game"""
    #clicked = Signal(Game)
    doubleClicked = Signal(Game)
    leftClicked = Signal(object, Qt.KeyboardModifiers)
    rightClicked = Signal(Game)
    focused = Signal(str)
    STYLESHEET = """
        GameCard {
            background: palette(window);
            border: 2px solid palette(mid);
            border-radius: 8px;
        }
        GameCard:hover {
            border-color: palette(highlight);
            background: palette(alternate-base);
        }
        GameCard:focus {
            border-color: palette(highlight);
            background: palette(alternate-base);
        }
        GameCard[selected="true"] {
            border-color: #ffaa00;  /* gold border when selected */
            background: palette(alternate-base);
        }
    """
    IMAGE_STYLESHEET = """
        QLabel {
            background: palette(mid);
            border: 1px solid palette(midlight);
            border-radius: 4px;
            color: palette(text);
            font-size: 10px;
        }
    """
    PLATFORM_STYLESHEET = "font-size: 11px;"
    
    def __init__(self, game: Game, placeholder: QPixmap):
        super().__init__()
        self.game = game
        self.placeholder = placeholder
        self._selected = False
        self.setStyleSheet(self.STYLESHEET)
        self.setup_ui()
        self.setFixedSize(200, 250)
        self.setFocusPolicy(Qt.StrongFocus)

    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self.image_frame = QFrame()
        self.image_frame.setFixedSize(180, 180)
        self.image_frame.setStyleSheet("border: none;")
        grid = QGridLayout(self.image_frame)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        
        self.image_label = QLabel(self.image_frame)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setGeometry(0, 0, 180, 180)
        self.image_label.setStyleSheet(self.IMAGE_STYLESHEET)
        self.image_label.setText("Loading...")
        
        self.badge_label = QLabel(self.image_frame)
        self.badge_label.setGeometry(140, 5, 35, 35)  # x, y, width, height
        self.badge_label.setAlignment(Qt.AlignCenter)
        self.badge_label.setStyleSheet("""
            QLabel {
                border-radius: 17px;
                color: white;
                font-weight: bold;
                font-size: 4px;
                background-color: rgba(0,0,0,0);
            }
        """)
        self.badge_label.hide()
        layout.addWidget(self.image_frame)

        # Title
        self.title_label = QLabel(self.game.title[:50])
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(40)
        self.title_label.setStyleSheet("font-weight: bold;")

        # Platform/region/format/size
        format_display = f"{self.game.platform} | {self.game.region}"
        if self.game.selected_format:
            format_display += f" | {self.game.selected_format}"
        if self.game.size_str:
            format_display += f" | {self.game.size_str}"
        self.platform_label = QLabel(format_display)
        self.platform_label.setAlignment(Qt.AlignCenter)
        self.platform_label.setStyleSheet(self.PLATFORM_STYLESHEET)

        layout.addWidget(self.title_label)
        layout.addWidget(self.platform_label)

    def set_compat_status(self, status_summary: str, status_list: Optional[List[str]] = None):
        if not status_summary or status_summary == "Unknown":
            self.badge_label.hide()
            return

        # First word as badge text
        full = status_summary.split()[0] if status_summary else "?"
        #self.badge_label.setText(badge_text)

        # Choose badge colour
        if "Playable" in status_summary:
            colour = "#0e8a16"
            badge_text = "Play"
        elif "Ingame+" in status_summary:
            colour = "#fbca04"
            badge_text = "IG+"
        elif "Ingame-" in status_summary:
            colour = "#e08a1e"
            badge_text = "IG-"
        elif "Bootable" in status_summary:
            colour = "#7030b0"
            badge_text = "Boot"
        elif "Menu" in status_summary:
            colour = "#1e64dc"
            badge_text = "Menu"
        elif "Intro" in status_summary:
            colour = "#c71585"
            badge_text = "Intro"
        elif "Nothing" in status_summary:
            colour = "#e02020"
            badge_text = "Not"
        else:
            colour = "#3030ff"
            badge_text = "?"
            
        self.badge_label.setText(badge_text)
        self.badge_label.setStyleSheet(f"""
            QLabel {{
                border-radius: 17px;
                color: white;
                font-weight: bold;
                font-size: 11px;
                background-color: {colour};
            }}
        """)
        self.badge_label.setToolTip("\n".join(status_list) if status_list else status_summary)
        self.badge_label.show()
        
    def refresh_theme(self):
        self.setStyleSheet(self.STYLESHEET)
        self.image_label.setStyleSheet(self.IMAGE_STYLESHEET)
        self.platform_label.setStyleSheet(self.PLATFORM_STYLESHEET)
        # Also reapply any dynamic styles
        self.title_label.setStyleSheet("font-weight: bold;")  # palette-independent
        #self.platform_label.setStyleSheet("color: palette(mid); font-size: 11px;")
        
    def set_image(self, pixmap: QPixmap):
        scaled = pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")
    
    def set_error(self, error: str):
        self.image_label.setText(f"Error:\n{error[:20]}...")
        self.image_label.setPixmap(self.placeholder)
        
    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        if self._selected != value:
            self._selected = value
            self.setProperty("selected", "true" if value else "false")
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.leftClicked.emit(self.game, event.modifiers())
            event.accept()
        elif event.button() == Qt.RightButton:
            self.rightClicked.emit(self.game)
            event.accept()
        super().mousePressEvent(event)
    def mouseReleaseEvent(self, event):
        event.accept()          
        super().mouseReleaseEvent(event)
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit(self.game)
            event.accept()
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.clicked.emit(self.game)
            event.accept()
        super().keyPressEvent(event)
    
    def focusInEvent(self, event):
        self.focused.emit(self.game.id)
        super().focusInEvent(event)

class MultiSelectDialog(QDialog):
    """Dialog for multiple selection"""
    changed = Signal(list)
    
    def __init__(self, title: str, items: List[Tuple[str, str]], selected: List[str] = None):
        super().__init__()
        self._set_icon()
        self.items = items
        self.selected = selected or []
        self.setWindowTitle(title)
        self.setFixedSize(400, 500)
        self.setup_ui()

    def _set_icon(self):
        """Set dialog icon"""
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(ICON_B64))
        self.setWindowIcon(QIcon(pixmap))
    def setup_ui(self):
        layout = QVBoxLayout(self)
        search = QLineEdit()
        search.setPlaceholderText("Filter items...")
        search.textChanged.connect(self.filter)
        layout.addWidget(search)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        for item_id, name in self.items:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, item_id)
            self.list_widget.addItem(item)
            if item_id in self.selected:
                item.setSelected(True)
        layout.addWidget(self.list_widget)
        buttons = QHBoxLayout()
        select_all = QPushButton("Select All")
        select_all.clicked.connect(self.select_all)
        clear_all = QPushButton("Clear All")
        clear_all.clicked.connect(self.clear_all)
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept_selection)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(select_all)
        buttons.addWidget(clear_all)
        buttons.addStretch()
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
    
    def filter(self, text: str):
        text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text not in item.text().lower())
    
    def select_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                item.setSelected(True)
    
    def clear_all(self):
        self.list_widget.clearSelection()
    
    def accept_selection(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.isSelected():
                selected.append(item.data(Qt.UserRole))
        self.changed.emit(selected)
        self.accept()

class SettingsDialog(QDialog):
    changed = Signal(dict)

    def __init__(self, settings: dict, main_window):
        super().__init__()
        self.main_window = main_window
        self.settings = settings.copy()
        self._set_icon()
        self.setWindowTitle("Settings")
        self.setFixedSize(450, 650)
        self.setup_ui()
        self.update_api_mode_ui()   # initial refresh

    def _set_icon(self):
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(ICON_B64))
        self.setWindowIcon(QIcon(pixmap))

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        # Create scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        # API Settings
        api_group = QGroupBox("API Settings")
        api_layout = QVBoxLayout()
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("API Source:"))
        self.api_mode_combo = QComboBox()
        self.api_mode_combo.addItem("🌐 Remote API (api.crocdb.net)", "remote")
        self.api_mode_combo.addItem("🖥️ Local Server", "local")
        current_mode = self.settings.get("api_mode", "remote")
        index = self.api_mode_combo.findData(current_mode)
        if index >= 0:
            self.api_mode_combo.setCurrentIndex(index)
        self.api_mode_combo.currentIndexChanged.connect(self.update_api_mode_ui)
        mode_layout.addWidget(self.api_mode_combo)
        mode_layout.addStretch()
        api_layout.addLayout(mode_layout)
        # Server status label
        self.server_status_label = QLabel()
        self.configure_server_btn = QPushButton("Configure Local Server")
        self.configure_server_btn.clicked.connect(self.show_local_server_dialog)
        server_layout = QHBoxLayout()
        server_layout.addWidget(self.server_status_label, 1)
        server_layout.addWidget(self.configure_server_btn)
        api_layout.addLayout(server_layout)
        self.start_on_launch_cb = QCheckBox("Start local server on launch")
        self.start_on_launch_cb.setChecked(self.settings.get("start_local_on_launch", False))
        self.start_on_launch_cb.setToolTip(
            "Automatically start the local server when SwamPy starts.\n"
            "Only applies when API Source is set to 'Local Server'."
        )
        api_layout.addWidget(self.start_on_launch_cb)
        # Remote URL (readonly)
        remote_layout = QHBoxLayout()
        remote_layout.addWidget(QLabel("Remote URL:"))
        self.remote_url_label = QLabel("https://api.crocdb.net/")
        self.remote_url_label.setStyleSheet("color: #888;")
        remote_layout.addWidget(self.remote_url_label)
        remote_layout.addStretch()
        api_layout.addLayout(remote_layout)
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        # UI
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        self.fullscreen_cb = QCheckBox("Start in fullscreen")
        self.fullscreen_cb.setChecked(self.settings.get("start_fullscreen", True))
        self.fullscreen_cb.setToolTip("If unchecked, the window will start in normal mode.")
        display_layout.addWidget(self.fullscreen_cb)
        # Theme
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        available_styles = QStyleFactory.keys()
        self.theme_combo.addItem("System Default", "system")
        for style in available_styles:
            self.theme_combo.addItem(style, style)
        current_theme = self.settings.get("theme", "system")
        index = self.theme_combo.findData(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        display_layout.addLayout(theme_row)
            
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        # Download settings
        download_group = QGroupBox("Download Settings")
        download_layout = QVBoxLayout()
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Location:"))
        self.path_edit = QLineEdit(self.settings.get("download_path", ""))
        self.path_edit.setReadOnly(True)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self.browse)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse)
        download_layout.addLayout(path_layout)
        self.es_cb = QCheckBox("Use EmulationStation-DE folders")
        self.es_cb.setChecked(self.settings.get("use_es_folders", True))
        download_layout.addWidget(self.es_cb)
        self.extract_zips_cb = QCheckBox("Extract downloaded zip files")
        self.extract_zips_cb.setChecked(self.settings.get("extract_zips", False))
        self.extract_zips_cb.setToolTip("When enabled, any .zip file will be extracted and the original zip removed.")
        download_layout.addWidget(self.extract_zips_cb)

        # Vita3K settings
        psv_btn_layout = QHBoxLayout()
        psv_btn_layout.addWidget(QLabel("PSVita / Vita3K Settings:"))
        self.psv_settings_btn = QPushButton("Configure...")
        self.psv_settings_btn.clicked.connect(self.open_psv_settings)
        psv_btn_layout.addWidget(self.psv_settings_btn)
        psv_btn_layout.addStretch()
        layout.addLayout(psv_btn_layout)
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        # Filter settings
        filter_group = QGroupBox("Filter Settings")
        filter_layout = QVBoxLayout()
        self.demo_cb = QCheckBox("Remove demos from results")
        self.demo_cb.setChecked(self.settings.get("remove_demos", True))
        filter_layout.addWidget(self.demo_cb)
        self.m3u_cb = QCheckBox("Create .m3u folders for multi-discs (PSX,SDC,SS)")
        self.m3u_cb.setChecked(self.settings.get("create_m3u_folders", True))
        self.m3u_cb.setToolTip("Automatically create .m3u folders for PS1, Dreamcast, and Saturn games...")
        filter_layout.addWidget(self.m3u_cb)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        # Cache settings
        cache_group = QGroupBox("Cache Settings")
        cache_layout = QVBoxLayout()
        cache_layout.addWidget(QLabel("Image Cache Size (MB):"))
        self.cache_spin = QSpinBox()
        self.cache_spin.setRange(10, 500)
        self.cache_spin.setValue(self.settings.get("cache_size_mb", 50))
        self.cache_spin.setSuffix(" MB")
        cache_layout.addWidget(self.cache_spin)
        clear_btn = QPushButton("Clear Image Cache")
        clear_btn.clicked.connect(lambda: self.changed.emit({"clear_cache": True}))
        cache_layout.addWidget(clear_btn)
        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        # Contact
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        contact_label = QLabel()
        contact_label.setText(
            '<b>Contact me:</b> <a href="mailto:tarrareii@proton.me">tarrareii@proton.me</a> | '
            '<b>My BTC:</b> <span style="font-family: monospace;">bc1qtgfeglvxgahdj3jaqjsjx5s4ag8yv3ht9qp40z</span>'
        )
        contact_label.setOpenExternalLinks(True)
        contact_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        contact_label.setAlignment(Qt.AlignCenter)
        contact_label.setStyleSheet("padding: 0px; color: #888;")
        main_layout.addWidget(contact_label)
        contact_cavv_label = QLabel()
        contact_cavv_label.setText(
            '<b>Contact Cavv: </b><a href="mailto:cavv255@gmail.com">cavv255@gmail.com</a> | '
            '<b>Donate to CrocDB:</b> <a href="https://ko-fi.com/crocdb">ko-fi.com/crocdb</a>'
        )
        contact_cavv_label.setOpenExternalLinks(True)
        contact_cavv_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        contact_cavv_label.setAlignment(Qt.AlignCenter)
        contact_cavv_label.setStyleSheet("padding: 2px; color: #888;")
        main_layout.addWidget(contact_cavv_label)
        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        main_layout.addLayout(buttons)

    def open_psv_settings(self):
        dialog = PSVitaSettingsDialog(self.main_window, self.settings)
        if dialog.exec() == QDialog.Accepted:
            new_psv_settings = dialog.get_settings()
            self.settings.update(new_psv_settings)

    # UI Update - Shows server state
    def update_api_mode_ui(self):
        """Called when API mode changes or dialog is opened/refreshed."""
        is_local = self.api_mode_combo.currentData() == "local"

        if not is_local:
            self.server_status_label.setText("🌐 Using remote API")
            self.configure_server_btn.setEnabled(True)
            return

        # Local mode – show actual server status
        if not FLASK_AVAILABLE:
            self.server_status_label.setText("🔴 crocapi module not available")
            self.configure_server_btn.setEnabled(False)
            return

        thread = self.main_window.local_server_thread
        if thread and thread.isRunning():
            self.server_status_label.setText("🟢 Local server running")
        else:
            self.server_status_label.setText("🟡 Local server not configured")
        self.configure_server_btn.setEnabled(True)

    # Server configuration dialog
    def show_local_server_dialog(self):
        dialog = LocalServerDialog(self.main_window, self)
        dialog.exec()
        # Update settings from dialog
        self.settings["local_server_host"] = dialog.host_combo.currentText().strip()
        self.settings["local_server_port"] = dialog.port_spin.value()
        # Refresh status label (server may have been started/stopped)
        self.update_api_mode_ui()

    def browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Download Location")
        if path:
            self.path_edit.setText(path)
    def browse_vita3k(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Vita3K executable",
            "", "Executable files (*.exe);;All files (*)"
        )
        if path:
            self.vita3k_edit.setText(path)

    def save(self):
        settings = {
            "download_path": self.path_edit.text(),
            "use_es_folders": self.es_cb.isChecked(),
            "remove_demos": self.demo_cb.isChecked(),
            "cache_size_mb": self.cache_spin.value(),
            "create_m3u_folders": self.m3u_cb.isChecked(),
            "extract_zips": self.extract_zips_cb.isChecked(),
            "api_mode": self.api_mode_combo.currentData(),
            "local_server_port": self.settings.get("local_server_port", 5000),
            "local_server_host": self.settings.get("local_server_host", "127.0.0.1"),
            "start_local_on_launch": self.start_on_launch_cb.isChecked(),
            "start_fullscreen": self.fullscreen_cb.isChecked(),
            "theme": self.theme_combo.currentData(),
            #"vita3k_path": self.settings.get("vita3k_path", ""),
            #"auto_install_vita3k": self.settings.get("auto_install_vita3k", False),
            #"decrypt_psv_pkg": self.settings.get("decrypt_psv_pkg", True),
            #"delete_after_vita3k_install": self.settings.get("delete_after_vita3k_install", False),
            #"show_vita3k_compat": self.settings.get("show_vita3k_compat", True),
        }
        vita_keys = [
            "vita3k_path",
            "auto_install_vita3k",
            "decrypt_psv_pkg",
            "delete_after_vita3k_install",
            "show_vita3k_compat",
            "vita3k_compat_filter_enabled",
            "vita3k_compat_filter"
        ]
        for key in vita_keys:
            if key in self.settings:
                settings[key] = self.settings[key]
        self.changed.emit(settings)
        self.accept()

class DownloadQueueDialog(QDialog):
    def __init__(self, manager: DownloadManager):
        super().__init__()
        self.manager = manager
        self._set_icon()
        self.setWindowTitle("Download Queue")
        self.setFixedSize(600, 400)
        self.setup_ui()

    def _set_icon(self):
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(ICON_B64))
        self.setWindowIcon(QIcon(pixmap))

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.status_label = QLabel("Downloads: 0 queued, 0 active")
        layout.addWidget(self.status_label)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        buttons = QHBoxLayout()
        self.pause_resume_btn = QPushButton("⏸️ Pause")
        self.pause_resume_btn.clicked.connect(self.toggle_pause)
        self.pause_resume_btn.setEnabled(False)

        cancel_current = QPushButton("Cancel Current")
        cancel_current.clicked.connect(self.cancel_current)

        clear_completed = QPushButton("Clear Completed")
        clear_completed.clicked.connect(self.clear_completed)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        buttons.addWidget(self.pause_resume_btn)
        buttons.addWidget(cancel_current)
        buttons.addWidget(clear_completed)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self.update_ui_state()

    def refresh_queue_display(self):
        self.list_widget.clear()
        if self.manager.current:
            self._add_game(self.manager.current, is_current=True)
        for game in self.manager.queue:
            self._add_game(game, is_current=False)
        self.update_ui_state()

    def _add_game(self, game: Game, is_current: bool):
        widget = QueueItemWidget(game, is_current)
        widget.moved_up.connect(self._on_move_up)
        widget.remove_clicked.connect(self._on_remove)

        item = QListWidgetItem(self.list_widget)
        item.setSizeHint(widget.sizeHint())
        item.setData(Qt.UserRole, game.id)

        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)

    def _on_move_up(self, game_id: str):
        if self.manager.move_to_top(game_id):
            self.refresh_queue_display()

    def _on_remove(self, game_id: str):
        self.manager.remove_from_queue(game_id)
        self.refresh_queue_display()

    def update_progress(self, game_id: str, progress: float):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and widget.game_id == game_id:
                for child in widget.children():
                    if isinstance(child, QProgressBar):
                        child.setValue(int(progress * 100))
                        break
                break
        if self.manager.current and self.manager.current.id == game_id:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(int(progress * 100))

    def complete(self, game_id: str, path: str):
        self._mark_game(game_id, success=True)
        self.progress_bar.setVisible(False)
        self.update_ui_state()

    def error(self, game_id: str, message: str):
        self._mark_game(game_id, success=False)
        self.progress_bar.setVisible(False)
        self.update_ui_state()

    def _mark_game(self, game_id: str, success: bool):
        color = "#2ecc71" if success else "#e74c3c"
        prefix = "✓" if success else "✗"
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and widget.game_id == game_id:
                for child in widget.children():
                    if isinstance(child, QLabel) and child.text().startswith(("✓", "✗")):
                        child.setText(f"{prefix} {child.text()[2:]}")
                        child.setStyleSheet(f"color: {color}; font-weight: bold;")
                        break
                    elif isinstance(child, QProgressBar):
                        child.setValue(100)
                        child.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
                break

    def toggle_pause(self):
        if self.manager.is_paused():
            self.manager.resume()
            self.pause_resume_btn.setText("⏸️ Pause")
        else:
            self.manager.pause()
            self.pause_resume_btn.setText("▶️ Resume")
        self.update_ui_state()

    def cancel_current(self):
        if self.manager.current:
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(CANCEL_B64))
            msg = QMessageBox(self)
            msg.setIconPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio))
            msg.setWindowTitle("Cancel Download")
            msg.setText(f"Cancel download of '{self.manager.current.title}'?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            if msg.exec() == QMessageBox.Yes:
                self.manager.cancel_current()
        else:
            QMessageBox.information(self, "Info", "No download in progress.")

    def clear_completed(self):
        self.refresh_queue_display()

    def update_ui_state(self):
        queue_count = len(self.manager.queue)
        has_current = self.manager.current is not None
        if has_current:
            status = f"Downloading: {self.manager.current.title}"
            if queue_count > 0:
                status += f" | {queue_count} queued"
        else:
            status = f"Downloads: {queue_count} queued"
        self.status_label.setText(status)
        self.pause_resume_btn.setEnabled(has_current or queue_count > 0)
        self.pause_resume_btn.setText("⏸️ Pause" if not self.manager.is_paused() else "▶️ Resume")
            
class QueueItemWidget(QWidget):
    moved_up = Signal(str)
    remove_clicked = Signal(str)
    
    def __init__(self, game: Game, is_current: bool = False):
        super().__init__()
        self.game_id = game.id
        self.setup_ui(game, is_current)
    
    def setup_ui(self, game: Game, is_current: bool):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        # Up Arrow button (not for first item)
        if not is_current:
            self.up_btn = QPushButton("↑")
            self.up_btn.setFixedSize(25, 25)
            self.up_btn.setToolTip("Move to the top of the queue after the current download")
            self.up_btn.clicked.connect(lambda: self.moved_up.emit(self.game_id))
            layout.addWidget(self.up_btn)
        else:
            layout.addSpacing(30)
        # Game info
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(game.title)
        title.setStyleSheet("font-weight: bold;")
        details = QLabel(f"{game.platform} | {game.selected_format or 'Unknown'}")
        details.setStyleSheet("color: #888; font-size: 11px;")
        info_layout.addWidget(title)
        info_layout.addWidget(details)
        layout.addWidget(info_widget, 1)
        # Progress bar
        if is_current:
            self.progress_bar = QProgressBar()
            self.progress_bar.setFixedWidth(100)
            self.progress_bar.setRange(0, 100)
            layout.addWidget(self.progress_bar)
        # Remove button
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(25, 25)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                color: #ff4444;
                border: 1px solid #ff4444;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: #ff4444;
                color: white;
            }
        """)
        self.remove_btn.setToolTip("Remove from queue")
        self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.game_id))
        layout.addWidget(self.remove_btn)

class PSVitaHelper:
    TSV_URL = "https://nopaystation.com/tsv/PSV_GAMES.tsv"

    def __init__(self):
        self.zrif_map = {}
        self.tsv_loaded = False
        self.pkg2zip_binary = None
        self._detect_pkg2zip_dir()
        
    def _detect_pkg2zip_dir(self):
        """Determine the directory containing pkg2zip binaries."""
        if getattr(sys, 'frozen', False):
            # Running as bundled executable
            if hasattr(sys, '_MEIPASS'):
                # One-file mode: files extracted to temp folder
                base = Path(sys._MEIPASS)
            else:
                # One-folder mode: files are next to the .exe
                base = Path(sys.executable).parent
        else:
            # Running as script
            base = Path(__file__).parent
        self.pkg2zip_dir = base / "pkg2zip"
    def ensure_tsv(self):
        if not self.tsv_loaded:
            self._load_tsv()

    def _load_tsv(self):
        try:
            response = requests.get(self.TSV_URL, timeout=10)
            if response.ok:
                tsv_data = response.text
                reader = csv.reader(tsv_data.splitlines(), delimiter='\t')
                rows = list(reader)
                if rows:
                    header = rows[0]
                    # Find column indices
                    title_col = 0
                    zrif_col = None
                    for i, col in enumerate(header):
                        if col.lower() == 'zrif':
                            zrif_col = i
                        elif col.lower() in ('title id', 'titleid'):
                            title_col = i
                    if zrif_col is None:
                        zrif_col = 4   # fallback (common position)
                    for row in rows[1:]:
                        if len(row) > max(title_col, zrif_col):
                            title_id = row[title_col].strip()
                            zrif = row[zrif_col].strip()
                            if zrif and zrif != 'MISSING':
                                self.zrif_map[title_id] = zrif
                    self.tsv_loaded = True
        except Exception as e:
            print(f"Error loading NoPayStation TSV: {e}")

    def get_zrif(self, title_id):
        self.ensure_tsv()
        return self.zrif_map.get(title_id)

    def ensure_pkg2zip(self):
        if self.pkg2zip_binary is not None:
            return True
        system = platform.system().lower()
        # Determine binary name
        if system == "windows":
            binary_name = "pkg2zip.exe"
        elif system == "linux":
            # Android check
            is_android = (os.environ.get("ANDROID_ROOT") is not None or
                          os.environ.get("PREFIX", "").find("com.termux") != -1 or
                          os.path.exists("/system/build.prop"))
            binary_name = "pkg2zip-android" if is_android else "pkg2zip"
        else:
            binary_name = "pkg2zip"
        binary_path = self.pkg2zip_dir / binary_name
        if not binary_path.exists():
            print(f"pkg2zip binary not found at {binary_path}")
            return False
        # Ensure executable on Unix
        if system != "windows":
            try:
                os.chmod(binary_path, 0o755)
            except:
                pass
        self.pkg2zip_binary = binary_path
        return True

    def decrypt_pkg(self, pkg_path, zrif, output_dir):
        """Decrypt .pkg to .zip. Returns path to zip or None."""
        if not self.ensure_pkg2zip():
            return None
        cmd = [str(self.pkg2zip_binary), str(pkg_path)]
        if zrif:
            cmd.append(zrif)
        cmd.extend(["-o", output_dir])
        try:
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=output_dir,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            if result.returncode == 0:
                # Find the most recent .zip file in the output directory
                output_path = Path(output_dir)
                zip_files = list(output_path.glob("*.zip"))
                if zip_files:
                    # Sort by modification time (newest first)
                    zip_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    return str(zip_files[0])
                else:
                    print("No .zip file found after pkg2zip")
                    return None
            else:
                print(f"pkg2zip error: {result.stderr}")
                return None
        except Exception as e:
            print(f"Error running pkg2zip: {e}")
            return None



class MainWindow(QMainWindow):
    """Main application window"""
    server_state = Signal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SwamPy: Dogwater CrocDB Browser")
        self._set_icon()
        self._is_initial_load = False
        self.current_page = 1
        self.total_pages = 1
        self.max_results = 20
        self.current_games: List[Game] = []
        self.focused_index = 0
        self.selected_games = set()          # set of game IDs currently selected
        self.last_selected_index = -1        # for shift-click range selection
        self.cards: List[GameCard] = []
        self.selected_platforms: List[str] = []
        self.selected_regions: List[str] = []
        self.settings = DEFAULT_SETTINGS.copy()
        self.performing_search = False
        self.search_pending = None
        self.search_retries = 0
        self.placeholder = self._create_placeholder()
        self.local_server_thread: Optional[LocalServerThread] = None
        self.setup_ui()
        # Drag select
        self.drag_select_active = False
        self.drag_origin = None
        self.drag_started = False
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self.grid_container)
        self.grid_container.setMouseTracking(True)
        self.grid_container.installEventFilter(self)
        
        self.cache = ImageCache(self.settings["cache_size_mb"])
        self.image_loader = ImageLoader()
        self._load_config()  
        self.psv_helper = PSVitaHelper()
        self.vita3k_compat = Vita3KCompatibility()
        if self.settings.get("show_vita3k_compat", True):
            # Optionally trigger a background fetch if cache is empty
            if not self.vita3k_compat.data:
                QTimer.singleShot(1000, self.vita3k_compat.fetch)  # lazy load
        self.download_manager = DownloadManager(
            self.settings["download_path"],
            self.settings["use_es_folders"],
            create_m3u=self.settings.get("create_m3u_folders", True),
            psv_helper=self.psv_helper,
            decrypt_psv_pkg=self.settings.get("decrypt_psv_pkg", True),
            auto_install_vita3k=self.settings.get("auto_install_vita3k", False),
            vita3k_path=self.settings.get("vita3k_path", ""),
            delete_after_vita3k_install=self.settings.get("delete_after_vita3k_install", False),
            extract_zips=self.settings.get("extract_zips", False)
        )
        self.setup_connections()
        self.queue_dialog: Optional[DownloadQueueDialog] = None
        QApplication.instance().paletteChanged.connect(self.on_system_palette_changed)    
        self._apply_theme(self.settings.get("theme", "system"))
        self.kill_process_on_port(self.settings.get("local_server_port", 5000))
        if (self.settings.get("api_mode") == "local" and
            self.settings.get("start_local_on_launch", False) and
            FLASK_AVAILABLE):
            # Autostart local server, then load once it's running
            self.start_server()
            self.local_server_thread.started.connect(self.load_initial)
            self.local_server_thread.error.connect(
                lambda: QTimer.singleShot(100, self.load_initial)
            )
        else:
            QTimer.singleShot(100, self.load_initial)
        if self.settings.get("start_fullscreen", True):
            self.showFullScreen()
        else:
            geometry = self.settings.get("window_geometry", "")
            if geometry:
                # Restore saved geometry
                self.restoreGeometry(QByteArray.fromBase64(geometry.encode('ascii')))
                self.showNormal()
            else:
                # First launch in windowed mode uses default size and center
                default_size = QSize(1200, 800)
                self.resize(default_size)
                screen = QApplication.primaryScreen().availableGeometry()
                center = screen.center()
                self.move(center.x() - default_size.width() // 2,
                          center.y() - default_size.height() // 2)
                self.showNormal()
    def _on_game_double_clicked(self, game: Game):
        self._download_game(game)
    def _download_game(self, game: Game):
        """Add a single game to download queue with space check."""
        if not game.download_url:
            QMessageBox.warning(self, "No Download", "No download URL available.")
            return
        try:
            response = requests.head(game.download_url, timeout=10)
            if size := response.headers.get('content-length'):
                game.file_size = int(size)
                if not self.download_manager.check_space(game.file_size):
                    reply = QMessageBox.warning(
                        self,
                        "Low Disk Space",
                        f"Insufficient space for '{game.title}'.\nAdd anyway?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
        except:
            pass
        self.download_manager.add(game)
        queue_size = len(self.download_manager.queue) + (1 if self.download_manager.current else 0)
        self.queue_btn.setText(f"Queue ({queue_size})")
        if not self.queue_dialog:
            self.queue_dialog = DownloadQueueDialog(self.download_manager)
            self.queue_dialog.setModal(False)
        self.queue_dialog.refresh_queue_display()
    def _create_cards_from_games(self):
        """Create GameCard widgets for self.current_games and add to grid."""
        for i, game in enumerate(self.current_games):
            card = GameCard(game, self.placeholder)
            if game.platform.lower() == 'psv' and game.rom_id and self.settings.get("show_vita3k_compat", True):
                status_list = self.vita3k_compat.get_status(game.rom_id)
                if status_list:
                    summary = self.vita3k_compat.get_status_summary(game.rom_id)
                    card.set_compat_status(summary, status_list)
            card.leftClicked.connect(self._on_card_left_clicked)
            card.rightClicked.connect(self._on_card_right_clicked)
            card.doubleClicked.connect(self._on_game_double_clicked)
            card.focused.connect(lambda gid=game.id: self._on_card_focused(gid))
            if game.cover_url:
                cached = self.cache.get(game.cover_url)
                if cached:
                    card.set_image(cached)
                else:
                    self.image_loader.add(game.cover_url, game.id)
            else:
                card.set_image(self.placeholder)
            self.cards.append(card)
        self._layout_cards()
        self.grid_container.setFocus()
        if self.cards:
            self.focused_index = 0
            self.cards[0].setFocus()
    def show_romset_manager(self):
        dialog = RomsetManagerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            romset_path = dialog.get_selected_romset()
            if romset_path:
                self.load_romset(romset_path)

    def load_romset(self, romset_path: Path):
        """Fetch all games listed in the romset and display them."""
        if not romset_path.exists():
            QMessageBox.warning(self, "Error", "Romset file does not exist.")
            return
        with open(romset_path, 'r', encoding='utf-8') as f:
            slugs = [line.strip() for line in f if line.strip()]
        if not slugs:
            QMessageBox.information(self, "Empty Romset", "The romset file is empty.")
            return
        unique_slugs = list(dict.fromkeys(slugs))
        total = len(unique_slugs)
        progress = QProgressDialog("Loading romset...", "Cancel", 0, total, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(500)
        games = []
        api_base = self.get_api_base_url()
        failed = 0
        for i, slug in enumerate(unique_slugs):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            progress.setLabelText(f"Fetching {i+1}/{total}: {slug}")

            try:
                response = requests.post(
                    urljoin(api_base, "entry"),
                    json={"slug": slug},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                if response.ok:
                    data = response.json()
                    # Extract the actual game data from the nested response
                    game_data = None
                    if isinstance(data, dict):
                        if "data" in data and isinstance(data["data"], dict):
                            inner = data["data"]
                            if "entry" in inner:
                                game_data = inner["entry"]
                            else:
                                game_data = inner  # fallback
                        else:
                            game_data = data  # direct game object
                    if game_data and game_data.get("title") and game_data.get("platform"):
                        title = game_data["title"]
                        platform = game_data["platform"]
                        regions = game_data.get("regions", [])
                        region = regions[0] if regions else "Unknown"
                        links = game_data.get("links", [])
                        download_url, selected_format, size_str = self._select_best_download_url(links)

                        base_name, disc_number, is_multi_disc = self._parse_disc_info(title, platform)

                        game = Game(
                            id=slug,
                            title=title[:50],
                            platform=platform,
                            region=region,
                            cover_url=game_data.get("boxart_url"),
                            rom_id=game_data.get("rom_id"),
                            download_url=download_url,
                            selected_format=selected_format,
                            size_str=size_str,
                            disc_number=disc_number,
                            base_game_name=base_name,
                            is_multi_disc=is_multi_disc
                        )
                        if game.platform.lower() == 'psv' and game.rom_id:
                            game.cover_url = f"https://raw.githubusercontent.com/tarrare2/psv-covers/main/covers/{game.rom_id}.jpg"
                        games.append(game)
                    else:
                        failed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error fetching {slug}: {e}")
                failed += 1

        progress.setValue(total)

        if games:
            self._clear_grid()
            self._clear_selection()
            self.current_games = games
            self._create_cards_from_games()
            self.total_pages = 1
            self.current_page = 1
            self._update_pagination()
            self.status_bar.showMessage(f"Loaded {len(games)} games from romset (failed: {failed})", 5000)
        else:
            QMessageBox.warning(self, "Load Failed", "No games could be loaded from the romset.")
    def _add_to_romset(self):
        """Add all selected games to a romset file"""
        if not self.selected_games:
            return
        dialog = RomsetDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        romset_path = dialog.get_selected_romset()
        if not romset_path:
            return
        # Gather slugs of selected games
        slugs = []
        for game in self.current_games:
            if game.id in self.selected_games:
                slugs.append(game.id)
        # Read existing slugs (if file exists) to avoid duplicates
        existing = set()
        if romset_path.exists():
            with open(romset_path, 'r', encoding='utf-8') as f:
                existing = set(line.strip() for line in f if line.strip())
        # Append new slugs that aren't already present
        new_slugs = [s for s in slugs if s not in existing]
        if new_slugs:
            with open(romset_path, 'a', encoding='utf-8') as f:
                for slug in new_slugs:
                    f.write(slug + '\n')
            QMessageBox.information(self, "Romset updated",
                                    f"Added {len(new_slugs)} game(s) to {romset_path.name}")
        else:
            QMessageBox.information(self, "No new games",
                                    "All selected games are already in that romset.")
    def _on_card_left_clicked(self, game: Game, modifiers: Qt.KeyboardModifiers):
        """Handle left click with modifiers: manage selection"""
        #print(f"Left clicked {game.id} with modifiers {modifiers}") #debug
        index = self.current_games.index(game)
        if modifiers & Qt.ControlModifier:
            # Ctrl+click: toggle selection of this card
            #print(f"Setting selected on {game.id}") #debug
            if game.id in self.selected_games:
                self.selected_games.remove(game.id)
                self.cards[index].selected = False
            else:
                self.selected_games.add(game.id)
                self.cards[index].selected = True
            self.last_selected_index = index
        elif modifiers & Qt.ShiftModifier and self.last_selected_index != -1:
            # Shift+click: select range from last selected to current
            start = min(self.last_selected_index, index)
            end = max(self.last_selected_index, index)
            for i in range(start, end + 1):
                gid = self.current_games[i].id
                self.selected_games.add(gid)
                self.cards[i].selected = True
            self.last_selected_index = index
        else:
            # Plain click: clear previous selection, select only this card
            self._clear_selection()
            self.selected_games.add(game.id)
            self.cards[index].selected = True
            self.last_selected_index = index
        # self.update_status_bar()
    def _on_card_right_clicked(self, game: Game):
        """Right click: ensure this card is selected (if not already) and show context menu"""
        index = self.current_games.index(game)
        # If this card is not selected, clear selection and select only this one
        if game.id not in self.selected_games:
            self._clear_selection()
            self.selected_games.add(game.id)
            self.cards[index].selected = True
            self.last_selected_index = index

        self._show_context_menu(QCursor.pos())

    def _clear_selection(self):
        """Deselect all cards"""
        for gid in self.selected_games:
            for i, game in enumerate(self.current_games):
                if game.id == gid:
                    self.cards[i].selected = False
                    break
        self.selected_games.clear()
        self.last_selected_index = -1

    def _show_context_menu(self, pos):
        """Create and show the right click context menu"""
        if not self.selected_games:
            return
        menu = QMenu(self)
        download_action = menu.addAction("Download")
        download_action.triggered.connect(self._download_selected)
        add_action = menu.addAction("Add to romset")
        add_action.triggered.connect(self._add_to_romset)
        menu.exec(pos)
    def _download_selected(self):
        """Add all selected games to download queue."""
        if not self.selected_games:
            return
        for game in self.current_games:
            if game.id in self.selected_games:
                self._download_game(game)
    def changeEvent(self, event):
        if event.type() == QEvent.ApplicationPaletteChange:
            print("System theme changed!")
            self._apply_theme(self.settings.get("theme", "system"))
            # refresh all GameCards on theme change. Reapplying the theme seems to be better
            #for card in self.findChildren(GameCard):
                #card.refresh_theme()
        super().changeEvent(event)
    """
    def _apply_theme(self, theme_name):
        app = QApplication.instance()
        if theme_name == "system":
            app.setStyle(QStyleFactory.create(""))
            app.setPalette(app.style().standardPalette())
        else:
            style = QStyleFactory.create(theme_name)
            if style:
                app.setStyle(style)

        # Force all GameCard widgets to refresh their theme
        for card in self.findChildren(GameCard):
            card.refresh_theme()

        # Optional: force a global repaint
        for widget in QApplication.allWidgets():
            widget.update()
    """
    def on_system_palette_changed(self, palette):
        """Called when the system theme (light/dark) changes."""
        # Refresh all GameCard widgets so they adapt to the new palette
        for card in self.findChildren(GameCard):
            card.refresh_theme()
        # Optional: force a repaint
        self.repaint()
    def _apply_theme(self, theme_name):
        app = QApplication.instance()

        # 1. Determine and set the new style
        if theme_name == "system":
            new_style = None  # Qt will use platform default
        else:
            new_style = QStyleFactory.create(theme_name)

        if not new_style and theme_name != "system":
            return  # style not available

        # 2. Set the style – this automatically updates the palette
        app.setStyle(new_style)

        # 3. Force all widgets to update to the new style/palette
        for widget in app.allWidgets():
            if not widget:
                continue
            # Temporarily remove stylesheet to force update of palette(role)
            ss = widget.styleSheet()
            widget.setStyleSheet("")
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.setStyleSheet(ss)
            widget.update()

        # 4. Explicitly refresh GameCard widgets
        for card in self.findChildren(GameCard):
            card.refresh_theme()

        # 5. Send ApplicationPaletteChange event to the whole app
        event = QEvent(QEvent.ApplicationPaletteChange)
        app.sendEvent(app, event)

        # 6. Process any pending events and repaint
        app.processEvents()
        for w in app.topLevelWidgets():
            w.repaint()
    def get_api_base_url(self) -> str:
        """Get the current API base URL based on settings"""
        if self.settings.get("api_mode") == "local" and FLASK_AVAILABLE:
            host = self.settings.get("local_server_host", "127.0.0.1")
            port = self.settings.get("local_server_port", 5000)
            return f"http://{host}:{port}/"
        else:
            return REMOTE_API_URL
    def on_local_server_error(self, error):
        """Handle local server error"""
        self.status_bar.showMessage(f"Local server error: {error}", 5000)
        
        reply = QMessageBox.critical(
            self,
            "Local Server Error",
            f"Failed to start or connect to local server:\n\n{error}\n\n"
            "Would you like to switch to remote API?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.settings["api_mode"] = "remote"
            self._save_config()
            self.load_initial()
    def kill_process_on_port(self, port):
        """Terminate any process that is listening on the given port."""
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                try:
                    proc = psutil.Process(conn.pid)
                    proc.terminate()          # polite termination
                    proc.wait(timeout=3)      # wait up to 3 seconds
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    try:
                        proc.kill()          # force kill if needed
                    except:
                        pass
                print(f"Killed process {conn.pid} using port {port}")
    def start_server(self, host=None, port=None):
        """Start the local server (called from dialog or on API mode switch)."""
        if self.local_server_thread and self.local_server_thread.isRunning():
            self.stop_server()               # blocks until thread stops
        host = host or self.settings.get("local_server_host", "127.0.0.1")
        port = port or self.settings.get("local_server_port", 5000)
        self.kill_process_on_port(port)
        self.local_server_thread = LocalServerThread(host, port)
        self.local_server_thread.started.connect(self._on_server_started)
        self.local_server_thread.error.connect(self._on_server_error)
        self.local_server_thread.stopped.connect(self._on_server_stopped)        
        self.server_state.emit("starting")
        self.status_bar.showMessage("Starting local API server...")
        self.local_server_thread.start()

    def stop_server(self):
        """Stop the local server."""
        if self.local_server_thread and self.local_server_thread.isRunning():
            self.status_bar.showMessage("Stopping local API server...")
            self.local_server_thread.stop()

    # Slots for thread signals + server_state emission
    def _on_server_started(self, url):
        """Called when the server thread successfully starts."""
        if self.local_server_thread:
            self.settings["local_server_host"] = self.local_server_thread.host
            self.settings["local_server_port"] = self.local_server_thread.port
            self._save_config()
        self.server_state.emit("running")
        self.status_bar.showMessage(f"Local API server running at {url}", 5000)
        QTimer.singleShot(2000, self._test_server_connection)

    def _on_server_error(self, error_msg):
        """Called when the server thread fails to start."""
        self.server_state.emit("error")
        self.status_bar.showMessage(f"Local server error: {error_msg}", 5000)
        # Ask user if they want to fall back to remote API
        self._handle_local_api_failure(error_msg)

    def _on_server_stopped(self):
        """Called when the server thread has fully stopped."""
        if self.sender() == self.local_server_thread:
            self.local_server_thread = None
            self.server_state.emit("stopped")
            self.status_bar.showMessage("Local API server stopped", 3000)

    def _test_server_connection(self):
        """Test the connection and autoswitch to remote if needed."""
        thread = self.local_server_thread
        if not thread or not thread.isRunning():
            return
        #url = thread.server_url
        try:
            url = urljoin(self.get_api_base_url(), "info")
            response = requests.get(url, timeout=3)
            if response.ok:
                self.status_bar.showMessage("Connected to local API server", 3000)
            else:
                self._handle_local_api_failure("Server not responding correctly")
        except Exception as e:
            self._handle_local_api_failure(str(e))

    def _handle_local_api_failure(self, error_detail=""):
        """Offer to switch to remote API when local server fails."""
        if self.settings.get("api_mode") != "local":
            return
        reply = QMessageBox.critical(
            self,
            "Local API Connection Failed",
            f"Local server error:\n{error_detail}\n\n"
            "Would you like to switch to the remote API?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.settings["api_mode"] = "remote"
            self._save_config()
            self.status_bar.showMessage("Switched to remote API", 3000)

    def _select_best_download_url(self, links):
        """Format selection based on heuristic rules."""
        if not links:
            return None, None
        # Group links by format
        links_by_format = {}
        for link in links:
            fmt = link.get("format", "").lower().strip()
            if fmt:
                links_by_format.setdefault(fmt, []).append(link)
        def get_url(fmt):
            if fmt in links_by_format and links_by_format[fmt]:
                link = links_by_format[fmt][0]
                return link.get("url"), fmt, link.get("size_str")
            return None, None, None
        # RULE 1: If bin/cue exists -> chd > iso > other > bin/cue
        if "bin/cue" in links_by_format:
            url, fmt, size = (
                get_url("chd") or
                get_url("iso") or
                self._get_any_single_file(links_by_format, exclude=["bin/cue"]) or
                get_url("bin/cue")
            )
            '''
            fmt = (
                "chd" if get_url("chd") else
                "iso" if get_url("iso") else
                "single" if self._get_any_single_file(links_by_format, exclude=["bin/cue"]) else
                "bin/cue"
            )
            '''
            #print(f"DEBUG: Selected {selected_fmt} from available: {list(links_by_format.keys())}")
            return url, fmt, size
        # RULE 2: If cia exists -> 3ds > cia
        if "cia" in links_by_format:
            url, fmt, size = get_url("3ds") or get_url("cia")
            #fmt = "3ds" if get_url("3ds") else "cia"
            return url, fmt, size
        # RULE 3: If nonpdrm/vpk/psv exists -> pkg > nonpdrm > vpk > psv
        vita_formats = ["pkg","nonpdrm", "vpk", "psv"]
        for vita_fmt in vita_formats:
            if vita_fmt in links_by_format:
                url, fmt, size = get_url("pkg") or get_url("nonpdrm") or get_url("vpk") or get_url("psv")
                return url, fmt, size
        # RULE 4: Default to first available
        first_fmt = next(iter(links_by_format))
        url, fmt, size = get_url(first_fmt)
        return url, fmt, size
    
    def _get_any_single_file(self, links_by_format, exclude=None):
        """Find any likely single-file format."""
        exclude = exclude or []
        multi_indicators = ["/", "+"]
        for fmt, links in links_by_format.items():
            if fmt in exclude:
                continue
            # Check if it looks like single file
            if not any(indicator in fmt for indicator in multi_indicators):
                if links and links[0].get("url"):
                    return links[0].get("url")
        return None

    def _parse_disc_info(self, title: str, platform: str) -> tuple[str, int, bool]:
        """Extract disc information from game title.
        Returns: (base_name, disc_number, is_multi_disc)
        """
        # Only check for discs on supported platforms
        if platform.lower() not in M3U_PLATFORMS:
            return title, 1, False
        patterns = [
            r'(.*?)\s*\(Disc\s*(\d+)\)',
            r'(.*?)\s*\(Disc\s*(\d+)\s*of\s*\d+\)',
            r'(.*?)\s*\[Disc\s*(\d+)\]',
            r'(.*?)\s*Disc\s*(\d+)',
            r'(.*?)\s*\(Part\s*(\d+)\)',
        ]
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                base_name = match.group(1).strip()
                disc_number = int(match.group(2))
                #print(f"DEBUG: '{title}' -> base='{base_name}', disc={disc_number}, multi={is_multi_disc}")
                return base_name, disc_number, True
        # No disc pattern found
        return title, 1, False
    
    def _set_icon(self):
        """Set window icon from base64"""
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(ICON_B64))
        self.setWindowIcon(QIcon(pixmap))
    
    def _create_placeholder(self) -> QPixmap:
        """Create placeholder pixmap"""
        try:
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(PLACEHOLDER_B64))
            if not pixmap.isNull():
                return pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except:
            pass
        # Fallback to cancel icon
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(CANCEL_B64))
        return pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    def _load_config(self):
        """Load configuration including cached API data"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                #print(f"Loaded config: {config}")  # debug
                self.selected_platforms = config.get("selected_platforms", [])
                self.selected_regions = config.get("selected_regions", [])
                # Update settings, but keep defaults for missing keys
                saved_settings = config.get("settings", {})
                self.settings.update(saved_settings)
                #print(f"Updated settings: {self.settings}") #debug
                self.cached_platforms = config.get("platforms_data", {})
                self.cached_regions = config.get("regions_data", {})
                if self.cached_platforms and "data" in self.cached_platforms:
                    platform_dict = self.cached_platforms["data"].get("platforms", {})
                    self.platforms = [(pid, info.get("name", pid.upper())) for pid, info in platform_dict.items()]
                else:
                    self.platforms = []
                if self.cached_regions and "data" in self.cached_regions:
                    region_dict = self.cached_regions["data"].get("regions", {})
                    self.regions = list(region_dict.items())
                else:
                    self.regions = []
                if len(self.selected_platforms) == 1 and self.platforms:
                    for pid, name in self.platforms:
                        if pid == self.selected_platforms[0]:
                            self.platform_btn.setText(name)
                            break
                if len(self.selected_regions) == 1 and self.regions:
                    for rid, name in self.regions:
                        if rid == self.selected_regions[0]:
                            self.region_btn.setText(name)
                            break
            else:
                print("Config file not found, using defaults")
                self.cached_platforms = {}
                self.cached_regions = {}
                self.platforms = []
                self.regions = []
        except Exception as e:
            print(f"Config load error: {e}")
            # Init empty caches on error
            self.cached_platforms = {}
            self.cached_regions = {}
            self.platforms = []
            self.regions = []
    
    def _cache_api_data(self, data_type: str, data: dict):
        """Cache API response data to config"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            if data_type == "platforms":
                config["platforms_data"] = data
                self.cached_platforms = data
            elif data_type == "regions":
                config["regions_data"] = data
                self.cached_regions = data
            with open(CONFIG_FILE, 'w') as f:# Save updated config
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Cache save error: {e}")
    
    def _save_config(self):
        """Save configuration including cached data"""
        try:
            config = {
                "selected_platforms": self.selected_platforms,
                "selected_regions": self.selected_regions,
                "settings": self.settings,
                "platforms_data": self.cached_platforms,
                "regions_data": self.cached_regions
            }
            # Ensure directory exists
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            #print(f"Saved config: {config}")  # debug
        except Exception as e:
            print(f"Config save error: {e}")
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search games...")
        self.search_input.setMinimumWidth(300)
        self.platform_btn = QPushButton(self._get_platform_text())
        self.platform_btn.setMinimumWidth(100)
        self.region_btn = QPushButton(self._get_region_text())
        self.region_btn.setMinimumWidth(100)
        self.search_btn = QPushButton("Search")
        self.queue_btn = QPushButton("Queue (0)")
        self.romset_btn = QPushButton("Romsets")
        self.settings_btn = QPushButton("Settings")
        #top.addWidget(QLabel("Search:"))
        top.addWidget(self.search_input)
        #top.addWidget(QLabel("Platform:"))
        top.addWidget(self.platform_btn)
        #top.addWidget(QLabel("Region:"))
        top.addWidget(self.region_btn)
        top.addWidget(self.search_btn)
        top.addWidget(self.queue_btn)
        top.addWidget(self.romset_btn)
        top.addWidget(self.settings_btn)
        layout.addLayout(top)
        class ScrollArea(QScrollArea):
            def keyPressEvent(self, event):
                if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                                  Qt.Key_PageUp, Qt.Key_PageDown):
                    event.ignore()
                else:
                    super().keyPressEvent(event)
        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setFocusPolicy(Qt.NoFocus)
        self.grid_container = QWidget()
        self.grid_container.setFocusPolicy(Qt.StrongFocus)
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(5)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        
        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)
        self.status_bar = self.statusBar()
        self.page_label = QLabel("Page 1 of 1")
        self.status_bar.addPermanentWidget(self.page_label)
        pagination = QHBoxLayout()
        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.setEnabled(False)
        self.page_combo = QComboBox()
        self.next_btn = QPushButton("Next →")
        self.next_btn.setEnabled(False)
        pagination.addWidget(self.prev_btn)
        pagination.addWidget(QLabel("Page:"))
        pagination.addWidget(self.page_combo)
        pagination.addStretch()
        pagination.addWidget(self.next_btn)
        layout.addLayout(pagination)
    
    def _get_platform_text(self) -> str:
        if not self.selected_platforms:
            return "All Platforms"
        elif len(self.selected_platforms) == 1:
            return "1 Platform"  # Will be updated when platforms loaded
        else:
            return f"{len(self.selected_platforms)} Platforms"
    
    def _get_region_text(self) -> str:
        if not self.selected_regions:
            return "All Regions"
        elif len(self.selected_regions) == 1:
            return "1 Region"  # Will be updated when regions loaded
        else:
            return f"{len(self.selected_regions)} Regions"
    
    def setup_connections(self):
        self.search_input.returnPressed.connect(self.search)
        self.platform_btn.clicked.connect(self.show_platforms)
        self.region_btn.clicked.connect(self.show_regions)
        self.search_btn.clicked.connect(self.search)
        self.queue_btn.clicked.connect(self.show_queue)
        self.romset_btn.clicked.connect(self.show_romset_manager)
        self.settings_btn.clicked.connect(self.show_settings)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        self.page_combo.activated.connect(self._on_page_change)
        self.image_loader.loaded.connect(self._on_image_loaded)# Threads
        self.image_loader.error.connect(self._on_image_error)
        self.download_manager.progress.connect(self._on_download_progress)
        self.download_manager.complete.connect(self._on_download_complete)
        self.download_manager.error.connect(self._on_download_error)
        self.grid_container.installEventFilter(self)# Events
        self.scroll.installEventFilter(self)
    
    def load_initial(self):
        """Load platforms and regions with cache or fetch"""
        api_base = self.get_api_base_url()
        self._is_initial_load = True
        if not self.platforms:# Check cached platforms, if none then fetch
            try:
                response = requests.get(urljoin(api_base, "platforms"), timeout=10)
                if response.ok:
                    data = response.json()
                    self._cache_api_data("platforms", data)  # Cache the response
                    if "data" in data and "platforms" in data["data"]:
                        self.platforms = [
                            (pid, info.get("name", pid.upper()))
                            for pid, info in data["data"]["platforms"].items()
                        ]
                    else:
                        self._load_fallback_platforms()
                else:
                    self._load_fallback_platforms()
            except:
                self._load_fallback_platforms()
        else:
            if len(self.selected_platforms) == 1:
                for pid, name in self.platforms:
                    if pid == self.selected_platforms[0]:
                        self.platform_btn.setText(name)
                        break
        if not self.regions:
            try:
                response = requests.get(urljoin(api_base, "regions"), timeout=10)
                if response.ok:
                    data = response.json()
                    self._cache_api_data("regions", data)
                    if "data" in data and "regions" in data["data"]:
                        self.regions = list(data["data"]["regions"].items())
                    else:
                        self._load_fallback_regions()
                else:
                    self._load_fallback_regions()
            except:
                self._load_fallback_regions()
        else:
            if len(self.selected_regions) == 1:
                for rid, name in self.regions:
                    if rid == self.selected_regions[0]:
                        self.region_btn.setText(name)
                        break
        self.platform_btn.setText(self._get_platform_text())
        self.region_btn.setText(self._get_region_text())
        self._is_initial_load = False
    
    def _load_fallback_platforms(self):
        """Load fallback platforms when API is unavailable"""
        self.platforms = [
            ("nes", "Nintendo Entertainment System"),
            ("snes", "Super Nintendo"),
            ("n64", "Nintendo 64"),
            ("gba", "Game Boy Advance"),
            ("gbc", "Game Boy Color"),
            ("gb", "Game Boy"),
            ("ps1", "PlayStation"),
            ("ps2", "PlayStation 2"),
            ("genesis", "Sega Genesis"),
            ("dreamcast", "Sega Dreamcast"),
        ]
    
    def _load_fallback_regions(self):
        """Load fallback regions when API is unavailable"""
        self.regions = [
            ("us", "USA"), ("eu", "Europe"),
            ("jp", "Japan"), ("other", "Other")
        ]
    
    def search(self):
        query = self.search_input.text().strip()
        self.current_page = 1
        self._search(query, self.selected_platforms, self.selected_regions, self.current_page)
    
    def _search(self, query: str, platforms: List[str], regions: List[str], page: int):
        data = {
            "search_key": query,
            "max_results": self.max_results,
            "page": page
        }
        if platforms:
            data["platforms"] = platforms
        if regions:
            data["regions"] = regions
        if (self.settings.get("api_mode") == "local" and self.local_server_thread and not self.local_server_thread.isRunning()):
            if self.search_pending is None:# Retry search when local server is just starting
                self.search_pending = (query, platforms, regions, page)
                self.search_retries = 0
                self._retry_search()
            return
        api_base = self.get_api_base_url()
        try:
            response = requests.post(
                urljoin(api_base, "search"),
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            if response.ok:
                data = response.json()
                self._display_games(data)
                if "data" in data and isinstance(data["data"], dict):
                    content = data["data"]
                    total = content.get("total_results", 0)
                    self.total_pages = content.get("total_pages", 1)
                    if self.total_pages == 1 and total > 0:
                        self.total_pages = max(1, (total + self.max_results - 1) // self.max_results)
                    self._update_pagination()
                    self.status_bar.showMessage(f"Found {total} games", 3000)
            else:
                self.status_bar.showMessage(f"API Error: {response.status_code}", 3000)
                if self.settings.get("api_mode") == "local":
                    self._handle_local_api_failure(str(e))
                    
        except requests.exceptions.ConnectionError:
            self.status_bar.showMessage(f"Cannot connect to API at {api_base}", 3000)
            if self.settings.get("api_mode") == "local":
                self._handle_local_api_failure(str(e))
        except Exception as e:
            self.status_bar.showMessage(f"Network Error: {e}", 3000)
            if self.settings.get("api_mode") == "local":
                self._handle_local_api_failure(str(e))
        self.performing_search = False
        
    def _retry_search(self):
        if not self.search_pending:
            return
        if self.search_retries >= 3:   # give up after 3 attempts
            self._handle_local_api_failure("Local server not responding after multiple attempts")
            self.search_pending = None
            return
        if self.local_server_thread and self.local_server_thread.isRunning():
            query, platforms, regions, page = self.search_pending
            self.search_pending = None
            self._search(query, platforms, regions, page)
        else:
            self.search_retries += 1
            QTimer.singleShot(3000, self._retry_search)   # retry every 3 seconds

    def _handle_local_api_failure(self, error_detail=""):
        """Offer to switch to remote API when local server fails."""
        if self.settings.get("api_mode") != "local":
            return
        if self._is_initial_load:
            # During initial load, just show a status message, no popup
            self.status_bar.showMessage(f"Local API not available: {error_detail}", 5000)
        else:
            reply = QMessageBox.critical(
                self,
                "Local API Connection Failed",
                f"Local server error:\n{error_detail}\n\n"
                "Would you like to switch to the remote API?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.settings["api_mode"] = "remote"
                self._save_config()
                self.status_bar.showMessage("Switched to remote API", 3000)
    def _passes_compat_filter(self, game_data: dict) -> bool:
        """Return True if the game passes the Vita3K compatibility filter."""
        if not self.settings.get("vita3k_compat_filter_enabled", False):
            return True
        platform = game_data.get("platform", "").lower()
        if platform != 'psv':
            return True  # non-PSV games are not filtered
        rom_id = game_data.get("rom_id")
        if not rom_id:
            return True  # can't filter
        status_list = self.vita3k_compat.get_status(rom_id)
        if not status_list:
            # No data = include based on setting
            return True
        # Extract main status (first non-issue label)
        main_status = None
        for label in status_list:
            if not label.startswith('-'):
                main_status = label
                break
        if not main_status:
            return True  # fallback
        allowed = self.settings.get("vita3k_compat_filter", [])
        return main_status in allowed
    def _display_games(self, data: dict):
        # Clear existing
        self._clear_grid()
        self._clear_selection()
        self.image_loader.clear()
        games_data = []
        if "data" in data:
            content = data["data"]
            if isinstance(content, dict) and "results" in content:
                games_data = content["results"]
            elif isinstance(content, list):
                games_data = content
        if not games_data:
            self._display_no_results()
            return
        for game_data in games_data:
            if not self._passes_compat_filter(game_data):
                continue
            if isinstance(game_data, dict):
                title = game_data.get("title", "Unknown")
                platform = game_data.get("platform", "Unknown")
                base_name, disc_number, is_multi_disc = self._parse_disc_info(title, platform)
                if self.settings["remove_demos"] and ("(Demo)" in title or "(Taikenban" in title):# Skip demos if enabled
                    continue
                slug = game_data.get("slug", "")
                platform = game_data.get("platform", "Unknown")
                regions = game_data.get("regions", [])
                region = regions[0] if regions else "Unknown"
                download_url = None
                selected_format = None
                links = game_data.get("links", [])
                if links:
                    download_url, selected_format, size_str = self._select_best_download_url(links)       
                game = Game(
                    id=slug,
                    title=title[:50],
                    platform=platform,
                    region=region,
                    size_str=size_str,
                    rom_id=game_data.get("rom_id"),
                    cover_url=game_data.get("boxart_url"),
                    download_url=download_url,
                    selected_format=selected_format,
                    disc_number=disc_number,
                    base_game_name=base_name,
                    is_multi_disc=is_multi_disc
                )
                if game.platform.lower() == 'psv' and game.rom_id:
                    game.cover_url = f"https://raw.githubusercontent.com/tarrare2/psv-covers/main/covers/{game.rom_id}.jpg"

                self.current_games.append(game)
        self._create_cards_from_games()


    def _display_no_results(self):
        """Display no results message with random animated WebP"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        webp_files = [AGLIA_B64, BONK_B64, PESCE_B64]
        selected_webp = random.choice(webp_files)
        
        gif_bytes = base64.b64decode(selected_webp)
        byte_array = QByteArray(gif_bytes)
        buffer = QBuffer()
        buffer.setData(byte_array)
        buffer.open(QBuffer.ReadOnly)
        movie = QMovie()
        movie.setDevice(buffer)
        webp_label = QLabel()
        webp_label.setMovie(movie)
        movie.start()
        webp_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(webp_label)

        message_label = QLabel("No results found")
        message_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #888;
                padding: 20px;
            }
        """)
        message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(message_label)
        suggestion_label = QLabel("Try a different search term or adjust your filters")
        suggestion_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #666;
            }
        """)
        suggestion_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(suggestion_label)
        self.grid_layout.addWidget(container, 0, 0, 1, 1, Qt.AlignCenter)
        self.current_games.clear()
        self.cards.clear()
        self.total_pages = 1
        self.current_page = 1
        self._update_pagination()
        # Update status bar
        self.status_bar.showMessage("No games found", 3000)
    
    def _clear_grid(self):
        """Clear all cards from the grid and free memory"""
        for card in self.cards:
            card.deleteLater()
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().setParent(None)
        self.cards.clear()
        self.current_games.clear()
    
    def _layout_cards(self):
        """Layout cards in grid based on current container width"""
        if not self.cards:
            return
        container_width = self.grid_container.width()
        available_width = container_width - self.grid_layout.contentsMargins().left() - self.grid_layout.contentsMargins().right()
        card_total_width = 200 + self.grid_layout.spacing()
        max_columns = max(1, available_width // card_total_width)
        self.grid_layout.setColumnMinimumWidth(0, 0)  # Reset minimum width
        for i, card in enumerate(self.cards):
            row = i // max_columns
            col = i % max_columns
            self.grid_layout.addWidget(card, row, col)
        
    def eventFilter(self, obj, event):
        # Reorder when container resizes
        if obj == self.grid_container and event.type() == QEvent.Resize:
            self._layout_cards()
            return True
        # Handle drag selection on the grid container
        if obj == self.grid_container:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                child = self.grid_container.childAt(event.position().toPoint())
                pos = event.position().toPoint()
                child = self.grid_container.childAt(pos)
                # Walk up to find a GameCard
                while child and not isinstance(child, GameCard):
                    child = child.parentWidget()
                if child is None or not isinstance(child, GameCard):
                    # Start potential drag on empty area
                    self.drag_select_active = True
                    self.drag_origin = event.position().toPoint()
                    self.drag_started = False
                    return True  # Consume event
                else:
                    return False  # Let the card handle it
            elif event.type() == QEvent.MouseMove and self.drag_select_active:
                # If movement exceeds threshold, start the rubber band
                if not self.drag_started:
                    delta = (event.position().toPoint() - self.drag_origin).manhattanLength()
                    if delta > 5:  # start drag after 5 pixels
                        self.drag_started = True
                        self.rubber_band.setGeometry(QRect(self.drag_origin, QSize()))
                        self.rubber_band.show()
                if self.drag_started:
                    # Update rubber band and selection
                    rect = QRect(self.drag_origin, event.position().toPoint()).normalized()
                    self.rubber_band.setGeometry(rect)
                    self._update_drag_selection(rect)
                return True
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton and self.drag_select_active:
                if self.drag_select_active:
                    if self.drag_started:
                        # Drag finished – selection already updated
                        self.rubber_band.hide()
                    else:
                        # Click on empty space without dragging – clear selection
                        child = self.grid_container.childAt(event.position().toPoint())
                        if child is None or not isinstance(child, GameCard):
                            self._clear_selection()
                    self.drag_select_active = False
                    self.drag_started = False
                    return True
                return False
        # Keyboard navigation
        if obj == self.grid_container and event.type() == QEvent.KeyPress:
            return self._handle_key(event)
        return super().eventFilter(obj, event)
    def _update_drag_selection(self, rect):
        """Select all cards whose geometry intersects the rubber band rectangle."""
        self._clear_selection()
        for i, card in enumerate(self.cards):
            if card.geometry().intersects(rect):
                card.selected = True
                self.selected_games.add(self.current_games[i].id)
        self.last_selected_index = -1
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
            return
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            focused = QApplication.focusWidget()
            if focused == self.search_input:
                self.performing_search = True
                super().keyPressEvent(event)
                return
            if self.performing_search:
                self.performing_search = False
                self.grid_container.setFocus()
                if self.cards:
                    self.cards[0].setFocus()
                return
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                          Qt.Key_PageUp, Qt.Key_PageDown):
            focused = QApplication.focusWidget()
            if focused in (self.search_input, self.platform_btn, self.region_btn):
                super().keyPressEvent(event)
                return
            if self._handle_key(event):
                return
        super().keyPressEvent(event)
    
    def _handle_key(self, event: QKeyEvent) -> bool:
        """Arrow keys move the focus, PageUp/Down changes pages, Return selects the focused card."""
        if not self.cards:
            return False
        container_width = self.grid_container.width()
        available_width = container_width - self.grid_layout.contentsMargins().left() - self.grid_layout.contentsMargins().right()
        card_total_width = 200 + self.grid_layout.spacing()
        cols = max(1, available_width // card_total_width)
        rows = (len(self.cards) + cols - 1) // cols
        row = self.focused_index // cols
        col = self.focused_index % cols
        handled = True
        if event.key() == Qt.Key_Right:
            new = self.focused_index + 1
            if new < len(self.cards):
                self.focused_index = new
        elif event.key() == Qt.Key_Left:
            new = self.focused_index - 1
            if new >= 0:
                self.focused_index = new
        elif event.key() == Qt.Key_Down:
            new_row = row + 1
            if new_row < rows:
                new = min(new_row * cols + col, len(self.cards) - 1)
                self.focused_index = new
        elif event.key() == Qt.Key_Up:
            new_row = row - 1
            if new_row >= 0:
                new = new_row * cols + col
                if new < len(self.cards):
                    self.focused_index = new
        elif event.key() == Qt.Key_PageDown:
            if self.current_page < self.total_pages:
                self.next_page()
        elif event.key() == Qt.Key_PageUp:
            if self.current_page > 1:
                self.prev_page()
        elif event.key() in (Qt.Key_Enter, Qt.Key_Return):
            if not self.performing_search and self.focused_index < len(self.current_games):
                self._download_game(self.current_games[self.focused_index])
        else:
            handled = False
        
        if handled and self.focused_index < len(self.cards):
            self.cards[self.focused_index].setFocus()
            self._scroll_to_card(self.focused_index)
        return handled
    
    def _scroll_to_card(self, index: int):
        """Supports the arrow keys moving the focus"""
        if not self.cards or index >= len(self.cards):
            return
        card = self.cards[index]
        viewport = self.scroll.viewport()
        card_rect = card.geometry()
        card_pos = card.mapTo(self.grid_container, card_rect.topLeft())
        container_pos = self.grid_container.mapTo(viewport, card_pos)
        view_rect = viewport.rect()
        card_in_view = QRect(container_pos, card_rect.size())
        scroll = self.scroll.verticalScrollBar()
        if card_in_view.top() < view_rect.top():
            scroll.setValue(scroll.value() + card_in_view.top() - view_rect.top())
        elif card_in_view.bottom() > view_rect.bottom():
            scroll.setValue(scroll.value() + card_in_view.bottom() - view_rect.bottom())
    
    def show_platforms(self):
        dialog = MultiSelectDialog("Select Platforms", self.platforms, self.selected_platforms)
        dialog.changed.connect(self._on_platforms_selected)
        dialog.exec()
    
    def show_regions(self):
        dialog = MultiSelectDialog("Select Regions", self.regions, self.selected_regions)
        dialog.changed.connect(self._on_regions_selected)
        dialog.exec()
    
    def _on_platforms_selected(self, selected: List[str]):
        self.selected_platforms = selected
        self.platform_btn.setText(self._get_platform_text())
        
        # Update button text for single selection
        if len(selected) == 1:
            for pid, name in self.platforms:
                if pid == selected[0]:
                    self.platform_btn.setText(name)
                    break
        
        self._save_config()
    
    def _on_regions_selected(self, selected: List[str]):
        self.selected_regions = selected
        self.region_btn.setText(self._get_region_text())
        if len(selected) == 1:
            for rid, name in self.regions:
                if rid == selected[0]:
                    self.region_btn.setText(name)
                    break
        self._save_config()
    
    def _on_image_loaded(self, game_id: str, pixmap: QPixmap):
        for i, game in enumerate(self.current_games):
            if game.id == game_id and game.cover_url:
                self.cache.put(game.cover_url, pixmap)
                if i < len(self.cards):
                    self.cards[i].set_image(pixmap)
                break
    
    def _on_image_error(self, game_id: str, error: str):
        for i, game in enumerate(self.current_games):
            if game.id == game_id and i < len(self.cards):
                self.cards[i].set_error(error)
                break
            
    def _on_card_focused(self, game_id: str):
        for i, game in enumerate(self.current_games):
            if game.id == game_id:
                self.focused_index = i
                break
    
    def _update_pagination(self):
        self.page_combo.blockSignals(True)
        self.page_combo.clear()
        if self.total_pages > 0:
            for i in range(1, self.total_pages + 1):
                self.page_combo.addItem(f"Page {i}", i)
            if self.current_page <= self.total_pages:
                self.page_combo.setCurrentIndex(self.current_page - 1)
        self.page_combo.blockSignals(False)
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
        has_results = len(self.current_games) > 0
        self.prev_btn.setEnabled(self.current_page > 1 and has_results)# Disables navigation if no results
        self.next_btn.setEnabled(self.current_page < self.total_pages and has_results)
        self.page_combo.setEnabled(has_results and self.total_pages > 1)
    
    def _on_page_change(self, index: int):
        if index >= 0:
            page = self.page_combo.itemData(index)
            if page and page != self.current_page:
                self.current_page = page
                self.load_page(page)
    
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_page(self.current_page)
    
    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_page(self.current_page)
    
    def load_page(self, page: int):
        query = self.search_input.text().strip()
        self._search(query, self.selected_platforms, self.selected_regions, page)
    
    def show_settings(self):
        dialog = SettingsDialog(self.settings, self)
        dialog.changed.connect(self._on_settings_changed)
        dialog.exec()
    
    def _on_settings_changed(self, new_settings: dict):
        if "clear_cache" in new_settings:
            self.cache.clear()
            return
        old_mode = self.settings.get("api_mode")
        new_mode = new_settings.get("api_mode")
        if old_mode != new_mode:
            if new_mode == "local" and FLASK_AVAILABLE:
                self.start_server()   # start with current host/port from settings
            elif new_mode == "remote":
                self.stop_server()
                self.status_bar.showMessage("Switched to remote API", 3000)
            self.load_initial()
            
        old_theme = self.settings.get("theme")
        new_theme = new_settings.get("theme")
        #if old_theme != new_theme:
        self._apply_theme(new_theme)
        self.settings.update(new_settings)
        self.download_manager.base_path = self.settings["download_path"]
        self.download_manager.use_es_folders = self.settings["use_es_folders"]
        if "create_m3u_folders" in new_settings:
            self.download_manager.create_m3u = new_settings["create_m3u_folders"]
        self.cache.max_size = self.settings["cache_size_mb"] * 1024 * 1024
        self.download_manager.extract_zips = new_settings.get("extract_zips", False)
        self.download_manager.auto_install_vita3k = new_settings.get("auto_install_vita3k", False)
        #print(f"MainWindow._on_settings_changed: new_settings['decrypt_psv_pkg'] = {new_settings.get('decrypt_psv_pkg')}")
        self.download_manager.decrypt_psv_pkg = new_settings.get("decrypt_psv_pkg", True)
        #print(f"After update: download_manager.decrypt_psv_pkg = {self.download_manager.decrypt_psv_pkg}")
        self.download_manager.vita3k_path = new_settings.get("vita3k_path", "")
        self.download_manager.delete_after_vita3k_install = new_settings.get("delete_after_vita3k_install", False)
        self._save_config()

    def show_queue(self):
        if not self.queue_dialog:
            self.queue_dialog = DownloadQueueDialog(self.download_manager)
            self.queue_dialog.setModal(False)
        self.queue_dialog.refresh_queue_display()
        self.queue_dialog.show()
        self.queue_dialog.raise_()
        self.queue_dialog.activateWindow()
    
    def _on_download_progress(self, game_id: str, progress: float):
        if self.queue_dialog:
            self.queue_dialog.update_progress(game_id, progress)
    
    def _on_download_complete(self, game_id: str, path: str):
        if self.queue_dialog:
            self.queue_dialog.complete(game_id, path)
        queue_size = len(self.download_manager.queue)
        self.queue_btn.setText(f"Queue ({queue_size})")
        self.status_bar.showMessage(f"Download complete: {path}", 5000)
    
    def _on_download_error(self, game_id: str, error: str):
        if self.queue_dialog:
            self.queue_dialog.error(game_id, error)
        queue_size = len(self.download_manager.queue)
        self.queue_btn.setText(f"Queue ({queue_size})")
        self.status_bar.showMessage(f"Download error: {error[:50]}...", 5000)
        # Show full error in a message box for Vita3K errors
        if "Vita3K installation failed" in error:
            QMessageBox.critical(self, "Vita3K Installation Error", error)
    
    def closeEvent(self, event):
        self.image_loader.stop()
        self.download_manager.stop()
        if self.local_server_thread and self.local_server_thread.isRunning():
            self.local_server_thread.stop()
        self.cache.clear()
        if not self.isFullScreen():
            geometry_bytes = self.saveGeometry().toBase64().data()
            self.settings["window_geometry"] = geometry_bytes.decode('ascii')
        else:
            # Don't save fullscreen geometry; keep the previously saved windowed geometry
            pass
        self._save_config()
        event.accept()

def main():
    app = QApplication(sys.argv)
    #app.setStyle("Fusion")#TODO: Add themes to the settings
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
