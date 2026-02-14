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
        # One‑file mode: files extracted to temp folder
        BASE_DIR = Path(sys._MEIPASS)
    else:
        # One‑folder mode: files are next to the .exe
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
CONFIG_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / ".swampy_config.json"
DEFAULT_SETTINGS = {
    "download_path": str(Path.cwd() / "swamp"),
    "use_es_folders": True,
    "remove_demos": True,
    "cache_size_mb": 50,
    "create_m3u_folders": True,
    "api_mode": "remote",  
    "local_server_port": 5000,
    "local_server_host": "127.0.0.1",
    "start_local_on_launch": False,
    "start_fullscreen": True,
    "window_geometry": ""
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
    """Dialog for local server configuration and status.
    Controls the single server thread owned by MainWindow.
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window          # reference to MainWindow
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


    # UI state management (synchronized with MainWindow's server thread)
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

    # Server control (delegated to MainWindow)
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
        # Use the URL that is currently displayed (or fallback to settings)
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
    
    def add(self, url: str, game_id: str):
        if url and url.startswith('http'):
            self.queue.append((url, game_id))
            if not self.isRunning():
                self.start()
    
    def run(self):
        while self._running:
            if self.queue:
                url, game_id = self.queue.pop(0)
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
            self.msleep(100)
    
    def stop(self):
        self._running = False
        self.wait()

class DownloadManager(QThread):
    """Thread for managing downloads"""
    progress = Signal(str, float)
    complete = Signal(str, str)
    error = Signal(str, str)
    
    def __init__(self, base_path: str = "", use_es_folders: bool = True, create_m3u: bool = True):
        super().__init__()
        self.base_path = base_path
        self.use_es_folders = use_es_folders
        self.create_m3u = create_m3u
        self.queue: List[Game] = []
        self.current: Optional[Game] = None
        self._running = True
        self._active = False
        self._cancel = False
        self._paused = False

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
        """Move a queued game to the top position."""
        for i, game in enumerate(self.queue):
            if game.id == game_id:
                # Pause if something is downloading
                if self.current:
                    self.pause()
                    # Re-add current to front of queue
                    self.queue.insert(0, self.current)
                    self.current = None
                
                # Move selected game to position 0
                self.queue.pop(i)
                self.queue.insert(0, game)
                return True
        return False
    
    def remove_from_queue(self, game_id: str):
        """Remove a game from queue."""
        # Remove from queue
        self.queue = [g for g in self.queue if g.id != game_id]
        
        # Cancel if it's the current download
        if self.current and self.current.id == game_id:
            self.cancel_current()
            self.current = None

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
                print(f"DEBUG: Moved to .m3u folder: {target_path.name}")
            
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
        while self._running and self.queue:
            self._cancel = False
            game = self.queue.pop(0)
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
                if path.lower().endswith('.zip'):
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
    
    def cancel_current(self):
        self._cancel = True
    
    def stop(self):
        self._running = False
        self.wait()

class GameCard(QFrame):
    """Widget for displaying a game"""
    clicked = Signal(Game)
    focused = Signal(str)
    
    def __init__(self, game: Game, placeholder: QPixmap):
        super().__init__()
        self.game = game
        self.placeholder = placeholder
        self.setup_ui()
        self.setFixedSize(200, 250)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("""
            GameCard {
                background: #1e1e1e;
                border: 2px solid transparent;
                border-radius: 8px;
            }
            GameCard:hover { border-color: #555; background: #252525; }
            GameCard:focus { border-color: #0078d7; background: #252525; }
        """)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(180, 180)
        self.image_label.setStyleSheet("""
            background: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 4px;
            color: #888;
            font-size: 10px;
        """)
        self.image_label.setText("Loading...")
        # Info
        self.title_label = QLabel(self.game.title[:50])
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(40)
        self.title_label.setStyleSheet("font-weight: bold;")
        format_display = f"{self.game.platform} | {self.game.region}"
        if self.game.selected_format:
            format_display += f" | {self.game.selected_format}"
        self.platform_label = QLabel(format_display)
        self.platform_label.setAlignment(Qt.AlignCenter)
        self.platform_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.image_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.platform_label)
    
    def set_image(self, pixmap: QPixmap):
        scaled = pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")
    
    def set_error(self, error: str):
        self.image_label.setText(f"Error:\n{error[:20]}...")
        self.image_label.setPixmap(self.placeholder)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.game)
    
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.clicked.emit(self.game)
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
        self.setFixedSize(400, 600)
        self.setup_ui()
        self.update_api_mode_ui()   # initial refresh

    def _set_icon(self):
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(ICON_B64))
        self.setWindowIcon(QIcon(pixmap))

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # ----- API Settings -----
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

        # Server status label (NO signal connection – we query directly)
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

        # ----- UI
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        self.fullscreen_cb = QCheckBox("Start in fullscreen")
        self.fullscreen_cb.setChecked(self.settings.get("start_fullscreen", True))
        self.fullscreen_cb.setToolTip("If unchecked, the window will start in normal mode.")
        display_layout.addWidget(self.fullscreen_cb)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # ----- Download Settings -----
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
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)

        # ----- Filter Settings -----
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

        # ----- Cache Settings -----
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

        # ----- Buttons -----
        buttons = QHBoxLayout()
        buttons.addStretch()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    # ------------------------------------------------------------------
    # UI Update – Shows REAL server state, no signals needed
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Server Configuration Dialog
    # ------------------------------------------------------------------
    def show_local_server_dialog(self):
        dialog = LocalServerDialog(self.main_window, self)
        dialog.exec()
        # Update settings from dialog
        self.settings["local_server_host"] = dialog.host_combo.currentText().strip()
        self.settings["local_server_port"] = dialog.port_spin.value()
        # Refresh status label (server may have been started/stopped)
        self.update_api_mode_ui()

    # ------------------------------------------------------------------
    # Other methods (browse, save) – unchanged
    # ------------------------------------------------------------------
    def browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Download Location")
        if path:
            self.path_edit.setText(path)

    def save(self):
        settings = {
            "download_path": self.path_edit.text(),
            "use_es_folders": self.es_cb.isChecked(),
            "remove_demos": self.demo_cb.isChecked(),
            "cache_size_mb": self.cache_spin.value(),
            "create_m3u_folders": self.m3u_cb.isChecked(),
            "api_mode": self.api_mode_combo.currentData(),
            "local_server_port": self.settings.get("local_server_port", 5000),
            "local_server_host": self.settings.get("local_server_host", "127.0.0.1"),
            "start_local_on_launch": self.start_on_launch_cb.isChecked(),
            "start_fullscreen": self.fullscreen_cb.isChecked()
        }
        self.changed.emit(settings)
        self.accept()

class DownloadQueueDialog(QDialog):
    """Download queue dialog with enhanced controls."""
    
    def __init__(self, manager: DownloadManager):
        super().__init__()
        self.manager = manager
        self.items: Dict[str, Tuple[QListWidgetItem, QueueItemWidget]] = {}
        #self._set_icon()
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(ICON_B64))
        self.setWindowIcon(QIcon(pixmap))
        self.setWindowTitle("Download Queue")
        self.setFixedSize(600, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Downloads: 0 queued, 0 active")
        layout.addWidget(self.status_label)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Control buttons
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
        
        # Update UI based on manager state
        self.update_ui_state()
    
    def add_download(self, game: Game):
        """Add a download to the queue display."""
        is_first = (len(self.items) == 0 and not self.manager.current)
        
        item_widget = QueueItemWidget(game, is_first)
        item_widget.moved_up.connect(self.move_item_up)
        item_widget.remove_clicked.connect(self.remove_item)
        
        item = QListWidgetItem(self.list_widget)
        item.setSizeHint(item_widget.sizeHint())
        item.setData(Qt.UserRole, game.id)
        
        self.items[game.id] = (item, item_widget)
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)
        
        self.update_ui_state()
    
    def move_item_up(self, game_id: str):
        """Move item to top of queue."""
        if self.manager.move_to_top(game_id):
            self.refresh_queue_display()
    
    def remove_item(self, game_id: str):
        """Remove item from queue."""
        self.manager.remove_from_queue(game_id)
        self.refresh_queue_display()
    
    def toggle_pause(self):
        """Toggle pause/resume state."""
        if self.manager.is_paused():
            self.manager.resume()
            self.pause_resume_btn.setText("⏸️ Pause")
        else:
            self.manager.pause()
            self.pause_resume_btn.setText("▶️ Resume")
        self.update_ui_state()
    
    def cancel_current(self):
        """Cancel the current download."""
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(CANCEL_B64))
        msg = QMessageBox(self)
        msg.setIconPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio))
        
        if self.manager.current:
            msg.setWindowTitle("Cancel Download")
            msg.setText(f"Cancel download of '{self.manager.current.title}'?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            
            if msg.exec() == QMessageBox.Yes:
                self.manager.cancel_current()
        else:
            msg.setWindowTitle("Info")
            msg.setText("No download in progress.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
    
    def refresh_queue_display(self):
        """Refresh the entire queue display."""
        self.list_widget.clear()
        self.items.clear()
        # Add current download first if it exists
        if self.manager.current:
            self.add_download(self.manager.current)
        # Add queued items
        for i, game in enumerate(self.manager.queue):
            self.add_download(game)
        self.update_ui_state()
    
    def update_ui_state(self):
        """Update UI based on download manager state."""
        queue_count = len(self.manager.queue)
        has_current = self.manager.current is not None
        # Update status label
        if has_current:
            status = f"Downloading: {self.manager.current.title}"
            if queue_count > 0:
                status += f" | {queue_count} queued"
        else:
            status = f"Downloads: {queue_count} queued"
        self.status_label.setText(status)
        # Update pause/resume button
        self.pause_resume_btn.setEnabled(has_current or queue_count > 0)
        if self.manager.is_paused():
            self.pause_resume_btn.setText("▶️ Resume")
        else:
            self.pause_resume_btn.setText("⏸️ Pause")
    
    def clear_completed(self):
        to_remove = []
        for game_id, item in self.items.items():
            if widget := self.list_widget.itemWidget(item):
                for child in widget.children():
                    if isinstance(child, QLabel) and child.text().startswith(("✓", "✗")):
                        to_remove.append(game_id)
                        break
        for game_id in to_remove:
            item = self.items.pop(game_id, None)
            if item:
                self.list_widget.takeItem(self.list_widget.row(item))
    
    def update_progress(self, game_id: str, progress: float):
        """Update progress bar for current download."""
        if game_id in self.items:
            item, widget = self.items[game_id]
            # Find progress bar in the widget
            for child in widget.children():
                if isinstance(child, QProgressBar):
                    child.setValue(int(progress * 100))
                    break
        # Also update main progress bar if current download
        if self.manager.current and self.manager.current.id == game_id:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(int(progress * 100))
    
    def complete(self, game_id: str, path: str):
        """Mark download as complete."""
        if game_id in self.items:
            item, widget = self.items[game_id]
            # Mark as completed
            for child in widget.children():
                if isinstance(child, QLabel):
                    child.setText(f"✓ {child.text()}")
                    child.setStyleSheet("color: #2ecc71; font-weight: bold;")
                    break
                elif isinstance(child, QProgressBar):
                    child.setValue(100)
                    child.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
        # Hide main progress bar
        self.progress_bar.setVisible(False)
        self.update_ui_state()
    
    def error(self, game_id: str, message: str):
        """Mark download as errored."""
        if game_id in self.items:
            item, widget = self.items[game_id]
            # Mark as error
            for child in widget.children():
                if isinstance(child, QLabel):
                    child.setText(f"✗ {child.text()}")
                    child.setStyleSheet("color: #e74c3c; font-weight: bold;")
                    break
                elif isinstance(child, QProgressBar):
                    child.setValue(100)
                    child.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
        # Hide main progress bar
        self.progress_bar.setVisible(False)
        self.update_ui_state()
            
class QueueItemWidget(QWidget):
    moved_up = Signal(str)
    remove_clicked = Signal(str)
    
    def __init__(self, game: Game, is_first: bool = False, is_current: bool = False):
        super().__init__()
        self.game_id = game.id
        self.setup_ui(game, is_first, is_current)
    
    def setup_ui(self, game: Game, is_first: bool, is_current: bool):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        # Up Arrow button (not for first item)
        if not is_first:
            self.up_btn = QPushButton("↑")
            self.up_btn.setFixedSize(25, 25)
            self.up_btn.setToolTip("Move to top")
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

class MainWindow(QMainWindow):
    """Main application window"""
    server_state = Signal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SwamPy: Dogwater CrocDB Browser")
        self._set_icon()
        self.current_page = 1
        self.total_pages = 1
        self.max_results = 20
        self.current_games: List[Game] = []
        self.focused_index = 0
        self.cards: List[GameCard] = []
        self.selected_platforms: List[str] = []
        self.selected_regions: List[str] = []
        self.settings = DEFAULT_SETTINGS.copy()
        self.performing_search = False
        self.placeholder = self._create_placeholder()
        self.local_server_thread: Optional[LocalServerThread] = None
        self.setup_ui()
        self.cache = ImageCache(self.settings["cache_size_mb"])
        self.image_loader = ImageLoader()
        self.download_manager = DownloadManager(
            self.settings["download_path"],
            self.settings["use_es_folders"],
            create_m3u=self.settings.get("create_m3u_folders", True)
        )
        self.queue_dialog: Optional[DownloadQueueDialog] = None
        self.setup_connections()
        self._load_config()
        self.kill_process_on_port(self.settings.get("local_server_port", 5000))
        if (self.settings.get("api_mode") == "local" and
            self.settings.get("start_local_on_launch", False) and
            FLASK_AVAILABLE):
            # Auto‑start local server, then load once it's running
            self.start_server()
            self.local_server_thread.started.connect(self.load_initial)
            self.local_server_thread.error.connect(
                lambda: QTimer.singleShot(100, self.load_initial)
            )
        else:
            # Not auto‑starting – load immediately (with a tiny delay to let UI settle)
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
                # First launch in windowed mode – use default size and center
                default_size = QSize(1200, 800)
                self.resize(default_size)
                screen = QApplication.primaryScreen().availableGeometry()
                center = screen.center()
                self.move(center.x() - default_size.width() // 2,
                          center.y() - default_size.height() // 2)
                self.showNormal()


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
            QApplication.processEvents()
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
        QTimer.singleShot(500, self._test_server_connection)

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
        """Test the connection and auto‑switch to remote if needed."""
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
                return links_by_format[fmt][0].get("url")
            return None        
        # RULE 1: If bin/cue exists -> chd > iso > other > bin/cue
        if "bin/cue" in links_by_format:
            selected_url = (
                get_url("chd") or
                get_url("iso") or
                self._get_any_single_file(links_by_format, exclude=["bin/cue"]) or
                get_url("bin/cue")
            )
            selected_fmt = (
                "chd" if get_url("chd") else
                "iso" if get_url("iso") else
                "single" if self._get_any_single_file(links_by_format, exclude=["bin/cue"]) else
                "bin/cue"
            )
            print(f"DEBUG: Selected {selected_fmt} from available: {list(links_by_format.keys())}")
            return selected_url, selected_fmt
        # RULE 2: If cia exists -> 3ds > cia
        if "cia" in links_by_format:
            selected_url = get_url("3ds") or get_url("cia")
            selected_fmt = "3ds" if get_url("3ds") else "cia"
            return selected_url, selected_fmt
        # RULE 3: If nonpdrm/vpk/psv exists -> pkg > nonpdrm > vpk > psv
        vita_formats = ["nonpdrm", "vpk", "psv"]
        for vita_fmt in vita_formats:
            if vita_fmt in links_by_format:
                selected_url = get_url("pkg") or get_url("nonpdrm") or get_url("vpk") or get_url("psv")
                selected_fmt = (
                    "pkg" if get_url("pkg") else
                    "nonpdrm" if get_url("nonpdrm") else
                    "vpk" if get_url("vpk") else
                    "psv"
                )
                return selected_url, selected_fmt
        # RULE 4: Default to first available
        first_fmt = next(iter(links_by_format))
        return get_url(first_fmt), first_fmt
    
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
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                self.selected_platforms = config.get("selected_platforms", [])# Load user selections, settings
                self.selected_regions = config.get("selected_regions", [])
                self.settings.update(config.get("settings", {}))
                self.cached_platforms = config.get("platforms_data", {})# And cached platform data if available
                self.cached_regions = config.get("regions_data", {})
                if self.cached_platforms and "data" in self.cached_platforms:# Extract platform list from cached data
                    platform_dict = self.cached_platforms["data"].get("platforms", {})
                    self.platforms = [(pid, info.get("name", pid.upper()))for pid, info in platform_dict.items()]
                else:
                    self.platforms = []
                if self.cached_regions and "data" in self.cached_regions:# Extract region list from cached data
                    region_dict = self.cached_regions["data"].get("regions", {})
                    self.regions = list(region_dict.items())
                else:
                    self.regions = []
                if len(self.selected_platforms) == 1 and self.platforms:# Update button text for single selection using cached data
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
                # Init empty caches if config doesn't exist
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
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
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
        self.platform_btn.setMinimumWidth(150)
        self.region_btn = QPushButton(self._get_region_text())
        self.region_btn.setMinimumWidth(150)
        self.search_btn = QPushButton("Search")
        self.queue_btn = QPushButton("Queue (0)")
        self.settings_btn = QPushButton("Settings")
        top.addWidget(QLabel("Search:"))
        top.addWidget(self.search_input)
        top.addWidget(QLabel("Platform:"))
        top.addWidget(self.platform_btn)
        top.addWidget(QLabel("Region:"))
        top.addWidget(self.region_btn)
        top.addWidget(self.search_btn)
        top.addWidget(self.queue_btn)
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
        self.queue_btn.clicked.connect(self.show_queue)

    def show_queue(self):
        if not self.queue_dialog:
            self.queue_dialog = DownloadQueueDialog(self.download_manager)
            self.queue_dialog.setModal(False)
        
        # Refresh display each time it's shown
        self.queue_dialog.refresh_queue_display()
        self.queue_dialog.show()
        self.queue_dialog.raise_()
        self.queue_dialog.activateWindow()
    
    def load_initial(self):
        """Load platforms and regions with cache or fetch"""
        api_base = self.get_api_base_url()
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
                    self._handle_local_api_failure()
                    
        except requests.exceptions.ConnectionError:
            self.status_bar.showMessage(f"Cannot connect to API at {api_base}", 3000)
            if self.settings.get("api_mode") == "local":
                self._handle_local_api_failure()
        except Exception as e:
            self.status_bar.showMessage(f"Network Error: {e}", 3000)
            if self.settings.get("api_mode") == "local":
                self._handle_local_api_failure()
        self.performing_search = False

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

    def _display_games(self, data: dict):
        # Clear existing
        self._clear_grid()
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
                    download_url, selected_format = self._select_best_download_url(links)
                    
                game = Game(
                    id=slug,
                    title=title[:50],
                    platform=platform,
                    region=region,
                    cover_url=game_data.get("boxart_url"),
                    download_url=download_url,
                    selected_format=selected_format,
                    disc_number=disc_number,
                    base_game_name=base_name,
                    is_multi_disc=is_multi_disc
                )
                self.current_games.append(game)
        for i, game in enumerate(self.current_games):
            card = GameCard(game, self.placeholder)
            card.clicked.connect(self._on_game_clicked)
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
        """Clear all cards from the grid"""
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
        """Re-layout cards when container resizes and handle key presses"""
        if obj == self.grid_container and event.type() == QEvent.Resize:
            self._layout_cards()
            return True
        if obj == self.grid_container and event.type() == QEvent.KeyPress:
            return self._handle_key(event)
        return super().eventFilter(obj, event)
    
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
                self._on_game_clicked(self.current_games[self.focused_index])
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
    
    def _on_game_clicked(self, game: Game):
        if not game.download_url:
            QMessageBox.warning(self, "No Download", "No download URL available.")
            return
        try:# Check disk space
            response = requests.head(game.download_url, timeout=10)
            if size := response.headers.get('content-length'):
                game.file_size = int(size)
                if not self.download_manager.check_space(game.file_size):
                    reply = QMessageBox.warning(
                        self,
                        "Low Disk Space",
                        f"Insufficient disk space for '{game.title}'.\n\n"
                        f"Required: {game.file_size/1024/1024:.1f} MB\n"
                        f"Add to queue anyway?",
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
        self.queue_dialog.add_download(game)
    
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

        self.settings.update(new_settings)
        self.download_manager.base_path = self.settings["download_path"]
        self.download_manager.use_es_folders = self.settings["use_es_folders"]
        if "create_m3u_folders" in new_settings:
            self.download_manager.create_m3u = new_settings["create_m3u_folders"]
        self.cache.max_size = self.settings["cache_size_mb"] * 1024 * 1024

        old_mode = self.settings.get("api_mode")
        new_mode = new_settings.get("api_mode")
        if old_mode != new_mode:
            if new_mode == "local" and FLASK_AVAILABLE:
                self.start_server()   # start with current host/port from settings
            elif new_mode == "remote":
                self.stop_server()
                self.status_bar.showMessage("Switched to remote API", 3000)
            self.load_initial()
    
        self._save_config()
    
    def show_queue(self):
        if not self.queue_dialog:
            self.queue_dialog = DownloadQueueDialog(self.download_manager)
            self.queue_dialog.setModal(False)
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
        self.status_bar.showMessage(f"Download error: {error}", 5000)
    
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
    app.setStyle("Fusion")#TODO: Add themes to the settings
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
