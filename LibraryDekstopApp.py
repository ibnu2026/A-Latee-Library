"""
Library Desktop Application v1.0
"""

import sys
import os
import sqlite3
import random
import uuid
import csv
import time
import threading
import traceback
import socket
import struct
from datetime import datetime as _SystemDateTime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict


INDONESIA_TIMEZONE = ZoneInfo("Asia/Jakarta")
_NETWORK_TIME_EPOCH = None
_NETWORK_TIME_MONOTONIC = None


def _current_indonesia_datetime():
    """Return waktu WIB, memakai waktu NTP jika sudah berhasil disinkronkan."""
    if _NETWORK_TIME_EPOCH is not None and _NETWORK_TIME_MONOTONIC is not None:
        epoch = _NETWORK_TIME_EPOCH + (time.monotonic() - _NETWORK_TIME_MONOTONIC)
        return _SystemDateTime.fromtimestamp(epoch, timezone.utc).astimezone(INDONESIA_TIMEZONE)
    return _SystemDateTime.now(INDONESIA_TIMEZONE)


def synchronize_indonesia_time():
    """Sinkronkan waktu aplikasi dengan server NTP, tanpa mengubah jam perangkat."""
    global _NETWORK_TIME_EPOCH, _NETWORK_TIME_MONOTONIC

    ntp_servers = ("time.google.com", "pool.ntp.org", "time.windows.com")
    ntp_epoch = 2208988800
    for server in ntp_servers:
        try:
            request = bytearray(48)
            request[0] = 0x1B
            started_at = time.time()
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(1.5)
                client.sendto(request, (server, 123))
                response, _ = client.recvfrom(48)
            finished_at = time.time()
            if len(response) < 48:
                continue

            server_seconds, server_fraction = struct.unpack("!II", response[40:48])
            server_epoch = (server_seconds - ntp_epoch) + (server_fraction / 2**32)
            network_offset = server_epoch - ((started_at + finished_at) / 2)
            _NETWORK_TIME_EPOCH = finished_at + network_offset
            _NETWORK_TIME_MONOTONIC = time.monotonic()
            print(f"[TIME] Sinkronisasi WIB berhasil dari {server}")
            return True
        except (OSError, ValueError) as error:
            print(f"[TIME] Gagal sinkronisasi dari {server}: {error}")

    print("[TIME] NTP tidak tersedia; memakai waktu perangkat dalam zona WIB sebagai fallback")
    return False


class IndonesiaDateTime(_SystemDateTime):
    """datetime aplikasi yang selalu menggunakan waktu Indonesia (WIB)."""

    @classmethod
    def now(cls, tz=None):
        current_time = _current_indonesia_datetime()
        if tz is None:
            return current_time.replace(tzinfo=None)
        return current_time.astimezone(tz)


datetime = IndonesiaDateTime

# GUI & Grafik
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import hashlib

# Import modern UI components
try:
    from modern_stylesheet import apply_modern_stylesheet, MODERN_STYLESHEET
except ImportError:
    def apply_modern_stylesheet(app):
        pass
    MODERN_STYLESHEET = ""

try:
    from sidebar_navigation import SidebarNavigation
except ImportError:
    SidebarNavigation = None

try:
    from zkteco_handler import ZKTecoFingerprintHandler
except ImportError as e:
    ZKTecoFingerprintHandler = None
    print(f"[WARNING] ZKTeco fingerprint handler not available: {e}")

try:
    from modern_ui_setup import setup_modern_ui
except ImportError:
    def setup_modern_ui(main_window):
        # Fallback ke old setup
        main_window.setup_ui()

# Try to import matplotlib, prefer Qt5Agg backend for embedding in Qt GUI
try:
    import matplotlib
    # Use Qt5Agg so FigureCanvasQTAgg works inside the PyQt5 application
    matplotlib.use("Qt5Agg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    MATPLOTLIB_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] matplotlib not available: {e}")
    MATPLOTLIB_AVAILABLE = False
    Figure = None
    FigureCanvas = None

# Barcode & QR
import cv2

# Try to import pytesseract, but don't fail if it's not available
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] pytesseract not available: {e}")
    PYTESSERACT_AVAILABLE = False
    pytesseract = None

# DO NOT import pyzbar at startup - use lazy import instead
# This avoids the libiconv.dll error at application startup
PYZBAR_AVAILABLE = False
decode = None

def get_pyzbar_decode():
    """Lazy import pyzbar.decode - only when needed"""
    global decode, PYZBAR_AVAILABLE
    if decode is None and not PYZBAR_AVAILABLE:
        try:
            from pyzbar.pyzbar import decode as pyzbar_decode
            decode = pyzbar_decode
            PYZBAR_AVAILABLE = True
        except ImportError as e:
            print(f"[WARN] pyzbar not available: {e}")
            print("   Install: pip install pyzbar-x64 (Windows) or pyzbar (Linux/Mac)")
            PYZBAR_AVAILABLE = False
            decode = None
    return decode

from PIL import Image
import qrcode
from reportlab.lib.pagesizes import A7
from reportlab.pdfgen import canvas


def map_role_to_jabatan(role):
    """Derive jabatan string from a normalized role."""
    normalized_role = (role or '').strip().lower()
    if normalized_role == 'administrator':
        return 'Administrator'
    if normalized_role == 'porseni':
        return 'PORSENI'
    return 'Pustakawan'

# Import modern auth UI
try:
    from modern_auth_ui import ModernLoginDialog, ModernRegisterDialog
except ImportError:
    ModernLoginDialog = None
    ModernRegisterDialog = None


# Database path - gunakan Documents folder untuk support write permission
def get_database_path():
    """
    Get path untuk database file dengan write permission
    Prioritas:
    1. %APPDATA%\\Latee Library\\ (Windows AppData - persistent)
    2. %USERPROFILE%\\Documents\\Latee Library\\ (fallback)
    3. Current folder (development)
    """
    import platform
    
    # Windows AppData path (recommended)
    if platform.system() == "Windows":
        appdata_path = os.path.expandvars(r"%APPDATA%\Latee Library")
    else:
        # Linux/Mac fallback
        appdata_path = os.path.expanduser("~/.latee_library")
    
    # Buat folder jika belum ada
    os.makedirs(appdata_path, exist_ok=True)
    
    db_path = os.path.join(appdata_path, "library_data.db")
    return db_path

DB_FILE = get_database_path()

# =======================================================
# ============== VISITOR REGISTRATION DIALOG ==============
# =======================================================
class VisitorRegistrationDialog(QtWidgets.QDialog):
    """Dialog pendaftaran pengunjung dengan fingerprint opsional."""
    
    RAYONS = [
        "Asy-Syafi'ie",
        "Al-Bukhori",
        "Al-Ghazali",
        "LSB",
        "LSM",
        "EAL",
        "LTQ",
        "DL",
        "PRA-DL",
        "KBS"
    ]
    ROOMS = [str(i) for i in range(1, 31)]
    
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db
        self.fingerprint_id = None
        self.setWindowTitle("Daftar Pengunjung Baru")
        self.setModal(True)
        self.setGeometry(100, 100, 500, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Nama
        layout.addWidget(QtWidgets.QLabel("Nama Pengunjung:"))
        self.nama_input = QtWidgets.QLineEdit()
        layout.addWidget(self.nama_input)
        
        # Rayon
        layout.addWidget(QtWidgets.QLabel("Rayon:"))
        self.rayon_combo = QtWidgets.QComboBox()
        self.rayon_combo.addItems(self.RAYONS)
        layout.addWidget(self.rayon_combo)
        
        # Nomor Kamar
        layout.addWidget(QtWidgets.QLabel("Nomor Kamar:"))
        self.kamar_combo = QtWidgets.QComboBox()
        self.kamar_combo.addItems(self.ROOMS)
        layout.addWidget(self.kamar_combo)

        self.fingerprint = None
        self.merged_bytes = None
        self.status_label = QtWidgets.QLabel("Fingerprint belum direkam (opsional)")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)

        self.btn_fingerprint = QtWidgets.QPushButton("Rekam Sidik Jari")
        self.btn_fingerprint.clicked.connect(self.start_fingerprint_enrollment)
        layout.addWidget(self.btn_fingerprint)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_save = QtWidgets.QPushButton("Simpan")
        btn_cancel = QtWidgets.QPushButton("Batal")
        btn_save.clicked.connect(self._validate_and_save)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
    
    def start_fingerprint_enrollment(self):
        """Start interactive fingerprint enrollment with the ZKTeco USB reader."""
        try:
            # Use fingerprint handler yang sudah disimpan saat init
            if not self.fingerprint:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Error",
                    "Fingerprint scanner tidak tersedia"
                )
                return
            
            fp = self.fingerprint
            
            if not fp.is_connected():
                QtWidgets.QMessageBox.warning(
                    self,
                    "Error",
                    "Fingerprint scanner tidak connect"
                )
                return
            
            # Get parent window untuk flag management
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'enrollment_active'):
                parent_window = parent_window.parent()
            
            if not parent_window:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Error",
                    "Cannot access main window"
                )
                return
            
            # ========== CHECK NAMA INPUT ==========
            nama = self.nama_input.text().strip()
            if not nama or len(nama) < 2:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Error",
                    "Masukkan nama pengunjung terlebih dahulu"
                )
                return
            
            # ========== SET FLAG ==========
            # Tell background scanner to STOP while enrollment is active
            parent_window.enrollment_active = True
            print("[ENROLLMENT] Set enrollment_active = True (stop BG scanner)")
            
            # Reset any unfinished enrollment state before starting again.
            fp.cancel_enrollment()
            
            # Start enrollment process
            if not fp.start_enrollment():
                parent_window.enrollment_active = False  # Reset jika gagal
                print("[ENROLLMENT] Set enrollment_active = False (enrollment failed)")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Error",
                    f"Gagal memulai enrollment:\n{fp.get_last_error()}"
                )
                return
            
            # Interactive enrollment dialog
            self.enrollment_count = 0
            self.enrollment_max = fp.REGISTER_FINGER_COUNT
            self._fp_handler = fp
            self.fingerprint_lock = parent_window.fingerprint_lock  # Get lock from parent MainWindow
            self._parent_window = parent_window  # Save parent untuk reset flag nanti
            
            self.scan_fingerprint_multiple()
        
        except Exception as e:
            print(f"[ENROLLMENT] Exception in start_fingerprint_enrollment: {e}")
            import traceback
            traceback.print_exc()
            # Ensure flag is always reset
            try:
                widget = self.parent()
                while widget:
                    if hasattr(widget, 'enrollment_active'):
                        widget.enrollment_active = False
                        print("[ENROLLMENT] EMERGENCY: Set enrollment_active = False (exception in enrollment)")
                        break
                    widget = widget.parent()
            except:
                pass
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Error starting enrollment:\n{e}"
            )

    def scan_fingerprint_multiple(self):
        """Scan fingerprint 3x untuk enrollment - AUTO DETECT (no click needed)"""
        
        # Check if done
        if self.enrollment_count >= self.enrollment_max:
            # Done scanning, save enrollment
            self.fingerprint_lock.acquire()  # Lock only for save operation
            enrollment_result = None
            try:
                fp = self._fp_handler
                # Get visitor name for fingerprint profile
                visitor_name = self.nama_input.text().strip()
                enrollment_result = fp.save_enrollment(owner_name=visitor_name)  # Pass name for in-memory fingerprints
                
                if enrollment_result and len(enrollment_result) == 2:
                    fp_id, merged_bytes = enrollment_result
                    
                    # ========== VALIDATE TEMPLATE ==========
                    # Check if template looks valid (not garbage/empty)
                    if not merged_bytes or len(merged_bytes) < 100:
                        print(f"[ENROLLMENT] [REJECT] Template invalid: empty or too small ({len(merged_bytes) if merged_bytes else 0} bytes)")
                        QtWidgets.QMessageBox.warning(
                            self,
                            "Scan Tidak Valid",
                            f"Sidik jari tidak terdeteksi dengan baik!\n\n"
                            f"Template size: {len(merged_bytes) if merged_bytes else 0} bytes (minimum: 100)\n\n"
                            f"Pastikan jari benar-benar menekan sensor.\n\n"
                            f"Silakan coba scan lagi."
                        )
                        # Reset enrollment state for retry
                        self.fingerprint_id = None
                        self.merged_bytes = None
                        self.enrollment_count = 0
                        self._parent_window.enrollment_active = False
                        self.status_label.setText("Status: Sidik jari tidak valid - coba lagi")
                        return
                    
                    # Template valid
                    self.fingerprint_id = fp_id
                    self.merged_bytes = merged_bytes  # Store template in memory (will save later when user clicks Simpan button)
                    self.status_label.setText(f" Sidik jari terekam (ID: {fp_id})")
                    self.status_label.setStyleSheet("color: green; font-weight: bold;")
                    QtWidgets.QMessageBox.information(
                        self,
                        "Berhasil",
                        f"Sidik jari berhasil direkam!\nFingerprint ID: {fp_id}\n\nTekan tombol 'Simpan' untuk menyimpan pendaftaran."
                    )
                    
                    # ⭐ DO NOT SAVE TO DATABASE HERE!
                    # Only save when user clicks "Simpan" button (in _validate_and_save method)
                    # This prevents duplicate detection error when saving same fingerprint twice
                    
                else:
                    error_detail = fp.get_last_error() or "Tidak diketahui"
                    if "Fingerprint sudah terdaftar" in error_detail:
                        self.fingerprint_id = None
                        self.merged_bytes = None
                        fp.cancel_enrollment()
                        QtWidgets.QMessageBox.warning(
                            self,
                            "Sidik jari sudah terdaftar",
                            f"Sidik jari ini sudah digunakan dan pendaftaran pengunjung ditolak.\n\n{error_detail}"
                        )
                        self.enrollment_count = 0
                        self._parent_window.enrollment_active = False
                        return

                    QtWidgets.QMessageBox.warning(
                        self,
                        "Error",
                        f"Gagal menyimpan enrollment:\n{error_detail}"
                    )
                    self.enrollment_count = 0
            except Exception as e:
                print(f"[ENROLLMENT] Exception during save: {e}")
                import traceback
                traceback.print_exc()
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    f"Error saving enrollment:\n{e}"
                )
            finally:
                self.fingerprint_lock.release()
            
            # ========== RESET FLAG ==========
            # Enrollment done - resume background scanner
            # ALWAYS reset this flag, even if there were errors
            self._parent_window.enrollment_active = False
            print("[ENROLLMENT] Set enrollment_active = False (enrollment complete)")
            return
        
        fp = self._fp_handler
        scan_num = self.enrollment_count + 1
        
        # Create dialog dengan instruksi (tanpa OK/Cancel buttons)
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"Rekam Sidik Jari - Scan {scan_num}/{self.enrollment_max}")
        dialog.setGeometry(100, 100, 500, 350)
        dialog.setModal(True)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Progress indicator
        progress = QtWidgets.QProgressBar()
        progress.setMaximum(self.enrollment_max)  # Dynamic based on enrollment_max
        progress.setValue(self.enrollment_count)
        layout.addWidget(progress)
        
        # Title
        title = QtWidgets.QLabel(f" Scan Sidik Jari ke-{scan_num}/{self.enrollment_max}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        info = QtWidgets.QLabel(
            "Tempelkan jari di reader ZKTeco sekarang...\n\n"
            "Pastikan jari dalam posisi baik dan tekan dengan stabil.\n\n"
            " Menunggu pembacaan sidik jari...\n"
            "(Tidak perlu klik apapun)"
        )
        info.setStyleSheet("color: #0066cc; font-size: 12px; padding: 20px;")
        info.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(info)
        
        # Status label
        status_label = QtWidgets.QLabel("Siap untuk scan...")
        status_label.setStyleSheet("color: #666; font-size: 11px;")
        status_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(status_label)
        
        # Cancel button (jika user ingin batal)
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QtWidgets.QPushButton("Batal Enrollment")
        btn_cancel.setMaximumWidth(200)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        scan_state = {'completed': False, 'result': None}
        
        def on_cancel():
            scan_state['completed'] = 'cancelled'
            dialog.reject()
        
        btn_cancel.clicked.connect(on_cancel)
        
        # Start auto-detection dengan polling dari main thread (SAFE!)
        def poll_scan():
            """Check untuk scan di main thread - THREAD SAFE"""
            if scan_state['completed']:
                return
            
            try:
                # Keep access to the USB reader single-threaded.
                self.fingerprint_lock.acquire()
                try:
                    success, count = fp.add_enrollment_scan()
                    
                    if success:
                        # Scan berhasil!
                        scan_state['completed'] = True
                        scan_state['result'] = count
                        
                        status_label.setText(f"Scan {count}/{self.enrollment_max} Berhasil!")
                        progress.setValue(count)
                        
                        # Close dialog setelah 1 detik
                        QtCore.QTimer.singleShot(1000, dialog.accept)
                        return
                finally:
                    self.fingerprint_lock.release()

                error_detail = fp.get_last_error() or ""
                if "Fingerprint sudah terdaftar" in error_detail:
                    scan_state['completed'] = 'duplicate'
                    status_label.setText("Sidik jari sudah terdaftar. Pendaftaran ditolak.")
                    QtCore.QTimer.singleShot(500, dialog.reject)
                    return
                
                # Tidak berhasil - cek timeout
                elapsed = poll_scan.elapsed
                remaining = 5.0 - elapsed
                
                if remaining > 0:
                    status_label.setText(f" Tunggu {remaining:.1f}s lagi...")
                    poll_scan.elapsed += 0.1
                    # Poll lagi
                    QtCore.QTimer.singleShot(100, poll_scan)
                else:
                    # Timeout
                    scan_state['completed'] = 'timeout'
                    status_label.setText("Waktu habis! Sidik jari tidak terdeteksi.")
                    QtCore.QTimer.singleShot(2000, dialog.reject)
                    
            except Exception as e:
                print(f"[ENROLLMENT] Error polling scan: {e}")
                traceback.print_exc()
                # Retry polling
                QtCore.QTimer.singleShot(100, poll_scan)
        
        poll_scan.elapsed = 0.0
        # Start polling dari main thread
        QtCore.QTimer.singleShot(100, poll_scan)
        
        # Show dialog (blocks until user closes or auto-closes)
        result = dialog.exec_()
        
        if scan_state['completed'] == 'duplicate':
            self.enrollment_count = 0
            fp.cancel_enrollment()
            self._parent_window.enrollment_active = False
            QtWidgets.QMessageBox.warning(
                self,
                "Sidik jari sudah terdaftar",
                f"Sidik jari ini sudah digunakan dan pendaftaran pengunjung ditolak.\n\n{fp.get_last_error()}"
            )
            return

        elif scan_state['completed'] == 'cancelled':
            # User cancelled enrollment
            self.enrollment_count = 0
            
            # ========== RESET FLAG ==========
            # Resume background scanner
            self._parent_window.enrollment_active = False
            print("[ENROLLMENT] Set enrollment_active = False (user cancelled)")
            
            QtWidgets.QMessageBox.information(
                self,
                "Dibatalkan",
                "Proses enrollment dibatalkan"
            )
            return
        
        elif scan_state['completed'] == True:
            # Scan successful - increment and continue
            self.enrollment_count = scan_state['result']
            QtCore.QTimer.singleShot(500, self.scan_fingerprint_multiple)
        
        else:
            # Timeout or error - retry same scan
            
            # ========== RESET FLAG ==========
            # Resume background scanner
            self._parent_window.enrollment_active = False
            print("[ENROLLMENT] Set enrollment_active = False (scan timeout/error)")
            
            # Get detailed error dari handler
            error_detail = fp.get_last_error() if fp else "Unknown error"
            print(f"[ENROLLMENT] Scan failed with error: {error_detail}")
            
            QtWidgets.QMessageBox.warning(
                self,
                "Scan Gagal",
                f"Sidik jari tidak terdeteksi.\n\nError: {error_detail}\n\n"
                "Coba ulang: Pastikan jari dalam posisi yang tepat dan tekan dengan stabil."
            )
    
    def _validate_and_save(self):
        """Validate data saat user klik tombol Simpan"""
        nama = self.nama_input.text().strip()
        if not nama or len(nama) < 3:
            QtWidgets.QMessageBox.warning(
                self,
                "Input Tidak Valid",
                "Nama minimum 3 karakter!"
            )
            return

        self.accept()
    
    def get_data(self):
        """Return registration data"""
        return {
            'nama': self.nama_input.text().strip(),
            'rayon': self.rayon_combo.currentText(),
            'kamar': self.kamar_combo.currentText(),
            'fingerprint_id': self.fingerprint_id,
            'template_bytes': self.merged_bytes
        }


# =======================================================
# ============== SCAN OLD VISITOR DIALOG ==============
# =======================================================
class RegisteredVisitorInfoDialog(QtWidgets.QDialog):
    """Pop-up yang muncul ketika fingerprint match dengan registered visitor"""
    
    def __init__(self, parent=None, santri_id=None, visitor_info=None):
        super().__init__(parent)
        self.santri_id = santri_id
        self.visitor_info = visitor_info or {}
        
        self.setWindowTitle("Pengunjung Terdaftar Terdeteksi")
        self.setModal(True)
        self.setGeometry(200, 200, 400, 250)
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f8ff;
                border: 3px solid #00aa00;
                border-radius: 8px;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Status icon & message
        title = QtWidgets.QLabel("Pengunjung Terdaftar")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00aa00;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)
        
        # Info box
        info_box = QtWidgets.QGroupBox("Informasi Pengunjung")
        info_layout = QtWidgets.QVBoxLayout(info_box)
        
        # Nama
        nama_label = QtWidgets.QLabel()
        nama_text = self.visitor_info.get("nama", "N/A")
        nama_label.setText(f"<b>Nama:</b> {nama_text}")
        nama_label.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(nama_label)
        
        # Rayon
        rayon_label = QtWidgets.QLabel()
        rayon_text = self.visitor_info.get("rayon", "N/A")
        rayon_label.setText(f"<b>Rayon:</b> {rayon_text}")
        rayon_label.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(rayon_label)
        
        # Kamar
        kamar_label = QtWidgets.QLabel()
        kamar_text = self.visitor_info.get("kamar", "N/A")
        kamar_label.setText(f"<b>Kamar:</b> {kamar_text}")
        kamar_label.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(kamar_label)
        
        # ID
        id_label = QtWidgets.QLabel()
        id_label.setText(f"<b>ID:</b> {self.santri_id}")
        id_label.setStyleSheet("font-size: 11px; color: #666;")
        info_layout.addWidget(id_label)
        
        layout.addWidget(info_box)
        layout.addStretch()
        
        # Close button
        btn_close = QtWidgets.QPushButton(" Tutup")
        btn_close.setStyleSheet("background: #00aa00; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
    
    def show_and_wait(self):
        """Show dialog untuk 3 seconds, atau sampai user close"""
        self.show()
        QtCore.QTimer.singleShot(3000, self.accept)


class ScanOldVisitorDialog(QtWidgets.QDialog):
    """Compatibility wrapper for the restored fingerprint scan action."""
    
    def __init__(self, parent=None, db=None, fingerprint_handler=None):
        super().__init__(parent)
        self.db = db
        if parent and hasattr(parent, "scan_fingerprint_visitor"):
            parent.scan_fingerprint_visitor()
        self.reject()

# =======================================================
# ============== REGISTERED VISITORS DIALOG ==============
# =======================================================
class RegisteredVisitorsDialog(QtWidgets.QDialog):
    """Dialog untuk menampilkan list pengunjung terdaftar dengan search"""
    
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Daftar Pengunjung")
        self.setModal(True)
        self.setGeometry(100, 100, 700, 500)
        self.init_ui()
        self.load_visitors()
    
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel("Daftar Pengunjung Terdaftar")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Search bar
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(QtWidgets.QLabel("Cari:"))
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Cari nama atau rayon...")
        self.search_input.textChanged.connect(self.filter_visitors)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Table untuk menampilkan pengunjung
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Nama", "Rayon", "Kamar", "Fingerprint ID"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_visitor_context_menu)
        layout.addWidget(self.table)
        
        # Close button
        btn_close = QtWidgets.QPushButton(" Tutup")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
    
    def load_visitors(self):
        """Load all registered visitors from database"""
        try:
            if not self.db:
                return
            
            c = self.db.conn.cursor()
            c.execute("SELECT id, nama, rayon, kamar, fingerprint_id FROM visitors ORDER BY nama")
            rows = c.fetchall()
            
            self.table.setRowCount(len(rows))
            
            for r, row in enumerate(rows):
                id_v, nama, rayon, kamar, fp_id = row
                
                self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(id_v)))
                self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(nama)))
                self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(rayon)))
                self.table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(kamar)))
                self.table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(fp_id)))
            
            self.table.resizeColumnsToContents()
        except Exception as e:
            print(f"Error loading visitors: {e}")

    def show_visitor_context_menu(self, position):
        row = self.table.rowAt(position.y())
        if row < 0:
            return

        visitor_id_item = self.table.item(row, 0)
        if not visitor_id_item:
            return

        menu = QtWidgets.QMenu(self)
        action_edit = menu.addAction("Edit Data")
        if menu.exec_(self.table.mapToGlobal(position)) == action_edit:
            self.edit_visitor_data(int(visitor_id_item.text()))

    def edit_visitor_data(self, visitor_id):
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT nama, rayon, kamar FROM visitors WHERE id = ?",
                (visitor_id,)
            )
            visitor = cursor.fetchone()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Gagal", f"Gagal memuat data pengunjung:\n{e}")
            return

        if not visitor:
            QtWidgets.QMessageBox.warning(self, "Data Tidak Ditemukan", "Data pengunjung sudah tidak tersedia.")
            self.load_visitors()
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Edit Data Pengunjung")
        dialog.setMinimumWidth(360)
        layout = QtWidgets.QVBoxLayout(dialog)
        form = QtWidgets.QFormLayout()

        nama_input = QtWidgets.QLineEdit(visitor[0] or "")
        rayon_input = QtWidgets.QComboBox()
        rayon_input.addItems(VisitorRegistrationDialog.RAYONS)
        rayon = visitor[1] or ""
        if rayon and rayon_input.findText(rayon) < 0:
            rayon_input.addItem(rayon)
        rayon_input.setCurrentText(rayon)

        kamar_input = QtWidgets.QComboBox()
        kamar_input.addItems(VisitorRegistrationDialog.ROOMS)
        kamar = str(visitor[2] or "")
        if kamar and kamar_input.findText(kamar) < 0:
            kamar_input.addItem(kamar)
        kamar_input.setCurrentText(kamar)
        form.addRow("Nama:", nama_input)
        form.addRow("Rayon:", rayon_input)
        form.addRow("Kamar:", kamar_input)
        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        nama = nama_input.text().strip()
        if not nama:
            QtWidgets.QMessageBox.warning(self, "Validasi", "Nama pengunjung wajib diisi.")
            return

        try:
            if not self.db.update_visitor(
                visitor_id,
                nama=nama,
                rayon=rayon_input.currentText(),
                kamar=kamar_input.currentText()
            ):
                raise ValueError("Data pengunjung tidak berhasil diperbarui.")

            self.load_visitors()
            parent_window = self.parent()
            if parent_window and hasattr(parent_window, "load_visitors"):
                parent_window.load_visitors()
            QtWidgets.QMessageBox.information(self, "Berhasil", "Data pengunjung berhasil diperbarui.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Gagal", f"Gagal memperbarui data pengunjung:\n{e}")
    
    def filter_visitors(self):
        """Filter visitors based on search input"""
        keyword = self.search_input.text().strip().lower()
        
        for row in range(self.table.rowCount()):
            item_nama = self.table.item(row, 1)
            item_rayon = self.table.item(row, 2)
            
            if item_nama and item_rayon:
                nama = item_nama.text().lower()
                rayon = item_rayon.text().lower()
                
                # Show row if keyword matches nama or rayon
                matches = keyword in nama or keyword in rayon
                self.table.setRowHidden(row, not matches)
            else:
                self.table.setRowHidden(row, not keyword)


class AvatarPickerWidget(QtWidgets.QFrame):
    """Widget avatar dengan overlay teks yang muncul saat hover."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self.setFixedSize(150, 150)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

        self.avatar_label = QtWidgets.QLabel(self)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setFixedSize(140, 140)
        self.avatar_label.setScaledContents(True)
        self.avatar_label.setStyleSheet("""
            QLabel {
                border: 3px solid #4c6ef5;
                border-radius: 70px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eef3ff, stop:1 #dfe8ff);
            }
        """)

        self.overlay = QtWidgets.QLabel("Klik untuk ganti foto", self)
        self.overlay.setAlignment(Qt.AlignCenter)
        self.overlay.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 0.88);
                color: #1f2937;
                border-radius: 70px;
                padding: 10px;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        self.overlay.setVisible(False)
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._layout_children()

    def _layout_children(self):
        self.avatar_label.move((self.width() - self.avatar_label.width()) // 2,
                               (self.height() - self.avatar_label.height()) // 2)
        self.avatar_label.setMask(QtGui.QRegion(self.avatar_label.rect(), QtGui.QRegion.Ellipse))
        self.overlay.setGeometry(self.avatar_label.geometry())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_children()

    def enterEvent(self, event):
        self.overlay.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.overlay.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.parent_dialog and hasattr(self.parent_dialog, 'upload_avatar'):
            self.parent_dialog.upload_avatar()
            return
        super().mousePressEvent(event)

    def setPixmap(self, pixmap):
        if pixmap and not pixmap.isNull():
            size = self.avatar_label.size()
            scaled = pixmap.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            circular = QtGui.QPixmap(size)
            circular.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(circular)
            painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
            path = QtGui.QPainterPath()
            path.addEllipse(0, 0, size.width(), size.height())
            painter.setClipPath(path)
            x = (size.width() - scaled.width()) // 2
            y = (size.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            self.avatar_label.setPixmap(circular)
        else:
            self.avatar_label.clear()


class EditProfileDialog(QtWidgets.QDialog):
    """Dialog untuk edit profil pustakawan"""
    
    def __init__(self, parent=None, db=None, current_user=None):
        super().__init__(parent)
        self.db = db
        self.current_user = current_user
        self.selected_avatar_path = None
        self.avatar_changed = False
        
        self.setWindowTitle("Edit Profil")
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.setFixedSize(480, 590)
        self.setStyleSheet("""
            QDialog {
                background: #f7f9ff;
            }
            QLabel, QLineEdit, QGroupBox, QPushButton {
                font-family: Segoe UI;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel("Edit Profil Pustakawan")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Avatar section
        avatar_container = QtWidgets.QFrame()
        avatar_container.setStyleSheet("""
            QFrame {
                background: #f8faff;
                border: 1px solid #dfe7ff;
                border-radius: 16px;
                padding: 16px;
            }
        """)
        avatar_layout = QtWidgets.QVBoxLayout(avatar_container)

        avatar_title = QtWidgets.QLabel("Foto Profil")
        avatar_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #3652b3;")
        avatar_title.setAlignment(Qt.AlignCenter)
        avatar_layout.addWidget(avatar_title)

        self.avatar_display = AvatarPickerWidget(self)
        self._refresh_avatar_display()
        avatar_layout.addWidget(self.avatar_display, alignment=Qt.AlignCenter)

        btn_remove = QtWidgets.QPushButton("Hapus Foto")
        btn_remove.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #c0392b;
                border: none;
                font-weight: 600;
                padding: 6px;
            }
            QPushButton:hover {
                color: #a93226;
                text-decoration: underline;
            }
        """)
        btn_remove.clicked.connect(self.remove_avatar)
        avatar_layout.addWidget(btn_remove, alignment=Qt.AlignCenter)

        layout.addWidget(avatar_container)
        layout.addSpacing(12)
        
        # Profile info
        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        
        self.username_label = QtWidgets.QLabel()
        self.username_label.setStyleSheet("color: #475467; font-weight: 600;")
        form.addRow("Username:", self.username_label)
        
        self.fullname_input = QtWidgets.QLineEdit()
        self.fullname_input.setPlaceholderText("Masukkan nama lengkap")
        self.fullname_input.setStyleSheet("padding: 8px; border: 1px solid #d0d5dd; border-radius: 8px;")
        form.addRow("Nama Lengkap:", self.fullname_input)

        self.jabatan_label = QtWidgets.QLabel()
        self.jabatan_label.setStyleSheet("color: #475467; padding: 8px; border: 1px solid #d0d5dd; border-radius: 8px; background: white;")
        form.addRow("Jabatan:", self.jabatan_label)
        
        layout.addLayout(form)
        
        self.btn_change_password = QtWidgets.QPushButton("Ubah Password")
        self.btn_change_password.setCursor(Qt.PointingHandCursor)
        self.btn_change_password.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #2563eb;
                border: 1px solid #c7d2fe;
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #eff6ff;
            }
        """)
        self.btn_change_password.clicked.connect(self.toggle_password_fields)
        layout.addWidget(self.btn_change_password, alignment=Qt.AlignLeft)

        # Password section
        pw_group = QtWidgets.QGroupBox("Ganti Password (Opsional)")
        pw_group.setVisible(False)
        pw_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 1px solid #dfe7ff;
                border-radius: 10px;
                margin-top: 8px;
                padding-top: 10px;
            }
        """)
        pw_layout = QtWidgets.QFormLayout()
        
        self.current_password = QtWidgets.QLineEdit()
        self.current_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.current_password.setStyleSheet("padding: 8px; border: 1px solid #d0d5dd; border-radius: 8px;")
        self.new_password = QtWidgets.QLineEdit()
        self.new_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.new_password.setStyleSheet("padding: 8px; border: 1px solid #d0d5dd; border-radius: 8px;")
        self.new_password2 = QtWidgets.QLineEdit()
        self.new_password2.setEchoMode(QtWidgets.QLineEdit.Password)
        self.new_password2.setStyleSheet("padding: 8px; border: 1px solid #d0d5dd; border-radius: 8px;")
        
        pw_layout.addRow("Password Saat Ini:", self.current_password)
        pw_layout.addRow("Password Baru:", self.new_password)
        pw_layout.addRow("Konfirmasi Password:", self.new_password2)
        
        pw_group.setLayout(pw_layout)
        self.pw_group = pw_group
        layout.addWidget(pw_group)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_save = QtWidgets.QPushButton("Simpan Perubahan")
        btn_save.setStyleSheet("""
            QPushButton {
                background: #4c6ef5;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 9px 14px;
                font-weight: 600;
            }
            QPushButton:hover { background: #3b5bdb; }
        """)
        btn_cancel = QtWidgets.QPushButton("Batal")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #f2f4f7;
                color: #344054;
                border: 1px solid #d0d5dd;
                border-radius: 8px;
                padding: 9px 14px;
                font-weight: 600;
            }
        """)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        btn_save.clicked.connect(self.save_changes)
        btn_cancel.clicked.connect(self.reject)
        
        self.load_current_data()
    
    def toggle_password_fields(self):
        visible = not self.pw_group.isVisible()
        self.pw_group.setVisible(visible)
        self.btn_change_password.setText("Batal Ubah Password" if visible else "Ubah Password")
        if not visible:
            self.current_password.clear()
            self.new_password.clear()
            self.new_password2.clear()

    def load_current_data(self):
        """Load data profil yang sekarang"""
        if self.current_user:
            self.username_label.setText(self.current_user.get('username', '-'))
            self.fullname_input.setText(self.current_user.get('full_name', ''))
            self.jabatan_label.setText(self.map_role_to_jabatan(self.current_user.get('role')))

    def map_role_to_jabatan(self, role):
        """Derive jabatan from role and keep it read-only."""
        role_value = (role or '').strip().lower()
        if role_value == 'administrator':
            return 'Administrator'
        if role_value == 'porseni':
            return 'PORSENI'
        return 'Pustakawan'

    def _refresh_avatar_display(self):
        """Perbarui tampilan avatar sesuai data user saat ini."""
        avatar_path = None
        if self.avatar_changed:
            avatar_path = self.selected_avatar_path
        elif self.current_user:
            avatar_path = self.current_user.get('avatar_path')

        if avatar_path and os.path.exists(avatar_path):
            circular_pix = self.create_circular_avatar(avatar_path, size=140)
            if circular_pix:
                self.avatar_display.setPixmap(circular_pix)
                return

        if self.current_user:
            name = self.current_user.get('full_name') or self.current_user.get('username') or "?"
        else:
            name = "?"
        pix = self.create_avatar_pixmap(name, size=140)
        self.avatar_display.setPixmap(pix)
    
    def create_circular_avatar(self, image_path, size=120):
        """Buat circular avatar dari foto dengan size yang konsisten"""
        try:
            # Load image
            original_pix = QtGui.QPixmap(image_path)
            if original_pix.isNull():
                return None
            
            # Resize ke square dulu (dengan langsung crop tengahnya)
            w = original_pix.width()
            h = original_pix.height()
            min_dim = min(w, h)
            
            # Crop ke persegi dari tengah
            x = (w - min_dim) // 2
            y = (h - min_dim) // 2
            cropped = original_pix.copy(x, y, min_dim, min_dim)
            
            # Scale ke size yang diinginkan dengan aspect ratio square seimbang
            scaled = cropped.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # Buat circular mask
            circular_pix = QtGui.QPixmap(size, size)
            circular_pix.fill(QtCore.Qt.transparent)
            
            painter = QtGui.QPainter(circular_pix)
            painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
            
            # Draw circular clipping area
            path = QtGui.QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            
            # Center the scaled image inside the circle
            x_offset = (size - scaled.width()) // 2
            y_offset = (size - scaled.height()) // 2
            painter.drawPixmap(x_offset, y_offset, scaled)
            painter.end()
            
            return circular_pix
        except Exception as e:
            print(f"Error creating circular avatar: {e}")
            return None
    
    def create_avatar_pixmap(self, name, size=40):
        """Buat QPixmap lingkaran dengan inisial"""
        initials = "?"
        if name:
            parts = str(name).strip().split()
            if len(parts) >= 2:
                initials = parts[0][0].upper() + parts[1][0].upper()
            else:
                initials = parts[0][0].upper()

        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pix)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        color = QtGui.QColor(100, 149, 237)
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(max(10, size // 3))
        painter.setFont(font)
        painter.setPen(QtGui.QColor(255, 255, 255))
        rect = QtCore.QRectF(0, 0, size, size)
        painter.drawText(rect, Qt.AlignCenter, initials)
        painter.end()
        return pix
    
    def upload_avatar(self):
        """Upload foto profil baru"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Pilih Foto Profil",
            "",
            "Image Files (*.jpg *.jpeg *.png *.bmp);;All Files (*)"
        )
        
        if not file_path:
            return
        
        pix = QtGui.QPixmap(file_path)
        if pix.isNull():
            QtWidgets.QMessageBox.warning(self, "Error", "File bukan gambar yang valid!")
            return
        
        try:
            import shutil
            from pathlib import Path
            
            if hasattr(sys, '_MEIPASS'):
                avatars_dir = os.path.join(str(Path.home()), "A Latee Library", "avatars")
            else:
                avatars_dir = "avatars"
            
            os.makedirs(avatars_dir, exist_ok=True)
            
            username = self.current_user.get('username', 'user') if self.current_user else 'user'
            ext = os.path.splitext(file_path)[1].lower()
            avatar_filename = f"{username}_avatar{ext}"
            avatar_path = os.path.join(avatars_dir, avatar_filename)
            
            shutil.copy(file_path, avatar_path)
            
            self.selected_avatar_path = avatar_path
            self.avatar_changed = True
            self._refresh_avatar_display()
            
            QtWidgets.QMessageBox.information(self, "Berhasil", "Foto profil siap digunakan. Klik Simpan untuk menyimpan perubahan.")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal menyimpan foto:\n{str(e)}")
    
    def remove_avatar(self):
        """Hapus foto profil custom (set to None)"""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Konfirmasi",
            "Hapus foto profil custom? Avatar akan kembali ke nama inisial.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.selected_avatar_path = None
            self.avatar_changed = True
            self._refresh_avatar_display()
            
            QtWidgets.QMessageBox.information(self, "Berhasil", "Foto profil akan dihapus saat Anda klik Simpan.")
    
    def save_changes(self):
        """Simpan perubahan profil"""
        try:
            if not self.current_user:
                QtWidgets.QMessageBox.warning(self, "Error", "Tidak ada user yang login!")
                return
            
            fullname = self.fullname_input.text().strip()
            current_pw = self.current_password.text()
            new_pw = self.new_password.text()
            new_pw2 = self.new_password2.text()
            
            username = self.current_user.get('username')
            
            # Cek nama lengkap duplikasi jika diubah
            if fullname and fullname != self.current_user.get('full_name', ''):
                c = self.db.conn.cursor()
                c.execute('SELECT id FROM users WHERE LOWER(full_name)=LOWER(?) AND username!=?', 
                         (fullname, username))
                if c.fetchone():
                    QtWidgets.QMessageBox.warning(self, "Error", "Nama lengkap tersebut sudah digunakan!")
                    return
            
            # Validasi dan update password jika ada input
            if (new_pw or new_pw2) and self.pw_group.isVisible():
                if not current_pw:
                    QtWidgets.QMessageBox.warning(self, "Error", "Masukkan password saat ini!")
                    return
                
                user = self.db.authenticate_user(username, current_pw)
                if not user:
                    QtWidgets.QMessageBox.warning(self, "Error", "Password saat ini salah!")
                    return
                
                if new_pw != new_pw2:
                    QtWidgets.QMessageBox.warning(self, "Error", "Password baru dan konfirmasi tidak cocok!")
                    return
                
                if len(new_pw) < 4:
                    QtWidgets.QMessageBox.warning(self, "Error", "Password baru minimal 4 karakter!")
                    return
                
                self.db.update_user_password(username, new_pw)
            
            # Update full_name, jabatan, dan avatar_path bersama-sama
            c = self.db.conn.cursor()
            
            if self.avatar_changed:
                avatar_to_save = self.selected_avatar_path
            else:
                avatar_to_save = self.current_user.get('avatar_path') if self.current_user else None
            
            jabatan = self.map_role_to_jabatan(self.current_user.get('role'))
            c.execute('UPDATE users SET full_name=?, jabatan=?, avatar_path=? WHERE username=?', 
                     (fullname, jabatan, avatar_to_save, username))
            self.db.conn.commit()

            if self.current_user is not None:
                self.current_user['full_name'] = fullname
                self.current_user['avatar_path'] = avatar_to_save
                self.current_user['jabatan'] = jabatan or ''
            
            QtWidgets.QMessageBox.information(self, "Berhasil", "Profil berhasil diperbarui!")
            self.accept()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal menyimpan perubahan:\n{e}")


# =======================================================
# ============== DATABASE HANDLER ========================
# =======================================================
class Database:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.create_tables()
        self.migrate_tables()  # Migrasi untuk kolom baru
    
    def get_qrcodes_dir(self):
        """Get folder path untuk QR codes"""
        import os
        from pathlib import Path
        
        if hasattr(sys, '_MEIPASS'):
            # Running dari executable (pyinstaller/NSIS)
            return os.path.join(str(Path.home()), "A Latee Library", "qrcodes")
        else:
            # Running dari source
            return "qrcodes"
    
    def get_cards_dir(self):
        """Get folder path untuk kartu"""
        import os
        from pathlib import Path
        
        if hasattr(sys, '_MEIPASS'):
            # Running dari executable (pyinstaller/NSIS)
            return os.path.join(str(Path.home()), "A Latee Library", "cards")
        else:
            # Running dari source
            return "cards"

    def create_tables(self):
        c = self.conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS books(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_buku TEXT,
            kategori TEXT,
            judul TEXT,
            penulis TEXT,
            penerbit TEXT,
            barcode TEXT UNIQUE,
            stok INTEGER DEFAULT 1,
            status TEXT DEFAULT 'ada',
            jumlah_dipinjam INTEGER DEFAULT 0,
            UNIQUE(kode_buku, kategori)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS sale_products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judul TEXT NOT NULL,
            penulis TEXT NOT NULL,
            harga REAL NOT NULL DEFAULT 0,
            barcode TEXT UNIQUE,
            stok INTEGER NOT NULL DEFAULT 1,
            created_at TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total REAL NOT NULL DEFAULT 0,
            created_at TEXT,
            dibuat_oleh TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS sale_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            jumlah INTEGER NOT NULL,
            harga REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES sales(id),
            FOREIGN KEY(product_id) REFERENCES sale_products(id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS members(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nis TEXT,
            nama TEXT,
            rayon TEXT,
            kamar TEXT,
            alamat TEXT,
            barcode TEXT UNIQUE,
            jenis_santri TEXT DEFAULT 'lama',
            qr_id TEXT
        )''')
        
        # Tambahkan kolom rayon jika belum ada
        try:
            c.execute('ALTER TABLE members ADD COLUMN rayon TEXT')
        except:
            pass  # Kolom sudah ada

        try:
            c.execute("ALTER TABLE members ADD COLUMN jenis_santri TEXT DEFAULT 'lama'")
            self.conn.commit()
        except:
            pass  # Kolom sudah ada

        try:
            c.execute("ALTER TABLE members ADD COLUMN qr_id TEXT")
            self.conn.commit()
        except:
            pass  # Kolom sudah ada
        try:
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_members_qr_id_unique ON members(qr_id) WHERE qr_id IS NOT NULL")
            self.conn.commit()
        except:
            pass
        
        # Tambahkan kolom penulis ke books jika belum ada
        try:
            c.execute('ALTER TABLE books ADD COLUMN penulis TEXT')
            self.conn.commit()
        except:
            pass  # Kolom sudah ada

        c.execute('''CREATE TABLE IF NOT EXISTS borrows(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            member_id INTEGER,
            tanggal_pinjam TEXT,
            tanggal_kembali TEXT,
            status INTEGER DEFAULT 0,
            diperpanjang INTEGER DEFAULT 0,
            denda INTEGER DEFAULT 0,
            FOREIGN KEY(book_id) REFERENCES books(id),
            FOREIGN KEY(member_id) REFERENCES members(id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS visitors(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT,
            kamar TEXT,
            rayon TEXT,
            fingerprint_id TEXT UNIQUE,
            waktu_kunjungan TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS visitor_visits(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id INTEGER NOT NULL,
            waktu_kunjungan TEXT NOT NULL,
            FOREIGN KEY(visitor_id) REFERENCES visitors(id)
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_visitor_visits_time ON visitor_visits(waktu_kunjungan)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_visitor_visits_visitor_id ON visitor_visits(visitor_id)')
        c.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_visitor_visits_unique_time
                     ON visitor_visits(visitor_id, waktu_kunjungan)''')

        # ------------------- Users (Pustakawan) -----------------------
        c.execute('''CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            full_name TEXT,
            avatar_path TEXT,
            role TEXT DEFAULT 'pustakawan',
            jabatan TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )''')

        # ------------------- Pending QR Codes (Sistem Generasi Massal) -----------------------
        c.execute('''CREATE TABLE IF NOT EXISTS pending_qr_codes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_id TEXT UNIQUE,
            barcode TEXT UNIQUE NOT NULL,
            member_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            linked_at TEXT,
            FOREIGN KEY(member_id) REFERENCES members(id)
        )''')
        
        # ------------------- Fingerprint Database (1000+ Santri) -----------------------
        # Menyimpan fingerprint template dari reader ZKTeco
        # Table ini adalah core dari fingerprint matching system
        c.execute('''CREATE TABLE IF NOT EXISTS santri_fingerprints(
            santri_id INTEGER PRIMARY KEY,
            nama TEXT NOT NULL,
            template_data BLOB NOT NULL,
            template_hash TEXT UNIQUE,
            quality INTEGER DEFAULT 80,
            timestamp TEXT DEFAULT (datetime('now')),
            rayon TEXT,
            kamar TEXT,
            status TEXT DEFAULT 'active'
        )''')
        
        # Index untuk quick lookup - will be created/verified in migrate_tables()
        # Don't try to create index here in case template_hash doesn't exist yet in existing tables

        self.conn.commit()

    def migrate_tables(self):
        """Migrasi database untuk menambahkan kolom baru"""
        c = self.conn.cursor()
        
        # Cek apakah kolom diperpanjang sudah ada di tabel borrows
        c.execute("PRAGMA table_info(borrows)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'diperpanjang' not in columns:
            c.execute('ALTER TABLE borrows ADD COLUMN diperpanjang INTEGER DEFAULT 0')
            self.conn.commit()
            print("[OK] Kolom 'diperpanjang' berhasil ditambahkan ke tabel borrows")
        
        if 'denda' not in columns:
            c.execute('ALTER TABLE borrows ADD COLUMN denda INTEGER DEFAULT 0')
            self.conn.commit()
            print("[OK] Kolom 'denda' berhasil ditambahkan ke tabel borrows")

        c.execute("PRAGMA table_info(sale_items)")
        sale_item_columns = [column[1] for column in c.fetchall()]
        if "harga_asli" not in sale_item_columns:
            c.execute("ALTER TABLE sale_items ADD COLUMN harga_asli REAL")
            self.conn.commit()
            print("[OK] Kolom 'harga_asli' berhasil ditambahkan ke tabel sale_items")

        for audit_column in ('dibuat_oleh', 'dikembalikan_oleh', 'denda_dibuat_oleh', 'denda_dibayar_oleh'):
            if audit_column not in columns:
                c.execute(f'ALTER TABLE borrows ADD COLUMN {audit_column} TEXT')
                self.conn.commit()
                print(f"[OK] Kolom '{audit_column}' berhasil ditambahkan ke tabel borrows")
        
        # Cek members dan tambahkan kolom rayon jika belum ada
        c.execute("PRAGMA table_info(members)")
        members_columns = [column[1] for column in c.fetchall()]
        if 'rayon' not in members_columns:
            try:
                c.execute('ALTER TABLE members ADD COLUMN rayon TEXT')
                self.conn.commit()
                print("[OK] Kolom 'rayon' berhasil ditambahkan ke tabel members")
            except:
                pass
        
        # Cek users dan tambahkan kolom role dan jabatan jika belum ada
        try:
            c.execute("PRAGMA table_info(users)")
            user_columns = [column[1] for column in c.fetchall()]
            if 'role' not in user_columns:
                c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'pustakawan'")
                self.conn.commit()
                print("[OK] Kolom 'role' berhasil ditambahkan ke tabel users")

                # Backfill role for existing rows
                c.execute("SELECT id, username, full_name, role FROM users")
                rows = c.fetchall()
                for user_id, username, full_name, current_role in rows:
                    inferred_role = self.normalize_role(current_role)
                    if (username or '').lower() == 'admin' or (full_name or '').lower() == 'administrator':
                        inferred_role = 'administrator'
                    c.execute('UPDATE users SET role=? WHERE id=?', (inferred_role, user_id))
                self.conn.commit()

            if 'jabatan' not in user_columns:
                c.execute("ALTER TABLE users ADD COLUMN jabatan TEXT")
                self.conn.commit()
                print("[OK] Kolom 'jabatan' berhasil ditambahkan ke tabel users")

            if 'barcode' not in user_columns:
                c.execute("ALTER TABLE users ADD COLUMN barcode TEXT")
                self.conn.commit()
                print("[OK] Kolom 'barcode' berhasil ditambahkan ke tabel users")

            c.execute("SELECT id FROM users WHERE barcode IS NULL OR barcode='' ORDER BY id")
            for (user_id,) in c.fetchall():
                c.execute("UPDATE users SET barcode=? WHERE id=?", (f"PUST-{user_id:06d}", user_id))
            self.conn.commit()
        except Exception as e:
            print(f"[WARN] Error migrating users: {e}")

        # Cek pending_qr_codes dan tambahkan kolom baru
        try:
            c.execute("PRAGMA table_info(pending_qr_codes)")
            pqr_columns = [column[1] for column in c.fetchall()]
            
            # Tambah kolom qr_id jika belum ada
            if 'qr_id' not in pqr_columns:
                c.execute('ALTER TABLE pending_qr_codes ADD COLUMN qr_id TEXT UNIQUE')
                self.conn.commit()
                print("[OK] Kolom 'qr_id' berhasil ditambahkan ke tabel pending_qr_codes")
            
            # Tambah kolom untuk tracking print dan status
            if 'printed_at' not in pqr_columns:
                c.execute('ALTER TABLE pending_qr_codes ADD COLUMN printed_at TEXT')
                self.conn.commit()
                print("[OK] Kolom 'printed_at' berhasil ditambahkan ke tabel pending_qr_codes")
            
            if 'is_blocked' not in pqr_columns:
                c.execute('ALTER TABLE pending_qr_codes ADD COLUMN is_blocked INTEGER DEFAULT 0')
                self.conn.commit()
                print("[OK] Kolom 'is_blocked' berhasil ditambahkan ke tabel pending_qr_codes")
        except:
            pass  # Table belum ada atau error lain
        
        # Migrate visitors table: nis -> rayon
        try:
            c.execute("PRAGMA table_info(visitors)")
            vis_columns = [column[1] for column in c.fetchall()]
            
            # Tambah rayon jika belum ada
            if 'rayon' not in vis_columns:
                c.execute('ALTER TABLE visitors ADD COLUMN rayon TEXT DEFAULT "Tidak Terdaftar"')
                self.conn.commit()
                print("[OK] Kolom 'rayon' berhasil ditambahkan ke tabel visitors")
        except:
            pass  # Kolom sudah ada
        
        # ========== MIGRATE santri_fingerprints: ADD template_hash untuk deduplication ==========
        try:
            c.execute("PRAGMA table_info(santri_fingerprints)")
            sfp_columns = [column[1] for column in c.fetchall()]
            
            # Add template_hash column if not exists
            if 'template_hash' not in sfp_columns:
                print("[MIGRATION] Adding template_hash column to santri_fingerprints...")
                # Add as TEXT first (without UNIQUE constraint to avoid conflicts with existing nulls)
                c.execute('ALTER TABLE santri_fingerprints ADD COLUMN template_hash TEXT')
                self.conn.commit()
                print("[OK] Kolom 'template_hash' berhasil ditambahkan ke tabel santri_fingerprints")
                
                # ========== BACKFILL: Generate hash untuk existing templates ==========
                print("[MIGRATION] Generating template hashes untuk existing records...")
                import hashlib
                c.execute('SELECT santri_id, template_data FROM santri_fingerprints WHERE template_hash IS NULL')
                rows_to_update = c.fetchall()
                
                updated_count = 0
                for santri_id, template_data in rows_to_update:
                    try:
                        if isinstance(template_data, bytes):
                            template_hash = hashlib.sha256(template_data).hexdigest()
                        else:
                            template_hash = hashlib.sha256(bytes.fromhex(str(template_data))).hexdigest()
                        
                        c.execute('UPDATE santri_fingerprints SET template_hash=? WHERE santri_id=?',
                                 (template_hash, santri_id))
                        updated_count += 1
                    except Exception as e:
                        print(f"  [WARN] Could not hash template for santri {santri_id}: {e}")
                        continue
                
                self.conn.commit()
                print(f"[OK] Generated hashes untuk {updated_count} templates")
                
                # ========== REMOVE DUPLICATES BASED ON HASH ==========
                # If same hash exists, keep only the one with highest quality
                print("[MIGRATION] Checking for duplicate templates by hash...")
                c.execute('''
                    SELECT template_hash, COUNT(*) as cnt
                    FROM santri_fingerprints
                    WHERE template_hash IS NOT NULL
                    GROUP BY template_hash
                    HAVING cnt > 1
                ''')
                duplicate_hashes = c.fetchall()
                
                deleted_count = 0
                for thash, cnt in duplicate_hashes:
                    print(f"  Found {cnt} templates with hash {thash[:16]}...")
                    # Get all santri_ids with this hash, keep the one with highest quality
                    c.execute('''
                        SELECT santri_id, quality
                        FROM santri_fingerprints
                        WHERE template_hash = ?
                        ORDER BY quality DESC
                    ''', (thash,))
                    rows = c.fetchall()
                    keep_id = rows[0][0]
                    for del_id, _ in rows[1:]:
                        c.execute('DELETE FROM santri_fingerprints WHERE santri_id=?', (del_id,))
                        print(f"    Deleted duplicate santri {del_id}, kept {keep_id}")
                        deleted_count += 1
                
                self.conn.commit()
                if deleted_count > 0:
                    print(f"[OK] Deleted {deleted_count} duplicate templates")
                
                # Create unique index on template_hash
                c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_template_hash_unique ON santri_fingerprints(template_hash)')
                self.conn.commit()
                print("[OK] Unique index untuk template_hash dibuat")
        except Exception as e:
            if "duplicate column name" not in str(e):
                print(f"[WARN] Error migrating santri_fingerprints: {e}")
        
        # ========== CREATE INDICES untuk santri_fingerprints ==========
        try:
            c.execute('CREATE INDEX IF NOT EXISTS idx_santri_nama ON santri_fingerprints(nama)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_santri_rayon ON santri_fingerprints(rayon)')
            self.conn.commit()
        except Exception as e:
            print(f"[WARN] Error creating indices: {e}")
        
        # Copy each existing visitor check-in before duplicate identities are consolidated.
        c.execute('''
            INSERT OR IGNORE INTO visitor_visits(visitor_id, waktu_kunjungan)
            SELECT id, waktu_kunjungan
            FROM visitors
            WHERE waktu_kunjungan IS NOT NULL AND waktu_kunjungan != ''
        ''')
        self.conn.commit()

        # ========== FIX FINGERPRINT DUPLICATES ==========
        # Migrate visitors table: ensure fingerprint_id is UNIQUE
        # If there are duplicates, keep only the first one
        try:
            print("[MIGRATION] Checking fingerprint_id uniqueness...")
            
            # Cek apakah ada duplicate fingerprint_id
            c.execute("""
                SELECT fingerprint_id, COUNT(*) as cnt 
                FROM visitors 
                WHERE fingerprint_id IS NOT NULL
                GROUP BY fingerprint_id 
                HAVING cnt > 1
            """)
            
            duplicates = c.fetchall()
            if duplicates:
                print(f"[WARNING] Found {len(duplicates)} duplicate fingerprint_id(s): {duplicates}")
                print("[MIGRATION] Removing duplicate fingerprint_id entries...")
                
                # Remove duplicates: keep first, delete rest
                for fp_id, cnt in duplicates:
                    # Get all IDs with this fingerprint_id, ordered by insertion
                    c.execute("""
                        SELECT id FROM visitors 
                        WHERE fingerprint_id = ?
                        ORDER BY id ASC
                    """, (fp_id,))
                    
                    ids = [row[0] for row in c.fetchall()]
                    
                    # Keep first ID, delete rest
                    if len(ids) > 1:
                        ids_to_delete = ids[1:]
                        for duplicate_id in ids_to_delete:
                            c.execute('''
                                INSERT OR IGNORE INTO visitor_visits(visitor_id, waktu_kunjungan)
                                SELECT ?, waktu_kunjungan
                                FROM visitor_visits
                                WHERE visitor_id = ?
                            ''', (ids[0], duplicate_id))
                            c.execute(
                                'DELETE FROM visitor_visits WHERE visitor_id=?',
                                (duplicate_id,)
                            )
                            c.execute('DELETE FROM visitors WHERE id=?', (duplicate_id,))
                        print(f"  - Removed {len(ids_to_delete)} duplicate(s) for fingerprint_id={fp_id}")
                
                self.conn.commit()
                print("[OK] Fingerprint duplicates removed")
            
            # Now add UNIQUE constraint
            # SQLite doesn't support ALTER TABLE ADD CONSTRAINT UNIQUE directly
            # We need to recreate the table
            print("[MIGRATION] Ensuring fingerprint_id UNIQUE constraint...")
            
            # Check if constraint already exists (by trying to insert duplicate)
            # For now, we'll just log that the data is clean
            # The CREATE TABLE statement already has UNIQUE
            
            print("[MIGRATION] [OK] Visitors table is properly cleaned)")
            
        except Exception as e:
            print(f"[MIGRATION] Warning during fingerprint migration: {e}")

        # ------------------- Buku -----------------------
    def add_book(self, kode, kategori, judul, penulis, penerbit, stok, barcode=None, status='ada', jumlah_dipinjam=0):
        c = self.conn.cursor()
        c.execute('INSERT INTO books(kode_buku,kategori,judul,penulis,penerbit,stok,barcode,status,jumlah_dipinjam) VALUES(?,?,?,?,?,?,?,?,?)',
                  (kode, kategori, judul, penulis, penerbit, stok, barcode, status, jumlah_dipinjam))
        self.conn.commit()
        return c.lastrowid

    def list_books(self):
        c = self.conn.cursor()
        # Select kolom dalam urutan yang sesuai dengan UI: id, kode, kategori, judul, PENULIS, penerbit, barcode, stok, status, jumlah_dipinjam
        c.execute('SELECT id, kode_buku, kategori, judul, penulis, penerbit, barcode, stok, status, jumlah_dipinjam FROM books')
        return c.fetchall()

    def search_books(self, keyword):
        """Cari buku berdasarkan kode_buku, judul, penulis, atau penerbit"""
        c = self.conn.cursor()
        like_keyword = f"%{keyword}%"
        c.execute('''SELECT * FROM books WHERE kode_buku LIKE ? OR judul LIKE ? OR penulis LIKE ? OR penerbit LIKE ?''',
                  (like_keyword, like_keyword, like_keyword, like_keyword))
        return c.fetchall()

    def update_book_barcode(self, book_id, barcode):
        """Update barcode untuk buku yang sudah ada"""
        c = self.conn.cursor()
        c.execute('UPDATE books SET barcode=? WHERE id=?', (barcode, book_id))
        self.conn.commit()

    def list_sale_products(self):
        c = self.conn.cursor()
        c.execute("SELECT id, judul, penulis, harga, barcode, stok FROM sale_products ORDER BY judul")
        return c.fetchall()

    def find_sale_product_by_barcode(self, barcode):
        c = self.conn.cursor()
        c.execute("SELECT id, judul, penulis, harga, barcode, stok FROM sale_products WHERE barcode=?", (barcode,))
        return c.fetchone()

    def update_book(self, id_, kode, kategori, judul, penulis, penerbit, stok, status, jumlah_dipinjam):
        c = self.conn.cursor()
        c.execute('''UPDATE books SET kode_buku=?, kategori=?, judul=?, penulis=?, penerbit=?, stok=?, status=?, jumlah_dipinjam=? WHERE id=?''',
                  (kode, kategori, judul, penulis, penerbit, stok, status, jumlah_dipinjam, id_))
        self.conn.commit()

    def delete_book(self, id_):
        self.conn.execute('DELETE FROM books WHERE id=?', (id_,))
        self.conn.commit()


    # ------------------- Anggota ---------------------
    def add_member(self, nama, kamar, rayon=None):
        """Tambah member baru dengan nama, kamar, dan rayon"""
        c = self.conn.cursor()
        c.execute('INSERT INTO members(nama, kamar, rayon, barcode) VALUES(?,?,?,?)',
                (nama, kamar, rayon, None))
        self.conn.commit()
        return c.lastrowid  # Return member ID yang baru
    
    def generate_barcode_for_member(self, member_id):
        """Generate barcode & QR code untuk member yang sudah ada"""
        import traceback
        log_file = "card_creation.log"
        
        try:
            with open(log_file, 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"[{datetime.now()}] generate_barcode_for_member(member_id={member_id})\n")
            
            c = self.conn.cursor()
            c.execute('SELECT nis, nama, kamar, barcode FROM members WHERE id=?', (member_id,))
            result = c.fetchone()
            if not result:
                with open(log_file, 'a') as f:
                    f.write(f"[ERROR] Member tidak ditemukan\n")
                raise ValueError("Member tidak ditemukan")
            
            nis, nama, kamar, existing_barcode = result
            with open(log_file, 'a') as f:
                f.write(f"[OK] Member: {nama} | Barcode: {existing_barcode}\n")
            
            # Jika sudah punya barcode, gunakan yang ada, tapi tetap buat kartu
            if existing_barcode:
                barcode = existing_barcode
                with open(log_file, 'a') as f:
                    f.write(f"  Menggunakan barcode existing: {barcode}\n")
            else:
                # Generate barcode unik
                barcode = str(uuid.uuid4())[:12]
                c.execute('UPDATE members SET barcode=? WHERE id=?', (barcode, member_id))
                self.conn.commit()
                with open(log_file, 'a') as f:
                    f.write(f"  Barcode baru: {barcode}\n")
            
            # Generate QR code
            with open(log_file, 'a') as f:
                f.write(f"  Calling generate_qr_for_member({barcode})...\n")
            qr_path = self.generate_qr_for_member(barcode)
            with open(log_file, 'a') as f:
                f.write(f"  QR Path result: {qr_path}\n")
                f.write(f"  QR exists: {os.path.exists(qr_path) if qr_path else 'N/A'}\n")
            
            # Buat kartu otomatis dengan desain dari assets
            with open(log_file, 'a') as f:
                f.write(f"  Calling create_member_card_with_design({nama}, {barcode}, {kamar}, {qr_path})...\n")
            card_path = self.create_member_card_with_design(nama, barcode, kamar, qr_path)
            with open(log_file, 'a') as f:
                f.write(f"  Card Path result: {card_path}\n")
                f.write(f"  Card exists: {os.path.exists(card_path) if card_path else 'N/A'}\n")
            
            with open(log_file, 'a') as f:
                f.write(f"[OK] SELESAI: barcode={barcode}, qr={qr_path}, card={card_path}\n")
                f.write(f"{'='*60}\n")
            
            return barcode, qr_path, card_path
        
        except Exception as e:
            with open(log_file, 'a') as f:
                f.write(f"[ERROR] EXCEPTION: {str(e)}\n")
                f.write(f"  Type: {type(e).__name__}\n")
                f.write(traceback.format_exc())
                f.write(f"{'='*60}\n")
            raise

    def generate_qr_for_member(self, nis):
        import os
        from pathlib import Path
        
        # Get qrcodes folder (compatible dengan installed app)
        qr_dir = self.get_qrcodes_dir()
        os.makedirs(qr_dir, exist_ok=True)
        filename = os.path.join(qr_dir, f"{nis}.png")
        
        print(f"[DEBUG] generate_qr_for_member: Creating QR at {filename}")
        
        # Use error_correction=qrcode.constants.ERROR_CORRECT_H for logo compatibility
        qr = qrcode.QRCode(
            version=None,  # Auto-detect version based on data
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # Maximum error correction for logo
            box_size=16,
            border=2
        )
        qr.add_data(nis)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filename)
        
        print(f"[DEBUG] generate_qr_for_member: QR saved, returning {filename}")
        print(f"[DEBUG] generate_qr_for_member: File exists: {os.path.exists(filename)}")
        
        return filename

    def load_card_config(self):
        """Load konfigurasi posisi QR code dari card_config.json"""
        import json
        
        config_paths = [
            "card_config.json",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "card_config.json"),
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    print(f"[OK] Config kartu loaded: {config_path}")
                    return config
                except Exception as e:
                    print(f"[WARN] Error loading config: {e}")
        
        print(f"[WARN] Config file tidak ditemukan, menggunakan default positioning")
        return {}
    
    def get_qr_position(self, config, design_filename, design_width, design_height):
        """
        Hitung posisi QR code berdasarkan konfigurasi
        Koordinat adalah TOP-LEFT dari QR code (bukan center)
        """
        # Default positioning jika config tidak ada
        default_config = {
            "x": 0.32,
            "y": 0.35,
            "size_percent": 0.25,
            "align": "center"
        }
        
        # Ambil config dari file
        config_dict = config.get(design_filename, {})
        qr_config = config_dict.get("qr_position", default_config)
        
        # Merge dengan default jika ada yang kurang
        qr_config = {**default_config, **qr_config}
        
        print(f"  QR Config: x={qr_config['x']}, y={qr_config['y']}, size={qr_config['size_percent']}, align={qr_config['align']}")
        
        # Hitung ukuran QR code
        if isinstance(qr_config['size_percent'], float) and qr_config['size_percent'] <= 1:
            qr_size = int(design_width * qr_config['size_percent'])
        else:
            qr_size = int(qr_config['size_percent'])
        
        # Hitung posisi X (relative to design center)
        if isinstance(qr_config['x'], float) and qr_config['x'] <= 1:
            # Relative positioning (0-1): 0 = left edge, 1 = right edge
            center_x = int(design_width * qr_config['x'])
        else:
            # Absolute pixel positioning
            center_x = int(qr_config['x'])
        
        # Hitung posisi Y (relative to design center)
        if isinstance(qr_config['y'], float) and qr_config['y'] <= 1:
            # Relative positioning (0-1): 0 = top edge, 1 = bottom edge
            center_y = int(design_height * qr_config['y'])
        else:
            # Absolute pixel positioning
            center_y = int(qr_config['y'])
        
        # Untuk alignment center, center_x/center_y adalah CENTER point dari QR
        # Ubah menjadi TOP-LEFT corner
        align = qr_config.get('align', 'center').lower()
        if align == 'center':
            paste_x = center_x - qr_size // 2
            paste_y = center_y - qr_size // 2
        elif align == 'top-left':
            paste_x = center_x
            paste_y = center_y
        elif align == 'top-right':
            paste_x = center_x - qr_size
            paste_y = center_y
        elif align == 'bottom-left':
            paste_x = center_x
            paste_y = center_y - qr_size
        elif align == 'bottom-right':
            paste_x = center_x - qr_size
            paste_y = center_y - qr_size
        else:
            paste_x = center_x - qr_size // 2
            paste_y = center_y - qr_size // 2
        
        # Ensure posisi tidak negative dan tidak out of bounds
        paste_x = max(0, min(paste_x, design_width - qr_size))
        paste_y = max(0, min(paste_y, design_height - qr_size))
        
        return paste_x, paste_y, qr_size

    def create_member_card_with_design(self, nama, nis, kamar, qr_path):
        """
        Membuat kartu anggota dengan menggabungkan desain dari assets dengan QR code.
        Hardcoded position: x=0.32 (32% dari kiri), y=0.35 (35% dari atas), size=25% dari lebar
        Nama file kartu sesuai QR code saja (nis = barcode)
        """
        from pathlib import Path
        import traceback
        
        print(f"\n[DEBUG] =============== create_member_card_with_design DIPANGGIL ===============")
        print(f"[DEBUG] Params: nama={nama}, nis={nis}, kamar={kamar}, qr_path={qr_path}")
        
        # Log ke file agar bisa di-debug
        log_file = "card_creation.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"[{datetime.now()}] BUAT KARTU: {nis}\n")
            f.write(f"  nama={nama}, kamar={kamar}, qr_path={qr_path}\n")
            f.write(f"{'='*60}\n")
        
        print(f"[DEBUG] Starting card creation...")
        
        try:
            # Setup folder
            cards_dir = "cards"
            os.makedirs(cards_dir, exist_ok=True)
            msg = f"[OK] Output folder: {cards_dir}"
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Cari desain
            design_path = "assets/depan.jpg"
            if not os.path.exists(design_path):
                msg = f"[ERROR] Design tidak ada: {design_path}"
                print(f"[DEBUG] {msg}")
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
                print(f"[DEBUG] =============== create_member_card_with_design SELESAI (GAGAL) ===============\n")
                return None
            
            msg = f"[OK] Design: {design_path}"
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Buka design dan QR
            msg = f"  Membuka design image..."
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            design_img = Image.open(design_path)
            design_width, design_height = design_img.size
            msg = f"[OK] Ukuran design: {design_width}x{design_height}"
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            msg = f"  Checking QR file: {qr_path}"
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
                f.write(f"    Current dir: {os.getcwd()}\n")
                f.write(f"    Absolute QR path: {os.path.abspath(qr_path)}\n")
                f.write(f"    QR exists: {os.path.exists(qr_path)}\n")
            
            if not os.path.exists(qr_path):
                msg = f"[ERROR] QR tidak ada: {qr_path}"
                print(f"[DEBUG] {msg}")
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
                print(f"[DEBUG] =============== create_member_card_with_design SELESAI (GAGAL) ===============\n")
                return None
            
            msg = f"  Membuka QR image..."
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            qr_img = Image.open(qr_path).convert("RGBA")
            msg = f"[OK] QR: {qr_path} (mode: {qr_img.mode})"
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Hitung posisi (hardcoded)
            qr_size = int(design_width * 0.25)  # 25% dari lebar
            paste_x = int(design_width * 0.32) - qr_size // 2  # 32% dari kiri, center
            paste_y = int(design_height * 0.35) - qr_size // 2  # 35% dari atas, center
            
            # Ensure dalam bounds
            paste_x = max(0, min(paste_x, design_width - qr_size))
            paste_y = max(0, min(paste_y, design_height - qr_size))
            
            msg = f"[OK] Posisi: ({paste_x}, {paste_y}), Ukuran: {qr_size}x{qr_size}"
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Resize dan paste QR
            msg = f"  Resizing QR..."
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
            msg = f"  Pasting QR ke design..."
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            design_img.paste(qr_img, (paste_x, paste_y), qr_img)
            msg = f"[OK] QR di-paste"
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Tambahkan barcode text dan QR ID dari database
            try:
                from PIL import ImageDraw, ImageFont
                
                msg = f"  Menambahkan barcode text dan QR ID..."
                print(f"[DEBUG] {msg}")
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
                
                draw = ImageDraw.Draw(design_img)
                
                # Coba pakai font
                try:
                    barcode_font_size = int(design_height * 0.034)
                    barcode_font = ImageFont.truetype("arial.ttf", barcode_font_size)
                    qrid_font_size = int(design_height * 0.032)
                    qrid_font = ImageFont.truetype("arial.ttf", qrid_font_size)
                except:
                    try:
                        barcode_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 10)
                        qrid_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 9)
                    except:
                        barcode_font = ImageFont.load_default()
                        qrid_font = ImageFont.load_default()
                
                # Warna text = #0A2A4F (RGB 10, 42, 79)
                text_color = (10, 42, 79)
                bg_color = (255, 255, 255)  # White background
                
                # 1. BARCODE TEXT (display barcode dari parameter nis)
                barcode_text = nis
                
                # Posisi barcode text di area putih bawah, sebelah kanan
                # Sejajarkan dengan area putih - sejajar kiri dengan "Berlaku sampai 3 tahun"
                barcode_x = int(design_width * 0.70)
                barcode_y = int(design_height * 0.47)
                
                # Define white background area width (sesuaikan dengan area putih)
                white_area_width = int(design_width * 0.35)  # Width area putih
                
                # Center align horizontal
                bbox = draw.textbbox((0, 0), barcode_text, font=barcode_font)
                barcode_text_width = bbox[2] - bbox[0]
                barcode_left_x = barcode_x - barcode_text_width // 2
                
                # Check if text fits in white area, if not reduce font size
                if barcode_text_width > white_area_width - 10:  # 10px padding
                    # Adjust font size
                    while barcode_text_width > white_area_width - 10 and barcode_font_size > 8:
                        barcode_font_size -= 1
                        barcode_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", barcode_font_size)
                        bbox = draw.textbbox((0, 0), barcode_text, font=barcode_font)
                        barcode_text_width = bbox[2] - bbox[0]
                    barcode_left_x = barcode_x - barcode_text_width // 2
                
                # Draw white background for barcode text
                text_height = bbox[3] - bbox[1]
                # Buat background putih dengan sisi kiri sejajar dengan QR ID background
                # QR ID akan memiliki left edge di qrid_left_x - 5
                # Jadi kita tentukan dulu qrid_left_x
                # Barcode text sudah dihitung, sekarang kita buat background-nya
                # Pertama kita perlu tahu posisi QR ID untuk align
                # Untuk sekarang, kita gunakan barcode_left_x - 5 sebagai left edge
                bg_rect_barcode = [barcode_left_x - 5, barcode_y - 5, barcode_left_x + barcode_text_width + 8, barcode_y + text_height + 8]
                draw.rectangle(bg_rect_barcode, fill=bg_color)
                
                # Draw text
                draw.text((barcode_left_x, barcode_y), barcode_text, fill=text_color, font=barcode_font)
                
                msg = f"[OK] Barcode text di-paste: '{barcode_text}' pada ({barcode_left_x}, {barcode_y})"
                print(f"[DEBUG] {msg}")
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
                
                # 2. QR ID (dari database pending_qr_codes)
                qr_id_text = ""
                try:
                    # Query database untuk mendapatkan qr_id dari pending_qr_codes
                    cursor = self.conn.cursor()
                    cursor.execute(
                        "SELECT qr_id FROM pending_qr_codes WHERE barcode = ? LIMIT 1",
                        (nis,)
                    )
                    result = cursor.fetchone()
                    if result:
                        qr_id_text = result[0]
                        msg = f"[OK] QR ID ditemukan di database: '{qr_id_text}'"
                    else:
                        msg = f"[WARN]  QR ID tidak ditemukan di database untuk barcode: {nis}"
                        qr_id_text = "N/A"
                    print(f"[DEBUG] {msg}")
                    with open(log_file, 'a') as f:
                        f.write(msg + "\n")
                except Exception as db_error:
                    msg = f"[WARN]  Error query database QR ID: {str(db_error)}"
                    print(f"[DEBUG] {msg}")
                    with open(log_file, 'a') as f:
                        f.write(msg + "\n")
                    qr_id_text = "ERROR"
                
                # Posisi QR ID di bawah barcode text - sejajarkan sisi kiri dengan barcode text
                qrid_y = barcode_y + int(design_height * 0.075)  # Letakkan di bawah barcode text, sedikit ke atas
                
                if qr_id_text:
                    # Hitung width QR ID text
                    bbox = draw.textbbox((0, 0), qr_id_text, font=qrid_font)
                    qrid_text_width = bbox[2] - bbox[0]
                    
                    # Check if text fits in white area, if not reduce font size
                    if qrid_text_width > white_area_width - 10:  # 10px padding
                        # Adjust font size
                        while qrid_text_width > white_area_width - 10 and qrid_font_size > 8:
                            qrid_font_size -= 1
                            qrid_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", qrid_font_size)
                            bbox = draw.textbbox((0, 0), qr_id_text, font=qrid_font)
                            qrid_text_width = bbox[2] - bbox[0]
                    
                    # Sejajarkan sisi kiri dengan barcode text (barcode_left_x)
                    qrid_left_x = barcode_left_x
                    
                    # Draw white background for QR ID text - dengan padding lebih tinggi (height)
                    text_height = bbox[3] - bbox[1]
                    bg_rect = [qrid_left_x - 5, qrid_y - 5, qrid_left_x + qrid_text_width + 8, qrid_y + text_height + 5]
                    draw.rectangle(bg_rect, fill=bg_color)
                    
                    # Draw text
                    draw.text((qrid_left_x, qrid_y), qr_id_text, fill=text_color, font=qrid_font)
                    
                    msg = f"[OK] QR ID text di-paste: '{qr_id_text}' pada ({qrid_left_x}, {qrid_y})"
                    print(f"[DEBUG] {msg}")
                    with open(log_file, 'a') as f:
                        f.write(msg + "\n")
                
            except Exception as text_error:
                msg = f"[WARN]  Warning - Text gagal ditambahkan: {str(text_error)}"
                print(f"[DEBUG] {msg}")
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
            
            # Simpan dengan nama sesuai QR code saja
            msg = f"  Saving kartu..."
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            card_filename = os.path.join(cards_dir, f"{nis}.jpg")
            design_img.save(card_filename, quality=95)
            msg = f"  File saved to: {card_filename}"
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Verify
            if os.path.exists(card_filename):
                file_size = os.path.getsize(card_filename) / 1024
                msg = f"[SUCCESS] KARTU DIBUAT: {card_filename} ({file_size:.1f} KB)"
                print(f"[DEBUG] {msg}")
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
                print(f"[DEBUG] =============== create_member_card_with_design SELESAI (SUKSES) ===============\n")
                with open(log_file, 'a') as f:
                    f.write(f"{'='*60}\n")
                return card_filename
            else:
                msg = f"[ERROR] File tidak ada setelah save: {card_filename}"
                print(f"[DEBUG] {msg}")
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
                print(f"[DEBUG] =============== create_member_card_with_design SELESAI (GAGAL) ===============\n")
                return None
                
        except Exception as e:
            msg = f"[ERROR] ERROR SAAT MEMBUAT KARTU: {str(e)}"
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            msg = f"  Exception type: {type(e).__name__}"
            print(f"[DEBUG] {msg}")
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            traceback.print_exc()
            with open(log_file, 'a') as f:
                f.write(traceback.format_exc())
            print(f"[DEBUG] =============== create_member_card_with_design SELESAI (ERROR) ===============\n")
            return None
        
        try:
            # Setup folder
            cards_dir = "cards"
            os.makedirs(cards_dir, exist_ok=True)
            msg = f"[OK] Output folder: {cards_dir}"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Cari desain
            design_path = "assets/depan.jpg"
            if not os.path.exists(design_path):
                msg = f"[ERROR] Design tidak ada: {design_path}"
                print(msg)
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
                print(f"{'='*60}\n")
                return None
            
            msg = f"[OK] Design: {design_path}"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Buka design dan QR
            msg = f"  Membuka design image..."
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            design_img = Image.open(design_path)
            design_width, design_height = design_img.size
            msg = f"[OK] Ukuran design: {design_width}x{design_height}"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            msg = f"  Checking QR file: {qr_path}"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
                f.write(f"    Current dir: {os.getcwd()}\n")
                f.write(f"    Absolute QR path: {os.path.abspath(qr_path)}\n")
                f.write(f"    QR exists: {os.path.exists(qr_path)}\n")
            
            if not os.path.exists(qr_path):
                msg = f"[ERROR] QR tidak ada: {qr_path}"
                print(msg)
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
                print(f"{'='*60}\n")
                return None
            
            msg = f"  Membuka QR image..."
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            qr_img = Image.open(qr_path).convert("RGBA")
            msg = f"[OK] QR: {qr_path} (mode: {qr_img.mode})"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Hitung posisi (hardcoded)
            qr_size = int(design_width * 0.25)  # 25% dari lebar
            paste_x = int(design_width * 0.32) - qr_size // 2  # 32% dari kiri, center
            paste_y = int(design_height * 0.35) - qr_size // 2  # 35% dari atas, center
            
            # Ensure dalam bounds
            paste_x = max(0, min(paste_x, design_width - qr_size))
            paste_y = max(0, min(paste_y, design_height - qr_size))
            
            msg = f"[OK] Posisi: ({paste_x}, {paste_y}), Ukuran: {qr_size}x{qr_size}"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Resize dan paste QR
            msg = f"  Resizing QR..."
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
            msg = f"  Pasting QR ke design..."
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            design_img.paste(qr_img, (paste_x, paste_y), qr_img)
            msg = f"[OK] QR di-paste"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Simpan dengan nama sesuai QR code saja
            msg = f"  Saving kartu..."
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            card_filename = os.path.join(cards_dir, f"{nis}.jpg")
            design_img.save(card_filename, quality=95)
            msg = f"  File saved to: {card_filename}"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            
            # Verify
            if os.path.exists(card_filename):
                file_size = os.path.getsize(card_filename) / 1024
                msg = f"[SUCCESS] KARTU DIBUAT: {card_filename} ({file_size:.1f} KB)"
                print(msg)
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
                print(f"{'='*60}\n")
                with open(log_file, 'a') as f:
                    f.write(f"{'='*60}\n")
                return card_filename
            else:
                msg = f"[ERROR] File tidak ada setelah save: {card_filename}"
                print(msg)
                with open(log_file, 'a') as f:
                    f.write(msg + "\n")
                print(f"{'='*60}\n")
                return None
                
        except Exception as e:
            msg = f"[ERROR] ERROR SAAT MEMBUAT KARTU: {str(e)}"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            msg = f"  Exception type: {type(e).__name__}"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
            traceback.print_exc()
            with open(log_file, 'a') as f:
                f.write(traceback.format_exc())
            print(f"{'='*60}\n")
            return None

    def create_member_card(self, nama, nis, kamar, qr_path):
        os.makedirs("cards", exist_ok=True)
        # Nama file menggunakan nama anggota (dengan sanitasi untuk invalid filename characters)
        safe_nama = "".join(c for c in nama if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"cards/{safe_nama}.pdf"

        c = canvas.Canvas(filename, pagesize=A7)
        width, height = A7

        # Background
        c.setFillColorRGB(0.9, 0.95, 1)
        c.rect(0, 0, width, height, fill=True, stroke=False)

        # Title
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(0, 0, 0.3)
        c.drawCentredString(width / 2, height - 20, "KARTU ANGGOTA PERPUSTAKAAN")

        # Data anggota
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(10, height - 45, f"Nama  : {nama}")
        c.drawString(10, height - 60, f"NIS   : {nis}")
        c.drawString(10, height - 75, f"Kamar : {kamar}")

        # QR Code
        if os.path.exists(qr_path):
            c.drawImage(qr_path, width - 70, height - 90, width=50, height=50)

        c.save()
        return filename
    
    def list_members(self):
        """List semua members dengan QR ID dari data member atau QR pending."""
        c = self.conn.cursor()
        c.execute('''SELECT m.id, m.nama, m.rayon, m.kamar, m.barcode,
                            COALESCE(m.qr_id, p.qr_id) AS qr_id
                     FROM members m
                     LEFT JOIN pending_qr_codes p ON m.barcode=p.barcode
                     ORDER BY m.id DESC''')
        return c.fetchall()

    def get_member_by_name(self, nama):
        """Get member info berdasarkan nama"""
        c = self.conn.cursor()
        c.execute('''SELECT id, nama, rayon, kamar, nis, alamat, barcode, jenis_santri, qr_id
                     FROM members WHERE nama=?''', (nama,))
        return c.fetchone()

    # =============== SISTEM GENERASI QR MASSAL ===============
    def generate_qr_id(self):
        """Generate QR ID dengan format: YYYYMMDD/A Latee Library/XXXX
        Dimana:
        - YYYYMMDD = tanggal pembuatan
        - A Latee Library = nama instansi
        - XXXX = counter continuous (tidak reset per hari)
        Contoh: 20260117/A Latee Library/0001, 20260118/A Latee Library/0002
        
        Returns:
            str: QR ID dengan format YYYYMMDD/A Latee Library/XXXX
        """
        today = datetime.now().strftime("%Y%m%d")
        institution = "A Latee Library"
        
        # Ambil counter terakhir dari database (tertinggi)
        c = self.conn.cursor()
        c.execute('''SELECT qr_id FROM (
                         SELECT qr_id FROM pending_qr_codes
                         UNION ALL
                         SELECT qr_id FROM members
                     )
                     WHERE qr_id LIKE "%/A Latee Library/%"
                     ORDER BY qr_id DESC LIMIT 1''')
        last_qr = c.fetchone()
        
        if last_qr:
            # Parse counter dari QR ID terakhir
            # Format: YYYYMMDD/A Latee Library/XXXX
            last_qr_id = last_qr[0]
            try:
                last_counter = int(last_qr_id.split('/')[-1])
                next_counter = last_counter + 1
            except (IndexError, ValueError):
                next_counter = 1
        else:
            next_counter = 1
        
        # Format baru: YYYYMMDD/A Latee Library/XXXX
        qr_id = f"{today}/{institution}/{next_counter:04d}"
        
        return qr_id
    
    def add_pending_qr(self, barcode, qr_id=None):
        """Simpan QR code ke pending_qr_codes dengan status 'pending'
        
        Args:
            barcode: UUID/barcode untuk QR code
            qr_id: Custom QR ID (opsional, akan auto-generate jika None)
        """
        if qr_id is None:
            qr_id = self.generate_qr_id()
        
        c = self.conn.cursor()
        c.execute('INSERT INTO pending_qr_codes(qr_id, barcode, status, created_at) VALUES(?,?,?,?)',
                  (qr_id, barcode, 'pending', datetime.now().isoformat()))
        self.conn.commit()
        return c.lastrowid
    
    def list_pending_qr_codes(self):
        """List semua pending QR codes (belum di-link ke anggota)"""
        c = self.conn.cursor()
        c.execute('''SELECT p.id, p.qr_id, p.barcode, p.status, p.created_at, m.nama, m.kamar, m.rayon
                     FROM pending_qr_codes p
                     LEFT JOIN members m ON p.member_id=m.id
                     WHERE p.status='pending' OR (p.status='linked' AND m.id IS NOT NULL)
                     ORDER BY p.created_at DESC''')
        return c.fetchall()
    
    def create_member_from_qr(self, barcode, nama, kamar, rayon=None, nis=None, tempat=None, tgl_lahir=None, alamat=None):
        """Buat member baru dari pending QR code"""
        c = self.conn.cursor()
        
        # Insert member baru
        c.execute('INSERT INTO members(nama, kamar, barcode, rayon) VALUES(?,?,?,?)',
                  (nama, kamar, barcode, rayon))
        member_id = c.lastrowid
        
        # Update pending QR code status to 'active' (QR sudah diinputkan ke sistem)
        c.execute('UPDATE pending_qr_codes SET member_id=?, status=?, linked_at=? WHERE barcode=?',
                  (member_id, 'active', datetime.now().isoformat(), barcode))
        
        self.conn.commit()
        return member_id
    
    def update_member(self, member_id, nama=None, kamar=None, rayon=None):
        """Update data anggota yang sudah terdaftar"""
        c = self.conn.cursor()
        
        # Prepare update fields
        fields = []
        values = []
        
        if nama is not None:
            fields.append("nama=?")
            values.append(nama)
        if kamar is not None:
            fields.append("kamar=?")
            values.append(kamar)
        if rayon is not None:
            fields.append("rayon=?")
            values.append(rayon)
        
        if not fields:
            return False
        
        values.append(member_id)
        query = f"UPDATE members SET {', '.join(fields)} WHERE id=?"
        c.execute(query, values)
        self.conn.commit()
        
        return c.rowcount > 0
    
    def get_pending_qr_by_barcode(self, barcode):
        """Get pending QR code details"""
        c = self.conn.cursor()
        c.execute('SELECT * FROM pending_qr_codes WHERE barcode=?', (barcode,))
        return c.fetchone()
    
    def delete_pending_qr(self, barcode):
        """Delete pending QR code (jika belum di-link)"""
        c = self.conn.cursor()
        c.execute('DELETE FROM pending_qr_codes WHERE barcode=? AND status=?', (barcode, 'pending'))
        self.conn.commit()
        return c.rowcount > 0
    
    def mark_qr_as_printed(self, barcode):
        """Tandai QR sebagai sudah dicetak"""
        c = self.conn.cursor()
        c.execute('UPDATE pending_qr_codes SET printed_at=? WHERE barcode=?',
                  (datetime.now().isoformat(), barcode))
        self.conn.commit()
    
    def activate_qr(self, barcode):
        """Aktifkan QR untuk digunakan (setelah kartu dicetak dan data diinput)"""
        c = self.conn.cursor()
        c.execute('UPDATE pending_qr_codes SET status=? WHERE barcode=? AND printed_at IS NOT NULL',
                  ('active', barcode))
        self.conn.commit()
        return c.rowcount > 0
    
    def block_qr(self, barcode):
        """Blokir QR jika kartu hilang/rusak"""
        c = self.conn.cursor()
        c.execute('UPDATE pending_qr_codes SET is_blocked=1 WHERE barcode=?', (barcode,))
        self.conn.commit()
    
    def unblock_qr(self, barcode):
        """Unblock QR yang sudah diblokir"""
        c = self.conn.cursor()
        c.execute('UPDATE pending_qr_codes SET is_blocked=0 WHERE barcode=?', (barcode,))
        self.conn.commit()
    
    def get_qr_status(self, barcode):
        """Get status QR code lengkap"""
        c = self.conn.cursor()
        c.execute('SELECT * FROM pending_qr_codes WHERE barcode=?', (barcode,))
        return c.fetchone()

    def is_qr_expired(self, barcode):
        """
        Check if QR code sudah expired (lebih dari 3 tahun dari tanggal created_at)
        Returns: (is_expired, message)
        """
        c = self.conn.cursor()
        c.execute('SELECT created_at FROM pending_qr_codes WHERE barcode=?', (barcode,))
        result = c.fetchone()
        
        if not result:
            return False, "QR tidak ditemukan"
        
        created_at_str = result[0]  # Format: ISO format dengan T (e.g., 2026-01-17T08:01:08.659191)
        
        try:
            # Parse created_at dari database - handle ISO format dengan atau tanpa microseconds
            try:
                # Try ISO format with microseconds
                if '.' in created_at_str:
                    created_at = datetime.strptime(created_at_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                else:
                    created_at = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                # Fallback ke format lama YYYY-MM-DD HH:MM:SS
                created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
            
            current_date = datetime.now()
            
            # Hitung 3 tahun dari created_at
            expiry_date = created_at + timedelta(days=3*365)  # 3 tahun
            
            if current_date > expiry_date:
                return True, f"QR ini sudah expired sejak {expiry_date.strftime('%d-%m-%Y')}"
            else:
                return False, f"QR masih berlaku hingga {expiry_date.strftime('%d-%m-%Y')}"
        except Exception as e:
            return False, f"Error checking expiry: {str(e)}"

    # ------------------- Users (Authentication) -----------------
    def normalize_role(self, role):
        """Normalisasi role user agar konsisten di database dan UI."""
        normalized_role = (role or 'pustakawan').strip().lower()
        if normalized_role in {'administrator', 'admin'}:
            return 'administrator'
        if normalized_role == 'porseni':
            return 'porseni'
        return 'pustakawan'

    def add_user(self, username, password, full_name=None, avatar_path=None, role='pustakawan', jabatan=None):
        """Tambah pustakawan baru (username unik). Password disimpan sebagai SHA256 hash."""
        # basic checks
        if not username or not password:
            raise ValueError("Username dan password wajib diisi")

        # enforce maximum users (15)
        c = self.conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        existing_count = c.fetchone()[0]
        if existing_count >= 15:
            raise ValueError("Batas akun pustakawan telah tercapai (maks 15 akun).")

        # check username exists
        existing = self.get_user_by_username(username)
        if existing:
            raise ValueError("Username sudah terdaftar")

        # check full_name duplication (if provided)
        if full_name:
            c = self.conn.cursor()
            c.execute('SELECT id FROM users WHERE LOWER(full_name)=LOWER(?)', (full_name,))
            if c.fetchone():
                raise ValueError("Nama lengkap tersebut sudah memiliki akun")

        normalized_role = self.normalize_role(role)
        if jabatan is None:
            jabatan = map_role_to_jabatan(normalized_role)

        pw_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        c = self.conn.cursor()
        c.execute('INSERT INTO users(username,password_hash,full_name,avatar_path,role,jabatan,barcode) VALUES(?,?,?,?,?,?,?)',
              (username, pw_hash, full_name, avatar_path, normalized_role, jabatan, None))
        user_id = c.lastrowid
        c.execute('UPDATE users SET barcode=? WHERE id=?', (f"PUST-{user_id:06d}", user_id))
        self.conn.commit()
        return user_id

    def authenticate_user(self, username, password):
        """Periksa username/password. Kembalikan row user atau None."""
        pw_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        c = self.conn.cursor()
        c.execute('SELECT id, username, full_name, avatar_path, role, jabatan, barcode FROM users WHERE username=? AND password_hash=?', (username, pw_hash))
        row = c.fetchone()
        if row:
            normalized_role = self.normalize_role(row[4])
            if (row[1] or '').lower() == 'admin' or (row[2] or '').lower() == 'administrator':
                normalized_role = 'administrator'
            return {
                'id': row[0],
                'username': row[1],
                'full_name': row[2],
                'avatar_path': row[3],
                'role': normalized_role,
                'jabatan': row[5] or '',
                'barcode': row[6] or f"PUST-{row[0]:06d}"
            }
        return None

    def get_user_by_username(self, username):
        c = self.conn.cursor()
        c.execute('SELECT id, username, full_name, avatar_path, role, jabatan, barcode FROM users WHERE username=?', (username,))
        row = c.fetchone()
        if row:
            normalized_role = self.normalize_role(row[4])
            if (row[1] or '').lower() == 'admin' or (row[2] or '').lower() == 'administrator':
                normalized_role = 'administrator'
            return {
                'id': row[0],
                'username': row[1],
                'full_name': row[2],
                'avatar_path': row[3],
                'role': normalized_role,
                'jabatan': row[5] or '',
                'barcode': row[6] or f"PUST-{row[0]:06d}"
            }
        return None

    def get_user_by_barcode(self, barcode):
        """Ambil akun pustakawan berdasarkan data QR pada kartu."""
        c = self.conn.cursor()
        c.execute('SELECT id, username, full_name, avatar_path, role, jabatan, barcode FROM users WHERE barcode=?', (barcode.strip(),))
        row = c.fetchone()
        if not row:
            return None
        normalized_role = self.normalize_role(row[4])
        if (row[1] or '').lower() == 'admin' or (row[2] or '').lower() == 'administrator':
            normalized_role = 'administrator'
        return {
            'id': row[0],
            'username': row[1],
            'full_name': row[2],
            'avatar_path': row[3],
            'role': normalized_role,
            'jabatan': row[5] or '',
            'barcode': row[6] or f"PUST-{row[0]:06d}"
        }

    def list_users(self):
        c = self.conn.cursor()
        c.execute('SELECT id, username, full_name, avatar_path, role, jabatan, barcode FROM users ORDER BY id')
        return c.fetchall()

    def update_user_password(self, username, new_password):
        """Update password for a user identified by username."""
        pw_hash = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
        c = self.conn.cursor()
        c.execute('UPDATE users SET password_hash=? WHERE username=?', (pw_hash, username))
        self.conn.commit()
        return c.rowcount

    def update_user(self, user_id, username=None, full_name=None, role=None, password=None, jabatan=None):
        """Update data pengguna."""
        c = self.conn.cursor()
        fields = []
        values = []

        if username is not None:
            fields.append('username=?')
            values.append(username)
        if full_name is not None:
            fields.append('full_name=?')
            values.append(full_name)
        if role is not None:
            normalized_role = self.normalize_role(role)
            fields.append('role=?')
            values.append(normalized_role)
        if jabatan is not None:
            fields.append('jabatan=?')
            values.append(jabatan)
        if password is not None:
            fields.append('password_hash=?')
            values.append(hashlib.sha256(password.encode('utf-8')).hexdigest())

        if not fields:
            return 0

        values.append(user_id)
        c.execute(f'UPDATE users SET {", ".join(fields)} WHERE id=?', values)
        self.conn.commit()
        return c.rowcount

    def delete_user(self, user_id):
        c = self.conn.cursor()
        c.execute('DELETE FROM users WHERE id=?', (user_id,))
        self.conn.commit()
        return c.rowcount

    def update_member(self, id_, data):
        c = self.conn.cursor()
        c.execute('UPDATE members SET nis=?, nama=?, kamar=?, alamat=?, barcode=? WHERE id=?',
                  (*data, id_))
        self.conn.commit()

    def delete_member(self, id_):
        self.conn.execute('DELETE FROM members WHERE id=?', (id_,))
        self.conn.commit()

    # ------------------- Pinjam / Kembali -------------
    def borrow_book(self, book_id, member_id=None, dibuat_oleh=None):
        c = self.conn.cursor()
        try:
            if member_id is not None:
                c.execute(
                    "SELECT COUNT(*) FROM borrows WHERE member_id=? AND status=0",
                    (member_id,)
                )
                active_borrows = c.fetchone()[0]
                if active_borrows >= 2:
                    raise ValueError("Anggota sudah mencapai batas maksimal 2 buku aktif")

                unpaid_fines = self.get_member_unpaid_fines(member_id)
                if unpaid_fines > 0:
                    raise ValueError(
                        f"Anggota masih memiliki denda belum dibayar sebesar Rp {unpaid_fines:,}"
                    )

            c.execute("SELECT stok FROM books WHERE id=?", (book_id,))
            book = c.fetchone()
            if not book or book[0] <= 0:
                raise ValueError("Stok buku tidak tersedia")

            c.execute('INSERT INTO borrows(book_id,member_id,tanggal_pinjam,status,dibuat_oleh) VALUES(?,?,?,?,?)',
                      (book_id, member_id, datetime.now().isoformat(), 0, dibuat_oleh))
            # Kurangi stok, tingkatkan jumlah_dipinjam dan set status = 'dipinjam'
            self.conn.execute('UPDATE books SET stok=stok-1, jumlah_dipinjam=jumlah_dipinjam+1, status=? WHERE id=?', ('dipinjam', book_id))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def calculate_fine(self, tanggal_pinjam, diperpanjang=0):
        """Hitung denda untuk pengembalian terlambat
        
        Args:
            tanggal_pinjam (str): Tanggal pinjam dalam format ISO
            
        Returns:
            tuple: (hari_terlambat, jumlah_denda)
            - Jika tidak terlambat: (0, 0)
            - Jika terlambat: (jumlah_hari, jumlah_hari * 1000)
        """
        try:
            pinjam_dt = datetime.fromisoformat(tanggal_pinjam)
            batas_dt = self.borrow_deadline(tanggal_pinjam, diperpanjang)
            hari_ini = datetime.now()
            
            # Hitung hari terlambat (hanya jika melebihi batas)
            if hari_ini > batas_dt:
                selisih = hari_ini - batas_dt
                hari_terlambat = selisih.days + (1 if selisih.seconds > 0 else 0)
                denda = hari_terlambat * 1000
                return hari_terlambat, denda
            else:
                return 0, 0
        except:
            return 0, 0

    def return_book(self, book_id, dikembalikan_oleh=None, member_id=None):
        """Mark a borrow record as returned and update book stock.

        Returns the calculated fine (denda) as integer.
        Raises ValueError if there's no active borrow record for the book.
        """
        c = self.conn.cursor()
        # Cari peminjaman aktif untuk buku ini
        query = "SELECT id, tanggal_pinjam, diperpanjang FROM borrows WHERE book_id=? AND status=0"
        params = [book_id]
        if member_id is not None:
            query += " AND member_id=?"
            params.append(member_id)
        query += " ORDER BY id DESC LIMIT 1"
        c.execute(query, params)
        row = c.fetchone()
        if not row:
            raise ValueError("Tidak ada catatan peminjaman aktif untuk buku ini")

        borrow_id, tanggal_pinjam, diperpanjang = row

        # Hitung denda berdasarkan tanggal_pinjam
        hari_terlambat, denda = self.calculate_fine(tanggal_pinjam, diperpanjang)

        # Update record peminjaman
        now_iso = datetime.now().isoformat()
        c.execute("UPDATE borrows SET tanggal_kembali=?, status=1, denda=?, dikembalikan_oleh=?, denda_dibuat_oleh=? WHERE id=?",
              (now_iso, denda, dikembalikan_oleh, dikembalikan_oleh if denda > 0 else None, borrow_id))

        # Update stok buku dan jumlah_dipinjam
        c.execute("UPDATE books SET stok=stok+1, jumlah_dipinjam=CASE WHEN jumlah_dipinjam>0 THEN jumlah_dipinjam-1 ELSE 0 END WHERE id=?", (book_id,))

        # Pastikan status buku kembali ke 'ada' jika stok > 0
        c.execute("SELECT stok FROM books WHERE id=?", (book_id,))
        stok_row = c.fetchone()
        if stok_row:
            stok_val = stok_row[0]
            status = 'ada' if stok_val > 0 else 'tidak tersedia'
            c.execute("UPDATE books SET status=? WHERE id=?", (status, book_id))

        self.conn.commit()
        return denda

    def get_unpaid_fines(self):
        """Get semua denda yang belum dibayar (status=1 dan denda>0)"""
        c = self.conn.cursor()
        c.execute('''SELECT b.id, m.nama, m.rayon, m.kamar, b.denda, bk.judul, b.tanggal_pinjam, b.tanggal_kembali, b.member_id
                     FROM borrows b
                     LEFT JOIN members m ON b.member_id = m.id
                     LEFT JOIN books bk ON b.book_id = bk.id
                     WHERE b.status=1 AND b.denda > 0
                     ORDER BY b.tanggal_kembali DESC''')
        result = c.fetchall()
        print(f"DEBUG get_unpaid_fines: returned {len(result) if result else 0} rows")
        return result

    def get_member_unpaid_fines(self, member_id):
        """Get total denda belum dibayar untuk member tertentu"""
        c = self.conn.cursor()
        c.execute('SELECT COALESCE(SUM(denda), 0) FROM borrows WHERE member_id=? AND status=1 AND denda > 0', (member_id,))
        row = c.fetchone()
        return row[0] if row else 0

    def get_member_active_borrow_count(self, member_id):
        """Get number of books currently borrowed by a member."""
        c = self.conn.cursor()
        c.execute(
            'SELECT COUNT(*) FROM borrows WHERE member_id=? AND status=0',
            (member_id,)
        )
        return c.fetchone()[0]

    def get_paid_fines(self):
        """Get denda yang sudah dibayar, bukan pengembalian tepat waktu."""
        c = self.conn.cursor()
        c.execute('''SELECT b.id, m.nama, m.rayon, m.kamar, b.denda, bk.judul, b.tanggal_pinjam, b.tanggal_kembali, b.member_id
                     FROM borrows b
                     LEFT JOIN members m ON b.member_id = m.id
                     LEFT JOIN books bk ON b.book_id = bk.id
                     WHERE b.status=1 AND b.denda=0 AND b.denda_dibayar_oleh IS NOT NULL
                     ORDER BY b.tanggal_kembali DESC''')
        result = c.fetchall()
        print(f"DEBUG get_paid_fines: returned {len(result) if result else 0} rows")
        return result

    def mark_fine_as_paid(self, borrow_id, dibayar_oleh=None):
        """Tandai denda sebagai sudah dibayar (set denda=0)"""
        c = self.conn.cursor()
        c.execute('UPDATE borrows SET denda=0, denda_dibayar_oleh=? WHERE id=?', (dibayar_oleh, borrow_id))
        self.conn.commit()

    def get_transaction_audit(self, borrow_id):
        c = self.conn.cursor()
        c.execute('''SELECT dibuat_oleh, dikembalikan_oleh, denda_dibuat_oleh, denda_dibayar_oleh
                     FROM borrows WHERE id=?''', (borrow_id,))
        return c.fetchone() or (None, None, None, None)

    def search_borrows(self, keyword):
        """Cari peminjaman berdasarkan nama peminjam atau judul buku"""
        c = self.conn.cursor()
        like_keyword = f"%{keyword}%"
        c.execute('''SELECT b.id, bk.judul, m.nama, b.tanggal_pinjam, b.diperpanjang
                     FROM borrows b
                     LEFT JOIN books bk ON b.book_id=bk.id
                     LEFT JOIN members m ON b.member_id=m.id
                     WHERE b.status=0 AND (m.nama LIKE ? OR bk.judul LIKE ?)''',
                  (like_keyword, like_keyword))
        return c.fetchall()

    def completed_borrows(self):
        """Tampilkan peminjaman yang sudah selesai/dikembalikan (status=1)"""
        c = self.conn.cursor()
        c.execute('''SELECT b.id, bk.judul, m.nama, m.rayon, m.kamar, b.tanggal_pinjam, b.tanggal_kembali
                     FROM borrows b
                     LEFT JOIN books bk ON b.book_id=bk.id
                     LEFT JOIN members m ON b.member_id=m.id
                     WHERE b.status=1
                     ORDER BY b.tanggal_kembali DESC
                     LIMIT 100''')
        return c.fetchall()

    def search_completed_borrows(self, keyword):
        """Cari peminjaman selesai berdasarkan nama peminjam atau judul buku"""
        c = self.conn.cursor()
        like_keyword = f"%{keyword}%"
        c.execute('''SELECT b.id, bk.judul, m.nama, m.rayon, m.kamar,
                    b.tanggal_pinjam, b.tanggal_kembali
                     FROM borrows b
                     LEFT JOIN books bk ON b.book_id=bk.id
                     LEFT JOIN members m ON b.member_id=m.id
                     WHERE b.status=1 AND (m.nama LIKE ? OR bk.judul LIKE ?)
                     ORDER BY b.tanggal_kembali DESC
                     LIMIT 100''',
                  (like_keyword, like_keyword))
        return c.fetchall()

    def active_borrows(self):
        """Query data peminjaman aktif untuk ditampilkan di tab pengembalian dengan status terlambat/diperpanjang"""
        c = self.conn.cursor()
        c.execute('''SELECT b.id, bk.judul, m.nama, m.rayon, m.kamar, b.tanggal_pinjam, b.diperpanjang
                     FROM borrows b
                     LEFT JOIN books bk ON b.book_id=bk.id
                     LEFT JOIN members m ON b.member_id=m.id
                     WHERE b.status=0
                     ORDER BY b.tanggal_pinjam ASC''')
        return c.fetchall()

    def borrow_deadline(self, tanggal_pinjam, diperpanjang=0, tanggal_perpanjangan=None):
        """Hitung batas pengembalian, dengan hari pinjam sebagai hari pertama."""
        pinjam_dt = datetime.fromisoformat(tanggal_pinjam)
        deadline = pinjam_dt + timedelta(days=3)
        if diperpanjang:
            # Empat hari inklusif dimulai dari tanggal batas lama: 26-29.
            deadline += timedelta(days=3)
        return deadline

    def extend_borrow(self, borrow_id, days=4):
        """Tandai peminjaman sebagai diperpanjang dengan periode inklusif."""
        if days < 1:
            raise ValueError("Jumlah hari perpanjangan harus lebih dari 0")
        c = self.conn.cursor()
        c.execute('SELECT status, diperpanjang FROM borrows WHERE id=?', (borrow_id,))
        row = c.fetchone()
        if not row:
            raise ValueError("Peminjaman tidak ditemukan")
        if row[0] != 0:
            raise ValueError("Peminjaman sudah dikembalikan")
        if row[1]:
            raise ValueError("Peminjaman sudah diperpanjang")
        c.execute('UPDATE borrows SET diperpanjang=1 WHERE id=?', (borrow_id,))
        self.conn.commit()

    def search_returns(self, keyword):
        """Cari data pengembalian berdasarkan nama peminjam atau judul buku"""
        c = self.conn.cursor()
        like_keyword = f"%{keyword}%"
        c.execute('''SELECT b.id, bk.judul, m.nama, m.rayon, m.kamar, b.tanggal_pinjam, b.diperpanjang
                     FROM borrows b
                     LEFT JOIN books bk ON b.book_id=bk.id
                     LEFT JOIN members m ON b.member_id=m.id
                     WHERE b.status=0 AND (m.nama LIKE ? OR bk.judul LIKE ?)
                     ORDER BY b.tanggal_pinjam ASC''',
                  (like_keyword, like_keyword))
        return c.fetchall()

    # ------------------- Pengunjung ------------------
    def add_visitor(self, nama, kamar, rayon, fingerprint_id):
        waktu_kunjungan = datetime.now().isoformat()
        c = self.conn.cursor()
        c.execute('INSERT INTO visitors(nama,kamar,rayon,fingerprint_id,waktu_kunjungan) VALUES(?,?,?,?,?)',
                  (nama, kamar, rayon, fingerprint_id, waktu_kunjungan))
        visitor_id = c.lastrowid
        c.execute(
            'INSERT INTO visitor_visits(visitor_id, waktu_kunjungan) VALUES(?,?)',
            (visitor_id, waktu_kunjungan)
        )
        self.conn.commit()
        return visitor_id

    def update_visitor(self, visitor_id, nama, rayon, kamar):
        """Update data pengunjung terdaftar tanpa mengubah riwayat kunjungannya."""
        c = self.conn.cursor()
        c.execute(
            'UPDATE visitors SET nama=?, rayon=?, kamar=? WHERE id=?',
            (nama, rayon, kamar, visitor_id)
        )
        self.conn.commit()
        return c.rowcount > 0

    def delete_visitor_visit(self, visit_id):
        """Hapus satu catatan kunjungan dan sinkronkan waktu kunjungan terakhir."""
        c = self.conn.cursor()
        try:
            c.execute(
                'SELECT visitor_id FROM visitor_visits WHERE id=?',
                (visit_id,)
            )
            row = c.fetchone()
            if not row:
                return False

            visitor_id = row[0]
            c.execute('DELETE FROM visitor_visits WHERE id=?', (visit_id,))
            deleted = c.rowcount > 0
            c.execute(
                'UPDATE visitors SET waktu_kunjungan=('
                'SELECT MAX(waktu_kunjungan) FROM visitor_visits WHERE visitor_id=?'
                ') WHERE id=?',
                (visitor_id, visitor_id)
            )
            self.conn.commit()
            return deleted
        except Exception:
            self.conn.rollback()
            raise

    def save_fingerprint_enrollment(self, santri_id, nama, template_bytes, rayon, kamar, quality=80):
        """
        Save enrolled fingerprint template from the ZKTeco reader.
        
        Fingerprint matching is handled by the ZKTeco SDK cache.
        
        Args:
            santri_id: Unique fingerprint identifier assigned by the application
            nama: Student name
            template_bytes: Fingerprint template bytes from the SDK
            rayon: Student dormitory
            kamar: Room number
            quality: Just for logging, not validation
            
        Returns:
            (success: bool, message: str)
        """
        try:
            import hashlib
            
            # Template has already been validated by the SDK capture operation.
            if not isinstance(template_bytes, bytes) or len(template_bytes) < 100:
                print(f"[DB] [FAIL] Invalid template bytes")
                return False, "Template tidak valid"
            
            # Calculate hash for audit trail only
            template_hash = hashlib.sha256(template_bytes).hexdigest()
            
            # Store the SDK template for future application startup loads.
            c = self.conn.cursor()
            
            # Check if santri_id already exist (prevent duplicate IDs)
            c.execute("SELECT nama FROM santri_fingerprints WHERE santri_id = ?", (santri_id,))
            existing = c.fetchone()
            
            if existing:
                # Update existing record
                print(f"[DB] [UPDATE] Updating existing santri_id {santri_id}")
                c.execute('''UPDATE santri_fingerprints
                            SET nama = ?, template_data = ?, template_hash = ?, timestamp = ?, rayon = ?, kamar = ?
                            WHERE santri_id = ?''',
                         (nama, template_bytes, template_hash, datetime.now().isoformat(), rayon, kamar, santri_id))
            else:
                # Insert new record
                c.execute('''INSERT INTO santri_fingerprints
                            (santri_id, nama, template_data, template_hash, quality, timestamp, rayon, kamar, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (santri_id, nama, template_bytes, template_hash, quality, datetime.now().isoformat(), rayon, kamar, 'active'))
            
            self.conn.commit()
            print(f"[DB] [OK] Sidik jari {nama} (ID:{santri_id}) tersimpan - {len(template_bytes)} bytes")
            return True, f"Sidik jari {nama} berhasil terekam"
            
        except Exception as e:
            print(f"[DB] [FAIL] Error saving fingerprint: {e}")
            return False, f"Error: {e}"
    
    def check_fingerprint_duplicate(self, template_bytes, match_threshold=0.95):
        """
        Check if similar fingerprint already exists in database
        
        Uses 2-layer approach:
        1. FAST: EXACT hash match (SHA256) - catches identical scans
        2. FUZZY: Hamming distance - catches similar but slightly different scans
        
        Args:
            template_bytes: Template to check
            match_threshold: Similarity threshold (0.0-1.0), default 0.95 = 95% match
            
        Returns:
            (found, existing_info) where found=True if duplicate found
            existing_info = {'santri_id': id, 'nama': name, 'rayon': rayon, 'similarity': 0.0-1.0, 'match_type': 'exact' or 'fuzzy'}
        """
        if not isinstance(template_bytes, bytes) or len(template_bytes) < 100:
            return False, None
        
        try:
            import hashlib
            new_hash = hashlib.sha256(template_bytes).hexdigest()
            
            c = self.conn.cursor()
            
            # ========== LAYER 1: EXACT HASH MATCH ==========
            # Fastest check - exact same fingerprint
            c.execute("""
                SELECT santri_id, nama, rayon, template_hash 
                FROM santri_fingerprints 
                WHERE template_hash = ? AND status='active'
            """, (new_hash,))
            exact_match = c.fetchone()
            
            if exact_match:
                santri_id, nama, rayon, _ = exact_match
                print(f"[DB] [WARN] EXACT DUPLICATE: {nama} (Santri {santri_id})")
                return True, {
                    'santri_id': santri_id,
                    'nama': nama,
                    'rayon': rayon,
                    'similarity': 1.0,
                    'match_type': 'exact'
                }
            
            # ========== LAYER 2: FUZZY MATCH (HAMMING DISTANCE) ==========
            # Secondary check - similar but slightly different scans
            c.execute("""
                SELECT santri_id, nama, template_data, rayon 
                FROM santri_fingerprints 
                WHERE status='active'
            """)
            rows = c.fetchall()
            
            for santri_id, nama, stored_template, rayon in rows:
                try:
                    if isinstance(stored_template, bytes):
                        db_template = stored_template
                    else:
                        db_template = bytes.fromhex(str(stored_template))
                    
                    # Calculate similarity using hamming distance
                    if len(db_template) == len(template_bytes):
                        # Hamming distance
                        distance = sum(bin(a ^ b).count('1') for a, b in zip(template_bytes, db_template))
                        max_distance = len(template_bytes) * 8
                        similarity = 1.0 - (distance / max_distance)
                        
                        if similarity >= match_threshold:
                            print(f"[DB] [WARN] FUZZY DUPLICATE: {nama} (Santri {santri_id}) - Similarity: {similarity:.1%}")
                            return True, {
                                'santri_id': santri_id,
                                'nama': nama,
                                'rayon': rayon,
                                'similarity': similarity,
                                'match_type': 'fuzzy'
                            }
                except Exception as e:
                    print(f"[DB] [WARN] Error checking fuzzy match for santri {santri_id}: {e}")
                    continue
            
            # No duplicate found
            return False, None
            
        except Exception as e:
            print(f"[DB] [FAIL] Error checking fingerprint duplicate: {e}")
            return False, None

    def add_visitor_visit(self, visitor_id, waktu_kunjungan=None):
        """Add a visit history entry for an existing visitor."""
        if waktu_kunjungan is None:
            waktu_kunjungan = datetime.now().isoformat()
        
        c = self.conn.cursor()
        c.execute(
            'INSERT INTO visitor_visits(visitor_id, waktu_kunjungan) VALUES(?,?)',
            (visitor_id, waktu_kunjungan)
        )
        c.execute('UPDATE visitors SET waktu_kunjungan=? WHERE id=?',
                  (waktu_kunjungan, visitor_id))
        self.conn.commit()

    def get_visitor_by_fingerprint(self, fid):
        c = self.conn.cursor()
        c.execute('''SELECT id, nama, rayon, kamar, fingerprint_id, waktu_kunjungan
                     FROM visitors WHERE fingerprint_id=? ORDER BY id DESC LIMIT 1''', (fid,))
        return c.fetchone()

    def visitors_per_month(self, year):
        c = self.conn.cursor()
        c.execute('SELECT waktu_kunjungan FROM visitor_visits')
        data = c.fetchall()
        monthly = defaultdict(int)
        for (w,) in data:
            d = datetime.fromisoformat(w)
            if d.year == year:
                monthly[d.month] += 1
        return monthly

    def borrows_per_month(self, year):
        c = self.conn.cursor()
        c.execute('SELECT tanggal_pinjam FROM borrows')
        data = c.fetchall()
        monthly = defaultdict(int)
        for (w,) in data:
            d = datetime.fromisoformat(w)
            if d.year == year:
                monthly[d.month] += 1
        return monthly

    # ------------------- Statistik Dashboard ----------
    def count_books(self):
        return self.conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]

    def count_members(self):
        return self.conn.execute('SELECT COUNT(*) FROM members').fetchone()[0]

    def count_active_borrows(self):
        return self.conn.execute('SELECT COUNT(*) FROM borrows WHERE status=0').fetchone()[0]

    def count_visitors_today(self):
        today = datetime.now().date().isoformat()
        return self.conn.execute(
            'SELECT COUNT(*) FROM visitor_visits WHERE DATE(waktu_kunjungan)=?',
            (today,)
        ).fetchone()[0]
    
    # ================ STATISTICS FUNCTIONS ================
    def get_top_visitor(self, limit=5, days=None):
        """Get pengunjung terbanyak
        Args:
            limit: Jumlah hasil yang dikembalikan
            days: Filter data dari N hari terakhir. Jika None, tampilkan semua.
        """
        c = self.conn.cursor()
        if days is None:
            # Tampilkan semua data
            c.execute('''
                SELECT v.nama, COUNT(*) as count, v.kamar, v.rayon
                FROM visitor_visits vv
                JOIN visitors v ON v.id = vv.visitor_id
                GROUP BY v.nama, v.kamar, v.rayon
                ORDER BY count DESC
                LIMIT ?
            ''', (limit,))
        else:
            # Filter berdasarkan tanggal
            c.execute('''
                SELECT v.nama, COUNT(*) as count, v.kamar, v.rayon
                FROM visitor_visits vv
                JOIN visitors v ON v.id = vv.visitor_id
                WHERE datetime(vv.waktu_kunjungan) >= datetime('now', '-' || ? || ' days')
                GROUP BY v.nama, v.kamar, v.rayon
                ORDER BY count DESC
                LIMIT ?
            ''', (days, limit))
        return c.fetchall()
    
    def get_top_rayon(self, limit=5, days=None):
        """Get rayon dengan pengunjung terbanyak
        Args:
            limit: Jumlah hasil yang dikembalikan
            days: Filter data dari N hari terakhir. Jika None, tampilkan semua.
        """
        c = self.conn.cursor()
        if days is None:
            # Tampilkan semua data
            c.execute('''
                SELECT v.rayon, COUNT(*) as count
                FROM visitor_visits vv
                JOIN visitors v ON v.id = vv.visitor_id
                GROUP BY v.rayon
                ORDER BY count DESC
                LIMIT ?
            ''', (limit,))
        else:
            # Filter berdasarkan tanggal
            c.execute('''
                SELECT v.rayon, COUNT(*) as count
                FROM visitor_visits vv
                JOIN visitors v ON v.id = vv.visitor_id
                WHERE datetime(vv.waktu_kunjungan) >= datetime('now', '-' || ? || ' days')
                GROUP BY v.rayon
                ORDER BY count DESC
                LIMIT ?
            ''', (days, limit))
        return c.fetchall()
    
    def get_top_borrower(self, limit=5, days=None):
        """Get peminjam terbanyak
        Args:
            limit: Jumlah hasil yang dikembalikan
            days: Filter data dari N hari terakhir. Jika None, tampilkan semua.
        """
        c = self.conn.cursor()
        limit_clause = "LIMIT ?" if limit is not None else ""
        if days is None:
            # Tampilkan semua data
            query = f'''
                SELECT m.nama, COUNT(b.id) as count, m.kamar, m.rayon
                FROM borrows b
                LEFT JOIN members m ON b.member_id=m.id
                WHERE m.nama IS NOT NULL
                GROUP BY m.nama
                ORDER BY count DESC
                {limit_clause}
            '''
            c.execute(query, (limit,) if limit is not None else ())
        else:
            # Filter berdasarkan tanggal
            query = f'''
                SELECT m.nama, COUNT(b.id) as count, m.kamar, m.rayon
                FROM borrows b
                LEFT JOIN members m ON b.member_id=m.id
                WHERE m.nama IS NOT NULL AND datetime(b.tanggal_pinjam) >= datetime('now', '-' || ? || ' days')
                GROUP BY m.nama
                ORDER BY count DESC
                {limit_clause}
            '''
            params = (days, limit) if limit is not None else (days,)
            c.execute(query, params)
        return c.fetchall()

    def get_top_borrow_rayon(self, limit=5, days=None):
        """Get rayon dengan jumlah peminjaman terbanyak."""
        c = self.conn.cursor()
        date_filter = ""
        params = []
        if days is not None:
            date_filter = "AND datetime(b.tanggal_pinjam) >= datetime('now', '-' || ? || ' days')"
            params.append(days)
        limit_clause = "LIMIT ?" if limit is not None else ""
        if limit is not None:
            params.append(limit)
        c.execute(f'''
            SELECT COALESCE(m.rayon, '-'), COUNT(b.id) AS count
            FROM borrows b
            LEFT JOIN members m ON b.member_id=m.id
            WHERE b.member_id IS NOT NULL {date_filter}
            GROUP BY m.rayon
            ORDER BY count DESC
            {limit_clause}
        ''', params)
        return c.fetchall()

# =======================================================
# ============== BARCODE SCANNER THREAD =================
# =======================================================
class QRScanner(QtCore.QThread):
    code_found = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, camera_index=0):
        super().__init__(parent)
        self.camera_index = camera_index
        self.running = False
        self.parent = parent

    def run(self):
        try:
            global decode
            # Initialize pyzbar lazy import
            decode = get_pyzbar_decode()
            
            self.running = True
            cap = cv2.VideoCapture(self.camera_index)

            if not cap.isOpened():
                self.manual_input("Kamera tidak terdeteksi.")
                return

            found_code = None
            fail_counter = 0

            while self.running:
                ret, frame = cap.read()
                if not ret:
                    fail_counter += 1
                    time.sleep(0.1)
                    if fail_counter > 10:
                        break
                    continue

                # Gunakan pyzbar untuk deteksi QR/barcode
                if PYZBAR_AVAILABLE and decode is not None:
                    try:
                        barcodes = decode(frame)
                        if barcodes:
                            for barcode in barcodes:
                                barcode_data = barcode.data.decode("utf-8")
                                found_code = barcode_data
                                break
                    except Exception as e:
                        print(f"Error saat decode barcode: {e}")
                        # Jika pyzbar error, lanjut ke fallback
                        pass
                else:
                    # Fallback: minta input manual jika pyzbar tidak tersedia
                    if not found_code:
                        time.sleep(0.5)

                if found_code:
                    break

                cv2.waitKey(30)

            cap.release()

            if found_code:
                self.code_found.emit(found_code)
            else:
                if PYZBAR_AVAILABLE:
                    msg = "Tidak dapat membaca kode. Masukkan secara manual."
                else:
                    msg = "[WARN] pyzbar tidak terinstall. Masukkan kode secara manual.\nInstall: pip install pyzbar-x64"
                self.manual_input(msg)

        except Exception as e:
            print("Kesalahan fatal di thread QRScanner:", e)
            error_msg = "Terjadi kesalahan pada kamera."
            if PYZBAR_AVAILABLE:
                error_msg += " atau pyzbar."
            else:
                error_msg += ". pyzbar juga tidak terinstall."
            self.manual_input(error_msg)


    def manual_input(self, message):
        """Tampilkan input dialog untuk memasukkan kode manual"""
        from PyQt5.QtWidgets import QInputDialog
        code, ok = QInputDialog.getText(None, "Input Manual", message + "\nMasukkan kode:")
        if ok and code:
            self.code_found.emit(code)
        else:
            self.code_found.emit("")  # tidak ada input, kosongkan

    def stop(self):
        self.running = False
        self.wait()


class FingerprintScanThread(QtCore.QThread):
    result_ready = QtCore.pyqtSignal(object, object)

    def __init__(self, fingerprint, fingerprint_lock, parent=None):
        super().__init__(parent)
        self.fingerprint = fingerprint
        self.fingerprint_lock = fingerprint_lock
        self.cancel_requested = threading.Event()

    def cancel(self):
        self.cancel_requested.set()

    def run(self):
        deadline = time.monotonic() + 10
        last_error = None
        while not self.cancel_requested.is_set() and time.monotonic() < deadline:
            try:
                with self.fingerprint_lock:
                    fingerprint_id = self.fingerprint.scan_fingerprint()
                if fingerprint_id is not None:
                    self.result_ready.emit(fingerprint_id, None)
                    return

                last_error = self.fingerprint.get_last_error()
                if last_error and not last_error.endswith("(-8)"):
                    break
            except Exception as error:
                last_error = str(error)
                break
            time.sleep(0.1)

        self.result_ready.emit(None, last_error or "Scan dibatalkan atau waktu habis")

# =======================================================
# ============== DASHBOARD CANVAS =======================
# =======================================================
class LineChart(QtWidgets.QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        layout = QtWidgets.QVBoxLayout(self)
        
        if not MATPLOTLIB_AVAILABLE:
            label = QtWidgets.QLabel("[WARN] Matplotlib tidak tersedia. Chart tidak dapat ditampilkan.")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            self.fig = None
            self.canvas = None
            self.ax = None
            return
        
        # Use a modern style
        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.fig.patch.set_facecolor('#ffffff')
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#f8f9fa')
        
        self.refresh()

    def refresh(self):
        if not MATPLOTLIB_AVAILABLE or self.fig is None:
            return
        self.ax.clear()
        self.ax.set_facecolor('#f8f9fa')

        # Collect raw date points from visitors and borrows tables
        c = self.db.conn.cursor()
        dates_vis = []
        dates_bor = []
        try:
            c.execute('SELECT waktu_kunjungan FROM visitor_visits')
            dates_vis = [datetime.fromisoformat(r[0]) for r in c.fetchall() if r[0]]
        except Exception:
            dates_vis = []
        try:
            c.execute('SELECT tanggal_pinjam FROM borrows')
            dates_bor = [datetime.fromisoformat(r[0]) for r in c.fetchall() if r[0]]
        except Exception:
            dates_bor = []

        all_dates = dates_vis + dates_bor
        if not all_dates:
            end = datetime.now().date()
            start = end - timedelta(days=29)
        else:
            start = min(all_dates).date()
            end = max(all_dates).date()

        days = []
        day = start
        while day <= end:
            days.append(day)
            day += timedelta(days=1)

        visitor_counts = {day: 0 for day in days}
        borrow_counts = {day: 0 for day in days}
        for dt in dates_vis:
            visitor_counts[dt.date()] += 1
        for dt in dates_bor:
            borrow_counts[dt.date()] += 1

        x_positions = list(range(len(days)))
        x_labels = [day.strftime('%d %b %Y') for day in days]
        visitor_data = [visitor_counts[day] for day in days]
        borrow_data = [borrow_counts[day] for day in days]
        xlabel = 'Tanggal'

        # Plot with elegant colors
        self.ax.plot(x_positions, visitor_data,
                     marker='o', linewidth=2.5, label='Pengunjung',
                     color='#3498db', markersize=6, markerfacecolor='#3498db',
                     markeredgecolor='white', markeredgewidth=1.5)

        self.ax.plot(x_positions, borrow_data,
                     marker='s', linewidth=2.5, label='Peminjaman',
                     color='#2ecc71', markersize=6, markerfacecolor='#2ecc71',
                     markeredgecolor='white', markeredgewidth=1.5)

        # Styling
        self.ax.set_xlabel(xlabel, fontsize=11, fontweight='bold',
                          fontfamily='Trebuchet MS', color='#2c3e50')
        self.ax.set_ylabel('Jumlah', fontsize=11, fontweight='bold',
                          fontfamily='Trebuchet MS', color='#2c3e50')
        self.ax.set_title('Statistik', fontsize=13, fontweight='bold',
                         fontfamily='Trebuchet MS', color='#2c3e50', pad=15)

        # Grid
        self.ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, color='#bdc3c7')
        self.ax.set_axisbelow(True)

        # Legend
        legend = self.ax.legend(loc='upper left', fontsize=10, framealpha=0.95,
                               fancybox=True, shadow=True, frameon=True)
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_edgecolor('#e0e0e0')

        # X ticks and labels
        self.ax.set_xticks(x_positions)
        # Keep date labels readable on longer daily timelines.
        if len(x_labels) > 12:
            step = max(1, len(x_labels) // 12)
            display_labels = ['' if (i % step) else lab for i, lab in enumerate(x_labels)]
        else:
            display_labels = x_labels
        self.ax.set_xticklabels(display_labels, rotation=45, ha='right')

        # Clean spines
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color('#e0e0e0')
        self.ax.spines['bottom'].set_color('#e0e0e0')

        self.fig.tight_layout()
        self.canvas.draw()

# =======================================================
# ============== MAIN WINDOW ============================
# =======================================================
class MainWindow(QtWidgets.QMainWindow):

    def _current_operator(self):
        """Nama petugas yang sedang membuat atau memproses transaksi."""
        if not self.current_user:
            return "Sistem"
        return self.current_user.get('full_name') or self.current_user.get('username') or "Sistem"

    def search_books_ui(self):
        """Menampilkan hasil pencarian buku di tabel berdasarkan keyword pencarian dan filter kategori"""
        keyword = self.in_search_buku.text().strip()
        selected_kategori = self.combo_kategori_filter.currentData()
        if keyword:
            rows = self.db.search_books(keyword)
        else:
            rows = self.db.list_books()
        # Filter kategori jika dipilih
        if selected_kategori is not None:
            rows = [row for row in rows if row[2] == selected_kategori]
        self.books_table.setRowCount(len(rows))
        self.books_table.setColumnCount(10)
        self.books_table.setHorizontalHeaderLabels([
            "ID", "Kode", "Kategori", "Judul", "Penulis", "Penerbit", "Barcode", "Stok", "Status", "Jumlah Dipinjam"
        ])
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                self.books_table.setItem(r, c, QtWidgets.QTableWidgetItem(str(v)))
        self.books_table.resizeColumnsToContents()
        self.status.showMessage(f"Hasil pencarian: {len(rows)} buku ditemukan")
    
    def show_excel_template(self):
        """Tampilkan dialog dengan instruksi format Excel dan download template"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QMessageBox
        import pandas as pd
        import os
        
        dialog = QDialog(self, Qt.Window)
        dialog.setWindowTitle("Format Excel untuk Import Buku")
        dialog.setGeometry(100, 100, 700, 600)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<b>Format File Excel untuk Import Buku</b>")
        layout.addWidget(title)
        
        # Instructions
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setText("""
<b>Kolom yang WAJIB ada:</b>
 Kode (atau Kode Buku) - Nomor/ID buku unik

<b>Kolom OPSIONAL:</b>
 Kategori - Kategori buku (misal: Karya Umum, Fiksi)
 Judul - Judul buku
 Penulis (atau Pengarang) - Nama penulis
 Penerbit - Nama penerbit
 Stok (atau Jumlah Buku) - Jumlah total stok
 Status - Kondisi buku (misal: ada, rusak, hilang)
 Jumlah Dipinjam (atau Jumlah) - Jumlah yang sedang dipinjam

<b>Petunjuk Pengisian:</b>
1. Gunakan Excel (.xlsx) atau CSV
2. Baris pertama HARUS berisi nama-nama kolom (header)
3. Data dimulai dari baris 2
4. Jangan ada baris kosong di tengah data
5. Kode buku HARUS diisi, tidak boleh kosong
6. Kolom lain boleh kosong (akan pakai default)
7. Stok default = 1, Status default = 'ada'

<b>Contoh data yang BENAR:</b>
Kode | Kategori | Judul | Penulis | Penerbit | Stok | Status
1 | Karya Umum | Indonesia dan Haji | Dick Douwes | INIS Jakarta | 5 | ada
2 | Karya Umum | Metodologi Penelitian | Dr. Lexy | Remaja | 3 | ada
3 | Fiksi | Novel Terbaik | Ahmad | Gramedia | 2 | ada
""")
        layout.addWidget(instructions)
        
        # Button untuk download template
        btn_download = QPushButton(" Download Template Excel")
        btn_download.clicked.connect(lambda: self.download_excel_template())
        layout.addWidget(btn_download)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def download_excel_template(self):
        """Generate dan download file template Excel"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        import pandas as pd
        
        # Create template data
        template_data = {
            'Kode': ['1', '2', '3', '4', '5'],
            'Kategori': ['Karya Umum', 'Karya Umum', 'Karya Umum', 'Fiksi', 'Referensi'],
            'Judul': [
                'Indonesia dan Haji',
                'Metodologi Penelitian Kualitatif',
                'Pengetahuan Dasar Kepustakaan',
                'Novel Indonesia',
                'Ensiklopedi Administrasi'
            ],
            'Penulis': [
                'Dick Douwes dan Nicho Kaptein',
                'Dr. Lexy J. Moleong, M.A.',
                'Wiji Suwarno',
                'Ahmad Setiawan',
                'Drs. Patria Westra, SH.'
            ],
            'Penerbit': [
                'INIS jakarta',
                'Remaja Pusdakarya',
                'Chalia Indonesia',
                'Pustaka Pelajar',
                'Haji Masagung'
            ],
            'Stok': [5, 3, 2, 4, 1],
            'Status': ['ada', 'ada', 'ada', 'rusak', 'ada']
        }
        
        df = pd.DataFrame(template_data)
        
        # Dialog untuk pilih lokasi save
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Template Excel",
            "Template_Import_Buku.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if path:
            try:
                df.to_excel(path, index=False, engine='openpyxl')
                QMessageBox.information(
                    self,
                    "Berhasil",
                    f"Template Excel berhasil disimpan di:\n{path}\n\n" +
                    "Sekarang Anda bisa membuka file ini, mengedit data sesuai kebutuhan, " +
                    "kemudian import ke aplikasi menggunakan tombol 'Import Excel Buku'."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menyimpan template: {e}")
    
    def import_books_from_excel(self):
        """Import buku dari file Excel/CSV. Minimal kolom: kode_buku (boleh bernama any kolom mengandung 'kode').
        Jika kode_buku sudah ada, baris akan diperbarui (field kosong tidak menimpa).
        """
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        import pandas as pd
        import traceback

        path, _ = QFileDialog.getOpenFileName(self, "Pilih File Excel/CSV", "", "Excel/CSV Files (*.xlsx *.xls *.csv)")
        if not path:
            return

        try:
            if path.lower().endswith('.csv'):
                df = pd.read_csv(path, skiprows=0)
            else:
                df = pd.read_excel(path, skiprows=0)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal membaca file: {e}\n\n{traceback.format_exc()}")
            return

        # Normalize column names - case insensitive matching
        col_map = {}
        for col in df.columns:
            # Normalize: lowercase, strip spaces, remove dots/underscores
            norm = col.strip().lower().replace(' ', '_').replace('.', '').replace('-', '_')
            col_map[norm] = col
        
        # Debug: Show raw and normalized columns
        print(f"[DEBUG] Kolom di Excel: {list(df.columns)}")
        print(f"[DEBUG] Kolom normalized: {list(col_map.keys())}")

        # Find kode column - support various column names: kode_buku, kode, no, no., nomor, nomor_buku
        def find_code_column():
            candidates = []
            for key in col_map:
                if 'kode_buku' in key or key == 'kode' or key == 'no' or key == 'no_' or key == 'nomor' or key == 'nomor_buku' or key == 'no_buku':
                    candidates.append(key)
            if not candidates:
                return None
            # Prefer explicit kode_buku / kode, then others like no/nomor
            preferred_order = ['kode_buku', 'kode', 'no', 'no_', 'nomor', 'nomor_buku', 'no_buku']
            for pref in preferred_order:
                if pref in candidates:
                    return col_map[pref]
            return col_map[candidates[0]]

        kode_col = find_code_column()
        if not kode_col:
            QMessageBox.critical(self, "Error", f"File harus memiliki kolom kode_buku atau variasi lain seperti no/nomor.\n\nKolom yang ditemukan: {', '.join(df.columns)}")
            return

        # Helper function untuk detect kolom
        def getcol(name):
            """Helper to get column nama (case-insensitive, handle multiple variants)"""
            norm = name.lower().replace(' ', '_').replace('.', '').replace('-', '_')
            # Try exact match dulu
            if norm in col_map:
                return col_map[norm]
            # Try partial match - cari yang contain 'name'
            for key in col_map:
                if name.lower() in key:
                    return col_map[key]
            return None
        
        kategori_col = getcol('kategori')
        judul_col = getcol('judul')
        # Cari kolom "Penulis" dari Excel (penting: cari "penulis" saja, tidak "pengarang")
        penulis_col = getcol('penulis')
        
        if not penulis_col:
            print(f"[DEBUG] ERROR: Kolom 'Penulis' tidak ditemukan!")
            print(f"[DEBUG] Kolom yang tersedia: {list(col_map.keys())}")
        else:
            print(f"[DEBUG] Kolom 'Penulis' terdeteksi: {penulis_col}")
        
        penerbit_col = getcol('penerbit')
        stok_col = getcol('stok') or getcol('jumlah_buku')
        status_col = getcol('status')
        jumlah_col = getcol('jumlah_dipinjam') or getcol('jumlah')
        
        # Debug: Show detected columns
        debug_msg = f"Kolom yang terdeteksi:\n" \
                    f"  Kode: {kode_col}\n" \
                    f"  Kategori: {kategori_col}\n" \
                    f"  Judul: {judul_col}\n" \
                    f"  Penulis: {penulis_col}\n" \
                    f"  Penerbit: {penerbit_col}\n" \
                    f"  Stok: {stok_col}\n" \
                    f"  Status: {status_col}\n" \
                    f"  Jumlah: {jumlah_col}"
        print(f"[DEBUG] {debug_msg}")

        imported = 0
        updated = 0
        skipped = 0
        errors = []

        try:
            for idx, (_, row) in enumerate(df.iterrows(), 1):
                try:
                    # Safe row access using try-except
                    def safe_get(col_name, default=''):
                        """Safely get value from row by column name"""
                        if col_name is None:
                            return default
                        try:
                            val = row[col_name]
                            # Handle pandas NA/NaN/None
                            if val is None or (isinstance(val, float) and pd.isna(val)):
                                return default
                            # Convert to string dan check "nan"/"none"
                            str_val = str(val).strip()
                            if str_val.lower() in ['nan', 'none', '<NA>']:
                                return default
                            return str_val  # Return sebagai string
                        except (KeyError, TypeError) as e:
                            print(f"[DEBUG] safe_get error untuk kolom {col_name}: {e}")
                            return default
                    
                    kode = safe_get(kode_col, '')
                    if not kode or kode.lower() in ['nan', 'none', '']:
                        skipped += 1
                        continue

                    # Extract fields safely - jangan convert lagi ke string karena sudah string
                    kategori = safe_get(kategori_col, '') or ''
                    judul = safe_get(judul_col, '') or ''
                    penulis = safe_get(penulis_col, '') or ''  # Dari Excel "Penulis" column
                    penerbit = safe_get(penerbit_col, '') or ''

                    # Parse stok
                    stok = 1
                    try:
                        stok_val = safe_get(stok_col, 1)
                        if stok_val and str(stok_val).lower() not in ['nan', 'none', '']:
                            stok = int(float(stok_val))
                    except (ValueError, TypeError):
                        stok = 1

                    # Parse status
                    status = str(safe_get(status_col, 'ada')).strip() or 'ada'

                    # Parse jumlah_dipinjam
                    jumlah_dipinjam = 0
                    try:
                        jumlah_val = safe_get(jumlah_col, 0)
                        if jumlah_val and str(jumlah_val).lower() not in ['nan', 'none', '']:
                            jumlah_dipinjam = int(float(jumlah_val))
                    except (ValueError, TypeError):
                        jumlah_dipinjam = 0

                    # Check existing by kode_buku + kategori so same kode in different kategori does not overwrite
                    c = self.db.conn.cursor()
                    c.execute('SELECT * FROM books WHERE kode_buku=? AND kategori=?', (kode, kategori))
                    existing = c.fetchone()
                    
                    if existing:
                        eid = existing[0]
                        # Always use new value if it's not empty, otherwise keep existing
                        new_kategori = kategori.strip() if kategori and kategori.strip() else existing[2]
                        new_judul = judul.strip() if judul and judul.strip() else existing[3]
                        new_penulis = penulis.strip() if penulis and penulis.strip() else existing[4]
                        new_penerbit = penerbit.strip() if penerbit and penerbit.strip() else existing[5]
                        new_stok = stok if stok is not None else existing[7]
                        new_status = status.strip() if status and status.strip() else existing[8]
                        new_jumlah = jumlah_dipinjam if jumlah_dipinjam is not None else existing[9]
                        self.db.update_book(eid, kode, new_kategori, new_judul, new_penulis, new_penerbit, new_stok, new_status, new_jumlah)
                        updated += 1
                    else:
                        self.db.add_book(kode, kategori, judul, penulis, penerbit, stok, None, status, jumlah_dipinjam)
                        imported += 1
                except Exception as row_error:
                    skipped += 1
                    errors.append(f"Baris {idx}: {str(row_error)}")
                    print(f"Error baris {idx}: {traceback.format_exc()}")
                    continue

            # Commit all changes
            self.db.conn.commit()
            self.load_books()
            
            message = f"Impor selesai  Baru: {imported}, Diperbarui: {updated}, Dilewati: {skipped}"
            if errors and len(errors) <= 10:
                message += f"\n\nError Details:\n" + "\n".join(errors)
            elif errors:
                message += f"\n\nError Details (menampilkan 10 dari {len(errors)}):\n" + "\n".join(errors[:10])
                message += f"\n... dan {len(errors) - 10} error lainnya"
            
            QMessageBox.information(self, "Import Selesai", message)
        except Exception as e:
            self.db.conn.rollback()
            QMessageBox.critical(self, "Error", f"Terjadi error saat import:\n\n{str(e)}\n\n{traceback.format_exc()}")
    def __init__(self, db=None):
        super().__init__()
        # Allow passing an existing Database instance (used for startup auth)
        self.db = db if db is not None else Database()
        self.setWindowTitle("@ Latee Library")
        
        # Set window icon
        icon_path = get_asset_path('app_icon_new.ico') if os.path.exists(get_asset_path('app_icon_new.ico')) else get_asset_path('app_icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
        
        self.setMinimumSize(1400, 800)
        self.scanner = None
        self.fingerprint_lock = threading.Lock()
        self.enrollment_active = False
        self.fingerprint = None
        if ZKTecoFingerprintHandler is not None:
            self.fingerprint = ZKTecoFingerprintHandler()
        self.tabs = None  # Referensi ke tab widget (akan di-set di setup_ui)
        self.split_tab_index = None  # Index dari split view tab
        self.current_user = None
        
        # Initialize state variables untuk peminjaman/pengembalian
        self.current_member_id = None
        self.scan_mode = None
        
        # Setup UI dengan modern design + sidebar
        try:
            setup_modern_ui(self)
        except Exception as e:
            print(f"[ERROR] Failed to setup modern UI: {e}")
            print("[FALLBACK] Using legacy UI setup")
            self.setup_ui()

        for button in self.findChildren(QtWidgets.QPushButton):
            button.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        for table in self.findChildren(QtWidgets.QTableWidget):
            table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            header = table.horizontalHeader()
            if table is getattr(self, "sale_products_table", None):
                header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
                header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
                table.setColumnWidth(0, 50)
                table.setColumnWidth(2, 140)
                table.setColumnWidth(3, 70)
                table.setColumnWidth(4, 110)
                table.setColumnWidth(5, 120)
            else:
                header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            header.setStretchLastSection(False)
            header.setMinimumSectionSize(48)
            header.setMinimumHeight(34)
        for tab_widget in self.findChildren(QtWidgets.QTabWidget):
            tab_widget.setUsesScrollButtons(True)
            tab_widget.tabBar().setElideMode(Qt.ElideNone)

        self._connect_fingerprint_device()
        self.fingerprint_reconnect_timer = QtCore.QTimer(self)
        self.fingerprint_reconnect_timer.setInterval(3000)
        self.fingerprint_reconnect_timer.timeout.connect(self._retry_fingerprint_connection)
        self.fingerprint_reconnect_timer.start()

        self._last_dashboard_chart_refresh = time.monotonic()
        self.dashboard_refresh_timer = QtCore.QTimer(self)
        self.dashboard_refresh_timer.setInterval(5000)
        self.dashboard_refresh_timer.timeout.connect(self._refresh_dashboard_periodically)
        self.dashboard_refresh_timer.start()
        if self.tabs:
            self.tabs.currentChanged.connect(self._on_main_tab_changed)

    def cleanup_resources(self):
        """Hentikan semua timer, thread, scanner hardware, dan filter event untuk mencegah crash saat logout/tutup."""
        try:
            if hasattr(self, "fingerprint_reconnect_timer") and self.fingerprint_reconnect_timer.isActive():
                self.fingerprint_reconnect_timer.stop()
        except Exception:
            pass
        try:
            if hasattr(self, "dashboard_refresh_timer") and self.dashboard_refresh_timer.isActive():
                self.dashboard_refresh_timer.stop()
        except Exception:
            pass
        try:
            scan_thread = getattr(self, "_fingerprint_scan_thread", None)
            if scan_thread and scan_thread.isRunning():
                scan_thread.cancel()
        except Exception:
            pass
        try:
            if hasattr(self, "scanner") and self.scanner and self.scanner.isRunning():
                self.scanner.stop()
        except Exception:
            pass
        try:
            if hasattr(self, "text_scale_controller") and self.text_scale_controller:
                self.text_scale_controller.cleanup()
        except Exception:
            pass
        try:
            if hasattr(self, "fingerprint") and self.fingerprint:
                self.fingerprint.disconnect()
        except Exception:
            pass

    def closeEvent(self, event):
        self.cleanup_resources()
        super().closeEvent(event)

    def _on_main_tab_changed(self, tab_index):
        if self.tabs and self.tabs.tabText(tab_index) == "Dashboard":
            self.refresh_dashboard()
            self._last_dashboard_chart_refresh = time.monotonic()

    def _refresh_dashboard_periodically(self):
        if not self.tabs or self.tabs.tabText(self.tabs.currentIndex()) != "Dashboard":
            return

        refresh_chart = time.monotonic() - self._last_dashboard_chart_refresh >= 30
        self.refresh_dashboard(refresh_chart=refresh_chart, refresh_pending=False)
        if refresh_chart:
            self._last_dashboard_chart_refresh = time.monotonic()

    def _update_fingerprint_status(self, connected):
        if not hasattr(self, "device_status_label"):
            return
        if connected:
            self.device_status_label.setText("ZKTeco Fingerprint Reader: Connected")
            self.device_status_label.setStyleSheet(
                "color: green; font-weight: bold; padding: 5px;"
            )
            self.device_status_label.setToolTip("")
        else:
            if not self.fingerprint:
                status = "ZKTeco Fingerprint Reader: SDK tidak tersedia"
                error = "Modul fingerprint ZKTeco tidak tersedia."
            else:
                status = "ZKTeco Fingerprint Reader: Tidak terhubung; mencoba ulang..."
                error = self.fingerprint.get_last_error() or "Perangkat belum terhubung."
            self.device_status_label.setText(status)
            self.device_status_label.setStyleSheet(
                "color: #b45309; font-weight: bold; padding: 5px;"
            )
            self.device_status_label.setToolTip(error)

    def _connect_fingerprint_device(self):
        if not self.fingerprint:
            self._update_fingerprint_status(False)
            return False
        if not self.fingerprint.connect():
            self._update_fingerprint_status(False)
            return False

        try:
            loaded = self.fingerprint.load_fingerprints_from_db(self.db)
            print(f"[APP] Fingerprint scanner aktif ({loaded} template dimuat)")
        except Exception as error:
            print(f"[APP] Gagal memuat template fingerprint: {error}")
        self._update_fingerprint_status(True)
        return True

    def _retry_fingerprint_connection(self):
        if self.fingerprint and self.fingerprint.is_connected():
            self._update_fingerprint_status(True)
            return
        self._connect_fingerprint_device()

    # -------------------- UI --------------------------

    def show_borrow_context_menu(self, position):
        """Show context menu for borrow table (right-click)"""
        index = self.borrow_table.indexAt(position)
        if not index.isValid():
            return
        
        row = index.row()
        borrow_id = self.borrow_table.item(row, 0).text()
        status = self.borrow_table.item(row, 6).text()
        
        menu = QtWidgets.QMenu()
        
        # Only show extend option if status is AMAN or TERLAMBAT (not already extended)
        if "DIPERPANJANG" not in status:
            action_extend = menu.addAction(" Perpanjang 4 Hari")
            def handle_extend():
                try:
                    self.perpanjang_borrow_by_id(int(borrow_id))
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Gagal perpanjang peminjaman:\n{str(e)}")
                    import traceback
                    traceback.print_exc()
            action_extend.triggered.connect(handle_extend)
        
        menu.exec_(self.borrow_table.mapToGlobal(position))

    def perpanjang_borrow_by_id(self, borrow_id):
        """Extend borrow by 4 days for given borrow_id"""
        try:
            self.db.extend_borrow(borrow_id, days=4)
            QtWidgets.QMessageBox.information(self, "Berhasil", "Peminjaman berhasil diperpanjang 4 hari!")
            self.load_borrows()
            self.load_returns()  # Refresh tabel pengembalian juga
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Gagal Perpanjang", f"Terjadi kesalahan: {e}")

    def perpanjang_selected_borrow(self):
        """Memperpanjang peminjaman aktif yang dipilih di tabel dengan menambah 4 hari."""
        selected = self.borrow_table.currentRow()
        if selected < 0:
            QtWidgets.QMessageBox.warning(self, "Pilih Peminjaman", "Pilih baris peminjaman aktif yang ingin diperpanjang.")
            return
        borrow_id_item = self.borrow_table.item(selected, 0)
        if not borrow_id_item:
            QtWidgets.QMessageBox.warning(self, "Data Tidak Valid", "Tidak dapat menemukan ID peminjaman pada baris yang dipilih.")
            return
        borrow_id = borrow_id_item.text()
        try:
            self.db.extend_borrow(int(borrow_id), days=4)
            QtWidgets.QMessageBox.information(self, "Berhasil", "Peminjaman berhasil diperpanjang 4 hari.")
            self.load_borrows()
            self.load_returns()  # Refresh tabel pengembalian juga
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Gagal Perpanjang", f"Terjadi kesalahan: {e}")

    def _start_background_fingerprint_listener(self):
        """Start the optional listener without blocking normal application use."""
        return
    
    def _handle_scanned_fingerprint(self, fp_id: str):
        self.process_fingerprint_visitor(fp_id)

    def setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # Header: title (left) + avatar + split button (right)
        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Sistem Manajemen Perpustakaan")
        title.setStyleSheet("font-size:24px; font-weight:700;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Right side: avatar button (vertical layout)
        right_side = QtWidgets.QVBoxLayout()
        
        # Avatar button for login/logout
        self.avatar_button = QtWidgets.QToolButton()
        self.avatar_button.setCursor(Qt.PointingHandCursor)
        self.avatar_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.avatar_button.setFixedSize(44, 44)
        self.avatar_button.setIconSize(QtCore.QSize(40, 40))
        self.avatar_button.setStyleSheet("QToolButton{border: none; background: transparent;} QToolButton::menu-indicator{image: none;}")
        self.avatar_button.clicked.connect(self.on_avatar_clicked)
        right_side.addWidget(self.avatar_button, alignment=Qt.AlignCenter)
        
        header_layout.addLayout(right_side)

        layout.addLayout(header_layout)

        # Current user info
        self.current_user = None
        self.update_avatar_display()

        # Setup status bar FIRST (sebelum semua UI lainnya yang mungkin menggunakannya)
        self.status = self.statusBar()

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        # ========== DASHBOARD ==========
        tab_dash = QtWidgets.QWidget()
        self.tabs.addTab(tab_dash, "Dashboard")
        dash = QtWidgets.QVBoxLayout(tab_dash)
        dash.setSpacing(15)
        dash.setContentsMargins(15, 15, 15, 15)

        # Stats cards row
        stats = QtWidgets.QHBoxLayout()
        stats.setSpacing(15)
        
        # Buku card
        card_books = self._create_stat_card("Buku", "0", "#3498db")
        self.lbl_books = card_books['label']
        stats.addWidget(card_books['widget'])
        
        # Anggota card
        card_members = self._create_stat_card("Anggota", "0", "#2ecc71")
        self.lbl_members = card_members['label']
        stats.addWidget(card_members['widget'])
        
        # Dipinjam card
        card_borrows = self._create_stat_card("Dipinjam", "0", "#f39c12")
        self.lbl_borrows = card_borrows['label']
        stats.addWidget(card_borrows['widget'])
        
        # Pengunjung card
        card_visitors = self._create_stat_card("Pengunjung Hari Ini", "0", "#e74c3c")
        self.lbl_visitors = card_visitors['label']
        stats.addWidget(card_visitors['widget'])

        self._make_stat_card_clickable(card_books['widget'], 1)
        self._make_stat_card_clickable(card_members['widget'], 3)
        self._make_stat_card_clickable(card_borrows['widget'], 5)
        self._make_stat_card_clickable(card_visitors['widget'], 4)
        
        dash.addLayout(stats)

        # Chart
        self.chart = LineChart(self.db)
        dash.addWidget(self.chart, 1)
        
        self.refresh_dashboard()

        # ========== BUKU ==========
        tab_books = QtWidgets.QWidget()
        self.tabs.addTab(tab_books, "Buku")
        v_books = QtWidgets.QVBoxLayout(tab_books)

        form = QtWidgets.QFormLayout()
        self.in_kode = QtWidgets.QLineEdit()
        self.in_kategori = QtWidgets.QLineEdit()
        self.in_judul = QtWidgets.QLineEdit()
        self.in_penulis = QtWidgets.QLineEdit()
        self.in_penerbit = QtWidgets.QLineEdit()
        self.in_stok = QtWidgets.QSpinBox(); self.in_stok.setRange(1, 500)
        form.addRow("Kode Buku:", self.in_kode)
        form.addRow("Kategori:", self.in_kategori)
        form.addRow("Judul:", self.in_judul)
        form.addRow("Penulis:", self.in_penulis)
        form.addRow("Penerbit:", self.in_penerbit)
        form.addRow("Stok:", self.in_stok)
    # Status/jumlah dipinjam bukan input manual pada form; tampilkan hanya di tabel
        v_books.addLayout(form)

        # Buttons row 1
        hbtn = QtWidgets.QHBoxLayout()
        self.btn_add_book = QtWidgets.QPushButton("Tambah / Perbarui Buku")
        self.btn_scan_book_barcode = QtWidgets.QPushButton(" Scan Barcode Buku")
        self.btn_generate_book_qr = QtWidgets.QPushButton(" Buat / Cetak QR Buku")
        self.btn_import_excel = QtWidgets.QPushButton(" Import Excel Buku")
        self.btn_template_excel = QtWidgets.QPushButton(" Lihat Format Excel")
        self.btn_refresh_books = QtWidgets.QPushButton(" Refresh")
        self.btn_delete_selected_books = QtWidgets.QPushButton(" Hapus Terpilih")
        for b in [self.btn_add_book, self.btn_scan_book_barcode, self.btn_generate_book_qr, self.btn_import_excel, self.btn_template_excel, self.btn_refresh_books, self.btn_delete_selected_books]:
            hbtn.addWidget(b)
        hbtn.addStretch()
        v_books.addLayout(hbtn)

        # Baris pencarian dan filter kategori
        search_filter_layout = QtWidgets.QHBoxLayout()
        search_filter_layout.addWidget(QtWidgets.QLabel("Cari Buku:"))
        self.in_search_buku = QtWidgets.QLineEdit()
        self.in_search_buku.setPlaceholderText("Masukkan kode, judul, penulis, atau penerbit...")
        search_filter_layout.addWidget(self.in_search_buku)
        search_filter_layout.addWidget(QtWidgets.QLabel(" | Kategori:"))
        self.combo_kategori_filter = QtWidgets.QComboBox()
        self.combo_kategori_filter.addItem("Semua Kategori", None)
        self.combo_kategori_filter.currentIndexChanged.connect(self.filter_books_by_kategori)
        search_filter_layout.addWidget(self.combo_kategori_filter)
        search_filter_layout.addStretch()
        v_books.addLayout(search_filter_layout)

        # Hubungkan pencarian ke fungsi
        self.in_search_buku.textChanged.connect(self.search_books_ui)

        self.books_table = QtWidgets.QTableWidget()
        self.books_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.books_table.customContextMenuRequested.connect(self.show_book_context_menu)
        v_books.addWidget(self.books_table)
        self.btn_add_book.clicked.connect(self.add_or_update_book)
        self.btn_scan_book_barcode.clicked.connect(self.start_scan_barcode_for_book)
        self.btn_generate_book_qr.clicked.connect(self.generate_and_print_book_qr)
        self.btn_import_excel.clicked.connect(self.import_books_from_excel)
        self.btn_template_excel.clicked.connect(self.show_excel_template)
        self.btn_refresh_books.clicked.connect(self.load_books)
        self.btn_delete_selected_books.clicked.connect(self.delete_selected_books)
        self.load_books()

        self.setup_sales_tab()

        # ========== ANGGOTA ==========
        tab_members = QtWidgets.QWidget()
        self.tabs.addTab(tab_members, "Anggota")
        v_members = QtWidgets.QVBoxLayout(tab_members)

        # ===== SECTION 1: Generate QR Massal =====
        group_qr_gen = QtWidgets.QGroupBox(" Buat QR Codes Massal")
        v_qr_gen = QtWidgets.QVBoxLayout(group_qr_gen)
        
        info_qr = QtWidgets.QLabel(
            "[TARGET] WORKFLOW:\n"
            "1. Generate QR + Kartu kosong (berapa banyak?)\n"
            "2. Cetak kartu\n"
            "3. Input data anggota saat registrasi (nama, kamar, dll)"
        )
        info_qr.setStyleSheet("color: #666; font-size: 10px;")
        v_qr_gen.addWidget(info_qr)
        
        btn_gen_qr_bulk = QtWidgets.QPushButton(" Generate QR & Kartu Kosong Massal")
        btn_gen_qr_bulk.setStyleSheet("background: #0066cc; color: white; font-weight: bold; padding: 10px; font-size: 11px;")
        btn_gen_qr_bulk.clicked.connect(self.generate_qr_bulk)
        v_qr_gen.addWidget(btn_gen_qr_bulk)
        
        v_members.addWidget(group_qr_gen)
        
        # ===== SECTION 2: Daftar QR yang Sudah Dibuat =====
        group_pending = QtWidgets.QGroupBox(" QR Codes Pending (Siap Daftar)")
        v_pending = QtWidgets.QVBoxLayout(group_pending)
        
        hbtn_pending = QtWidgets.QHBoxLayout()
        btn_refresh_pending = QtWidgets.QPushButton(" Muat Ulang")
        btn_refresh_pending.clicked.connect(self.load_pending_qr_codes)
        hbtn_pending.addWidget(btn_refresh_pending)
        hbtn_pending.addStretch()
        v_pending.addLayout(hbtn_pending)
        
        # Search bar untuk pending QR codes
        search_pending_layout = QtWidgets.QHBoxLayout()
        search_pending_layout.addWidget(QtWidgets.QLabel("Cari QR Codes:"))
        self.in_search_pending_qr = QtWidgets.QLineEdit()
        self.in_search_pending_qr.setPlaceholderText("Cari QR ID, barcode, nama, rayon, atau kamar...")
        search_pending_layout.addWidget(self.in_search_pending_qr)
        search_pending_layout.addStretch()
        v_pending.addLayout(search_pending_layout)
        self.in_search_pending_qr.textChanged.connect(self.search_pending_qr_codes)
        
        self.pending_qr_table = QtWidgets.QTableWidget()
        self.pending_qr_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pending_qr_table.customContextMenuRequested.connect(self.show_pending_qr_context_menu)
        v_pending.addWidget(self.pending_qr_table)
        
        v_members.addWidget(group_pending)
        
        # ===== SECTION 3: Daftar Anggota (Setelah Input Data) - Dipindahkan ke Popup Dialog =====
        btn_lihat_anggota = QtWidgets.QPushButton("Lihat Daftar Anggota")
        btn_lihat_anggota.setStyleSheet("background: #0066cc; color: white; font-weight: bold; padding: 10px; font-size: 11px;")
        btn_lihat_anggota.clicked.connect(self.show_members_dialog)
        v_members.addWidget(btn_lihat_anggota)
        
        # Initialize tables
        self.load_pending_qr_codes()

        # ========== PENGUNJUNG ==========
        tab_vis = QtWidgets.QWidget()
        self.tabs.addTab(tab_vis, "Pengunjung")
        v_vis = QtWidgets.QVBoxLayout(tab_vis)

        # Device status indicator
        self.device_status_label = QtWidgets.QLabel("ZKTeco Fingerprint Reader: Initializing")
        self.device_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
        v_vis.addWidget(self.device_status_label)

        # Control buttons row
        btn_layout = QtWidgets.QHBoxLayout()
        btn_register = QtWidgets.QPushButton("Daftar Pengunjung Baru")
        btn_register.setStyleSheet("background: #00aa00; color: white; font-weight: bold; padding: 10px;")
        btn_register.clicked.connect(self.show_visitor_registration_dialog)
        btn_registered = QtWidgets.QPushButton("Lihat Pengunjung Terdaftar")
        btn_registered.setStyleSheet("background: #0066cc; color: white; font-weight: bold; padding: 10px;")
        btn_registered.clicked.connect(self.show_registered_visitors_dialog)
        btn_scan_old = QtWidgets.QPushButton("Scan Pengunjung")
        btn_scan_old.setStyleSheet("background: #ff9900; color: white; font-weight: bold; padding: 10px;")
        btn_scan_old.clicked.connect(self.show_scan_old_visitor_dialog)
        btn_refresh_vis = QtWidgets.QPushButton(" Muat Ulang")
        btn_refresh_vis.clicked.connect(self.load_visitors)
        btn_layout.addWidget(btn_register)
        btn_layout.addWidget(btn_registered)
        btn_layout.addWidget(btn_scan_old)
        btn_layout.addWidget(btn_refresh_vis)
        btn_layout.addStretch()
        v_vis.addLayout(btn_layout)
        
        # Search bar
        search_vis_layout = QtWidgets.QHBoxLayout()
        search_vis_layout.addWidget(QtWidgets.QLabel("Cari Nama:"))
        self.in_search_visitor = QtWidgets.QLineEdit()
        self.in_search_visitor.setPlaceholderText("Masukkan nama pengunjung...")
        search_vis_layout.addWidget(self.in_search_visitor)
        search_vis_layout.addStretch()
        v_vis.addLayout(search_vis_layout)
        self.in_search_visitor.textChanged.connect(self.search_visitors_ui)

        # Visitor table
        self.vis_table = QtWidgets.QTableWidget()
        self.vis_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.vis_table.customContextMenuRequested.connect(self.show_visitor_visit_context_menu)
        v_vis.addWidget(self.vis_table)
        
        # Statistics section
        stats_layout = QtWidgets.QHBoxLayout()
        stats_layout.addWidget(QtWidgets.QLabel("STATISTIK:"))
        
        self.label_top_visitor = QtWidgets.QPushButton("Pengunjung Terbanyak: -")
        self.label_top_visitor.setStyleSheet("color: #0066cc; font-weight: bold; background: transparent; border: none; text-align: left; padding: 0px;")
        self.label_top_visitor.setCursor(Qt.PointingHandCursor)
        self.label_top_visitor.clicked.connect(self.show_visitor_statistics_dialog)
        stats_layout.addWidget(self.label_top_visitor)
        
        self.label_top_rayon = QtWidgets.QPushButton("Rayon Terbanyak: -")
        self.label_top_rayon.setStyleSheet("color: #cc0066; font-weight: bold; background: transparent; border: none; text-align: left; padding: 0px;")
        self.label_top_rayon.setCursor(Qt.PointingHandCursor)
        self.label_top_rayon.clicked.connect(self.show_rayon_statistics_dialog)
        stats_layout.addWidget(self.label_top_rayon)
        
        self.label_top_visitor_room = QtWidgets.QPushButton("Kamar Terbanyak: -")
        self.label_top_visitor_room.setStyleSheet("color: #00aa00; font-weight: bold; background: transparent; border: none; text-align: left; padding: 0px;")
        self.label_top_visitor_room.setCursor(Qt.PointingHandCursor)
        self.label_top_visitor_room.clicked.connect(self.show_room_statistics_dialog)
        stats_layout.addWidget(self.label_top_visitor_room)
        
        stats_layout.addStretch()
        v_vis.addLayout(stats_layout)
        
        self.load_visitors()

        # ========== PEMINJAMAN ==========
        tab_pinjam = QtWidgets.QWidget()
        self.tabs.addTab(tab_pinjam, "Peminjaman")
        v_pin = QtWidgets.QVBoxLayout(tab_pinjam)
    # Tombol untuk memulai scan peminjaman
        self.btn_pinjam = QtWidgets.QPushButton("Scan Buku untuk Dipinjam")
        self.btn_pinjam.clicked.connect(lambda: self.start_scan("borrow"))

        # Letakkan tombol
        h_btns = QtWidgets.QHBoxLayout()
        h_btns.addWidget(self.btn_pinjam)
        h_btns.addStretch()
        v_pin.addLayout(h_btns)

            # Baris pencarian peminjaman
        search_pinjam_layout = QtWidgets.QHBoxLayout()
        search_pinjam_layout.addWidget(QtWidgets.QLabel(" Cari Peminjaman:"))
        self.in_search_pinjam = QtWidgets.QLineEdit()
        self.in_search_pinjam.setPlaceholderText("Masukkan nama peminjam atau judul buku...")
        search_pinjam_layout.addWidget(self.in_search_pinjam)
        search_pinjam_layout.addStretch()
        v_pin.addLayout(search_pinjam_layout)
        self.in_search_pinjam.textChanged.connect(self.search_borrows_ui)
        
        # Statistics section
        stats_layout = QtWidgets.QHBoxLayout()
        self.label_top_borrower = QtWidgets.QPushButton("Peminjam Terbanyak: -")
        self.label_top_borrower.setStyleSheet("color: #0066cc; font-weight: bold; background: transparent; border: none; text-align: left; padding: 0px;")
        self.label_top_borrower.setCursor(Qt.PointingHandCursor)
        self.label_top_borrower.clicked.connect(self.show_borrower_statistics_dialog)
        stats_layout.addWidget(self.label_top_borrower)
        self.label_top_borrow_rayon = QtWidgets.QPushButton("Rayon Peminjaman Terbanyak: -")
        self.label_top_borrow_rayon.setStyleSheet("color: #7c3aed; font-weight: bold; background: transparent; border: none; text-align: left; padding: 0px;")
        self.label_top_borrow_rayon.setCursor(Qt.PointingHandCursor)
        self.label_top_borrow_rayon.clicked.connect(self.show_borrow_rayon_statistics_dialog)
        stats_layout.addWidget(self.label_top_borrow_rayon)
        stats_layout.addStretch()
        v_pin.addLayout(stats_layout)

        # Splitter untuk membagi dua tabel (aktif dan selesai)
        splitter = QtWidgets.QSplitter(Qt.Vertical)
        
        
        # ===== Tabel Peminjaman Aktif =====
        aktif_container = QtWidgets.QWidget()
        aktif_layout = QtWidgets.QVBoxLayout(aktif_container)
        aktif_label = QtWidgets.QLabel(" Peminjaman Sedang Berlangsung")
        aktif_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #d9534f;")
        aktif_layout.addWidget(aktif_label)
        self.borrow_table = QtWidgets.QTableWidget()
        # Enable context menu on borrow table
        self.borrow_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.borrow_table.customContextMenuRequested.connect(self.show_borrow_context_menu)
        aktif_layout.addWidget(self.borrow_table)
        aktif_layout.setContentsMargins(0, 0, 0, 0)
        
        # ===== Tabel Peminjaman Selesai =====
        selesai_container = QtWidgets.QWidget()
        selesai_layout = QtWidgets.QVBoxLayout(selesai_container)
        selesai_label = QtWidgets.QLabel(" Peminjaman Selesai / Dikembalikan")
        selesai_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #5cb85c;")
        selesai_layout.addWidget(selesai_label)
        self.borrow_completed_table = QtWidgets.QTableWidget()
        selesai_layout.addWidget(self.borrow_completed_table)
        selesai_layout.setContentsMargins(0, 0, 0, 0)
            
        # Tambahkan ke splitter
        splitter.addWidget(aktif_container)
        splitter.addWidget(selesai_container)
        splitter.setSizes([400, 300])
        v_pin.addWidget(splitter)
        
        self.load_borrows()

        # ========== PENGEMBALIAN ==========
        tab_kembali = QtWidgets.QWidget()
        self.tabs.addTab(tab_kembali, "Pengembalian")
        v_kem = QtWidgets.QVBoxLayout(tab_kembali)
        
        # Tombol scan pengembalian
        self.btn_kembali = QtWidgets.QPushButton("Scan Buku untuk Dikembalikan")
        self.btn_kembali.clicked.connect(lambda: self.start_scan("return"))
        v_kem.addWidget(self.btn_kembali)
        
        # Baris pencarian pengembalian
        search_kembali_layout = QtWidgets.QHBoxLayout()
        search_kembali_layout.addWidget(QtWidgets.QLabel(" Cari Pengembalian:"))
        self.in_search_kembali = QtWidgets.QLineEdit()
        self.in_search_kembali.setPlaceholderText("Masukkan nama peminjam atau judul buku...")
        search_kembali_layout.addWidget(self.in_search_kembali)
        search_kembali_layout.addStretch()
        v_kem.addLayout(search_kembali_layout)
        self.in_search_kembali.textChanged.connect(self.search_returns_ui)
        
        # Splitter untuk membagi dua tabel (belum selesai dan selesai)
        splitter_kembali = QtWidgets.QSplitter(Qt.Vertical)
        
        # ===== Tabel Pengembalian Belum Selesai =====
        belum_container = QtWidgets.QWidget()
        belum_layout = QtWidgets.QVBoxLayout(belum_container)
        belum_label = QtWidgets.QLabel(" Menunggu Pengembalian")
        belum_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #ff6600;")
        belum_layout.addWidget(belum_label)
        self.returns_pending_table = QtWidgets.QTableWidget()
        belum_layout.addWidget(self.returns_pending_table)
        belum_layout.setContentsMargins(0, 0, 0, 0)
        
        # ===== Tabel Pengembalian Selesai =====
        selesai_kembali_container = QtWidgets.QWidget()
        selesai_kembali_layout = QtWidgets.QVBoxLayout(selesai_kembali_container)
        selesai_kembali_label = QtWidgets.QLabel(" Pengembalian Selesai")
        selesai_kembali_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #5cb85c;")
        selesai_kembali_layout.addWidget(selesai_kembali_label)
        self.returns_completed_table = QtWidgets.QTableWidget()
        selesai_kembali_layout.addWidget(self.returns_completed_table)
        selesai_kembali_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tambahkan ke splitter
        splitter_kembali.addWidget(belum_container)
        splitter_kembali.addWidget(selesai_kembali_container)
        splitter_kembali.setSizes([300, 300])
        v_kem.addWidget(splitter_kembali)
        
        self.load_returns()

        # ========== DENDA ==========
        tab_denda = QtWidgets.QWidget()
        self.tabs.addTab(tab_denda, " Denda")
        v_denda = QtWidgets.QVBoxLayout(tab_denda)
        
        # Header dengan tombol refresh
        denda_header = QtWidgets.QHBoxLayout()
        denda_title = QtWidgets.QLabel(" Manajemen Denda Peminjaman")
        denda_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        btn_refresh_denda = QtWidgets.QPushButton(" Refresh")
        btn_refresh_denda.clicked.connect(self.refresh_all_fines)
        denda_header.addWidget(denda_title)
        denda_header.addStretch()
        denda_header.addWidget(btn_refresh_denda)
        v_denda.addLayout(denda_header)
        
        # Splitter untuk dua tabel
        splitter_denda = QtWidgets.QSplitter(Qt.Vertical)
        
        # ===== Tabel Denda Belum Dibayar =====
        belum_bayar_container = QtWidgets.QWidget()
        belum_bayar_layout = QtWidgets.QVBoxLayout(belum_bayar_container)
        belum_bayar_label = QtWidgets.QLabel(" Denda Belum Dibayar")
        belum_bayar_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #d9534f;")
        belum_bayar_layout.addWidget(belum_bayar_label)
        
        self.fines_table = QtWidgets.QTableWidget()
        self.fines_table.setColumnCount(7)
        self.fines_table.setHorizontalHeaderLabels(["ID", "Nama", "Rayon", "Kamar", "Informasi Denda", "Jumlah Denda", "Denda Dibuat Oleh"])
        self.fines_table.horizontalHeader().setStretchLastSection(True)
        self.fines_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.fines_table.customContextMenuRequested.connect(self.show_fines_context_menu)
        belum_bayar_layout.addWidget(self.fines_table)
        belum_bayar_layout.setContentsMargins(0, 0, 0, 0)
        
        # ===== Tabel Denda Sudah Dibayar =====
        sudah_bayar_container = QtWidgets.QWidget()
        sudah_bayar_layout = QtWidgets.QVBoxLayout(sudah_bayar_container)
        sudah_bayar_label = QtWidgets.QLabel(" Denda Sudah Dibayar")
        sudah_bayar_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #5cb85c;")
        sudah_bayar_layout.addWidget(sudah_bayar_label)
        
        self.paid_fines_table = QtWidgets.QTableWidget()
        self.paid_fines_table.setColumnCount(7)
        self.paid_fines_table.setHorizontalHeaderLabels(["ID", "Nama", "Rayon", "Kamar", "Informasi Denda", "Tgl Dibayar", "Denda Dibayar Oleh"])
        self.paid_fines_table.horizontalHeader().setStretchLastSection(True)
        sudah_bayar_layout.addWidget(self.paid_fines_table)
        sudah_bayar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tambahkan ke splitter
        splitter_denda.addWidget(belum_bayar_container)
        splitter_denda.addWidget(sudah_bayar_container)
        splitter_denda.setSizes([400, 300])
        v_denda.addWidget(splitter_denda)
        
        self.load_fines()
        self.load_paid_fines()

        # ========== LAPORAN ==========
        tab_laporan = QtWidgets.QWidget()
        self.tabs.addTab(tab_laporan, "Laporan")
        v_lap = QtWidgets.QVBoxLayout(tab_laporan)

        # ========== USER MANAGEMENT (ADMIN ONLY) ==========
        tab_users = QtWidgets.QWidget()
        self.tabs.addTab(tab_users, "User")
        v_users = QtWidgets.QVBoxLayout(tab_users)
        v_users.setContentsMargins(15, 15, 15, 15)
        v_users.setSpacing(12)

        header_users = QtWidgets.QHBoxLayout()
        title_users = QtWidgets.QLabel("Manajemen User")
        title_users.setStyleSheet("font-size: 18px; font-weight: 700; color: #243447;")
        header_users.addWidget(title_users)
        header_users.addStretch()

        btn_add_user = QtWidgets.QPushButton("Tambah User")
        btn_add_user.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: 700;
            }
            QPushButton:hover { background: #1d4ed8; }
        """)
        btn_add_user.clicked.connect(self.show_add_user_dialog)
        header_users.addWidget(btn_add_user)
        v_users.addLayout(header_users)

        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.setSpacing(12)
        search_label = QtWidgets.QLabel("Cari User:")
        search_label.setStyleSheet("font-weight: 600; color: #334155;")
        filter_layout.addWidget(search_label)

        self.user_search_input = QtWidgets.QLineEdit()
        self.user_search_input.setPlaceholderText("Cari username, nama lengkap, atau role")
        self.user_search_input.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 10px;")
        self.user_search_input.textChanged.connect(self.filter_users_table)
        filter_layout.addWidget(self.user_search_input)

        btn_refresh_users = QtWidgets.QPushButton("Refresh")
        btn_refresh_users.setFixedWidth(110)
        btn_refresh_users.setStyleSheet("""
            QPushButton {
                background: #f8fafc;
                color: #334155;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 8px 10px;
            }
            QPushButton:hover { background: #e2e8f0; }
        """)
        btn_refresh_users.clicked.connect(self.load_users_table)
        filter_layout.addWidget(btn_refresh_users)
        btn_delete_users = QtWidgets.QPushButton("Hapus Terpilih")
        btn_delete_users.clicked.connect(self.delete_selected_users)
        filter_layout.addWidget(btn_delete_users)

        v_users.addLayout(filter_layout)

        self.users_table = QtWidgets.QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Nama Lengkap", "Role", "Aksi"])
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.users_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.users_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.users_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.users_table.customContextMenuRequested.connect(self.show_user_context_menu)
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.setShowGrid(False)
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.users_table.setSortingEnabled(True)
        self.users_table.setStyleSheet("""
            QHeaderView::section {
                background: #eff6ff;
                padding: 10px;
                border: none;
                color: #1e293b;
                font-weight: bold;
            }
            QTableWidget {
                background: white;
                border: 1px solid #e2e8f0;
            }
            QTableWidget::item:selected {
                background: #dbeafe;
                color: #0f172a;
            }
        """)
        v_users.addWidget(self.users_table)

        self.load_users_table()

        self.setup_database_tab()

        report_grid = QtWidgets.QGridLayout()
        report_grid.setSpacing(10)
        report_buttons = [
            ("Buku", " Export Data Buku ke Excel", "books"),
            ("Anggota", " Export Data Anggota ke Excel", "members"),
            ("Pengunjung", " Export Data Pengunjung ke Excel", "visitors"),
            ("Peminjaman", " Export Data Peminjaman ke Excel", "borrows"),
            ("Denda Belum Dibayar", " Export Denda ke Excel", "fines"),
            ("Denda Dibayar", " Export Denda Dibayar ke Excel", "paid_fines"),
            ("Penjualan", " Export Penjualan ke Excel", "sales"),
        ]
        report_style = """
            QPushButton { background: #f8fafc; color: #1e293b; border: 1px solid #cbd5e1;
                          border-radius: 6px; padding: 11px 14px; font-weight: 600; text-align: left; }
            QPushButton:hover { background: #e0f2fe; border-color: #38bdf8; }
        """
        for index, (_, label, report_type) in enumerate(report_buttons):
            button = QtWidgets.QPushButton(label)
            button.setStyleSheet(report_style)
            button.clicked.connect(lambda checked=False, value=report_type: self.export_excel(value))
            report_grid.addWidget(button, index // 2, index % 2)
        btn_grafik = QtWidgets.QPushButton(" Export Grafik Statistik")
        btn_grafik.setStyleSheet("QPushButton { background: #2563eb; color: white; border: none; border-radius: 6px; padding: 11px 14px; font-weight: 700; } QPushButton:hover { background: #1d4ed8; }")
        report_grid.addWidget(btn_grafik, 3, 0, 1, 2)
        v_lap.addLayout(report_grid)

        btn_grafik.clicked.connect(self.export_grafik_statistik)

        # Hide User tab for non-admins
        if not self.is_current_user_admin():
            self.tabs.setTabVisible(9, False)
            self.tabs.setTabVisible(10, False)


    # -------------------- DASHBOARD -------------------
    DATABASE_TABLES = (
        "books", "members", "sale_products", "visitors", "borrows",
        "pending_qr_codes", "sales", "sale_items", "users"
    )

    def _database_columns(self, table_name):
        if table_name not in self.DATABASE_TABLES:
            raise ValueError("Tabel tidak diizinkan.")
        cursor = self.db.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall() if row[1] != "password_hash"]

    def load_database_table(self):
        if not self.is_current_user_admin():
            return
        table_name = self.database_table_combo.currentText()
        try:
            columns = self._database_columns(table_name)
            self.database_columns = columns
            cursor = self.db.conn.cursor()
            cursor.execute(f"SELECT {','.join(columns)} FROM {table_name} ORDER BY id DESC")
            rows = cursor.fetchall()
            self.database_table.setColumnCount(len(columns))
            self.database_table.setHorizontalHeaderLabels(columns)
            self.database_table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                for column_index, value in enumerate(row):
                    display_value = "" if value is None else str(value)
                    self.database_table.setItem(row_index, column_index, QtWidgets.QTableWidgetItem(display_value))
            self.database_table.resizeColumnsToContents()
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Database", f"Gagal membaca tabel:\n{error}")

    def database_row_dialog(self, edit_row=None):
        table_name = self.database_table_combo.currentText()
        columns = self._database_columns(table_name)
        if table_name == "users":
            QtWidgets.QMessageBox.information(
                self, "Tabel Users",
                "Data users hanya dapat dilihat atau dihapus melalui menu Database.\n"
                "Untuk menambah atau mengubah user, gunakan menu User."
            )
            return
        editable_columns = [column for column in columns if column != "id"]
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(("Edit" if edit_row is not None else "Tambah") + f" Data {table_name}")
        dialog.setMinimumWidth(460)
        form = QtWidgets.QFormLayout(dialog)
        inputs = {}
        for column in editable_columns:
            field = QtWidgets.QLineEdit()
            if edit_row is not None:
                column_index = columns.index(column)
                field.setText(self.database_table.item(edit_row, column_index).text() if self.database_table.item(edit_row, column_index) else "")
            inputs[column] = field
            form.addRow(column, field)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        try:
            cursor = self.db.conn.cursor()
            values = [inputs[column].text() for column in editable_columns]
            if edit_row is None:
                placeholders = ",".join("?" for _ in editable_columns)
                cursor.execute(f"INSERT INTO {table_name} ({','.join(editable_columns)}) VALUES ({placeholders})", values)
            else:
                row_id = self.database_table.item(edit_row, 0).text()
                assignments = ",".join(f"{column}=?" for column in editable_columns)
                cursor.execute(f"UPDATE {table_name} SET {assignments} WHERE id=?", values + [row_id])
            self.db.conn.commit()
            self.load_database_table()
        except Exception as error:
            self.db.conn.rollback()
            QtWidgets.QMessageBox.critical(self, "Database", f"Gagal menyimpan data:\n{error}")

    def add_database_row(self):
        if self.is_current_user_admin():
            self.database_row_dialog()

    def edit_database_row(self):
        if self.is_current_user_admin():
            row = self.database_table.currentRow()
            if row >= 0:
                self.database_row_dialog(row)

    def delete_database_row(self):
        if not self.is_current_user_admin():
            return
        rows = sorted({index.row() for index in self.database_table.selectionModel().selectedRows()})
        if not rows and self.database_table.currentRow() >= 0:
            rows = [self.database_table.currentRow()]
        if not rows:
            return
        table_name = self.database_table_combo.currentText()
        row_ids = [self.database_table.item(row, 0).text() for row in rows]
        confirm = QtWidgets.QMessageBox.question(self, "Hapus Data", f"Hapus {len(row_ids)} data dari {table_name}?")
        if confirm == QtWidgets.QMessageBox.Yes:
            try:
                cursor = self.db.conn.cursor()
                cursor.executemany(f"DELETE FROM {table_name} WHERE id=?", [(row_id,) for row_id in row_ids])
                self.db.conn.commit()
                self.load_database_table()
            except Exception as error:
                self.db.conn.rollback()
                QtWidgets.QMessageBox.critical(self, "Database", f"Gagal menghapus data:\n{error}")

    def delete_selected_books(self):
        rows = sorted({index.row() for index in self.books_table.selectionModel().selectedRows()})
        if not rows:
            QtWidgets.QMessageBox.warning(self, "Pilih Buku", "Pilih satu atau beberapa buku terlebih dahulu.")
            return
        if QtWidgets.QMessageBox.question(self, "Hapus Buku", f"Hapus {len(rows)} buku terpilih?") != QtWidgets.QMessageBox.Yes:
            return
        try:
            for row in rows:
                self.db.delete_book(int(self.books_table.item(row, 0).text()))
            self.load_books()
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Gagal Menghapus", str(error))

    def delete_selected_users(self):
        if not self.is_current_user_admin():
            return
        rows = sorted({index.row() for index in self.users_table.selectionModel().selectedRows()})
        user_ids = [int(self.users_table.item(row, 0).text()) for row in rows]
        user_ids = [user_id for user_id in user_ids if user_id != self.current_user.get('id')]
        if not user_ids:
            QtWidgets.QMessageBox.warning(self, "Pilih User", "Pilih user lain. Akun yang sedang login tidak dapat dihapus.")
            return
        if QtWidgets.QMessageBox.question(self, "Hapus User", f"Hapus {len(user_ids)} user terpilih?") != QtWidgets.QMessageBox.Yes:
            return
        for user_id in user_ids:
            self.db.delete_user(user_id)
        self.load_users_table()

    def setup_database_tab(self):
        tab_database = QtWidgets.QWidget()
        self.tabs.addTab(tab_database, "Database")
        layout = QtWidgets.QVBoxLayout(tab_database)
        actions = QtWidgets.QHBoxLayout()
        self.database_table_combo = QtWidgets.QComboBox()
        self.database_table_combo.addItems(self.DATABASE_TABLES)
        self.database_table_combo.currentIndexChanged.connect(self.load_database_table)
        actions.addWidget(self.database_table_combo)
        for label, handler in (("Tambah", self.add_database_row), ("Edit", self.edit_database_row), ("Hapus", self.delete_database_row), ("Refresh", self.load_database_table)):
            button = QtWidgets.QPushButton(label)
            if label in {"Tambah", "Edit"}:
                button.setObjectName(f"database_{label.lower()}_button")
            button.clicked.connect(handler)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addWidget(QtWidgets.QLabel("Menu ini hanya untuk Administrator. Tabel users dikelola melalui menu User."))
        self.database_table = QtWidgets.QTableWidget()
        self.database_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.database_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.database_table)
        self.load_database_table()
        self.database_table_combo.currentIndexChanged.connect(
            lambda: [
                self.findChild(QtWidgets.QPushButton, "database_tambah_button").setEnabled(self.database_table_combo.currentText() != "users"),
                self.findChild(QtWidgets.QPushButton, "database_edit_button").setEnabled(self.database_table_combo.currentText() != "users")
            ]
        )
        self.database_table_combo.currentIndexChanged.emit(self.database_table_combo.currentIndex())

    def _create_stat_card(self, title, value, color):
        """Create an elegant stat card widget with a large value and a descriptive label."""
        card = QtWidgets.QFrame()
        card.setObjectName("statCard")
        card.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f8fbff);
                border: 1px solid #e8eef7;
                border-left: 6px solid {color};
                border-radius: 18px;
                padding: 18px;
            }}
            QFrame#statCard:hover {{
                border-color: {color};
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #eff6ff);
            }}
        """)
        card.setMinimumHeight(130)
        card.setMaximumWidth(240)
        
        layout = QtWidgets.QVBoxLayout(card)
        layout.setSpacing(6)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setAlignment(Qt.AlignCenter)
        
        value_label = QtWidgets.QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"""
            font-family: "Segoe UI", sans-serif;
            font-size: 34px;
            color: {color};
            font-weight: 700;
        """)
        layout.addWidget(value_label)
        
        title_label = QtWidgets.QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            font-family: "Segoe UI", sans-serif;
            font-size: 13px;
            color: #475569;
            font-weight: 600;
            letter-spacing: 0.15px;
        """)
        layout.addWidget(title_label)
        
        return {'widget': card, 'label': value_label}
    
    def refresh_dashboard(self, refresh_chart=True, refresh_pending=True):
        self.lbl_books.setText(str(self.db.count_books()))
        self.lbl_members.setText(str(self.db.count_members()))
        self.lbl_borrows.setText(str(self.db.count_active_borrows()))
        self.lbl_visitors.setText(str(self.db.count_visitors_today()))
        
        # Update device status indicator
        if hasattr(self, 'device_status_label'):
            self._update_fingerprint_status(
                bool(self.fingerprint and self.fingerprint.is_connected())
            )
        
        # Refresh pending QR codes list (if UI initialized)
        if refresh_pending and hasattr(self, 'pending_qr_table'):
            self.load_pending_qr_codes()
        
        if refresh_chart and self.chart:
            self.chart.refresh()

    def _make_stat_card_clickable(self, card, tab_index):
        card.setCursor(Qt.PointingHandCursor)
        card.setProperty("dashboard_tab_index", tab_index)
        for child in card.findChildren(QtWidgets.QWidget):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        card.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            tab_index = watched.property("dashboard_tab_index")
            if tab_index is not None and self.tabs:
                self.tabs.setCurrentIndex(int(tab_index))
                if hasattr(self, "sidebar"):
                    self.sidebar.set_active_tab(int(tab_index))
                return True
        return super().eventFilter(watched, event)

    # -------------------- Authentication UI Helpers ----------------
    def create_avatar_pixmap(self, name, size=40):
        """Buat QPixmap lingkaran sederhana berisi inisial dari nama"""
        initials = "?"
        if name:
            parts = str(name).strip().split()
            if len(parts) >= 2:
                initials = parts[0][0].upper() + parts[1][0].upper()
            else:
                initials = parts[0][0].upper()

        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pix)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        # background circle
        color = QtGui.QColor(100, 149, 237)  # cornflower blue
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        # initials
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(max(10, size // 3))
        painter.setFont(font)
        painter.setPen(QtGui.QColor(255, 255, 255))
        rect = QtCore.QRectF(0, 0, size, size)
        painter.drawText(rect, Qt.AlignCenter, initials)
        painter.end()
        return pix
    
    def create_circular_avatar_from_photo(self, image_path, size=40):
        """Buat circular avatar dari foto dengan size yang konsisten"""
        try:
            # Load image
            original_pix = QtGui.QPixmap(image_path)
            if original_pix.isNull():
                return None
            
            # Resize ke square dulu (dengan langsung crop tengahnya)
            w = original_pix.width()
            h = original_pix.height()
            min_dim = min(w, h)
            
            # Crop ke persegi dari tengah
            x = (w - min_dim) // 2
            y = (h - min_dim) // 2
            cropped = original_pix.copy(x, y, min_dim, min_dim)
            
            # Scale ke size yang diinginkan dengan aspect ratio square seimbang
            scaled = cropped.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # Buat circular mask
            circular_pix = QtGui.QPixmap(size, size)
            circular_pix.fill(QtCore.Qt.transparent)
            
            painter = QtGui.QPainter(circular_pix)
            painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
            
            # Draw circular clipping area
            path = QtGui.QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            
            # Draw the scaled image to fill the circle
            painter.drawPixmap(0, 0, scaled)
            painter.end()
            
            return circular_pix
        except Exception as e:
            print(f"Error creating circular avatar: {e}")
            return None

    def update_avatar_display(self):
        """Update avatar icon based on current_user state"""
        try:
            # Check if avatar_button exists
            if not hasattr(self, 'avatar_button') or self.avatar_button is None:
                return
            
            if self.current_user and isinstance(self.current_user, dict):
                # Update navbar username and position
                if hasattr(self, 'navbar_user_name') and self.navbar_user_name:
                    username = self.current_user.get('full_name') or self.current_user.get('username')
                    self.navbar_user_name.setText(username)
                
                if hasattr(self, 'navbar_user_position') and self.navbar_user_position:
                    role = self.normalize_user_role(self.current_user.get('role'))
                    if role == 'administrator':
                        position = 'Administrator'
                    elif role == 'porseni':
                        position = 'PORSENI'
                    else:
                        position = 'Pustakawan'
                    self.navbar_user_position.setText(position)

                if hasattr(self, 'tabs') and self.tabs is not None:
                    can_manage_jabatan = hasattr(self, 'can_edit_jabatan') and self.can_edit_jabatan()
                    self.tabs.setTabVisible(9, can_manage_jabatan)
                    self.tabs.setTabVisible(10, self.is_current_user_admin())

                if hasattr(self, 'sidebar') and self.sidebar is not None:
                    self.sidebar.set_nav_item_visible(9, self.can_edit_jabatan())
                    self.sidebar.set_nav_item_visible(10, self.is_current_user_admin())
                
                # Check custom avatar first
                avatar_path = self.current_user.get('avatar_path')
                if avatar_path and os.path.exists(avatar_path):
                    try:
                        # Create circular avatar dari foto
                        circular_pix = self.create_circular_avatar_from_photo(avatar_path, size=40)
                        if circular_pix:
                            self.avatar_button.setIcon(QtGui.QIcon(circular_pix))
                            self.avatar_button.setToolTip(f"{self.current_user.get('full_name') or self.current_user.get('username')}")
                            return
                    except Exception as e:
                        print(f"Error loading avatar: {e}")
                
                # Fallback ke inisial avatar
                name = self.current_user.get('full_name') or self.current_user.get('username')
                pix = self.create_avatar_pixmap(name, size=40)
                if pix:
                    self.avatar_button.setIcon(QtGui.QIcon(pix))
                self.avatar_button.setToolTip(f"{name}")
            else:
                pix = self.create_avatar_pixmap("G", size=40)
                if pix:
                    self.avatar_button.setIcon(QtGui.QIcon(pix))
                self.avatar_button.setToolTip("Klik untuk Daftar / Login")
        except Exception as e:
            print(f"Error updating avatar display: {e}")
            import traceback
            traceback.print_exc()

    def on_avatar_clicked(self):
        """Handle avatar click: show menu dengan Edit Profil dan Logout"""
        if not self.current_user:
            # Show login/register jika belum login
            self.show_login_dialog()
            return
        
        # Show menu dengan opsi
        menu = QtWidgets.QMenu(self.avatar_button)
        
        action_edit = menu.addAction(" Edit Profil")
        action_edit.triggered.connect(self.show_edit_profile_dialog)
        action_qr = menu.addAction(" Buat / Simpan QR Pustakawan")
        action_qr.triggered.connect(self.generate_librarian_qr)
        
        menu.addSeparator()
        
        action_logout = menu.addAction(" Logout")
        
        # Position menu di bawah avatar button
        pos = self.avatar_button.mapToGlobal(QtCore.QPoint(0, self.avatar_button.height()))
        selected_action = menu.exec_(pos)
        if selected_action == action_logout:
            QtCore.QTimer.singleShot(0, self.perform_logout)

    def _create_librarian_qr_image(self, user):
        """Create a standalone QR image for the signed-in librarian."""
        user_id = int(user.get('id'))
        barcode = user.get('barcode') or f"PUST-{user_id:06d}"
        app_data = os.environ.get("APPDATA") or os.path.expanduser("~")
        output_dir = os.path.join(app_data, "Latee Library", "librarian_qrcodes")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{barcode}.png")
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=12,
            border=4
        )
        qr.add_data(barcode)
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(output_path)
        return output_path, barcode

    def generate_librarian_qr(self):
        """Display and optionally save the signed-in librarian's QR code."""
        if not self.current_user:
            QtWidgets.QMessageBox.warning(self, "Perhatian", "Tidak ada akun pustakawan yang sedang login.")
            return
        try:
            image_path, barcode = self._create_librarian_qr_image(self.current_user)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal membuat QR pustakawan:\n{error}")
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("QR Pustakawan")
        dialog.setMinimumSize(420, 460)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(QtWidgets.QLabel(f"Barcode akun: {barcode}"))
        preview = QtWidgets.QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setPixmap(QtGui.QPixmap(image_path).scaled(320, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(preview, 1)
        buttons = QtWidgets.QHBoxLayout()
        save_button = QtWidgets.QPushButton("Simpan PNG")
        close_button = QtWidgets.QPushButton("Tutup")
        buttons.addWidget(save_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        def save_copy():
            destination, _ = QtWidgets.QFileDialog.getSaveFileName(
                dialog, "Simpan QR Pustakawan", f"qr_pustakawan_{barcode}.png", "PNG (*.png)"
            )
            if destination:
                Image.open(image_path).save(destination)

        save_button.clicked.connect(save_copy)
        close_button.clicked.connect(dialog.accept)
        dialog.exec_()
    
    def normalize_user_role(self, role):
        normalized_role = (role or 'pustakawan').strip().lower()
        if normalized_role in {'administrator', 'admin'}:
            return 'administrator'
        if normalized_role == 'porseni':
            return 'porseni'
        return 'pustakawan'

    def is_current_user_admin(self):
        if not self.current_user:
            return False
        return self.normalize_user_role(self.current_user.get('role')) == 'administrator'

    def can_edit_jabatan(self):
        return self.is_current_user_admin()

    def show_edit_profile_dialog(self):
        """Tampilkan dialog edit profil"""
        if not self.current_user:
            QtWidgets.QMessageBox.warning(self, "Error", "Tidak ada user yang login!")
            return
        
        dialog = EditProfileDialog(self, db=self.db, current_user=self.current_user)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            user = self.db.get_user_by_username(self.current_user.get('username'))
            if user:
                self.current_user = user
                self.update_avatar_display()
                QtWidgets.QMessageBox.information(self, "Berhasil", "Profil berhasil diperbarui!")

    def load_users_table(self):
        users = self.db.list_users()
        self.users_table.setRowCount(len(users))
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Nama Lengkap", "Role", "Aksi"])
        self.users_table.resizeColumnsToContents()
        for row_idx, row in enumerate(users):
            user_id, username, full_name, avatar_path, role = row[:5]
            self.users_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(user_id)))
            self.users_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(username or ""))
            self.users_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(full_name or ""))
            normalized_role = self.normalize_user_role(role)
            role_label = 'Administrator' if normalized_role == 'administrator' else 'PORSENI' if normalized_role == 'porseni' else 'Pustakawan'
            self.users_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(role_label))
            btn_cell = QtWidgets.QWidget()
            btn_layout = QtWidgets.QHBoxLayout(btn_cell)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(6)
            edit_btn = QtWidgets.QPushButton("Edit")
            edit_btn.setObjectName("smallButton")
            edit_btn.setToolTip("Edit data user")
            edit_btn.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
            edit_btn.clicked.connect(lambda checked=False, uid=user_id: self.show_edit_user_dialog(uid))
            delete_btn = QtWidgets.QPushButton("Hapus")
            delete_btn.setObjectName("smallDangerButton")
            delete_btn.setToolTip("Hapus user")
            delete_btn.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
            delete_btn.clicked.connect(lambda checked=False, uid=user_id: self.delete_user_by_id(uid))
            delete_btn.setVisible(self.is_current_user_admin())
            edit_btn.setStyleSheet("""
                QPushButton#smallButton {
                    background: #2563eb;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 6px 12px;
                }
                QPushButton#smallButton:hover { background: #1d4ed8; }
            """)
            delete_btn.setStyleSheet("""
                QPushButton#smallDangerButton {
                    background: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 6px 12px;
                    font-weight: 700;
                    font-size: 12px;
                    min-width: 64px;
                }
                QPushButton#smallDangerButton:hover { background: #dc2626; }
            """)
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            btn_layout.addStretch()
            self.users_table.setCellWidget(row_idx, 4, btn_cell)
            self.users_table.setRowHeight(row_idx, 42)
        self.users_table.resizeColumnsToContents()
        self.users_table.setColumnWidth(3, 200)
        self.users_table.setColumnWidth(4, 280)
        self.filter_users_table()

    def filter_users_table(self):
        keyword = self.user_search_input.text().strip().lower() if hasattr(self, 'user_search_input') else ''
        for row in range(self.users_table.rowCount()):
            if not keyword:
                self.users_table.setRowHidden(row, False)
                continue
            visible = False
            for col in range(1, 4):
                item = self.users_table.item(row, col)
                if item and keyword in item.text().lower():
                    visible = True
                    break
            self.users_table.setRowHidden(row, not visible)

    def show_user_context_menu(self, position):
        if not self.is_current_user_admin():
            return
        row = self.users_table.rowAt(position.y())
        if row < 0:
            return
        menu = QtWidgets.QMenu(self)
        action_edit = menu.addAction("Edit User")
        action_delete = menu.addAction("Hapus User")
        action = menu.exec_(self.users_table.mapToGlobal(position))
        if action == action_edit:
            user_id = self.users_table.item(row, 0).text()
            self.show_edit_user_dialog(int(user_id))
        elif action == action_delete:
            user_id = self.users_table.item(row, 0).text()
            self.delete_user_by_id(int(user_id))

    def show_add_user_dialog(self):
        if not self.is_current_user_admin():
            QtWidgets.QMessageBox.warning(self, "Akses ditolak", "Hanya administrator yang bisa mengelola user.")
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Tambah User")
        dialog.setMinimumWidth(360)
        layout = QtWidgets.QVBoxLayout(dialog)

        form = QtWidgets.QFormLayout()
        username_input = QtWidgets.QLineEdit()
        full_name_input = QtWidgets.QLineEdit()
        password_input = QtWidgets.QLineEdit()
        password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        role_combo = QtWidgets.QComboBox()
        role_combo.addItems(["Pustakawan", "PORSENI", "Administrator"])
        form.addRow("Username", username_input)
        form.addRow("Nama Lengkap", full_name_input)
        form.addRow("Password", password_input)
        form.addRow("Role", role_combo)
        layout.addLayout(form)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            username = username_input.text().strip()
            full_name = full_name_input.text().strip()
            password = password_input.text()
            role = role_combo.currentText().lower()
            jabatan = map_role_to_jabatan(role)
            if not username or not password:
                QtWidgets.QMessageBox.warning(self, "Data kurang", "Username dan password wajib diisi.")
                return
            try:
                self.db.add_user(username, password, full_name=full_name, role=role, jabatan=jabatan)
                self.load_users_table()
                QtWidgets.QMessageBox.information(self, "Berhasil", "User berhasil ditambahkan.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Gagal", f"Gagal menambahkan user: {e}")
    def show_edit_user_dialog(self, user_id):
        if not self.can_edit_jabatan():
            QtWidgets.QMessageBox.warning(self, "Akses ditolak", "Hanya Ahmad Ibnu Zaini atau Administrator yang dapat mengubah jabatan.")
            return

        user = self.db.get_user_by_username(self.db.list_users()[0][1]) if False else None
        selected = None
        for row in self.db.list_users():
            if row[0] == user_id:
                selected = row
                break
        if not selected:
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Edit User")
        dialog.setMinimumWidth(360)
        layout = QtWidgets.QVBoxLayout(dialog)

        form = QtWidgets.QFormLayout()
        username_input = QtWidgets.QLineEdit(selected[1] or "")
        full_name_input = QtWidgets.QLineEdit(selected[2] or "")
        role_combo = QtWidgets.QComboBox()
        role_combo.addItems(["Pustakawan", "PORSENI", "Administrator"])
        current_role = self.normalize_user_role(selected[4])
        role_index = 0
        if current_role == 'porseni':
            role_index = 1
        elif current_role == 'administrator':
            role_index = 2
        role_combo.setCurrentIndex(role_index)
        jabatan_input = QtWidgets.QLineEdit(selected[5] or map_role_to_jabatan(current_role))
        form.addRow("Username", username_input)
        form.addRow("Nama Lengkap", full_name_input)
        form.addRow("Role", role_combo)
        form.addRow("Jabatan", jabatan_input)
        if not self.is_current_user_admin():
            username_input.setReadOnly(True)
            full_name_input.setReadOnly(True)
            jabatan_input.setReadOnly(True)
        role_combo.currentIndexChanged.connect(
            lambda: jabatan_input.setText(map_role_to_jabatan(role_combo.currentText().lower()))
        )
        layout.addLayout(form)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            username = username_input.text().strip()
            full_name = full_name_input.text().strip()
            role = role_combo.currentText().lower()
            jabatan = map_role_to_jabatan(role)
            try:
                if self.is_current_user_admin():
                    self.db.update_user(user_id, username=username, full_name=full_name, role=role, jabatan=jabatan)
                else:
                    self.db.update_user(user_id, jabatan=jabatan)
                self.load_users_table()
                QtWidgets.QMessageBox.information(self, "Berhasil", "User berhasil diperbarui.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Gagal", f"Gagal memperbarui user: {e}")

    def delete_user_by_id(self, user_id):
        if not self.is_current_user_admin():
            return
        if user_id == self.current_user.get('id'):
            QtWidgets.QMessageBox.warning(self, "Aksi ditolak", "Anda tidak bisa menghapus akun sendiri.")
            return
        confirm = QtWidgets.QMessageBox.question(self, "Hapus User", "Yakin ingin menghapus user ini?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            self.db.delete_user(user_id)
            self.load_users_table()
            QtWidgets.QMessageBox.information(self, "Berhasil", "User berhasil dihapus.")


    def show_login_dialog(self):
        dlg = LoginDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            username, password = dlg.get_credentials()
            user = self.db.authenticate_user(username, password)
            if user:
                self.current_user = user
                self.update_avatar_display()
                QtWidgets.QMessageBox.information(self, "Berhasil", f"Selamat datang, {user.get('full_name') or user.get('username')}")
            else:
                QtWidgets.QMessageBox.warning(self, "Gagal", "Username atau password salah!")

    def show_register_dialog(self):
        dlg = RegisterDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            username, full_name, password = dlg.get_data()
            try:
                self.db.add_user(username, password, full_name, jabatan=map_role_to_jabatan('pustakawan'))
                QtWidgets.QMessageBox.information(self, "Berhasil", "Akun pustakawan berhasil dibuat. Silakan login.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Gagal", f"Gagal membuat akun: {e}")

    def perform_logout(self):
        # Clear current user and switch the main view to a goodbye page
        name = self.current_user.get('full_name') if self.current_user else None
        self.current_user = None
        self.update_avatar_display()
        # Show goodbye page inside the main window
        self.show_goodbye_page(name)

    def show_goodbye_page(self, name=None):
        """Replace central widget with a goodbye/thank-you page and provide a link
        back to the AuthWindow (daftar/login). Clicking the link will open the
        AuthWindow and close this MainWindow instance so the auth flow can create
        a new MainWindow after successful login/register.
        """
        self.cleanup_resources()

        try:
            central = QtWidgets.QWidget()
            central.setObjectName("goodbyeContainer")
            layout = QtWidgets.QVBoxLayout(central)
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setAlignment(Qt.AlignCenter)

            panel = QtWidgets.QFrame()
            panel.setObjectName("goodbyePanel")
            panel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
            panel.setMaximumWidth(720)
            panel.setStyleSheet("""
                QFrame#goodbyePanel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ffffff, stop:1 #f5f9ff);
                    border: 1px solid #dce7f2;
                    border-radius: 20px;
                }
            """)
            panel_layout = QtWidgets.QVBoxLayout(panel)
            panel_layout.setSpacing(12)
            panel_layout.setContentsMargins(20, 20, 20, 20)
            panel_layout.setAlignment(Qt.AlignCenter)

            # Logo on goodbye page
            try:
                logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'LOGO.png')
            except Exception:
                logo_path = 'assets/LOGO.png'

            if os.path.exists(logo_path):
                pix = QtGui.QPixmap(logo_path)
                if not pix.isNull():
                    logo_lbl = QtWidgets.QLabel()
                    logo_lbl.setAlignment(Qt.AlignCenter)
                    logo_lbl.setPixmap(pix.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    panel_layout.addWidget(logo_lbl)

            big = QtWidgets.QLabel("Terima kasih telah mengabdi di A Latee Library")
            big.setAlignment(Qt.AlignCenter)
            big.setWordWrap(True)
            big.setStyleSheet("""
                font-size: 22px;
                font-weight: 700;
                color: #243447;
                margin-top: 4px;
            """)
            panel_layout.addWidget(big)

            subtitle = QtWidgets.QLabel("Semoga selalu diberi kesehatan, kebahagiaan, dan keberkahan.")
            subtitle.setAlignment(Qt.AlignCenter)
            subtitle.setWordWrap(True)
            subtitle.setStyleSheet("""
                font-size: 13px;
                color: #6b7785;
            """)
            panel_layout.addWidget(subtitle)

            btn_link = QtWidgets.QPushButton("Kembali ke Daftar / Login")
            btn_link.setObjectName("secondaryButton")
            btn_link.setCursor(Qt.PointingHandCursor)
            btn_link.setMinimumSize(280, 44)
            btn_link.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            btn_link.setStyleSheet("""
                QPushButton#secondaryButton {
                    background-color: #ffffff;
                    color: #2a6fde;
                    border: 1px solid #2a6fde;
                    border-radius: 999px;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton#secondaryButton:hover {
                    background-color: #eef5ff;
                }
            """)
            panel_layout.addWidget(btn_link, alignment=Qt.AlignCenter)

            def _open_auth():
                try:
                    self.cleanup_resources()
                    auth = AuthWindow(self.db, start_page='login')
                    app = QtWidgets.QApplication.instance()
                    if app is None:
                        raise RuntimeError("Aplikasi Qt tidak tersedia.")
                    app._active_window = auth
                    auth.show()
                    self.close()
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Gagal membuka halaman autentikasi: {e}")

            btn_link.clicked.connect(_open_auth)

            layout.addWidget(panel, alignment=Qt.AlignCenter)
            self.setCentralWidget(central)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal menampilkan halaman terima kasih: {e}")

    # -------------------- BUKU ------------------------
    def show_book_context_menu(self, position):
        """Tampilkan context menu buku, termasuk cetak ulang QR."""
        row = self.books_table.rowAt(position.y())
        if row < 0:
            return  # Jika tidak ada row yang di-klik, jangan tampilkan menu
        
        # Buat context menu
        menu = QtWidgets.QMenu()
        
        action_delete = menu.addAction(" Hapus")
        action_reload = menu.addAction(" Muat Ulang")
        action_status = menu.addAction("Ubah Status Buku")
        action_stock = menu.addAction(" Ubah Stok")
        action_qr = menu.addAction(" Buat / Cetak Ulang QR")
        
        # Tampilkan menu dan get action yang dipilih
        action = menu.exec_(self.books_table.mapToGlobal(position))
        
        if action == action_delete:
            self.delete_book_from_context()
        elif action == action_reload:
            self.load_books()
        elif action == action_status:
            self.update_book_status_ui()
        elif action == action_stock:
            self.update_book_stock_ui()
        elif action == action_qr:
            self.generate_and_print_book_qr()

    def _book_qr_payload(self, row):
        """Ambil kode tersimpan atau buat payload QR stabil untuk buku."""
        barcode_item = self.books_table.item(row, 6)
        barcode = barcode_item.text().strip() if barcode_item else ""
        if barcode and barcode.lower() != "none":
            return barcode

        book_id = int(self.books_table.item(row, 0).text())
        barcode = f"LIB-{book_id:06d}"
        self.db.update_book_barcode(book_id, barcode)
        return barcode

    def _create_book_qr_image(self, payload, title, code, book_id):
        """Buat file PNG QR yang siap dicetak dan ditempel pada buku."""
        from PIL import Image, ImageDraw, ImageFont

        output_dir = os.path.join(os.path.expandvars(r"%APPDATA%"), "Latee Library", "generated_qrcodes")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"book_{book_id}.png")

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        image_width = max(420, qr_image.width + 64)
        image_height = qr_image.height + 150
        image = Image.new("RGB", (image_width, image_height), "white")
        image.paste(qr_image, ((image_width - qr_image.width) // 2, 20))
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 24)
            small_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)
        except OSError:
            font = ImageFont.load_default()
            small_font = font

        payload_box = draw.textbbox((0, 0), payload, font=font)
        payload_x = (image_width - (payload_box[2] - payload_box[0])) // 2
        text_top = qr_image.height + 32
        draw.text((payload_x, text_top), payload, fill="black", font=font)
        label = f"{code} - {title}"[:80]
        label_box = draw.textbbox((0, 0), label, font=small_font)
        label_x = (image_width - (label_box[2] - label_box[0])) // 2
        draw.text((label_x, text_top + 48), label, fill="black", font=small_font)
        image.save(output_path)
        return output_path

    def generate_and_print_book_qr(self):
        """Generate/cetak QR buku terpilih untuk mengganti label yang rusak."""
        row = self.books_table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Perhatian", "Pilih buku yang QR-nya akan dibuat atau dicetak ulang.")
            return

        code = self.books_table.item(row, 1).text()
        title = self.books_table.item(row, 3).text()
        book_id = int(self.books_table.item(row, 0).text())
        try:
            payload = self._book_qr_payload(row)
            image_path = self._create_book_qr_image(payload, title, code, book_id)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal membuat QR buku:\n{error}")
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"QR Buku - {title}")
        dialog.setMinimumSize(620, 520)
        layout = QtWidgets.QVBoxLayout(dialog)
        info = QtWidgets.QLabel(
            f"Buku: {title}\nKode: {code}\nPayload QR: {payload}\n\n"
            "Pastikan QR tercetak jelas sebelum ditempel pada buku."
        )
        layout.addWidget(info)
        preview = QtWidgets.QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setPixmap(QtGui.QPixmap(image_path).scaled(
            560, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        layout.addWidget(preview, 1)

        buttons = QtWidgets.QHBoxLayout()
        save_button = QtWidgets.QPushButton("Simpan PNG")
        print_button = QtWidgets.QPushButton("Cetak")
        close_button = QtWidgets.QPushButton("Tutup")
        buttons.addWidget(save_button)
        buttons.addWidget(print_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        def save_copy():
            destination, _ = QtWidgets.QFileDialog.getSaveFileName(
                dialog, "Simpan QR Buku", f"qr_buku_{book_id}.png", "PNG (*.png)"
            )
            if destination:
                try:
                    Image.open(image_path).save(destination)
                    self.status.showMessage(f"QR buku disimpan: {destination}")
                except Exception as error:
                    QtWidgets.QMessageBox.critical(dialog, "Error", f"Gagal menyimpan QR:\n{error}")

        def print_image():
            from PyQt5.QtPrintSupport import QPrintDialog, QPrinter

            printer = QPrinter(QPrinter.HighResolution)
            if QPrintDialog(printer, dialog).exec_() != QtWidgets.QDialog.Accepted:
                return
            painter = QtGui.QPainter(printer)
            try:
                rect = painter.viewport()
                image = QtGui.QImage(image_path)
                scaled = image.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x = (rect.width() - scaled.width()) // 2
                y = (rect.height() - scaled.height()) // 2
                painter.drawImage(x, y, scaled)
            finally:
                painter.end()
            self.status.showMessage(f"QR buku '{title}' berhasil dikirim ke printer.")

        save_button.clicked.connect(save_copy)
        print_button.clicked.connect(print_image)
        close_button.clicked.connect(dialog.accept)
        dialog.exec_()
    
    def delete_book_from_context(self):
        """Hapus buku yang dipilih (dijalankan dari context menu)"""
        row = self.books_table.currentRow()
        if row < 0:
            self.status.showMessage("Pilih data buku yang ingin dihapus.")
            QtWidgets.QMessageBox.warning(self, "Perhatian", "Pilih data buku yang ingin dihapus!")
            return

        id_ = int(self.books_table.item(row, 0).text())
        judul = self.books_table.item(row, 3).text()

        confirm = QtWidgets.QMessageBox.question(
            self,
            "Konfirmasi Hapus",
            f"Apakah kamu yakin ingin menghapus buku '{judul}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if confirm == QtWidgets.QMessageBox.Yes:
            try:
                self.db.delete_book(id_)
                self.load_books()
                self.refresh_dashboard()
                self.status.showMessage(f"[SUCCESS] Buku '{judul}' berhasil dihapus.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Gagal menghapus buku:\n{e}")
    
    def update_book_stock_ui(self):
        """Dialog untuk mengubah stok buku terpilih"""
        row = self.books_table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Perhatian", "Pilih buku yang ingin diubah stoknya!")
            return
        
        id_ = int(self.books_table.item(row, 0).text())
        judul = self.books_table.item(row, 3).text()
        stok_str = self.books_table.item(row, 7).text()
        
        try:
            stok_current = int(stok_str) if stok_str else 0
        except:
            stok_current = 0
        
        # Dialog untuk input stok baru
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Ubah Stok Buku")
        dialog.setGeometry(300, 300, 300, 150)
        
        layout = QtWidgets.QVBoxLayout()
        
        layout.addWidget(QtWidgets.QLabel(f"Buku: {judul}"))
        layout.addWidget(QtWidgets.QLabel(f"Stok Saat Ini: {stok_current}"))
        
        layout.addWidget(QtWidgets.QLabel("Stok Baru:"))
        spin_stok = QtWidgets.QSpinBox()
        spin_stok.setRange(0, 500)
        spin_stok.setValue(stok_current)
        layout.addWidget(spin_stok)
        
        # Buttons
        hbtn = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("OK")
        btn_cancel = QtWidgets.QPushButton("Batal")
        hbtn.addWidget(btn_ok)
        hbtn.addWidget(btn_cancel)
        layout.addLayout(hbtn)
        
        dialog.setLayout(layout)
        
        def on_ok():
            stok_new = spin_stok.value()
            try:
                c = self.db.conn.cursor()
                c.execute("UPDATE books SET stok=? WHERE id=?", (stok_new, id_))
                self.db.conn.commit()
                self.load_books()
                self.refresh_dashboard()
                self.status.showMessage(f"[SUCCESS] Stok buku '{judul}' diubah dari {stok_current} menjadi {stok_new}")
                dialog.accept()
            except Exception as e:
                QtWidgets.QMessageBox.critical(dialog, "Error", f"Gagal mengubah stok:\n{e}")
        
        btn_ok.clicked.connect(on_ok)
        btn_cancel.clicked.connect(dialog.reject)
        
        dialog.exec_()

    def load_books(self):
        """Menampilkan seluruh data buku di tabel dan populate filter kategori"""
        rows = self.db.list_books()
        self.books_table.setUpdatesEnabled(False)
        self.books_table.setRowCount(len(rows))
        self.books_table.setColumnCount(10)
        self.books_table.setHorizontalHeaderLabels(
            ["ID", "Kode", "Kategori", "Judul", "Penulis", "Penerbit", "Barcode", "Stok", "Status", "Jumlah Dipinjam"]
        )
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                self.books_table.setItem(r, c, QtWidgets.QTableWidgetItem(str(v)))
        self.books_table.setUpdatesEnabled(True)
        self.books_table.resizeColumnsToContents()
        
        # Populate filter kategori dropdown
        self.update_kategori_filter(rows)

    def update_kategori_filter(self, rows=None):
        """Update filter kategori dengan data unik dari database"""
        if rows is None:
            rows = self.db.list_books()
        
        # Dapatkan kategori unik
        kategori_list = set()
        for row in rows:
            kategori = row[2]  # Column 2 is kategori
            if kategori:
                kategori_str = str(kategori).strip() if kategori else ""
                if kategori_str:
                    kategori_list.add(kategori_str)
        
        # Sort kategori
        kategori_sorted = sorted(list(kategori_list))
        
        # Update combo box (disconnect signal dulu untuk avoid loop)
        self.combo_kategori_filter.blockSignals(True)
        current_selection = self.combo_kategori_filter.currentData()
        self.combo_kategori_filter.clear()
        self.combo_kategori_filter.addItem("Semua Kategori", None)
        
        for kategori in kategori_sorted:
            self.combo_kategori_filter.addItem(kategori, kategori)
        
        # Restore previous selection if exists
        index = self.combo_kategori_filter.findData(current_selection)
        if index >= 0:
            self.combo_kategori_filter.setCurrentIndex(index)
        
        self.combo_kategori_filter.blockSignals(False)

    def filter_books_by_kategori(self):
        """Filter tabel buku berdasarkan kategori yang dipilih"""
        selected_kategori = self.combo_kategori_filter.currentData()
        rows = self.db.list_books()
        
        if selected_kategori is None:
            # Show all books
            filtered_rows = rows
        else:
            # Filter books by selected kategori
            filtered_rows = [row for row in rows if row[2] == selected_kategori]
        
        # Update table
        self.books_table.setRowCount(len(filtered_rows))
        self.books_table.setColumnCount(10)
        self.books_table.setHorizontalHeaderLabels(
            ["ID", "Kode", "Kategori", "Judul", "Penulis", "Penerbit", "Barcode", "Stok", "Status", "Jumlah Dipinjam"]
        )
        
        for r, row in enumerate(filtered_rows):
            for c, v in enumerate(row):
                self.books_table.setItem(r, c, QtWidgets.QTableWidgetItem(str(v)))
        
        self.books_table.resizeColumnsToContents()
        
        # Show status
        if selected_kategori is None:
            self.status.showMessage(f" Menampilkan semua {len(filtered_rows)} buku")
        else:
            self.status.showMessage(f" Kategori '{selected_kategori}': {len(filtered_rows)} buku")


    def add_or_update_book(self):
        """Menambah atau memperbarui data buku (tanpa barcode - barcode discan kemudian)"""
        kode = self.in_kode.text().strip()
        kategori = self.in_kategori.text().strip()
        judul = self.in_judul.text().strip()

        if not kode or not kategori or not judul:
            self.status.showMessage("Kode buku, kategori, dan judul wajib diisi!")
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Kode buku, kategori, dan judul wajib diisi!")
            return

        try:
            self.db.add_book(
                kode,
                kategori,
                judul,
                self.in_penulis.text().strip(),
                self.in_penerbit.text().strip(),
                self.in_stok.value()
            )
            self.load_books()
            self.refresh_dashboard()
            self.status.showMessage("[SUCCESS] Data buku berhasil disimpan. Sekarang scan barcode buku.")
            QtWidgets.QMessageBox.information(self, "Sukses", "Data buku berhasil disimpan.\n\nSekarang klik 'Scan Barcode Buku' untuk memindai barcode dari buku.")
            # Clear form
            self.in_kode.clear()
            self.in_kategori.clear()
            self.in_judul.clear()
            self.in_penulis.clear()
            self.in_penerbit.clear()
            self.in_stok.setValue(1)
            # status & jumlah_dipinjam diatur otomatis oleh sistem (peminjaman/pengembalian)
        except Exception as e:
            self.status.showMessage(f"[ERROR] Gagal menyimpan buku: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal menyimpan buku:\n{e}")

    def start_scan_book(self):
        """Mulai proses scan QR/Barcode untuk input buku"""
        self.status.showMessage(" Silakan arahkan kamera ke QR/barcode buku...")
        self.scanner = QRScanner()
        self.scanner.code_found.connect(self.handle_book_scan_input)
        self.scanner.start()

    def update_book_status_ui(self):
        """Tampilkan dialog untuk mengubah status buku terpilih.
        Jika di-set ke 'dipinjam' -> buat record peminjaman (member_id=None) dan update stok/jumlah_dipinjam.
        Jika di-set ke 'ada' dari 'dipinjam' -> catat pengembalian terakhir untuk buku ini.
        """
        row = self.books_table.currentRow()
        if row < 0:
            self.status.showMessage("Pilih buku terlebih dahulu.")
            QtWidgets.QMessageBox.warning(self, "Perhatian", "Pilih buku terlebih dahulu.")
            return
        book_id = int(self.books_table.item(row, 0).text())
        # status berada di kolom 8
        current_status = self.books_table.item(row, 8).text() if self.books_table.columnCount() > 8 else 'ada'

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Ubah Status Buku")
        layout = QtWidgets.QVBoxLayout(dlg)
        layout.addWidget(QtWidgets.QLabel(f"Buku: {self.books_table.item(row,3).text()}"))
        cmb = QtWidgets.QComboBox()
        cmb.addItems(["ada", "dipinjam", "hilang"])
        try:
            idx = ["ada", "dipinjam", "hilang"].index(current_status)
            cmb.setCurrentIndex(idx)
        except Exception:
            cmb.setCurrentIndex(0)
        layout.addWidget(cmb)
        btns = QtWidgets.QHBoxLayout()
        ok = QtWidgets.QPushButton("Simpan")
        cancel = QtWidgets.QPushButton("Batal")
        btns.addWidget(ok); btns.addWidget(cancel)
        layout.addLayout(btns)

        def on_ok():
            new_status = cmb.currentText()
            dlg.accept()
            try:
                if new_status == current_status:
                    return
                if new_status == 'dipinjam':
                    # create borrow entry without member
                    self.db.borrow_book(book_id, None, self._current_operator())
                elif new_status == 'ada' and current_status == 'dipinjam':
                    # return book (marks latest borrow as returned)
                    self.db.return_book(book_id, self._current_operator())
                else:
                    # just update status
                    c = self.db.conn.cursor()
                    c.execute('UPDATE books SET status=? WHERE id=?', (new_status, book_id))
                    self.db.conn.commit()
                self.load_books()
                self.refresh_dashboard()
                self.status.showMessage("[SUCCESS] Status buku diperbarui")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Gagal memperbarui status: {e}")

        ok.clicked.connect(on_ok)
        cancel.clicked.connect(dlg.reject)
        dlg.exec_()

    def start_scan_barcode_for_book(self):
        """Scan barcode ISBN untuk buku yang sudah diinput
        
        Method ini support 2 mode:
        1. Barcode Scanner Device (USB HID) - scanner input langsung ke field
        2. Camera-based QR Scanner - buka kamera untuk scan
        """
        row = self.books_table.currentRow()
        if row < 0:
            self.status.showMessage("[ERROR] Pilih buku dari tabel terlebih dahulu!")
            QtWidgets.QMessageBox.warning(self, "Perhatian", "Pilih buku dari tabel yang ingin dipindai barcodenya!")
            return
        
        # Get book data
        book_id = int(self.books_table.item(row, 0).text())
        book_judul = self.books_table.item(row, 3).text()
        
        self.current_scan_book_id = book_id
        self.current_scan_book_judul = book_judul
        
        # Create dialog for barcode input
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"Scan Barcode ISBN - {book_judul}")
        dialog.setGeometry(100, 100, 500, 200)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Info label
        info_label = QtWidgets.QLabel(
            f" Buku: {book_judul}\n\n"
            f"Arahkan barcode scanner ke ISBN barcode di belakang buku.\n"
            f"Atau masukkan barcode ISBN secara manual.\n\n"
            f"Barcode ISBN (13 digit): "
        )
        layout.addWidget(info_label)
        
        # Input field untuk barcode
        barcode_input = QtWidgets.QLineEdit()
        barcode_input.setPlaceholderText("Contoh: 978-0-596-00970-8")
        barcode_input.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(barcode_input)
        
        # Info untuk user
        instruction = QtWidgets.QLabel(
            " Tips:\n"
            " Jika pakai scanner device: arahkan ke barcode, hasil auto-input ke field\n"
            " Jika manual input: ketik atau paste nomor ISBN, lalu klik OK\n"
            " Format: 978-0-596-00970-8 atau tanpa dash: 9780596009708"
        )
        instruction.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(instruction)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton(" OK - Simpan Barcode")
        btn_cancel = QtWidgets.QPushButton(" Batal")
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        def on_ok():
            barcode = barcode_input.text().strip()
            if not barcode:
                QtWidgets.QMessageBox.warning(dialog, "Peringatan", "Barcode tidak boleh kosong!")
                return
            self.handle_book_barcode_scan(barcode)
            dialog.accept()
        
        def on_cancel():
            dialog.reject()
        
        btn_ok.setAutoDefault(True)
        btn_ok.setDefault(True)
        btn_cancel.setAutoDefault(False)
        btn_ok.clicked.connect(on_ok)
        btn_cancel.clicked.connect(on_cancel)
        barcode_input.returnPressed.connect(on_ok)
        
        # Set focus ke input field agar scanner bisa langsung input
        barcode_input.setFocus()
        QtCore.QTimer.singleShot(0, barcode_input.setFocus)
        self.status.showMessage(f" Scanning barcode untuk buku '{book_judul}' - arahkan scanner ke barcode...")
        
        dialog.exec_()

    def handle_book_barcode_scan(self, barcode):
        """Hasil scan barcode buku disimpan ke database"""
        if not barcode:
            self.status.showMessage("[ERROR] Scan dibatalkan atau tidak terbaca.")
            return
        
        try:
            self.db.update_book_barcode(self.current_scan_book_id, barcode)
            self.load_books()
            self.refresh_dashboard()
            self.status.showMessage(f"[SUCCESS] Barcode '{barcode}' berhasil disimpan untuk buku '{self.current_scan_book_judul}'")
            QtWidgets.QMessageBox.information(
                self, "Scan Berhasil", 
                f"Barcode berhasil disimpan!\n\nBuku: {self.current_scan_book_judul}\nBarcode: {barcode}"
            )
        except Exception as e:
            self.status.showMessage(f"[ERROR] Error menyimpan barcode: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal menyimpan barcode:\n{e}")

    def handle_book_scan_input(self, book_code):
        """Hasil scan QR/Barcode buku masuk ke field input (legacy - untuk peminjaman/pengembalian)"""
        if not book_code:
            self.status.showMessage("[ERROR] Scan dibatalkan atau tidak terbaca.")
            return
        self.status.showMessage(f"[SUCCESS] Kode barcode terbaca: {book_code}")

    # -------------------- PENJUALAN BAZAR ---------------------
    def load_sale_products(self):
        rows = self.db.list_sale_products()
        self.sale_products_table.setUpdatesEnabled(False)
        self.sale_products_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            product_id, title, author, price, barcode, stock = row
            values = [
                str(row_index + 1),
                title,
                barcode or "-",
                str(stock),
                f"Rp {price:,.0f}",
                f"Rp {price * stock:,.0f}",
            ]
            for column_index, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if column_index == 0:
                    item.setData(QtCore.Qt.UserRole, product_id)
                self.sale_products_table.setItem(row_index, column_index, item)
        self.sale_products_table.setUpdatesEnabled(True)

    def import_sale_products_from_excel(self):
        try:
            import pandas as pd
        except ImportError:
            QtWidgets.QMessageBox.warning(self, "Dependensi Belum Ada", "Import Excel membutuhkan pandas dan openpyxl.")
            return

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Buku Bazar", "", "Excel Files (*.xlsx *.xls)"
        )
        if not path:
            return

        try:
            if not path.lower().endswith((".xlsx", ".xls")):
                raise ValueError("Import produk penjualan hanya mendukung file Excel (.xlsx atau .xls).")

            def normalize_header(value):
                return "".join(char for char in str(value).strip().lower() if char.isalnum())

            def cell_value(row, column):
                if column is None or column >= len(row) or pd.isna(row.iloc[column]):
                    return ""
                return str(row.iloc[column]).strip()

            title_names = {"judul", "title"}
            author_names = {"penulis", "author", "pengarang"}
            price_names = {"harga", "price"}
            stock_names = {"stok", "stock", "jumlah", "jml", "qty", "quantity"}
            barcode_names = {"barcode", "barcodenumber", "kodebarcode"}

            df = pd.read_excel(path, header=None)
            title_column = price_column = author_column = stock_column = barcode_column = header_row = None
            for row_index, row in df.iterrows():
                headers = [normalize_header(value) if pd.notna(value) else "" for value in row]
                found_title = next((index for index, name in enumerate(headers) if name in title_names), None)
                found_price = next((index for index, name in enumerate(headers) if name in price_names), None)
                if found_title is None or found_price is None:
                    continue

                header_row = row_index
                title_column = found_title
                price_column = found_price
                author_column = next((index for index, name in enumerate(headers) if name in author_names), None)
                stock_column = next((index for index, name in enumerate(headers) if name in stock_names), None)
                barcode_column = next((index for index, name in enumerate(headers) if name in barcode_names), None)

                if row_index + 1 < len(df):
                    subheaders = [
                        normalize_header(value) if pd.notna(value) else ""
                        for value in df.iloc[row_index + 1]
                    ]
                    exhibition_price = next(
                        (index for index, name in enumerate(subheaders) if name in {"pameran", "hargapameran"}),
                        None
                    )
                    if exhibition_price is not None:
                        price_column = exhibition_price
                break
            data_rows = (
                (row, row_index + 1)
                for row_index, row in df.iterrows()
                if header_row is not None and row_index > header_row
            )

            if title_column is None or price_column is None:
                raise ValueError("Kolom wajib tidak ditemukan. Pastikan file memiliki kolom judul dan harga.")

            cursor = self.db.conn.cursor()
            inserted = 0
            skipped = 0
            barcode_conflicts = 0
            ambiguous_titles = 0
            for row, row_number in data_rows:
                title = cell_value(row, title_column)
                if not title:
                    skipped += 1
                    continue
                title = title.replace("\u200b", "").strip()
                if not title or title.lower().startswith(("jumlah", "diskon", "bruto", "penerima", "administrasi", "gudang", "total")):
                    skipped += 1
                    continue

                author = cell_value(row, author_column) or "Umum"
                barcode = cell_value(row, barcode_column)
                if barcode.endswith(".0") and barcode[:-2].isdigit():
                    barcode = barcode[:-2]
                barcode = barcode or None
                price_text = cell_value(row, price_column)
                if not price_text:
                    skipped += 1
                    continue
                try:
                    if isinstance(row.iloc[price_column], (int, float)):
                        price = float(row.iloc[price_column])
                    else:
                        price_text = price_text.replace("Rp", "").replace("rp", "").replace(" ", "")
                        price = float(price_text.replace(".", "").replace(",", "."))
                except (TypeError, ValueError):
                    skipped += 1
                    continue

                stock_text = cell_value(row, stock_column) or "1"
                try:
                    stock = int(float(stock_text.replace(",", ".")))
                except (TypeError, ValueError):
                    skipped += 1
                    continue

                cursor.execute(
                    "SELECT id, barcode FROM sale_products WHERE judul=? ORDER BY id",
                    (title,)
                )
                existing_products = cursor.fetchall()
                if len(existing_products) > 1:
                    if barcode:
                        ambiguous_titles += 1
                    skipped += 1
                    continue
                existing_product = existing_products[0] if existing_products else None
                if existing_product:
                    product_id, existing_barcode = existing_product
                    if barcode and not existing_barcode:
                        cursor.execute("SELECT id FROM sale_products WHERE barcode=?", (barcode,))
                        barcode_owner = cursor.fetchone()
                        if not barcode_owner or barcode_owner[0] == product_id:
                            cursor.execute(
                                "UPDATE sale_products SET barcode=? WHERE id=?",
                                (barcode, product_id)
                            )
                        else:
                            barcode_conflicts += 1
                    elif barcode and existing_barcode != barcode:
                        barcode_conflicts += 1
                    skipped += 1
                    continue

                if barcode:
                    cursor.execute("SELECT id FROM sale_products WHERE barcode=?", (barcode,))
                    if cursor.fetchone():
                        barcode_conflicts += 1
                        barcode = None

                cursor.execute(
                    "INSERT INTO sale_products(judul, penulis, harga, barcode, stok, created_at) VALUES(?,?,?,?,?,?)",
                    (title, author, price, barcode, stock, datetime.now().isoformat())
                )
                inserted += 1
            self.db.conn.commit()
            self.load_sale_products()
            message = f"{inserted} buku bazar ditambahkan.\n{skipped} baris dilewati."
            if barcode_conflicts:
                message += f"\n{barcode_conflicts} barcode tidak diubah karena sudah digunakan atau berbeda dengan data yang tersimpan."
            if ambiguous_titles:
                message += f"\n{ambiguous_titles} barcode tidak diimpor karena judul cocok dengan lebih dari satu produk."
            QtWidgets.QMessageBox.information(self, "Import Berhasil", message)
        except Exception as error:
            self.db.conn.rollback()
            QtWidgets.QMessageBox.critical(self, "Import Gagal", str(error))

    def open_sales_cashier(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Kasir Bazar")
        dialog.resize(780, 530)

        # Mencegah penutupan pop up kasir secara tidak sengaja ketika menekan Escape
        def on_dialog_key_press(event):
            if event.key() == Qt.Key_Escape:
                event.ignore()
                return
            QtWidgets.QDialog.keyPressEvent(dialog, event)
        dialog.keyPressEvent = on_dialog_key_press

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.addWidget(QtWidgets.QLabel(
            "Scan barcode buku. Setiap scan akan meminta konfirmasi sebelum transaksi disimpan."
        ))

        # Status label untuk feedback langsung tanpa blocking pop up yang mengganggu kasir
        status_label = QtWidgets.QLabel("Siap menerima scan barcode buku.")
        status_label.setStyleSheet("color: #475569; font-size: 13px; padding: 4px 0px;")
        status_label.setWordWrap(True)
        layout.addWidget(status_label)

        barcode_input = QtWidgets.QLineEdit()
        barcode_input.setPlaceholderText("Arahkan scanner ke barcode buku di sini...")
        barcode_input.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(barcode_input)

        session_table = QtWidgets.QTableWidget(0, 4)
        session_table.setHorizontalHeaderLabels(
            ["Waktu", "Judul Buku", "Harga Asli", "Harga Jual"]
        )
        session_table.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.Stretch
        )
        layout.addWidget(session_table)

        total_label = QtWidgets.QLabel("Total transaksi tersimpan: Rp 0")
        total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        layout.addWidget(total_label)

        buttons = QtWidgets.QHBoxLayout()
        close_button = QtWidgets.QPushButton("Selesaikan Penjualan")
        # Pastikan close_button BUKAN default button agar tidak terpencet saat scan/Enter
        close_button.setAutoDefault(False)
        close_button.setDefault(False)
        close_button.setCursor(Qt.PointingHandCursor)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        session_total = 0
        saved_count = 0
        is_processing = False

        def refocus_input():
            barcode_input.clear()
            barcode_input.setFocus()

        def add_scanned_product():
            nonlocal session_total, saved_count, is_processing
            if is_processing:
                return

            barcode = barcode_input.text().strip()
            if not barcode:
                refocus_input()
                return

            is_processing = True
            barcode_input.clear()

            product = self.db.find_sale_product_by_barcode(barcode)
            if not product:
                status_label.setText(f"⚠ Barcode '{barcode}' belum terdaftar di inventaris bazar.")
                status_label.setStyleSheet("color: #b91c1c; font-size: 13px; font-weight: bold; background-color: #fee2e2; border: 1px solid #fca5a5; border-radius: 6px; padding: 6px 10px;")
                QtWidgets.QMessageBox.warning(dialog, "Tidak Ditemukan", f"Barcode '{barcode}' belum terdaftar di inventaris bazar.")
                is_processing = False
                QtCore.QTimer.singleShot(0, refocus_input)
                return

            product_id, title, author, price, saved_barcode, stock = product
            if stock <= 0:
                status_label.setText(f"⚠ Stok '{title}' habis.")
                status_label.setStyleSheet("color: #b91c1c; font-size: 13px; font-weight: bold; background-color: #fee2e2; border: 1px solid #fca5a5; border-radius: 6px; padding: 6px 10px;")
                QtWidgets.QMessageBox.warning(dialog, "Stok Habis", f"Stok {title} tidak mencukupi.")
                is_processing = False
                QtCore.QTimer.singleShot(0, refocus_input)
                return

            sale_price = price + 5000

            confirmation = QtWidgets.QMessageBox(dialog)
            confirmation.setWindowTitle("Konfirmasi Transaksi")
            confirmation.setIcon(QtWidgets.QMessageBox.Question)
            confirmation.setWindowModality(Qt.WindowModal)
            confirmation.setText(
                f"Judul buku: {title}\n"
                f"Harga asli: Rp {price:,.0f}\n"
                f"Harga jual: Rp {sale_price:,.0f}\n\n"
                "Simpan transaksi ini?"
            )
            save_button = confirmation.addButton(
                "Simpan Transaksi", QtWidgets.QMessageBox.AcceptRole
            )
            cancel_button = confirmation.addButton("Batal", QtWidgets.QMessageBox.RejectRole)
            confirmation.setDefaultButton(save_button)
            confirmation.exec_()

            if confirmation.clickedButton() != save_button:
                # Transaksi batal: hanya pop up konfirmasi yang ditutup, pop up buka kasir tetap terbuka
                status_label.setText(f"Transaksi untuk '{title}' dibatalkan. Siap scan buku berikutnya.")
                status_label.setStyleSheet("color: #b45309; font-size: 13px; font-weight: 500; background-color: #fef3c7; border: 1px solid #fde68a; border-radius: 6px; padding: 6px 10px;")
                is_processing = False
                QtCore.QTimer.singleShot(0, refocus_input)
                return

            cursor = self.db.conn.cursor()
            try:
                cursor.execute(
                    "SELECT judul, harga, stok FROM sale_products WHERE id=? AND barcode=?",
                    (product_id, barcode),
                )
                current_product = cursor.fetchone()
                if not current_product:
                    raise ValueError("Produk berubah atau tidak lagi terdaftar. Silakan scan ulang.")
                current_title, current_price, current_stock = current_product
                if current_stock <= 0:
                    raise ValueError(f"Stok {current_title} sudah habis.")
                if current_title != title or current_price != price:
                    raise ValueError(
                        "Data produk berubah setelah konfirmasi dibuka. Silakan scan ulang."
                    )

                cursor.execute(
                    "UPDATE sale_products SET stok=stok-1 WHERE id=? AND barcode=? AND stok>0",
                    (product_id, barcode),
                )
                if cursor.rowcount != 1:
                    raise ValueError(f"Stok {title} sudah habis.")

                cursor.execute(
                    "INSERT INTO sales(total, created_at, dibuat_oleh) VALUES(?,?,?)",
                    (
                        sale_price,
                        datetime.now().isoformat(),
                        self.current_user.get("username") if self.current_user else "Sistem",
                    ),
                )
                sale_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO sale_items(sale_id, product_id, jumlah, harga, harga_asli) "
                    "VALUES(?,?,?,?,?)",
                    (sale_id, product_id, 1, sale_price, price),
                )
                self.db.conn.commit()

                session_total += sale_price
                saved_count += 1
                row_index = session_table.rowCount()
                session_table.insertRow(row_index)
                values = [
                    datetime.now().strftime("%H:%M:%S"),
                    title,
                    f"Rp {price:,.0f}",
                    f"Rp {sale_price:,.0f}",
                ]
                for column, value in enumerate(values):
                    session_table.setItem(
                        row_index, column, QtWidgets.QTableWidgetItem(value)
                    )
                session_table.scrollToBottom()
                total_label.setText(
                    f"Total transaksi tersimpan: Rp {session_total:,.0f}"
                )

                # Feedback instan di jendela kasir tanpa pop up blocking yang menghentikan ritme scan
                status_label.setText(
                    f"✓ Transaksi '{title}' (Harga Jual: Rp {sale_price:,.0f}) BERHASIL DISIMPAN! Siap scan berikutnya."
                )
                status_label.setStyleSheet("color: #15803d; font-size: 13px; font-weight: bold; background-color: #dcfce7; border: 1px solid #86efac; border-radius: 6px; padding: 6px 10px;")
            except Exception as error:
                self.db.conn.rollback()
                status_label.setText(f"❌ Gagal menyimpan transaksi: {error}")
                status_label.setStyleSheet("color: #b91c1c; font-size: 13px; font-weight: bold; background-color: #fee2e2; border: 1px solid #fca5a5; border-radius: 6px; padding: 6px 10px;")
                QtWidgets.QMessageBox.critical(dialog, "Gagal Menyimpan", str(error))
            finally:
                is_processing = False
                QtCore.QTimer.singleShot(0, refocus_input)

        barcode_input.returnPressed.connect(add_scanned_product)

        def close_cashier():
            dialog.hide()
            dialog.accept()

        close_button.clicked.connect(close_cashier)

        def on_dialog_close(event):
            dialog.hide()
            event.accept()

        dialog.closeEvent = on_dialog_close

        QtCore.QTimer.singleShot(0, refocus_input)
        dialog.exec_()

        # Update tabel data penjualan utama setelah jendela kasir ditutup
        # Hanya jika ada transaksi yang disimpan selama kasir dibuka
        if saved_count > 0:
            QtCore.QTimer.singleShot(10, self.load_sale_products)

    def setup_sales_tab(self):
        tab_sales = QtWidgets.QWidget()
        self.tabs.addTab(tab_sales, "Penjualan")
        layout = QtWidgets.QVBoxLayout(tab_sales)
        actions = QtWidgets.QHBoxLayout()
        import_button = QtWidgets.QPushButton("Import Excel Buku Jual")
        cashier_button = QtWidgets.QPushButton("Buka Kasir")
        refresh_button = QtWidgets.QPushButton("Refresh")
        for button in (import_button, cashier_button, refresh_button):
            button.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addWidget(QtWidgets.QLabel(
            "Kolom tabel mengikuti sheet FAKTUR: No, Judul, Barcode, Stok, Harga, Total Harga."
        ))
        self.sale_products_table = QtWidgets.QTableWidget(0, 6)
        self.sale_products_table.setHorizontalHeaderLabels(
            ["No", "Judul", "Barcode", "Stok", "Harga", "Total Harga"]
        )
        header = self.sale_products_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.sale_products_table.setColumnWidth(0, 50)
        self.sale_products_table.setColumnWidth(2, 140)
        self.sale_products_table.setColumnWidth(3, 70)
        self.sale_products_table.setColumnWidth(4, 110)
        self.sale_products_table.setColumnWidth(5, 120)
        layout.addWidget(self.sale_products_table)
        import_button.clicked.connect(self.import_sale_products_from_excel)
        cashier_button.clicked.connect(self.open_sales_cashier)
        refresh_button.clicked.connect(self.load_sale_products)
        self.load_sale_products()

    # -------------------- ANGGOTA ---------------------
    def import_new_members_from_excel(self, refresh_callback=None):
        """Import santri baru, buat QR, dan ekspor data QR ke Excel."""
        try:
            import pandas as pd
        except ImportError:
            QtWidgets.QMessageBox.warning(
                self, "Dependensi Belum Ada",
                "Import Excel membutuhkan pandas dan openpyxl.\n\n"
                "Jalankan: pip install pandas openpyxl"
            )
            return

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Pilih Data Santri Baru", "",
            "Excel/CSV Files (*.xlsx *.xls *.csv)"
        )
        if not path:
            return

        try:
            df = pd.read_csv(path) if path.lower().endswith('.csv') else pd.read_excel(path)
            columns = {str(column).strip().lower(): column for column in df.columns}

            def column_value(row, *names):
                for name in names:
                    if name in columns:
                        value = row[columns[name]]
                        if pd.notna(value):
                            return str(value).strip()
                return ""

            required_columns = {
                "nama": ("nama", "name", "nama lengkap"),
                "rayon": ("rayon", "asrama"),
                "kamar": ("kamar", "nomor kamar", "room")
            }
            missing_columns = [
                label for label, names in required_columns.items()
                if not any(name in columns for name in names)
            ]
            if missing_columns:
                raise ValueError(
                    "Kolom wajib tidak ditemukan: " + ", ".join(missing_columns) +
                    ". Minimal Excel: nama, rayon, kamar."
                )

            cursor = self.db.conn.cursor()
            inserted = 0
            skipped = 0
            imported_members = []
            for _, row in df.iterrows():
                nama = column_value(row, "nama", "name", "nama lengkap")
                if not nama:
                    skipped += 1
                    continue

                nis = column_value(row, "nis", "nisn")
                kamar = column_value(row, "kamar", "nomor kamar", "room")
                rayon = column_value(row, "rayon", "asrama")
                alamat = column_value(row, "alamat", "address")
                if not rayon or not kamar:
                    skipped += 1
                    continue

                cursor.execute(
                    "SELECT id FROM members WHERE nama=? AND COALESCE(nis, '')=?",
                    (nama, nis)
                )
                if cursor.fetchone():
                    skipped += 1
                    continue

                import uuid
                barcode = f"SANTRI-{uuid.uuid4().hex[:12].upper()}"
                qr_id = self.db.generate_qr_id()
                self.db.generate_qr_for_member(barcode)
                cursor.execute(
                    "INSERT INTO members(nis, nama, rayon, kamar, alamat, barcode, jenis_santri, qr_id) VALUES(?,?,?,?,?,?,?,?)",
                    (nis, nama, rayon, kamar, alamat, barcode, "baru", qr_id)
                )
                imported_members.append({
                    "nama": nama,
                    "rayon": rayon,
                    "kamar": kamar,
                    "qr_id": qr_id,
                    "barcode": barcode,
                })
                inserted += 1

            self.db.conn.commit()
            report_path = None
            report_error = None
            if imported_members:
                try:
                    report_path = self.export_imported_members_to_excel(imported_members)
                except Exception as e:
                    report_error = e

            self.refresh_dashboard()
            if refresh_callback:
                refresh_callback()

            report_message = (
                f"\n\nFile Excel data anggota:\n{report_path}"
                if report_path else
                (
                    f"\n\nData berhasil diimpor, tetapi file Excel gagal dibuat:\n{report_error}"
                    if report_error else
                    "\n\nTidak ada anggota baru yang berhasil diimpor, jadi file Excel tidak dibuat."
                )
            )
            message_box = (
                QtWidgets.QMessageBox.warning
                if report_error else
                QtWidgets.QMessageBox.information
            )
            message_box(
                self, "Import Berhasil",
                f"{inserted} data santri baru ditambahkan.\n"
                f"{skipped} baris dilewati karena kosong atau sudah terdaftar.\n\n"
                "QR ID, barcode, dan file QR dibuat otomatis. Santri baru dapat langsung memakai QR tersebut."
                f"{report_message}"
            )
        except Exception as e:
            self.db.conn.rollback()
            QtWidgets.QMessageBox.critical(self, "Import Gagal", f"Data santri gagal diimpor:\n{e}")

    def export_imported_members_to_excel(self, members):
        """Buat Excel untuk anggota yang berhasil ditambahkan dari satu impor."""
        from pathlib import Path
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        if hasattr(sys, '_MEIPASS'):
            laporan_dir = os.path.join(str(Path.home()), "A Latee Library", "laporan")
        else:
            laporan_dir = "laporan"
        os.makedirs(laporan_dir, exist_ok=True)

        filename = f"Data_Anggota_QR_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
        filepath = os.path.join(laporan_dir, filename)

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Anggota Baru"
        headers = ["No", "Nama", "Rayon", "Kamar", "QR ID", "Barcode"]
        worksheet.append(headers)

        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        for cell in worksheet[1]:
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for number, member in enumerate(members, start=1):
            worksheet.append([
                number,
                member["nama"],
                member["rayon"],
                member["kamar"],
                member["qr_id"],
                member["barcode"],
            ])

        for column, width in {"A": 8, "B": 30, "C": 20, "D": 15, "E": 38, "F": 24}.items():
            worksheet.column_dimensions[column].width = width
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        workbook.save(filepath)
        return filepath

    def show_members_dialog(self):
        """Tampilkan dialog popup dengan tabel anggota terdaftar, filter rayon, dan pencarian"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Daftar Anggota Terdaftar")
        dialog.setGeometry(100, 100, 1000, 600)
        dialog.setMinimumSize(800, 450)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # ===== Filter & Search Layout =====
        filter_layout = QtWidgets.QHBoxLayout()
        
        # Filter Rayon
        filter_layout.addWidget(QtWidgets.QLabel(" Rayon:"))
        combo_rayon = QtWidgets.QComboBox()
        combo_rayon.addItem("Semua", None)
        combo_rayon.addItem("Asy-Syafi'ie", "Asy-Syafi'ie")
        combo_rayon.addItem("Al-Bukhori", "Al-Bukhori")
        combo_rayon.addItem("Al-Ghazali", "Al-Ghazali")
        combo_rayon.addItem("LSB", "LSB")
        combo_rayon.addItem("LSM", "LSM")
        combo_rayon.addItem("EAL", "EAL")
        combo_rayon.addItem("LTQ", "LTQ")
        combo_rayon.addItem("DL", "DL")
        combo_rayon.addItem("PRA-DL", "PRA-DL")
        combo_rayon.addItem("KBS", "KBS")
        filter_layout.addWidget(combo_rayon)
        
        filter_layout.addSpacing(20)
        
        # Search bar
        filter_layout.addWidget(QtWidgets.QLabel(" Cari:"))
        search_input = QtWidgets.QLineEdit()
        search_input.setPlaceholderText("Nama, Barcode, atau QR ID...")
        filter_layout.addWidget(search_input)
        
        layout.addLayout(filter_layout)
        
        # ===== Members Table =====
        members_table = QtWidgets.QTableWidget()
        members_table.setContextMenuPolicy(Qt.CustomContextMenu)
        members_table.setColumnCount(6)
        members_table.setHorizontalHeaderLabels(["ID", "Nama", "Rayon", "Kamar", "QR ID", "Barcode"])
        members_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(members_table)
        
        # ===== Load members data =====
        def load_members_dialog():
            rows = self.db.list_members()
            display_members_table(rows)
        
        # ===== Display table dengan data =====
        def display_members_table(rows):
            members_table.setRowCount(len(rows))
            
            for r, row in enumerate(rows):
                # row: (id, nama, rayon, kamar, barcode, qr_id)
                id_v, nama, rayon, kamar, barcode, qr_id = row
                
                items = [
                    str(id_v),
                    str(nama) if nama else "-",
                    str(rayon) if rayon else "-",
                    str(kamar) if kamar else "-",
                    str(qr_id) if qr_id else "-",
                    str(barcode) if barcode else "-"
                ]
                
                for c, v in enumerate(items):
                    members_table.setItem(r, c, QtWidgets.QTableWidgetItem(v))
            
            members_table.resizeColumnsToContents()
        
        # ===== Filter & Search functionality =====
        def filter_and_search():
            selected_rayon = combo_rayon.currentData()
            keyword = search_input.text().strip().lower()
            rows = self.db.list_members()
            
            filtered_rows = []
            for row in rows:
                # row: (id, nama, rayon, kamar, barcode, qr_id)
                id_v, nama, rayon, kamar, barcode, qr_id = row
                
                # Filter by rayon
                if selected_rayon is not None and rayon != selected_rayon:
                    continue
                
                # Filter by keyword (nama, barcode, qr_id)
                if keyword:
                    nama_str = (nama or "").lower()
                    barcode_str = (barcode or "").lower()
                    qr_id_str = (qr_id or "").lower()
                    
                    if not (keyword in nama_str or 
                            keyword in barcode_str or 
                            keyword in qr_id_str):
                        continue
                
                filtered_rows.append(row)
            
            display_members_table(filtered_rows)
            
            # Show count info
            total = len(rows)
            found = len(filtered_rows)
            if keyword or selected_rayon:
                status_text = f"Menampilkan {found} dari {total} anggota"
            else:
                status_text = f"Total {total} anggota"
        
        # ===== Context menu untuk edit dan delete =====
        def show_member_context_menu(position):
            row = members_table.rowAt(position.y())
            if row < 0:
                return
            
            member_id = int(members_table.item(row, 0).text())
            member_name = members_table.item(row, 1).text()
            member_barcode = members_table.item(row, 5).text()
            
            menu = QtWidgets.QMenu()
            action_edit = menu.addAction(" Edit Data")
            
            def handle_edit():
                try:
                    self.edit_member_data(member_id, member_barcode, dialog, load_members_dialog)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(dialog, "Error", f"Gagal membuka dialog edit:\n{str(e)}")
                    import traceback
                    traceback.print_exc()
            
            action_edit.triggered.connect(handle_edit)
            menu.addSeparator()
            action_delete = menu.addAction(" Hapus")
            action = menu.exec_(members_table.mapToGlobal(position))
            
            if action == action_delete:
                confirm = QtWidgets.QMessageBox.question(
                    dialog,
                    "Konfirmasi Hapus",
                    f"Apakah kamu yakin ingin menghapus anggota '{member_name}'?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )
                
                if confirm == QtWidgets.QMessageBox.Yes:
                    try:
                        self.db.delete_member(member_id)
                        load_members_dialog()
                        self.refresh_dashboard()
                        QtWidgets.QMessageBox.information(dialog, "Berhasil", f"Anggota '{member_name}' berhasil dihapus.")
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(dialog, "Error", f"Gagal menghapus anggota:\n{e}")
        
        members_table.customContextMenuRequested.connect(show_member_context_menu)
        combo_rayon.currentIndexChanged.connect(filter_and_search)
        search_input.textChanged.connect(filter_and_search)
        
        # ===== Buttons =====
        btn_layout = QtWidgets.QHBoxLayout()
        btn_import_new = QtWidgets.QPushButton("Import Excel Santri Baru")
        btn_import_new.setToolTip("Import data santri baru, buat QR anggota, dan ekspor hasilnya ke Excel")
        btn_import_new.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        btn_import_new.clicked.connect(lambda: self.import_new_members_from_excel(load_members_dialog))
        btn_layout.addWidget(btn_import_new)

        btn_refresh = QtWidgets.QPushButton(" Muat Ulang")
        btn_refresh.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        btn_refresh.clicked.connect(load_members_dialog)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addStretch()
        
        btn_close = QtWidgets.QPushButton("Tutup")
        btn_close.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        btn_close.clicked.connect(dialog.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        # Load initial data
        load_members_dialog()
        
        # Show dialog
        dialog.exec_()
    
    def load_members(self):
        """Deprecated: load_members() dipindahkan ke dalam show_members_dialog().
        Method ini tetap ada untuk backward compatibility."""
        pass

    # ==================== SISTEM QR GENERATION MASSAL ====================
    def load_pending_qr_codes(self):
        """Load pending QR codes yang belum di-link ke anggota"""
        rows = self.db.list_pending_qr_codes()
        self.display_pending_qr_table(rows)
    
    def search_pending_qr_codes(self):
        """Filter pending QR codes berdasarkan data yang tampil di tabel."""
        keyword = self.in_search_pending_qr.text().strip().lower()
        rows = self.db.list_pending_qr_codes()
        
        # Filter berdasarkan qr_id atau barcode
        filtered_rows = []
        for row in rows:
            # row: (id, qr_id, barcode, status, created_at, nama, kamar, rayon)
            id_v, qr_id, barcode, status, created_at, nama, kamar, rayon = row
            
            # Convert None ke string kosong untuk search
            id_str = str(id_v).lower()
            qr_id_str = (qr_id if qr_id else "").lower()
            barcode_str = (barcode if barcode else "").lower()
            status_str = (status if status else "").lower()
            nama_str = (nama if nama else "").lower()
            rayon_str = (rayon if rayon else "").lower()
            kamar_str = (kamar if kamar else "").lower()
            if (keyword in id_str or keyword in qr_id_str or keyword in barcode_str or
                    keyword in status_str or keyword in nama_str or keyword in rayon_str or
                    keyword in kamar_str):
                filtered_rows.append(row)
        
        self.display_pending_qr_table(filtered_rows)
        
        # Tampilkan info di status bar
        total = len(rows)
        found = len(filtered_rows)
        if keyword:
            self.status.showMessage(f"[CHECK] Ditemukan {found} dari {total} QR codes")
        else:
            self.status.showMessage(f"[*] Total pending QR codes: {total}")
    
    def display_pending_qr_table(self, rows):
        """Display pending QR codes ke table widget"""
        self.pending_qr_table.setRowCount(len(rows))
        self.pending_qr_table.setColumnCount(8)
        self.pending_qr_table.setHorizontalHeaderLabels(["ID", "QR ID", "Barcode", "Status", "Dibuat", "Nama Anggota", "Rayon", "Kamar"])
        
        for r, row in enumerate(rows):
            # row: (id, qr_id, barcode, status, created_at, nama, kamar, rayon)
            id_v, qr_id, barcode, status, created_at, nama, kamar, rayon = row
            
            # Check if QR is blocked
            qr_info = self.db.get_qr_status(barcode)
            is_blocked = qr_info[8] if qr_info and len(qr_info) > 8 else 0
            
            # Format tanggal
            try:
                dt = datetime.fromisoformat(created_at)
                tanggal_str = dt.strftime("%d-%m-%Y %H:%M")
            except:
                tanggal_str = created_at
            
            # Info anggota
            if nama:
                info = nama
            else:
                info = "---"
            
            # Display QR ID atau empty jika None
            qr_id_display = qr_id if qr_id else "---"
            rayon_display = rayon if rayon else "---"
            kamar_display = kamar if kamar else "---"
            
            items = [str(id_v), qr_id_display, barcode, status, tanggal_str, info, rayon_display, kamar_display]
            for c, v in enumerate(items):
                item = QtWidgets.QTableWidgetItem(str(v))
                if status == "pending":
                    item.setBackground(QtGui.QColor(255, 253, 208))  # Light yellow
                elif status == "linked":
                    item.setBackground(QtGui.QColor(200, 255, 200))  # Light green
                elif status == "active":
                    item.setBackground(QtGui.QColor(173, 216, 230))  # Light blue
                self.pending_qr_table.setItem(r, c, item)
        
        self.pending_qr_table.resizeColumnsToContents()
    
    def generate_qr_bulk(self):
        """Generate QR codes & Kartu kosong dalam jumlah massal (tanpa member)"""
        # Ask user berapa banyak QR yang mau dibuat
        count, ok = QtWidgets.QInputDialog.getInt(
            self, 
            "Generate QR Massal",
            "Berapa banyak barcode + kartu yang ingin dibuat?\n(untuk input member nanti)",
            min=1,
            max=1000,
            value=10,
            step=10
        )
        
        if not ok or count <= 0:
            return
        
        # Confirm
        msg = f"Generate {count} QR codes + kartu kosong?\n\n"
        msg += "Kartu akan disimpan tanpa data member.\n"
        msg += "Data member bisa diisi nanti saat registrasi."
        
        reply = QtWidgets.QMessageBox.question(
            self, "Konfirmasi", msg,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply != QtWidgets.QMessageBox.Yes:
            return
        
        # Generate QR codes
        progress = QtWidgets.QProgressDialog(
            "Generating QR codes & kartu...", "Cancel", 0, count, self
        )
        progress.setWindowModality(QtCore.Qt.WindowModal)
        
        success = 0
        failed = 0
        barcodes_created = []
        
        for i in range(count):
            progress.setValue(i)
            QtCore.QCoreApplication.processEvents()
            
            if progress.wasCanceled():
                break
            
            try:
                # Generate random barcode (UUID tanpa member)
                import uuid
                barcode = str(uuid.uuid4())[:12]
                
                # Generate QR via Database class
                qr_path = self.db.generate_qr_for_member(barcode)
                
                # PENTING: Simpan barcode ke database pending_qr_codes SEBELUM membuat kartu
                # Agar QR ID sudah tersedia saat card creation butuh query database
                qr_id_generated = None
                try:
                    self.db.add_pending_qr(barcode)
                    print(f"[DEBUG] add_pending_qr({barcode}) berhasil")
                    
                    # Fetch the generated QR ID immediately from the same connection
                    cursor = self.db.conn.cursor()
                    cursor.execute(
                        "SELECT qr_id FROM pending_qr_codes WHERE barcode = ? LIMIT 1",
                        (barcode,)
                    )
                    result = cursor.fetchone()
                    qr_id_generated = result[0] if result else None
                    print(f"[DEBUG] QR ID generated: {qr_id_generated}")
                except Exception as db_error:
                    print(f"[ERROR] add_pending_qr({barcode}) gagal: {db_error}")
                    import traceback
                    traceback.print_exc()
                
                # Create card dari QR
                try:
                    from PIL import Image
                    from pathlib import Path
                    
                    # Find design_path (compatible dengan installed app)
                    if hasattr(sys, '_MEIPASS'):
                        # Running dari executable (pyinstaller/NSIS)
                        design_path = os.path.join(sys._MEIPASS, "assets", "depan.jpg")
                    else:
                        # Running dari source
                        design_path = os.path.join("assets", "depan.jpg")
                    
                    if not os.path.exists(design_path):
                        raise FileNotFoundError(f"Design file not found: {design_path}")
                    
                    # Open design dan QR
                    design = Image.open(design_path).convert("RGB")
                    qr_img = Image.open(qr_path).convert("RGBA")
                    
                    # Sizing
                    design_width, design_height = design.size
                    qr_size = int(design_width * 0.25)  # 25% dari design width
                    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
                    
                    # Position (centered)
                    paste_x = int(design_width * 0.32) - qr_size // 2
                    paste_y = int(design_height * 0.35) - qr_size // 2
                    
                    # Paste QR
                    design.paste(qr_img, (paste_x, paste_y), qr_img)
                    
                    # TAMBAHKAN BARCODE TEXT DAN QR ID (seperti di create_member_card_with_design)
                    try:
                        from PIL import ImageDraw, ImageFont
                        
                        draw = ImageDraw.Draw(design)
                        
                        # Setup font
                        try:
                            barcode_font_size = int(design_height * 0.034)
                            barcode_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", barcode_font_size)
                            qrid_font_size = int(design_height * 0.032)
                            qrid_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", qrid_font_size)
                        except:
                            try:
                                barcode_font = ImageFont.truetype("arial.ttf", 10)
                                qrid_font = ImageFont.truetype("arial.ttf", 9)
                            except:
                                barcode_font = ImageFont.load_default()
                                qrid_font = ImageFont.load_default()
                        
                        # Warna text = #0A2A4F (RGB 10, 42, 79)
                        text_color = (10, 42, 79)
                        bg_color = (255, 255, 255)  # White background
                        
                        # 1. BARCODE TEXT
                        barcode_text = barcode
                        barcode_x = int(design_width * 0.70)
                        barcode_y = int(design_height * 0.47)
                        white_area_width = int(design_width * 0.35)
                        
                        # Center align horizontal
                        bbox = draw.textbbox((0, 0), barcode_text, font=barcode_font)
                        barcode_text_width = bbox[2] - bbox[0]
                        barcode_left_x = barcode_x - barcode_text_width // 2
                        
                        # Check if text fits
                        if barcode_text_width > white_area_width - 10:
                            while barcode_text_width > white_area_width - 10 and barcode_font_size > 8:
                                barcode_font_size -= 1
                                barcode_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", barcode_font_size)
                                bbox = draw.textbbox((0, 0), barcode_text, font=barcode_font)
                                barcode_text_width = bbox[2] - bbox[0]
                            barcode_left_x = barcode_x - barcode_text_width // 2
                        
                        # Draw white background for barcode
                        text_height = bbox[3] - bbox[1]
                        bg_rect_barcode = [barcode_left_x - 5, barcode_y - 5, barcode_left_x + barcode_text_width + 8, barcode_y + text_height + 8]
                        draw.rectangle(bg_rect_barcode, fill=bg_color)
                        draw.text((barcode_left_x, barcode_y), barcode_text, fill=text_color, font=barcode_font)
                        
                        # 2. QR ID (dari database pending_qr_codes atau dari variable yang sudah di-generate)
                        qr_id_text = ""
                        try:
                            # Coba gunakan qr_id_generated dulu (yang sudah di-fetch setelah insert)
                            if qr_id_generated:
                                qr_id_text = qr_id_generated
                                print(f"[DEBUG] Menggunakan qr_id_generated: {qr_id_text}")
                            else:
                                # Fallback: query dari database dengan self.db.conn
                                cursor = self.db.conn.cursor()
                                cursor.execute(
                                    "SELECT qr_id FROM pending_qr_codes WHERE barcode = ? LIMIT 1",
                                    (barcode,)
                                )
                                result = cursor.fetchone()
                                qr_id_text = result[0] if result else "N/A"
                                print(f"[DEBUG] Fallback query hasil: {qr_id_text}")
                        except Exception as e:
                            print(f"[DEBUG] Error getting QR ID: {e}")
                            qr_id_text = "N/A"
                        
                        # Posisi QR ID di bawah barcode text
                        qrid_y = barcode_y + int(design_height * 0.075)
                        
                        if qr_id_text:
                            bbox = draw.textbbox((0, 0), qr_id_text, font=qrid_font)
                            qrid_text_width = bbox[2] - bbox[0]
                            
                            if qrid_text_width > white_area_width - 10:
                                while qrid_text_width > white_area_width - 10 and qrid_font_size > 8:
                                    qrid_font_size -= 1
                                    qrid_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", qrid_font_size)
                                    bbox = draw.textbbox((0, 0), qr_id_text, font=qrid_font)
                                    qrid_text_width = bbox[2] - bbox[0]
                            
                            qrid_left_x = barcode_left_x
                            text_height = bbox[3] - bbox[1]
                            bg_rect = [qrid_left_x - 5, qrid_y - 5, qrid_left_x + qrid_text_width + 8, qrid_y + text_height + 5]
                            draw.rectangle(bg_rect, fill=bg_color)
                            draw.text((qrid_left_x, qrid_y), qr_id_text, fill=text_color, font=qrid_font)
                    except Exception as text_error:
                        print(f"[WARN] Barcode/QR ID text gagal: {text_error}")
                    
                    # Save card (gunakan folder dari database helper)
                    cards_dir = self.db.get_cards_dir()
                    os.makedirs(cards_dir, exist_ok=True)
                    card_path = os.path.join(cards_dir, f"{barcode}.jpg")
                    design.save(card_path, "JPEG", quality=95)
                    
                    success += 1
                    barcodes_created.append(barcode)
                    progress.setLabelText(f"[OK] Kartu {i+1}/{count}")
                except Exception as e:
                    failed += 1
                    progress.setLabelText(f"[WARN] Kartu {i+1}/{count}: {str(e)}")
                    print(f"[ERROR] Kartu {i+1}: {str(e)}")
                    import traceback
                    traceback.print_exc()
            except Exception as e:
                failed += 1
                progress.setLabelText(f" QR {i+1}/{count}: {str(e)}")
                print(f"[ERROR] QR {i+1}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        progress.setValue(count)
        progress.close()
        
        # Show result
        msg = f"[SUCCESS] Generate QR selesai!\n\n"
        msg += f"Sukses: {success}\n"
        msg += f"Gagal: {failed}\n"
        msg += f"\nQR codes dan kartu disimpan di:\n"
        msg += f" qrcodes/\n"
        msg += f" cards/\n\n"
        msg += f"Barcode yang dibuat:\n"
        for bc in barcodes_created[:5]:  # Show first 5
            msg += f"   {bc}\n"
        if len(barcodes_created) > 5:
            msg += f"  ... dan {len(barcodes_created) - 5} lainnya"
        
        QtWidgets.QMessageBox.information(self, "Sukses", msg)
        self.refresh_dashboard()
        
        # Show result
        msg = f"[SUCCESS] Selesai!\n\n"
        msg += f"Berhasil: {success}\n"
        msg += f"Gagal: {failed}\n\n"
        msg += f"QR codes & kartu tersimpan di folder:\n"
        msg += f"   qrcodes/\n"
        msg += f"   cards/"
        
        QtWidgets.QMessageBox.information(self, "Hasil Generate", msg)
        self.status.showMessage(f"[SUCCESS] Generate massal selesai: {success} sukses, {failed} gagal")
    
    def show_pending_qr_context_menu(self, position):
        """Context menu untuk pending QR codes"""
        try:
            index = self.pending_qr_table.indexAt(position)
            if not index.isValid():
                return
            
            row = index.row()
            barcode = self.pending_qr_table.item(row, 2).text()
            status = self.pending_qr_table.item(row, 3).text()
            
            qr_info = self.db.get_qr_status(barcode)
            is_blocked = 0
            printed_at = None
            
            if qr_info and len(qr_info) > 8:
                is_blocked = qr_info[8]  # Check is_blocked column
            if qr_info and len(qr_info) > 7:
                printed_at = qr_info[7]  # Check printed_at column
            
            menu = QtWidgets.QMenu()
            
            if status == "pending":
                action_input = menu.addAction("Input Data Anggota")
                def handle_input():
                    try:
                        self.input_member_from_qr(barcode)
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(self, "Error", f"Gagal membuka dialog input:\n{str(e)}")
                        import traceback
                        traceback.print_exc()
                action_input.triggered.connect(handle_input)
                menu.addSeparator()
                action_delete = menu.addAction("Hapus QR Ini")
                def handle_delete():
                    try:
                        self.delete_pending_qr(barcode)
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(self, "Error", f"Gagal menghapus QR:\n{str(e)}")
                        import traceback
                        traceback.print_exc()
                action_delete.triggered.connect(handle_delete)
            
            elif status == "linked":
                # QR sudah linked ke anggota
                action_activate = menu.addAction("Aktifkan QR")
                def handle_activate():
                    try:
                        self.activate_qr(barcode)
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(self, "Error", f"Gagal mengaktifkan QR:\n{str(e)}")
                        import traceback
                        traceback.print_exc()
                action_activate.triggered.connect(handle_activate)
                menu.addSeparator()
                action_view = menu.addAction("Lihat Data Anggota")
                def handle_view():
                    try:
                        self.view_member_from_qr(barcode)
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(self, "Error", f"Gagal menampilkan data anggota:\n{str(e)}")
                        import traceback
                        traceback.print_exc()
                action_view.triggered.connect(handle_view)
            
            elif status == "active":
                # QR sudah aktif
                action_view = menu.addAction("Lihat Data Anggota")
                def handle_view_active():
                    try:
                        self.view_member_from_qr(barcode)
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(self, "Error", f"Gagal menampilkan data anggota:\n{str(e)}")
                        import traceback
                        traceback.print_exc()
                action_view.triggered.connect(handle_view_active)
                menu.addSeparator()
                
                if is_blocked:
                    action_unblock = menu.addAction("Unblock QR (Kartu Ditemukan)")
                    def handle_unblock():
                        try:
                            self.unblock_qr_action(barcode)
                        except Exception as e:
                            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal unblock QR:\n{str(e)}")
                            import traceback
                            traceback.print_exc()
                    action_unblock.triggered.connect(handle_unblock)
                else:
                    action_block = menu.addAction("Blokir QR (Kartu Hilang/Rusak)")
                    def handle_block():
                        try:
                            self.block_qr_action(barcode)
                        except Exception as e:
                            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal blokir QR:\n{str(e)}")
                            import traceback
                            traceback.print_exc()
                    action_block.triggered.connect(handle_block)
            
            menu.exec_(self.pending_qr_table.mapToGlobal(position))
        
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal membuka context menu:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def input_member_from_qr(self, barcode):
        """Input data anggota dari QR code"""
        from QRGenerationSystem import MemberDataInputDialog
        
        dlg = MemberDataInputDialog(self, db=self.db, barcode=barcode)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.load_pending_qr_codes()
            self.load_members()
            self.refresh_dashboard()
    
    def edit_member_data(self, member_id, barcode, parent_dialog, refresh_callback):
        """Edit data anggota yang sudah terdaftar"""
        from QRGenerationSystem import MemberDataInputDialog
        
        dlg = MemberDataInputDialog(self, db=self.db, barcode=barcode, member_id=member_id, edit_mode=True)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            refresh_callback()  # Refresh tabel di dialog popup
            self.load_pending_qr_codes()
            self.load_members()
            self.refresh_dashboard()
    
    def delete_pending_qr(self, barcode):
        """Delete pending QR code"""
        reply = QtWidgets.QMessageBox.question(
            self, "Konfirmasi",
            f"Hapus QR code {barcode}?\n\nTindakan ini tidak dapat dibatalkan.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            if self.db.delete_pending_qr(barcode):
                QtWidgets.QMessageBox.information(self, "Sukses", "QR code berhasil dihapus.")
                self.load_pending_qr_codes()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "Hanya QR dengan status pending yang bisa dihapus.")
    
    def view_member_from_qr(self, barcode):
        """View member details dari QR code"""
        # Find member dengan barcode ini
        for row in self.db.list_members():
            if row[5] == barcode:  # row[5] adalah barcode
                member_info = f"ID: {row[0]}\nNama: {row[2]}\nNIS: {row[1]}\nKamar: {row[3]}"
                QtWidgets.QMessageBox.information(self, "Data Anggota", member_info)
                return
    

    def print_all_pending_cards(self):
        """Mark semua QR codes yang sudah linked sebagai printed"""
        rows = self.db.list_pending_qr_codes()
        linked_count = 0
        
        for row in rows:
            id_v, barcode, status, created_at, nama, kamar = row
            if status == "linked" and nama:
                try:
                    self.db.mark_qr_as_printed(barcode)
                    linked_count += 1
                except:
                    pass
        
        if linked_count > 0:
            QtWidgets.QMessageBox.information(
                self, "Sukses",
                f"[OK] {linked_count} QR code siap untuk diaktifkan.\n\n"
                f"Ambil file QR di folder 'qrcodes' untuk desain kartu Anda.\n\n"
                f"Selanjutnya: Klik 'Aktifkan QR' di tabel untuk mengaktifkan kartu."
            )
            self.load_pending_qr_codes()
        else:
            QtWidgets.QMessageBox.warning(
                self, "Info",
                "Tidak ada QR code yang sudah di-link ke anggota."
            )
    
    def activate_qr(self, barcode):
        """Aktifkan QR setelah kartu dicetak"""
        if self.db.activate_qr(barcode):
            QtWidgets.QMessageBox.information(
                self, "Sukses",
                f"[OK] QR code berhasil diaktifkan!\n\n"
                f"Kartu anggota sudah siap digunakan untuk peminjaman."
            )
            self.load_pending_qr_codes()
        else:
            QtWidgets.QMessageBox.warning(
                self, "Error",
                f"[!] QR belum dicetak.\n\n"
                f"Pastikan kartu sudah dicetak sebelum mengaktifkan."
            )
    
    def block_qr_action(self, barcode):
        """Blokir QR jika kartu hilang/rusak"""
        reply = QtWidgets.QMessageBox.question(
            self, "Blokir QR",
            f"Blokir QR code ini karena kartu hilang/rusak?\n\n"
            f"Barcode: {barcode}\n\n"
            f"QR tidak bisa digunakan untuk peminjaman setelah diblokir.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.db.block_qr(barcode)
            QtWidgets.QMessageBox.information(
                self, "Sukses",
                f"[OK] QR code berhasil diblokir.\n\n"
                f"QR tidak bisa digunakan untuk peminjaman."
            )
            self.load_pending_qr_codes()
    
    def unblock_qr_action(self, barcode):
        """Unblock QR jika kartu ditemukan"""
        reply = QtWidgets.QMessageBox.question(
            self, "Unblock QR",
            f"Unblock QR code ini karena kartu ditemukan?\n\n"
            f"Barcode: {barcode}",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.db.unblock_qr(barcode)
            QtWidgets.QMessageBox.information(
                self, "Sukses",
                f"[OK] QR code berhasil di-unblock.\n\n"
                f"QR sudah bisa digunakan lagi untuk peminjaman."
            )
            self.load_pending_qr_codes()

    def add_or_update_member(self):
        """Tambah anggota TANPA barcode (barcode di-generate nanti via tombol Generate QR)"""
        nis = self.m_nis.text().strip()
        nama = self.m_nama.text().strip()
        kamar = self.m_kamar.text().strip()
        alamat = self.m_alamat.text().strip()
        tempat = self.m_tempat.text().strip()
        tgl_lahir = self.m_tgl_lahir.date().toString("yyyy-MM-dd")
        
        if not nama or not kamar:
            self.status.showMessage("[ERROR] Nama dan Kamar wajib diisi!")
            QtWidgets.QMessageBox.warning(self, "Validasi", "Nama dan Kamar wajib diisi!")
            return
        
        try:
            member_id = self.db.add_member(nis, nama, kamar, alamat, tempat, tgl_lahir)
            self.load_members()
            self.refresh_dashboard()
            self.status.showMessage("[SUCCESS] Data anggota berhasil disimpan.")
            msg = f"[SUCCESS] Data anggota berhasil disimpan!\n\n"
            msg += f"Nama: {nama}\n"
            msg += f"NIS: {nis if nis else '(kosong)'}\n"
            msg += f"Kamar: {kamar}\n"
            msg += f"Tempat Lahir: {tempat if tempat else '(kosong)'}\n"
            msg += f"Tanggal Lahir: {tgl_lahir}\n\n"
            msg += f"Catatan: Barcode akan di-generate ketika Anda klik tombol 'Generate QR'"
            QtWidgets.QMessageBox.information(self, "Sukses", msg)
            # Clear form
            self.m_nis.clear()
            self.m_nama.clear()
            self.m_kamar.clear()
            self.m_alamat.clear()
            self.m_tempat.clear()
            self.m_tgl_lahir.setDate(QtCore.QDate.currentDate())
        except Exception as e:
            self.status.showMessage(f"[ERROR] Error: {str(e)}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Terjadi kesalahan:\n{e}")

    def generate_qr_clicked(self):
        """Generate barcode & QR code untuk anggota yang dipilih"""
        print("[DEBUG] ============ generate_qr_clicked() DIPANGGIL ============")
        
        row = self.members_table.currentRow()
        if row < 0:
            print("[DEBUG] No row selected")
            self.status.showMessage("[ERROR] Pilih anggota terlebih dahulu")
            QtWidgets.QMessageBox.warning(self, "Perhatian", "Pilih anggota terlebih dahulu!")
            return
        
        member_id = int(self.members_table.item(row, 0).text())  # ID ada di kolom 0
        nama = self.members_table.item(row, 2).text()
        print(f"[DEBUG] Selected member_id={member_id}, nama={nama}")
        
        try:
            print(f"[DEBUG] Calling db.generate_barcode_for_member({member_id})...")
            barcode, qr_path, card_path = self.db.generate_barcode_for_member(member_id)
            print(f"[DEBUG] Result: barcode={barcode}, qr_path={qr_path}, card_path={card_path}")
            
            self.load_members()
            self.refresh_dashboard()
            
            msg = f"[SUCCESS] QR Code dan Kartu berhasil di-generate!\n\n"
            msg += f"Nama: {nama}\n"
            msg += f"Barcode: {barcode}\n"
            
            if qr_path:
                msg += f" QR Code: {qr_path}\n"
            else:
                msg += f"[WARN] QR Code gagal dibuat\n"
            
            if card_path:
                msg += f" Kartu: {card_path}\n"
                self.status.showMessage(f"[SUCCESS] QR code dan kartu dihasilkan untuk {nama}")
            else:
                msg += f"[WARN] Kartu gagal dibuat\n"
                self.status.showMessage(f"[WARN] Hanya QR code yang berhasil untuk {nama}")
            
            print(f"[DEBUG] Showing message: {msg}")
            QtWidgets.QMessageBox.information(self, "Sukses", msg)
            print("[DEBUG] ============ generate_qr_clicked() SELESAI ============\n")
        except Exception as e:
            print(f"[DEBUG] EXCEPTION: {str(e)}")
            print(f"[DEBUG] Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            self.status.showMessage(f"[ERROR] Error: {str(e)}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal generate QR:\n{e}")
            print("[DEBUG] ============ generate_qr_clicked() SELESAI (ERROR) ============\n")


    # -------------------- PENGUNJUNG ------------------
    def show_visitor_visit_context_menu(self, position):
        row = self.vis_table.rowAt(position.y())
        if row < 0:
            return

        visit_id_item = self.vis_table.item(row, 0)
        if not visit_id_item:
            return

        menu = QtWidgets.QMenu(self)
        delete_action = menu.addAction("Hapus Catatan Kunjungan")
        if menu.exec_(self.vis_table.mapToGlobal(position)) == delete_action:
            self.delete_visitor_visit(int(visit_id_item.text()))

    def delete_visitor_visit(self, visit_id):
        confirmation = QtWidgets.QMessageBox.question(
            self,
            "Hapus Catatan Kunjungan",
            "Yakin ingin menghapus catatan kunjungan ini?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if confirmation != QtWidgets.QMessageBox.Yes:
            return

        try:
            if not self.db.delete_visitor_visit(visit_id):
                QtWidgets.QMessageBox.warning(
                    self, "Data Tidak Ditemukan", "Catatan kunjungan sudah tidak tersedia."
                )
            self.search_visitors_ui()
            self.refresh_dashboard()
        except Exception as error:
            QtWidgets.QMessageBox.critical(
                self, "Gagal", f"Gagal menghapus catatan kunjungan:\n{error}"
            )

    def load_visitors(self):
        c = self.db.conn.cursor()
        # Explicit column selection to avoid schema mismatch
        c.execute("""
            SELECT vv.id, v.nama, v.rayon, v.kamar, v.fingerprint_id, vv.waktu_kunjungan
            FROM visitor_visits vv
            JOIN visitors v ON v.id = vv.visitor_id
            ORDER BY vv.id DESC
            LIMIT 50
        """)
        rows = c.fetchall()
        self.populate_visitors_table(rows)
        self.update_visitor_statistics()
        self.status.showMessage(f"[INFO] Riwayat kunjungan (50 terakhir): {len(rows)}")

    def get_waktu_kunjungan(self, jam):
        """
        Tentukan periode waktu kunjungan berdasarkan jam
        Siang: 08:00 - 11:00
        Malam: 21:00 - 23:00
        """
        try:
            # jam may be a string 'HH' or 'HH:MM:SS' or integer
            if isinstance(jam, str):
                hour = int(jam.split(':')[0]) if ':' in jam else int(jam)
            else:
                hour = int(jam)

            # New ranges: Siang 08:00-11:00, Malam 21:00-23:00
            if 8 <= hour <= 11:
                return "Siang"
            elif 21 <= hour <= 23:
                return "Malam"
            else:
                return "Luar Jam"
        except:
            return "Tidak Terdaftar"

    def populate_visitors_table(self, rows, table_widget=None):
        if table_widget is None:
            table_widget = self.vis_table
            
        table_widget.setRowCount(len(rows))
        # Columns: ID, Nama, Rayon, Kamar, Fingerprint, Tanggal, Jam, Waktu
        table_widget.setColumnCount(8)
        table_widget.setHorizontalHeaderLabels(["ID", "Nama", "Rayon", "Kamar", "Fingerprint", "Tanggal", "Jam", "Waktu"])
        
        for r, row in enumerate(rows):
            if len(row) != 6:
                print(f"[ERROR] Row {r} has {len(row)} values, expected 6: {row}")
                continue
            id_v, nama, rayon, kamar, fingerprint, waktu_iso = row
            
            # Parse waktu_kunjungan (ISO format)
            try:
                dt = datetime.fromisoformat(waktu_iso)
                tanggal = dt.strftime("%d-%m-%Y")
                jam = dt.strftime("%H:%M:%S")
                waktu_status = self.get_waktu_kunjungan(dt.strftime("%H"))
            except:
                tanggal = "-"
                jam = "-"
                waktu_status = "-"
            
            # Isi kolom
            table_widget.setItem(r, 0, QtWidgets.QTableWidgetItem(str(id_v)))
            table_widget.setItem(r, 1, QtWidgets.QTableWidgetItem(str(nama)))
            table_widget.setItem(r, 2, QtWidgets.QTableWidgetItem(str(rayon)))
            table_widget.setItem(r, 3, QtWidgets.QTableWidgetItem(str(kamar)))
            table_widget.setItem(r, 4, QtWidgets.QTableWidgetItem(str(fingerprint)))
            table_widget.setItem(r, 5, QtWidgets.QTableWidgetItem(tanggal))
            table_widget.setItem(r, 6, QtWidgets.QTableWidgetItem(jam))
            
            waktu_item = QtWidgets.QTableWidgetItem(waktu_status)
            if waktu_status == "Siang":
                waktu_item.setBackground(QtGui.QColor(144, 238, 144))
            elif waktu_status == "Malam":
                waktu_item.setBackground(QtGui.QColor(173, 216, 230))
            else:
                waktu_item.setBackground(QtGui.QColor(255, 255, 200))
            table_widget.setItem(r, 7, waktu_item)
        
        table_widget.resizeColumnsToContents()

    def search_visitors_ui(self):
        """Pencarian pengunjung berdasarkan keyword nama"""
        keyword = self.in_search_visitor.text().strip()
        c = self.db.conn.cursor()
        if keyword:
            c.execute("""
                SELECT vv.id, v.nama, v.rayon, v.kamar, v.fingerprint_id, vv.waktu_kunjungan
                FROM visitor_visits vv
                JOIN visitors v ON v.id = vv.visitor_id
                WHERE v.nama LIKE ?
                ORDER BY vv.id DESC
                LIMIT 100
            """, (f"%{keyword}%",))
        else:
            c.execute("""
                SELECT vv.id, v.nama, v.rayon, v.kamar, v.fingerprint_id, vv.waktu_kunjungan
                FROM visitor_visits vv
                JOIN visitors v ON v.id = vv.visitor_id
                ORDER BY vv.id DESC
                LIMIT 50
            """)
        rows = c.fetchall()
        self.populate_visitors_table(rows, self.vis_table)
        self.update_visitor_statistics()
        self.status.showMessage(f"[CHECK] Hasil pencarian: {len(rows)} kunjungan ditemukan")
    
    def update_visitor_statistics(self):
        """Update visitor statistics untuk tab pengunjung"""
        try:
            # Statistik ditampilkan melalui satu tombol Info dan dialog bertab.
            if hasattr(self, 'btn_visitor_info'):
                self.btn_visitor_info.setText(" Info Pengunjung")
        except Exception as e:
            print(f"Error updating visitor statistics: {e}")
    
    def show_visitor_registration_dialog(self):
        """Tampilkan dialog registrasi pengunjung baru"""
        dialog = VisitorRegistrationDialog(self, self.db)
        dialog.fingerprint = self.fingerprint
        result = dialog.exec_()
        
        if result == QtWidgets.QDialog.Accepted:
            data = dialog.get_data()
            
            # Validate data
            if not data['nama']:
                QtWidgets.QMessageBox.warning(self, "Error", "Nama pengunjung harus diisi!")
                return
            
            # Add visitor to database
            try:
                visitor_id = self.db.add_visitor(
                    nama=data['nama'],
                    kamar=data['kamar'],
                    rayon=data['rayon'],
                    fingerprint_id=data.get('fingerprint_id')
                )
                if data.get('fingerprint_id') and data.get('template_bytes'):
                    saved, message = self.db.save_fingerprint_enrollment(
                        int(data['fingerprint_id']),
                        data['nama'],
                        data['template_bytes'],
                        data['rayon'],
                        data['kamar']
                    )
                    if not saved:
                        raise RuntimeError(message)
                QtWidgets.QMessageBox.information(self, "Sukses", f"Pengunjung {data['nama']} berhasil didaftar!")
                self.load_visitors()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Gagal mendaftar pengunjung:\n{e}")
    
    def show_registered_visitors_dialog(self):
        """Tampilkan dialog list pengunjung terdaftar dengan fitur pencarian"""
        dialog = RegisteredVisitorsDialog(self, self.db)
        dialog.exec_()
    
    def show_scan_old_visitor_dialog(self):
        """Tampilkan dialog untuk scan pengunjung lama dengan daftar hadir"""
        self.scan_fingerprint_visitor()
    
    def update_borrow_statistics(self):
        """Update borrow statistics"""
        try:
            # Statistik ditampilkan melalui satu tombol Info dan dialog bertab.
            if hasattr(self, 'btn_borrower_info'):
                self.btn_borrower_info.setText(" Info Peminjaman")
        except Exception as e:
            print(f"Error updating borrow statistics: {e}")

    def _show_ranked_info_dialog(self, title, tab_configs):
        """Tampilkan beberapa statistik terkait dalam satu dialog bertab."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(1050, 720)
        dialog.setMinimumSize(800, 550)
        layout = QtWidgets.QVBoxLayout(dialog)

        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Filter Periode:"))
        combo_period = QtWidgets.QComboBox()
        for label, days in (
            ("Semua Data", None),
            ("1 Bulan (30 hari)", 30),
            ("3 Bulan (90 hari)", 90),
            ("6 Bulan (180 hari)", 180),
            ("1 Tahun (365 hari)", 365),
        ):
            combo_period.addItem(label, days)
        filter_layout.addWidget(combo_period)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        tab_widget = QtWidgets.QTabWidget()
        pages = []
        for tab_name, headers, loader, exporter in tab_configs:
            page = QtWidgets.QWidget()
            page_layout = QtWidgets.QVBoxLayout(page)
            table = QtWidgets.QTableWidget(0, len(headers) + 1)
            table.setHorizontalHeaderLabels(["Peringkat", *headers])
            table.setWordWrap(False)
            table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
            table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
            table.horizontalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.ResizeToContents
            )
            table.horizontalHeader().setStretchLastSection(True)
            page_layout.addWidget(table)

            if exporter:
                export_button = QtWidgets.QPushButton(" Export Excel")
                export_button.clicked.connect(
                    lambda checked=False, callback=exporter: callback(combo_period.currentData())
                )
                page_layout.addWidget(export_button, alignment=QtCore.Qt.AlignRight)

            tab_widget.addTab(page, tab_name)
            pages.append((table, loader))

        def load_statistics():
            days = combo_period.currentData()
            for table, loader in pages:
                rows = loader(days)
                table.setRowCount(len(rows))
                for row_index, row in enumerate(rows):
                    values = [str(row_index + 1), *[str(value) if value not in (None, "") else "-" for value in row]]
                    for column, value in enumerate(values):
                        table.setItem(row_index, column, QtWidgets.QTableWidgetItem(value))
                table.resizeColumnsToContents()

        combo_period.currentIndexChanged.connect(load_statistics)
        load_statistics()
        layout.addWidget(tab_widget)

        close_button = QtWidgets.QPushButton("Tutup")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=QtCore.Qt.AlignRight)
        dialog.exec_()

    def show_visitor_info_dialog(self):
        """Tampilkan ringkasan pengunjung, rayon, dan kamar dalam satu pop-up."""
        def visitor_rows(days):
            return [
                (nama, rayon, kamar, count)
                for nama, count, kamar, rayon in self.db.get_top_visitor(limit=20, days=days)
            ]

        def rayon_rows(days):
            return self.db.get_top_rayon(limit=20, days=days)

        def room_rows(days):
            c = self.db.conn.cursor()
            date_filter = ""
            params = []
            if days is not None:
                date_filter = "WHERE datetime(vv.waktu_kunjungan) >= datetime('now', '-' || ? || ' days')"
                params.append(days)
            c.execute(f'''SELECT v.rayon, v.kamar, COUNT(*) AS count
                          FROM visitor_visits vv
                          JOIN visitors v ON v.id = vv.visitor_id
                          {date_filter}
                          GROUP BY v.rayon, v.kamar ORDER BY count DESC LIMIT 20''', params)
            return c.fetchall()

        self._show_ranked_info_dialog(
            "Info Pengunjung",
            [
                ("Pengunjung", ("Nama Pengunjung", "Rayon", "Kamar", "Jumlah Kunjungan"), visitor_rows, self.export_visitor_statistics),
                ("Rayon", ("Rayon", "Jumlah Pengunjung"), rayon_rows, self.export_rayon_pie_chart),
                ("Kamar", ("Rayon", "Kamar", "Jumlah Pengunjung"), room_rows, self.export_room_statistics),
            ],
        )

    def show_borrower_info_dialog(self):
        """Tampilkan ringkasan peminjam, rayon, dan kamar dalam satu pop-up."""
        def borrower_rows(days):
            return [
                (nama, rayon, kamar, count)
                for nama, count, kamar, rayon in self.db.get_top_borrower(limit=None, days=days)
            ]

        def rayon_rows(days):
            return self.db.get_top_borrow_rayon(limit=None, days=days)

        def room_rows(days):
            c = self.db.conn.cursor()
            date_filter = ""
            params = []
            if days is not None:
                date_filter = "AND datetime(b.tanggal_pinjam) >= datetime('now', '-' || ? || ' days')"
                params.append(days)
            c.execute(f'''SELECT COALESCE(m.rayon, '-'), COALESCE(m.kamar, '-'), COUNT(*) AS count
                          FROM borrows b LEFT JOIN members m ON b.member_id=m.id
                          WHERE b.member_id IS NOT NULL {date_filter}
                          GROUP BY m.rayon, m.kamar ORDER BY count DESC''', params)
            return c.fetchall()

        self._show_ranked_info_dialog(
            "Info Peminjaman",
            [
                ("Peminjam", ("Nama Peminjam", "Rayon", "Kamar", "Jumlah Peminjaman"), borrower_rows, self.export_borrower_statistics),
                ("Rayon", ("Rayon", "Jumlah Peminjaman"), rayon_rows, None),
                ("Kamar", ("Rayon", "Kamar", "Jumlah Peminjaman"), room_rows, None),
            ],
        )

    def show_visitor_statistics_dialog(self):
        """Tampilkan dialog statistik pengunjung dengan filter waktu"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("[INFO] Statistik Pengunjung Terbanyak")
        dialog.setGeometry(100, 100, 700, 500)
        dialog.setMinimumSize(600, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # ===== Filter Waktu =====
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Filter Periode:"))
        
        combo_period = QtWidgets.QComboBox()
        periods = {
            "Semua Data": None,
            "1 Bulan (30 hari)": 30,
            "3 Bulan (90 hari)": 90,
            "6 Bulan (180 hari)": 180,
            "1 Tahun (365 hari)": 365,
        }
        for label, days in periods.items():
            combo_period.addItem(label, days)
        
        filter_layout.addWidget(combo_period)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # ===== Results Table =====
        table = QtWidgets.QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Peringkat", "Nama Pengunjung", "Rayon", "Kamar", "Jumlah Kunjungan"])
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        # ===== Load data function =====
        def load_statistics():
            days = combo_period.currentData()
            top_visitors = self.db.get_top_visitor(limit=20, days=days)
            
            table.setRowCount(len(top_visitors))
            for r, (nama, count, kamar, rayon) in enumerate(top_visitors):
                table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(r + 1)))
                table.setItem(r, 1, QtWidgets.QTableWidgetItem(nama))
                table.setItem(r, 2, QtWidgets.QTableWidgetItem(rayon if rayon else "-"))
                table.setItem(r, 3, QtWidgets.QTableWidgetItem(kamar if kamar else "-"))
                table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(count)))
            
            table.resizeColumnsToContents()
        
        combo_period.currentIndexChanged.connect(load_statistics)
        load_statistics()
        
        # ===== Buttons =====
        btn_layout = QtWidgets.QHBoxLayout()
        btn_export = QtWidgets.QPushButton("[SAVE] Export Excel")
        btn_export.clicked.connect(lambda: self.export_visitor_statistics(combo_period.currentData()))
        btn_layout.addWidget(btn_export)
        btn_layout.addStretch()
        btn_close = QtWidgets.QPushButton("Tutup")
        btn_close.clicked.connect(dialog.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        dialog.exec_()
    
    def show_rayon_statistics_dialog(self):
        """Tampilkan dialog statistik rayon terbanyak dengan filter waktu"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("[INFO] Statistik Rayon Terbanyak")
        dialog.setGeometry(100, 100, 600, 500)
        dialog.setMinimumSize(500, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # ===== Filter Waktu =====
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Filter Periode:"))
        
        combo_period = QtWidgets.QComboBox()
        periods = {
            "Semua Data": None,
            "1 Bulan (30 hari)": 30,
            "3 Bulan (90 hari)": 90,
            "6 Bulan (180 hari)": 180,
            "1 Tahun (365 hari)": 365,
        }
        for label, days in periods.items():
            combo_period.addItem(label, days)
        
        filter_layout.addWidget(combo_period)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # ===== Results Table =====
        table = QtWidgets.QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Peringkat", "Rayon", "Jumlah Pengunjung"])
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        # ===== Load data function =====
        def load_statistics():
            days = combo_period.currentData()
            top_rayons = self.db.get_top_rayon(limit=20, days=days)
            
            table.setRowCount(len(top_rayons))
            for r, (rayon, count) in enumerate(top_rayons):
                table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(r + 1)))
                table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(rayon)))
                table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(count)))
            
            table.resizeColumnsToContents()
        
        combo_period.currentIndexChanged.connect(load_statistics)
        load_statistics()
        
        # ===== Buttons =====
        btn_layout = QtWidgets.QHBoxLayout()
        btn_export_csv = QtWidgets.QPushButton(" Export Excel")
        btn_export_csv.clicked.connect(lambda: self.export_rayon_pie_chart(combo_period.currentData()))
        btn_layout.addWidget(btn_export_csv)
        btn_layout.addStretch()
        btn_close = QtWidgets.QPushButton(" Tutup")
        btn_close.clicked.connect(dialog.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        dialog.exec_()
    
    def show_borrow_rayon_statistics_dialog(self):
        """Show rayon ranking based on borrowing transactions."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Statistik Rayon Peminjaman")
        dialog.resize(560, 420)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(QtWidgets.QLabel("Rayon dengan jumlah peminjaman terbanyak"))
        table = QtWidgets.QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Peringkat", "Rayon", "Jumlah Peminjaman"])
        rows = self.db.get_top_borrow_rayon(limit=50)
        table.setRowCount(len(rows))
        for index, (rayon, count) in enumerate(rows):
            values = [str(index + 1), str(rayon), str(count)]
            for column, value in enumerate(values):
                table.setItem(index, column, QtWidgets.QTableWidgetItem(value))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        close_button = QtWidgets.QPushButton("Tutup")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)
        dialog.exec_()

    def show_borrower_statistics_dialog(self):
        """Tampilkan dialog statistik peminjam terbanyak dengan filter waktu"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("[INFO] Statistik Peminjam Terbanyak")
        dialog.setGeometry(100, 100, 700, 500)
        dialog.setMinimumSize(600, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # ===== Filter Waktu =====
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Filter Periode:"))
        
        combo_period = QtWidgets.QComboBox()
        periods = {
            "Semua Data": None,
            "1 Bulan (30 hari)": 30,
            "3 Bulan (90 hari)": 90,
            "6 Bulan (180 hari)": 180,
            "1 Tahun (365 hari)": 365,
        }
        for label, days in periods.items():
            combo_period.addItem(label, days)
        
        filter_layout.addWidget(combo_period)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # ===== Results Table =====
        table = QtWidgets.QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Peringkat", "Nama Peminjam", "Rayon", "Kamar", "Jumlah Peminjaman"])
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        # ===== Load data function =====
        def load_statistics():
            days = combo_period.currentData()
            top_borrowers = self.db.get_top_borrower(limit=20, days=days)
            
            table.setRowCount(len(top_borrowers))
            for r, (nama, count, kamar, rayon) in enumerate(top_borrowers):
                table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(r + 1)))
                table.setItem(r, 1, QtWidgets.QTableWidgetItem(nama))
                table.setItem(r, 2, QtWidgets.QTableWidgetItem(rayon if rayon else "-"))
                table.setItem(r, 3, QtWidgets.QTableWidgetItem(kamar if kamar else "-"))
                table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(count)))
            
            table.resizeColumnsToContents()
        
        combo_period.currentIndexChanged.connect(load_statistics)
        load_statistics()
        
        # ===== Buttons =====
        btn_layout = QtWidgets.QHBoxLayout()
        btn_export = QtWidgets.QPushButton(" Export Excel")
        btn_export.clicked.connect(lambda: self.export_borrower_statistics(combo_period.currentData()))
        btn_layout.addWidget(btn_export)
        btn_layout.addStretch()
        btn_close = QtWidgets.QPushButton(" Tutup")
        btn_close.clicked.connect(dialog.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        dialog.exec_()
    
    def show_room_statistics_dialog(self):
        """Tampilkan dialog statistik kamar pengunjung terbanyak dengan filter waktu - include rayon"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("[INFO] Statistik Kamar Pengunjung Terbanyak")
        dialog.setGeometry(100, 100, 700, 500)
        dialog.setMinimumSize(600, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # ===== Filter Waktu =====
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Filter Periode:"))
        
        combo_period = QtWidgets.QComboBox()
        periods = {
            "Semua Data": None,
            "1 Bulan (30 hari)": 30,
            "3 Bulan (90 hari)": 90,
            "6 Bulan (180 hari)": 180,
            "1 Tahun (365 hari)": 365,
        }
        for label, days in periods.items():
            combo_period.addItem(label, days)
        
        filter_layout.addWidget(combo_period)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # ===== Results Table =====
        table = QtWidgets.QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Peringkat", "Rayon", "Kamar", "Jumlah Pengunjung"])
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        # ===== Load data function =====
        def load_statistics():
            days = combo_period.currentData()
            # Query untuk mendapat kamar dengan rayon dari visitors table
            c = self.db.conn.cursor()
            if days is None:
                c.execute('''SELECT v.rayon, v.kamar, COUNT(*) as count 
                             FROM visitor_visits vv
                             JOIN visitors v ON v.id = vv.visitor_id
                             GROUP BY v.rayon, v.kamar 
                             ORDER BY count DESC 
                             LIMIT 20''')
            else:
                c.execute(f'''SELECT v.rayon, v.kamar, COUNT(*) as count 
                              FROM visitor_visits vv
                              JOIN visitors v ON v.id = vv.visitor_id
                              WHERE datetime(vv.waktu_kunjungan) >= datetime('now', '-{days} days')
                              GROUP BY v.rayon, v.kamar 
                              ORDER BY count DESC 
                              LIMIT 20''')
            
            top_rooms = c.fetchall()
            
            table.setRowCount(len(top_rooms))
            for r, (rayon, kamar, count) in enumerate(top_rooms):
                table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(r + 1)))
                table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(rayon) if rayon else "-"))
                table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(kamar) if kamar else "-"))
                table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(count)))
            
            table.resizeColumnsToContents()
        
        combo_period.currentIndexChanged.connect(load_statistics)
        load_statistics()
        
        # ===== Buttons =====
        btn_layout = QtWidgets.QHBoxLayout()
        btn_export = QtWidgets.QPushButton(" Export Excel")
        btn_export.clicked.connect(lambda: self.export_room_statistics(combo_period.currentData()))
        btn_layout.addWidget(btn_export)
        btn_layout.addStretch()
        btn_close = QtWidgets.QPushButton(" Tutup")
        btn_close.clicked.connect(dialog.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        dialog.exec_()
    
    def export_visitor_statistics(self, days=None):
        """Export statistik pengunjung terbanyak ke file Excel/CSV"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            import os
            from pathlib import Path
        except ImportError:
            QtWidgets.QMessageBox.warning(self, "Error", "openpyxl belum terinstall.\nInstall: pip install openpyxl")
            return
        
        try:
            # Create laporan folder
            if hasattr(sys, '_MEIPASS'):
                laporan_dir = os.path.join(str(Path.home()), "A Latee Library", "laporan")
            else:
                laporan_dir = "laporan"
            os.makedirs(laporan_dir, exist_ok=True)
            
            # Get data
            top_visitors = self.db.get_top_visitor(limit=100, days=days)
            
            if not top_visitors:
                QtWidgets.QMessageBox.information(self, "Info", "Tidak ada data pengunjung untuk di-export")
                return
            
            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Pengunjung Terbanyak"
            
            # Add title and period info
            period_text = "Semua Data" if days is None else f"{days} Hari Terakhir"
            ws['A1'] = f"Statistik Pengunjung Terbanyak ({period_text})"
            ws['A1'].font = Font(bold=True, size=14)
            ws.merge_cells('A1:E1')
            
            # Add headers
            headers = ["Peringkat", "Nama Pengunjung", "Rayon", "Kamar", "Jumlah Kunjungan"]
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col)
                cell.value = header
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
            
            # Add data
            for r, (nama, count, kamar, rayon) in enumerate(top_visitors, 4):
                ws.cell(row=r, column=1).value = r - 3
                ws.cell(row=r, column=2).value = nama
                ws.cell(row=r, column=3).value = rayon if rayon else "-"
                ws.cell(row=r, column=4).value = kamar if kamar else "-"
                ws.cell(row=r, column=5).value = count
                ws.cell(row=r, column=5).alignment = Alignment(horizontal="center")
            
            # Adjust column widths
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 25
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 18
            
            # Save file with timestamp
            fname = f"Statistik_Pengunjung_Terbanyak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(laporan_dir, fname)
            wb.save(filepath)
            
            QtWidgets.QMessageBox.information(self, "Sukses", f"Data berhasil di-export ke:\nlaporan/{fname}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal export data:\n{e}")
    
    def export_room_statistics(self, days=None):
        """Export statistik kamar terbanyak ke file Excel/CSV"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            import os
            from pathlib import Path
        except ImportError:
            QtWidgets.QMessageBox.warning(self, "Error", "openpyxl belum terinstall.\nInstall: pip install openpyxl")
            return
        
        try:
            # Create laporan folder
            if hasattr(sys, '_MEIPASS'):
                laporan_dir = os.path.join(str(Path.home()), "A Latee Library", "laporan")
            else:
                laporan_dir = "laporan"
            os.makedirs(laporan_dir, exist_ok=True)
            
            # Get data
            top_rooms = self.db.get_top_rayon(limit=100, days=days)
            
            if not top_rooms:
                QtWidgets.QMessageBox.information(self, "Info", "Tidak ada data kamar untuk di-export")
                return
            
            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Kamar Terbanyak"
            
            # Add title and period info
            period_text = "Semua Data" if days is None else f"{days} Hari Terakhir"
            ws['A1'] = f"Statistik Kamar/Rayon Terbanyak ({period_text})"
            ws['A1'].font = Font(bold=True, size=14)
            ws.merge_cells('A1:C1')
            
            # Add headers
            headers = ["Peringkat", "Kamar/Rayon", "Jumlah Pengunjung"]
            header_fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col)
                cell.value = header
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
            
            # Add data
            for r, (kamar, count) in enumerate(top_rooms, 4):
                ws.cell(row=r, column=1).value = r - 3
                ws.cell(row=r, column=2).value = kamar
                ws.cell(row=r, column=3).value = count
                ws.cell(row=r, column=3).alignment = Alignment(horizontal="center")
            
            # Adjust column widths
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 25
            ws.column_dimensions['C'].width = 18
            
            # Save file with timestamp
            fname = f"Statistik_Kamar_Terbanyak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(laporan_dir, fname)
            wb.save(filepath)
            
            QtWidgets.QMessageBox.information(self, "Sukses", f"Data berhasil di-export ke:\nlaporan/{fname}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal export data:\n{e}")
    
    def export_borrower_statistics(self, days=None):
        """Export statistik peminjam terbanyak ke file Excel"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            import os
            from pathlib import Path
        except ImportError:
            QtWidgets.QMessageBox.warning(self, "Error", "openpyxl belum terinstall.\nInstall: pip install openpyxl")
            return
        
        try:
            # Create laporan folder
            if hasattr(sys, '_MEIPASS'):
                laporan_dir = os.path.join(str(Path.home()), "A Latee Library", "laporan")
            else:
                laporan_dir = "laporan"
            os.makedirs(laporan_dir, exist_ok=True)
            
            # Get data
            top_borrowers = self.db.get_top_borrower(limit=100, days=days)
            
            if not top_borrowers:
                QtWidgets.QMessageBox.information(self, "Info", "Tidak ada data peminjam untuk di-export")
                return
            
            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Peminjam Terbanyak"
            
            # Add title and period info
            period_text = "Semua Data" if days is None else f"{days} Hari Terakhir"
            ws['A1'] = f"Statistik Peminjam Terbanyak ({period_text})"
            ws['A1'].font = Font(bold=True, size=14)
            ws.merge_cells('A1:E1')
            
            # Add headers
            headers = ["Peringkat", "Nama Peminjam", "Rayon", "Kamar", "Jumlah Peminjaman"]
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col)
                cell.value = header
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
            
            # Add data
            for r, (nama, count, kamar, rayon) in enumerate(top_borrowers, 4):
                ws.cell(row=r, column=1).value = r - 3
                ws.cell(row=r, column=2).value = nama
                ws.cell(row=r, column=3).value = rayon if rayon else "-"
                ws.cell(row=r, column=4).value = kamar if kamar else "-"
                ws.cell(row=r, column=5).value = count
                ws.cell(row=r, column=5).alignment = Alignment(horizontal="center")
            
            # Adjust column widths
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 25
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 18
            
            # Save file with timestamp
            fname = f"Statistik_Peminjam_Terbanyak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(laporan_dir, fname)
            wb.save(filepath)
            
            QtWidgets.QMessageBox.information(self, "Sukses", f"Data berhasil di-export ke:\nlaporan/{fname}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal export data:\n{e}")
    
    def export_rayon_pie_chart(self, days=None):
        """Export statistik rayon/kamar terbanyak sebagai diagram lingkaran"""
        try:
            import matplotlib.pyplot as plt
            from matplotlib import rcParams
            import os
            from pathlib import Path
            # Set font untuk mendukung bahasa Indonesia
            rcParams['font.sans-serif'] = ['Arial']
        except ImportError:
            QtWidgets.QMessageBox.warning(self, "Error", "matplotlib belum terinstall.\nInstall: pip install matplotlib")
            return
        
        try:
            # Create laporan folder
            if hasattr(sys, '_MEIPASS'):
                laporan_dir = os.path.join(str(Path.home()), "A Latee Library", "laporan")
            else:
                laporan_dir = "laporan"
            os.makedirs(laporan_dir, exist_ok=True)
            
            # Get data
            top_rooms = self.db.get_top_rayon(limit=10, days=days)
            
            if not top_rooms:
                QtWidgets.QMessageBox.information(self, "Info", "Tidak ada data untuk di-export")
                return
            
            # Prepare data for chart
            labels = [str(room[0]) for room in top_rooms]
            sizes = [room[1] for room in top_rooms]
            
            # Create pie chart
            fig, ax = plt.subplots(figsize=(10, 7))
            colors = plt.cm.Set3(range(len(labels)))
            pie_output = ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                colors=colors, startangle=90)
            wedges = pie_output[0]
            texts = pie_output[1]
            autotexts = pie_output[2] if len(pie_output) > 2 else []
            
            # Improve text visibility
            for text in texts:
                text.set_fontsize(10)
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(9)
            
            # Add title
            period_text = "Semua Data" if days is None else f"{days} Hari Terakhir"
            ax.set_title(f"Statistik Kamar/Rayon Terbanyak\n({period_text})", 
                        fontsize=14, fontweight='bold', pad=20)
            
            # Save figure with timestamp
            fname = f"Diagram_Kamar_Terbanyak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(laporan_dir, fname)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            QtWidgets.QMessageBox.information(self, "Sukses", f"Diagram berhasil di-export ke:\nlaporan/{fname}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal export diagram:\n{e}")

    def scan_fingerprint_visitor(self):
        """
        Scan fingerprint pengunjung menggunakan reader USB ZKTeco
        
        Flow:
        1. Buka dialog dengan instruksi
        2. Tunggu user tempelkan jari di reader ZKTeco
        3. SDK ZKTeco membaca fingerprint
        4. Cocokkan dengan database
        5. Catat check-in atau daftarkan pengunjung baru
        """
        # Check fingerprint handler
        if not self.fingerprint:
            self._play_visitor_feedback(False)
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                "Fingerprint scanner tidak tersedia"
            )
            return
        
        if not self.fingerprint.is_connected():
            self._play_visitor_feedback(False)
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                "Fingerprint scanner tidak connect"
            )
            return
        
        # Buka dialog untuk scan fingerprint
        dialog, status_label = self.show_fingerprint_dialog_with_callback()
        if not dialog:
            return
        
        self._visitor_fingerprint_dialog = dialog
        self._visitor_fingerprint_status = status_label
        dialog.finished.connect(self._cancel_visitor_fingerprint_scan)
        QtCore.QTimer.singleShot(0, lambda: self._start_visitor_fingerprint_scan(dialog))

    def _play_visitor_feedback(self, success):
        """Play distinct feedback tones for successful and failed visitor scans."""
        try:
            import winsound
            winsound.Beep(1100 if success else 450, 180 if success else 450)
        except ImportError:
            QtWidgets.QApplication.beep()
        except (OSError, RuntimeError) as error:
            print(f"[VISITOR] Gagal memutar suara: {error}")
            QtWidgets.QApplication.beep()

    def _start_visitor_fingerprint_scan(self, dialog):
        if not dialog.isVisible():
            return

        status_label = getattr(self, "_visitor_fingerprint_status", None)
        if status_label:
            status_label.setStyleSheet(
                "color: #0066cc; font-weight: bold; font-size: 12px; padding: 10px;"
            )
            status_label.setText(
                " Scan otomatis aktif. Tempelkan jari ke reader ZKTeco."
            )

        self._fingerprint_scan_thread = FingerprintScanThread(
            self.fingerprint, self.fingerprint_lock, self
        )
        self._fingerprint_scan_thread.result_ready.connect(
            self._on_visitor_fingerprint_scan_finished
        )
        self._fingerprint_scan_thread.start()

    def _cancel_visitor_fingerprint_scan(self):
        scan_thread = getattr(self, "_fingerprint_scan_thread", None)
        if scan_thread and scan_thread.isRunning():
            scan_thread.cancel()

    @QtCore.pyqtSlot(object, object)
    def _on_visitor_fingerprint_scan_finished(self, fingerprint_id, error):
        dialog = getattr(self, "_visitor_fingerprint_dialog", None)
        status_label = getattr(self, "_visitor_fingerprint_status", None)
        if not dialog or not status_label or not dialog.isVisible():
            return

        if error:
            status_label.setStyleSheet(
                "color: #cc0000; font-weight: bold; font-size: 12px; padding: 10px;"
            )
            status_label.setText(f" Scan gagal: {error}\nScan akan berlanjut otomatis.")
            self._play_visitor_feedback(False)
        elif fingerprint_id is not None:
            self.process_fingerprint_visitor(fingerprint_id, scan_dialog=dialog)
        else:
            error_detail = self.fingerprint.get_last_error() or "Fingerprint tidak terdeteksi"
            status_label.setStyleSheet(
                "color: #cc0000; font-weight: bold; font-size: 12px; padding: 10px;"
            )
            status_label.setText(
                f" Scan gagal: {error_detail}\nScan akan berlanjut otomatis."
            )
            self._play_visitor_feedback(False)

        QtCore.QTimer.singleShot(
            1000, lambda: self._start_visitor_fingerprint_scan(dialog)
        )

    def show_fingerprint_dialog_with_callback(self):
        """
        Dialog untuk scan fingerprint dengan status update dari SDK ZKTeco.
        
        Returns:
            tuple: (dialog, status_label) atau (None, None) jika cancel
        """
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Scan Pengunjung - ZKTeco Fingerprint Reader")
        dialog.setGeometry(150, 150, 550, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Device status
        device_status = QtWidgets.QLabel(
            " ZKTeco Fingerprint Reader: Connected" if self.fingerprint and self.fingerprint.is_connected()
            else " ZKTeco Fingerprint Reader: Tidak terhubung"
        )
        device_status.setStyleSheet(
            "color: green; font-weight: bold; font-size: 11px;" if self.fingerprint and self.fingerprint.is_connected()
            else "color: red; font-weight: bold; font-size: 11px;"
        )
        layout.addWidget(device_status)
        
        # Title
        title = QtWidgets.QLabel(" Scan Fingerprint Pengunjung")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Instructions
        info_label = QtWidgets.QLabel(
            "Instruksi Scan dengan reader ZKTeco:\n"
            "1. Pastikan jari bersih dan kering\n"
            "2. Tempelkan jari ke reader ZKTeco\n"
            "3. Tekan dengan tekanan sedang (jangan terlalu keras)\n"
            "4. Angkat jari setelah scan berhasil; scan berikutnya berjalan otomatis\n\n"
            " Waktu tunggu: 10 detik"
        )
        info_label.setStyleSheet("color: #333; background: #f0f0f0; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Status display (will be updated)
        status_label = QtWidgets.QLabel(" Menunggu jari... Letakkan jari ke reader ZKTeco.")
        status_label.setStyleSheet("color: #0066cc; font-weight: bold; font-size: 12px; padding: 10px;")
        layout.addWidget(status_label)
        
        # Fingerprint ID display
        fp_id_label = QtWidgets.QLabel("Fingerprint ID: [waiting...]")
        fp_id_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(fp_id_label)
        
        # User info (akan diupdate setelah scan)
        user_info_label = QtWidgets.QLabel("")
        user_info_label.setStyleSheet("color: #333; font-size: 10px;")
        layout.addWidget(user_info_label)
        
        # Controls
        btn_layout = QtWidgets.QHBoxLayout()
        btn_cancel = QtWidgets.QPushButton(" Tutup")
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        btn_cancel.clicked.connect(dialog.reject)
        
        # Show dialog
        dialog.show()
        QtCore.QCoreApplication.processEvents()
        
        return dialog, status_label

    def process_fingerprint_visitor(self, fingerprint_id, scan_dialog=None):
        """
        Proses hasil scan fingerprint dari SDK ZKTeco.
        
        Args:
            fingerprint_id (int): ID fingerprint dari SDK ZKTeco
        """
        try:
            # Cari visitor berdasarkan fingerprint_id
            visitor = self.db.get_visitor_by_fingerprint(str(fingerprint_id))
            
            if visitor:
                # Check-in existing visitor
                # Visitor data is returned as (id, nama, rayon, kamar, ...).
                vid = visitor[0]
                nama = visitor[1]
                rayon = visitor[2]
                kamar = visitor[3]
                
                # Record a separate row for every check-in.
                self.db.add_visitor_visit(vid)
                
                # Show welcome message
                waktu = datetime.now().strftime('%H:%M:%S')
                msg = (
                    f" SELAMAT DATANG KEMBALI!\n\n"
                    f" Nama: {nama}\n"
                    f" Kamar: {kamar}\n"
                    f" Rayon: {rayon or '-'}\n\n"
                    f" Waktu: {waktu}"
                )
                if scan_dialog:
                    self._set_visitor_scan_feedback(
                        scan_dialog,
                        f" Check-in berhasil!\nNama: {nama} | Kamar: {kamar} | Rayon: {rayon or '-'}\nWaktu: {waktu}",
                        True
                    )
                else:
                    QtWidgets.QMessageBox.information(self, "Check-in Berhasil", msg)
            
            else:
                # New fingerprint - ask for visitor data
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle("Daftarkan Pengunjung Baru")
                dialog.setGeometry(150, 150, 400, 300)
                layout = QtWidgets.QFormLayout(dialog)
                
                inp_nama = QtWidgets.QLineEdit()
                inp_kamar = QtWidgets.QLineEdit()
                inp_rayon = QtWidgets.QComboBox()
                inp_rayon.addItems(["Umum", "LTQ", "DL", "PRA-DL", "KBS"])
                
                layout.addRow("Nama Pengunjung:", inp_nama)
                layout.addRow("Kamar/Kelas:", inp_kamar)
                layout.addRow("Rayon:", inp_rayon)
                
                btn_layout = QtWidgets.QHBoxLayout()
                btn_save = QtWidgets.QPushButton(" Simpan & Catat Check-in")
                btn_cancel = QtWidgets.QPushButton(" Batal")
                btn_layout.addWidget(btn_save)
                btn_layout.addWidget(btn_cancel)
                layout.addRow(btn_layout)
                
                registration_saved = {"nama": None, "kamar": None, "rayon": None}

                def on_save():
                    nama = inp_nama.text().strip()
                    kamar = inp_kamar.text().strip() or "Umum"
                    rayon = inp_rayon.currentText()
                    
                    if not nama:
                        if scan_dialog:
                            self._set_visitor_scan_feedback(
                                scan_dialog, " Check-in gagal: nama tidak boleh kosong.", False
                            )
                        else:
                            self._play_visitor_feedback(False)
                        QtWidgets.QMessageBox.warning(dialog, "Validasi", "Nama tidak boleh kosong!")
                        return
                    
                    # Save to database
                    try:
                        self.db.add_visitor(nama, kamar, rayon, str(fingerprint_id))
                    except Exception as error:
                        if scan_dialog:
                            self._set_visitor_scan_feedback(
                                scan_dialog, f" Check-in gagal: {error}", False
                            )
                        QtWidgets.QMessageBox.critical(
                            dialog, "Gagal Menyimpan", f"Data pengunjung gagal disimpan:\n{error}"
                        )
                        return
                    registration_saved.update(nama=nama, kamar=kamar, rayon=rayon)
                    dialog.accept()
                
                btn_save.clicked.connect(on_save)
                btn_cancel.clicked.connect(dialog.reject)
                
                dialog.exec()

                if registration_saved["nama"] and scan_dialog:
                    self._set_visitor_scan_feedback(
                        scan_dialog,
                        f" Check-in berhasil!\nNama: {registration_saved['nama']} | "
                        f"Kamar: {registration_saved['kamar']} | Rayon: {registration_saved['rayon']}",
                        True
                    )
                elif registration_saved["nama"]:
                    QtWidgets.QMessageBox.information(
                        self,
                        "Sukses",
                        f"Pengunjung {registration_saved['nama']} berhasil dicatat."
                    )
                elif not registration_saved["nama"]:
                    if scan_dialog and scan_dialog.isVisible():
                        status_label = getattr(self, "_visitor_fingerprint_status", None)
                        if status_label:
                            status_label.setText(
                                " Pendaftaran dibatalkan. Scan akan berlanjut otomatis."
                            )
                    return
            
            # Refresh tampilan
            self.load_visitors()
            self.refresh_dashboard()
            self.status.showMessage(f" Check-in berhasil - Fingerprint ID: {fingerprint_id}")
        
        except Exception as e:
            if scan_dialog:
                self._set_visitor_scan_feedback(
                    scan_dialog, f" Check-in gagal: {e}", False
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error",
                    f" Gagal memproses fingerprint:\n{str(e)}"
                )

    def _set_visitor_scan_feedback(self, scan_dialog, message, success):
        status_label = getattr(self, "_visitor_fingerprint_status", None)
        if status_label and scan_dialog.isVisible():
            color = "#008000" if success else "#cc0000"
            status_label.setStyleSheet(
                f"color: {color}; font-weight: bold; font-size: 12px; padding: 10px;"
            )
            status_label.setText(message)
        self._play_visitor_feedback(success)

    # -------------------- PINJAM/KEMBALI --------------
    def _status_table_item(self, status):
        """Create a readable status cell for borrowing and return tables."""
        status_item = QtWidgets.QTableWidgetItem(status)
        colors = {
            "AMAN": ("#dcfce7", "#166534"),
            "TERLAMBAT": ("#fee2e2", "#991b1b"),
            "DIPERPANJANG": ("#ffedd5", "#9a3412"),
            "DIKEMBALIKAN": ("#dbeafe", "#1e40af"),
        }
        background, foreground = colors.get(status, ("#f1f5f9", "#334155"))
        status_item.setBackground(QtGui.QColor(background))
        status_item.setForeground(QtGui.QColor(foreground))
        status_item.setTextAlignment(QtCore.Qt.AlignCenter)
        status_item.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        return status_item

    def load_borrows(self):
        # Load peminjaman aktif (status=0)
        rows = self.db.active_borrows()
        self.borrow_table.setRowCount(len(rows))
        self.borrow_table.setColumnCount(10)
        self.borrow_table.setHorizontalHeaderLabels(["ID", "Judul Buku", "Nama Peminjam", "Rayon", "Kamar", "Tanggal Pinjam", "Batas Waktu", "Status", "Denda", "Dibuat Oleh"])
        for r, row in enumerate(rows):
            id_v, judul, nama, rayon, kamar, tanggal_pinjam, diperpanjang = row
            # Kalkulasi batas waktu: tanggal pinjam dihitung sebagai hari pertama.
            try:
                batas_dt = self.db.borrow_deadline(tanggal_pinjam, diperpanjang)
                batas_str = batas_dt.strftime("%d-%m-%Y")
                hari_terlambat, denda = self.db.calculate_fine(tanggal_pinjam, diperpanjang)
                
                # Tentukan status peminjaman
                if hari_terlambat:
                    status_str = "TERLAMBAT"
                    batas_str += " [WARN]"
                elif diperpanjang == 1:
                    status_str = "DIPERPANJANG"
                else:
                    status_str = "AMAN"
                denda_str = f"Rp {denda:,}" if denda > 0 else "Rp 0"
            except:
                batas_str = "-"
                status_str = "-"
                denda_str = "Rp 0"
            
            self.borrow_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(id_v)))
            self.borrow_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(judul)))
            self.borrow_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(nama)))
            self.borrow_table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(rayon)))
            self.borrow_table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(kamar)))
            self.borrow_table.setItem(r, 5, QtWidgets.QTableWidgetItem(str(tanggal_pinjam)))
            
            # Item untuk batas waktu dengan color coding
            batas_item = QtWidgets.QTableWidgetItem(batas_str)
            if status_str == "TERLAMBAT":
                batas_item.setBackground(QtGui.QColor(255, 200, 200))  # Light red
            elif status_str == "DIPERPANJANG":
                batas_item.setBackground(QtGui.QColor(255, 235, 180))  # Light orange
            else:
                batas_item.setBackground(QtGui.QColor(200, 255, 200))  # Light green
            self.borrow_table.setItem(r, 6, batas_item)
            
            self.borrow_table.setItem(r, 7, self._status_table_item(status_str))
            
            self.borrow_table.setItem(r, 8, QtWidgets.QTableWidgetItem(denda_str))
            audit = self.db.get_transaction_audit(id_v)
            self.borrow_table.setItem(r, 9, QtWidgets.QTableWidgetItem(audit[0] or "Sistem"))
        
        self.borrow_table.resizeColumnsToContents()
        self.borrow_table.setColumnWidth(7, max(self.borrow_table.columnWidth(7), 110))
        
        # Load peminjaman selesai (status=1)
        completed_rows = self.db.completed_borrows()
        self.borrow_completed_table.setRowCount(len(completed_rows))
        self.borrow_completed_table.setColumnCount(10)
        self.borrow_completed_table.setHorizontalHeaderLabels(["ID", "Judul Buku", "Nama Peminjam", "Rayon", "Kamar", "Tanggal Pinjam", "Tanggal Kembali", "Status", "Denda", "Dikembalikan Oleh"])
        for r, row in enumerate(completed_rows):
            # row format: (id, judul, nama, rayon, kamar, tanggal_pinjam, tanggal_kembali)
            id_v, judul, nama, rayon, kamar, tanggal_pinjam, tanggal_kembali = row
            
            # Get denda untuk borrow ini
            c = self.db.conn.cursor()
            c.execute('SELECT denda FROM borrows WHERE id=?', (id_v,))
            denda_row = c.fetchone()
            denda = denda_row[0] if denda_row else 0
            denda_str = f"Rp {denda:,}" if denda > 0 else "Rp 0"
            
            self.borrow_completed_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(id_v)))
            self.borrow_completed_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(judul)))
            self.borrow_completed_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(nama)))
            self.borrow_completed_table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(rayon)))
            self.borrow_completed_table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(kamar)))
            self.borrow_completed_table.setItem(r, 5, QtWidgets.QTableWidgetItem(str(tanggal_pinjam)))
            self.borrow_completed_table.setItem(r, 6, QtWidgets.QTableWidgetItem(str(tanggal_kembali)))
            self.borrow_completed_table.setItem(r, 7, self._status_table_item("DIKEMBALIKAN"))
            self.borrow_completed_table.setItem(r, 8, QtWidgets.QTableWidgetItem(denda_str))
            audit = self.db.get_transaction_audit(id_v)
            self.borrow_completed_table.setItem(r, 9, QtWidgets.QTableWidgetItem(audit[1] or "-"))
        self.borrow_completed_table.resizeColumnsToContents()
        
        # Update statistics
        self.update_borrow_statistics()
        
        self.status.showMessage(f"Peminjaman aktif: {len(rows)} | Selesai: {len(completed_rows)}")


    def search_borrows_ui(self):
        """Pencarian peminjaman berdasarkan keyword nama peminjam atau judul buku untuk KEDUA TABEL"""
        keyword = self.in_search_pinjam.text().strip()
        
        if keyword:
            # Cari di peminjaman aktif
            active_rows = self.db.search_borrows(keyword)
            # Cari di peminjaman selesai
            completed_rows = self.db.search_completed_borrows(keyword)
        else:
            # Tampilkan semua peminjaman aktif dan selesai
            active_rows = self.db.active_borrows()
            completed_rows = self.db.completed_borrows()
        
        # Update tabel peminjaman aktif
        self.borrow_table.setRowCount(len(active_rows))
        self.borrow_table.setColumnCount(7)
        self.borrow_table.setHorizontalHeaderLabels(["ID", "Judul Buku", "Nama Peminjam", "Tanggal Pinjam", "Batas Waktu", "Status", "Denda"])
        for r, row in enumerate(active_rows):
            id_v, judul, nama = row[:3]
            if len(row) >= 7:
                tanggal_pinjam, diperpanjang = row[5:7]
            else:
                tanggal_pinjam, diperpanjang = row[3:5]
            try:
                batas_dt = self.db.borrow_deadline(tanggal_pinjam, diperpanjang)
                batas_str = batas_dt.strftime("%d-%m-%Y")
                
                if datetime.now() > batas_dt:
                    status_str = "TERLAMBAT"
                    batas_str += " [WARN]"
                else:
                    status_str = "AMAN"
            except:
                batas_str = "-"
                status_str = "-"
            
            self.borrow_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(id_v)))
            self.borrow_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(judul)))
            self.borrow_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(nama)))
            self.borrow_table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(tanggal_pinjam)))
            
            batas_item = QtWidgets.QTableWidgetItem(batas_str)
            if "TERLAMBAT" in status_str:
                batas_item.setBackground(QtGui.QColor(255, 200, 200))
            else:
                batas_item.setBackground(QtGui.QColor(200, 255, 200))
            self.borrow_table.setItem(r, 4, batas_item)
            
            self.borrow_table.setItem(r, 5, self._status_table_item(status_str))
            _, denda = self.db.calculate_fine(tanggal_pinjam, diperpanjang)
            self.borrow_table.setItem(r, 6, QtWidgets.QTableWidgetItem(f"Rp {denda:,}" if denda else "Rp 0"))
        
        self.borrow_table.resizeColumnsToContents()
        self.borrow_table.setColumnWidth(5, max(self.borrow_table.columnWidth(5), 110))
        
        # Update tabel peminjaman selesai
        self.borrow_completed_table.setRowCount(len(completed_rows))
        self.borrow_completed_table.setColumnCount(7)
        self.borrow_completed_table.setHorizontalHeaderLabels(["ID", "Judul Buku", "Nama Peminjam", "Tanggal Pinjam", "Tanggal Kembali", "Denda", "Status"])
        for r, row in enumerate(completed_rows):
            if len(row) == 7:
                id_v, judul, nama, rayon, kamar, tanggal_pinjam, tanggal_kembali = row
            else:
                id_v, judul, nama, rayon, kamar, tanggal_pinjam, tanggal_kembali = row[:7]
            c = self.db.conn.cursor()
            c.execute("SELECT denda FROM borrows WHERE id=?", (id_v,))
            denda_row = c.fetchone()
            denda = denda_row[0] if denda_row else 0
            values = [id_v, judul, nama, tanggal_pinjam, tanggal_kembali, f"Rp {denda:,}" if denda else "Rp 0"]
            for col, value in enumerate(values):
                self.borrow_completed_table.setItem(r, col, QtWidgets.QTableWidgetItem(str(value)))
            self.borrow_completed_table.setItem(r, 6, self._status_table_item("DIKEMBALIKAN"))
        self.borrow_completed_table.resizeColumnsToContents()
        
        # Update status message
        if keyword:
            total = len(active_rows) + len(completed_rows)
            self.status.showMessage(f"� Hasil pencarian: {len(active_rows)} aktif + {len(completed_rows)} selesai (Total: {total})")
        else:
            self.status.showMessage(f"��� Peminjaman aktif: {len(active_rows)} | [OK] Selesai: {len(completed_rows)}")

    def load_returns(self):
        """Load data pengembalian dengan dua tabel: belum selesai (dengan status terlambat/diperpanjang) dan selesai"""
        # Query data peminjaman aktif (belum dikembalikan)
        rows = self.db.active_borrows()
        
        # Pisahkan berdasarkan status
        terlambat_rows = []
        diperpanjang_rows = []
        aman_rows = []
        
        for row in rows:
            id_v, judul, nama, rayon, kamar, tanggal_pinjam, diperpanjang = row
            try:
                batas_dt = self.db.borrow_deadline(tanggal_pinjam, diperpanjang)
                
                if datetime.now() > batas_dt:
                    terlambat_rows.append(row)
                elif diperpanjang == 1:
                    diperpanjang_rows.append(row)
                else:
                    aman_rows.append(row)
            except:
                aman_rows.append(row)
        
        # Gabungkan: terlambat + diperpanjang + aman
        pending_rows = terlambat_rows + diperpanjang_rows + aman_rows
        
        # Load tabel pengembalian belum selesai dengan kolom DENDA
        self.returns_pending_table.setRowCount(len(pending_rows))
        self.returns_pending_table.setColumnCount(10)
        self.returns_pending_table.setHorizontalHeaderLabels(["ID", "Judul Buku", "Nama Peminjam", "Rayon", "Kamar", "Tanggal Pinjam", "Batas Waktu", "Status", "Denda", "Dibuat Oleh"])
        
        for r, row in enumerate(pending_rows):
            id_v, judul, nama, rayon, kamar, tanggal_pinjam, diperpanjang = row
            try:
                batas_dt = self.db.borrow_deadline(tanggal_pinjam, diperpanjang)
                batas_str = batas_dt.strftime("%d-%m-%Y")
                
                if datetime.now() > batas_dt:
                    status_str = "TERLAMBAT"
                    bg_color = QtGui.QColor(255, 100, 100)  # Red
                elif diperpanjang == 1:
                    status_str = "DIPERPANJANG"
                    bg_color = QtGui.QColor(255, 165, 0)  # Orange
                else:
                    status_str = "AMAN"
                    bg_color = QtGui.QColor(100, 200, 100)  # Green
            except:
                batas_str = "-"
                status_str = "-"
                bg_color = QtGui.QColor(200, 200, 200)
            
            # Denda berjalan dihitung dari batas waktu; kolom DB baru diisi saat pengembalian.
            _, denda = self.db.calculate_fine(tanggal_pinjam, diperpanjang)
            denda_str = f"Rp {denda:,}" if denda > 0 else "Rp 0"
            
            self.returns_pending_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(id_v)))
            self.returns_pending_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(judul)))
            self.returns_pending_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(nama)))
            self.returns_pending_table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(rayon) if rayon else "-"))
            self.returns_pending_table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(kamar) if kamar else "-"))
            self.returns_pending_table.setItem(r, 5, QtWidgets.QTableWidgetItem(str(tanggal_pinjam)))
            
            batas_item = QtWidgets.QTableWidgetItem(batas_str)
            batas_item.setBackground(bg_color)
            self.returns_pending_table.setItem(r, 6, batas_item)
            
            self.returns_pending_table.setItem(r, 7, self._status_table_item(status_str))
            
            self.returns_pending_table.setItem(r, 8, QtWidgets.QTableWidgetItem(denda_str))
            audit = self.db.get_transaction_audit(id_v)
            self.returns_pending_table.setItem(r, 9, QtWidgets.QTableWidgetItem(audit[0] or "Sistem"))
        
        self.returns_pending_table.resizeColumnsToContents()
        self.returns_pending_table.setColumnWidth(7, max(self.returns_pending_table.columnWidth(7), 110))
        
        # Load tabel pengembalian selesai
        completed_rows = self.db.completed_borrows()
        self.returns_completed_table.setRowCount(len(completed_rows))
        self.returns_completed_table.setColumnCount(10)
        self.returns_completed_table.setHorizontalHeaderLabels(["ID", "Judul Buku", "Nama Peminjam", "Rayon", "Kamar", "Tanggal Pinjam", "Tanggal Kembali", "Status", "Denda", "Dikembalikan Oleh"])
        
        for r, row in enumerate(completed_rows):
            id_v, judul, nama, rayon, kamar, tanggal_pinjam, tanggal_kembali = row[:7]
            
            # Get denda
            c = self.db.conn.cursor()
            c.execute('SELECT denda FROM borrows WHERE id=?', (id_v,))
            denda_row = c.fetchone()
            denda = denda_row[0] if denda_row else 0
            denda_str = f"Rp {denda:,}" if denda > 0 else "Rp 0"
            
            self.returns_completed_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(id_v)))
            self.returns_completed_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(judul)))
            self.returns_completed_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(nama)))
            self.returns_completed_table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(rayon) if rayon else "-"))
            self.returns_completed_table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(kamar) if kamar else "-"))
            self.returns_completed_table.setItem(r, 5, QtWidgets.QTableWidgetItem(str(tanggal_pinjam)))
            self.returns_completed_table.setItem(r, 6, QtWidgets.QTableWidgetItem(str(tanggal_kembali)))
            self.returns_completed_table.setItem(r, 7, self._status_table_item("DIKEMBALIKAN"))
            self.returns_completed_table.setItem(r, 8, QtWidgets.QTableWidgetItem(denda_str))
            audit = self.db.get_transaction_audit(id_v)
            self.returns_completed_table.setItem(r, 9, QtWidgets.QTableWidgetItem(audit[1] or "-"))
        
        self.returns_completed_table.resizeColumnsToContents()
        self.returns_completed_table.setColumnWidth(7, max(self.returns_completed_table.columnWidth(7), 110))
        self.status.showMessage(f"Pengembalian: {len(pending_rows)} menunggu | [OK] {len(completed_rows)} selesai")

    def search_returns_ui(self):
        """Pencarian data pengembalian mencakup KEDUA tabel (belum selesai & selesai) berdasarkan nama peminjam atau judul buku"""
        keyword = self.in_search_kembali.text().strip()
        
        # ===== TABEL 1: PENGEMBALIAN BELUM SELESAI =====
        if keyword:
            rows = self.db.search_returns(keyword)
        else:
            rows = self.db.active_borrows()
        
        # Pisahkan berdasarkan status
        terlambat_rows = []
        diperpanjang_rows = []
        aman_rows = []
        
        for row in rows:
            id_v, judul, nama, rayon, kamar, tanggal_pinjam, diperpanjang = row
            try:
                batas_dt = self.db.borrow_deadline(tanggal_pinjam, diperpanjang)
                
                if datetime.now() > batas_dt:
                    terlambat_rows.append(row)
                elif diperpanjang == 1:
                    diperpanjang_rows.append(row)
                else:
                    aman_rows.append(row)
            except:
                aman_rows.append(row)
        
        # Gabungkan: terlambat + diperpanjang + aman
        pending_rows = terlambat_rows + diperpanjang_rows + aman_rows
        
        # Update tabel pengembalian belum selesai
        self.returns_pending_table.setRowCount(len(pending_rows))
        self.returns_pending_table.setColumnCount(10)
        self.returns_pending_table.setHorizontalHeaderLabels(["ID", "Judul Buku", "Nama Peminjam", "Rayon", "Kamar", "Tanggal Pinjam", "Batas Waktu", "Status", "Denda", "Dibuat Oleh"])
        
        for r, row in enumerate(pending_rows):
            id_v, judul, nama, rayon, kamar, tanggal_pinjam, diperpanjang = row
            try:
                batas_dt = self.db.borrow_deadline(tanggal_pinjam, diperpanjang)
                batas_str = batas_dt.strftime("%d-%m-%Y")
                
                if datetime.now() > batas_dt:
                    status_str = "TERLAMBAT"
                    bg_color = QtGui.QColor(255, 100, 100)
                elif diperpanjang == 1:
                    status_str = "DIPERPANJANG"
                    bg_color = QtGui.QColor(255, 165, 0)
                else:
                    status_str = "AMAN"
                    bg_color = QtGui.QColor(100, 200, 100)
            except:
                batas_str = "-"
                status_str = "-"
                bg_color = QtGui.QColor(200, 200, 200)
            
            self.returns_pending_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(id_v)))
            self.returns_pending_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(judul)))
            self.returns_pending_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(nama)))
            self.returns_pending_table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(rayon) if rayon else "-"))
            self.returns_pending_table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(kamar) if kamar else "-"))
            self.returns_pending_table.setItem(r, 5, QtWidgets.QTableWidgetItem(str(tanggal_pinjam)))
            
            batas_item = QtWidgets.QTableWidgetItem(batas_str)
            batas_item.setBackground(bg_color)
            self.returns_pending_table.setItem(r, 6, batas_item)
            
            self.returns_pending_table.setItem(r, 7, self._status_table_item(status_str))
            _, denda = self.db.calculate_fine(tanggal_pinjam, diperpanjang)
            self.returns_pending_table.setItem(r, 8, QtWidgets.QTableWidgetItem(f"Rp {denda:,}" if denda else "Rp 0"))
            audit = self.db.get_transaction_audit(id_v)
            self.returns_pending_table.setItem(r, 9, QtWidgets.QTableWidgetItem(audit[0] or "Sistem"))
        
        self.returns_pending_table.resizeColumnsToContents()
        self.returns_pending_table.setColumnWidth(7, max(self.returns_pending_table.columnWidth(7), 110))
        
        # ===== TABEL 2: PENGEMBALIAN SELESAI (juga di-search jika keyword ada) =====
        if keyword:
            completed_rows = self.db.search_completed_borrows(keyword)
        else:
            # Jika tidak ada keyword, tampilkan semua completed borrows
            completed_rows = self.db.completed_borrows()
        
        # Update tabel pengembalian selesai
        self.returns_completed_table.setRowCount(len(completed_rows))
        self.returns_completed_table.setColumnCount(10)
        self.returns_completed_table.setHorizontalHeaderLabels(["ID", "Judul Buku", "Nama Peminjam", "Rayon", "Kamar", "Tanggal Pinjam", "Tanggal Kembali", "Status", "Denda", "Dikembalikan Oleh"])
        
        for r, row in enumerate(completed_rows):
            id_v, judul, nama, rayon, kamar, tanggal_pinjam, tanggal_kembali = row[:7]
            c = self.db.conn.cursor()
            c.execute("SELECT denda FROM borrows WHERE id=?", (id_v,))
            denda_row = c.fetchone()
            denda = denda_row[0] if denda_row else 0
            
            self.returns_completed_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(id_v)))
            self.returns_completed_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(judul)))
            self.returns_completed_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(nama)))
            self.returns_completed_table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(rayon or "-")))
            self.returns_completed_table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(kamar or "-")))
            self.returns_completed_table.setItem(r, 5, QtWidgets.QTableWidgetItem(str(tanggal_pinjam)))
            self.returns_completed_table.setItem(r, 6, QtWidgets.QTableWidgetItem(str(tanggal_kembali)))
            self.returns_completed_table.setItem(r, 7, self._status_table_item("DIKEMBALIKAN"))
            self.returns_completed_table.setItem(r, 8, QtWidgets.QTableWidgetItem(f"Rp {denda:,}" if denda else "Rp 0"))
            audit = self.db.get_transaction_audit(id_v)
            self.returns_completed_table.setItem(r, 9, QtWidgets.QTableWidgetItem(audit[1] or "-"))
        
        self.returns_completed_table.resizeColumnsToContents()
        self.returns_completed_table.setColumnWidth(6, max(self.returns_completed_table.columnWidth(6), 110))
        
        # Update status message
        if keyword:
            self.status.showMessage(f"[CHECK] Hasil pencarian: {len(pending_rows)} menunggu | [OK] {len(completed_rows)} selesai")

    def start_scan(self, mode):
        """
        Start scanning process for Peminjaman/Pengembalian
        Mode: "borrow" atau "return"
        
        Flow:
        1. Scan/Input barcode anggota (member)
        2. Scan/Input ISBN buku (book)
        3. Process transaction
        """
        self.scan_mode = mode
        mode_label = "Peminjaman" if mode == "borrow" else "Pengembalian"
        
        # Step 1: Ask for member barcode/NIS
        member_code = self.show_scan_input_dialog(
            title=f"Scan Anggota - {mode_label}",
            label=" Barcode/NIS Anggota",
            info=f"Scan kartu anggota atau masukkan NIS untuk {mode_label.lower()} buku.\n\n"
                 f"Arahkan scanner ke barcode anggota."
        )
        
        if not member_code:
            self.status.showMessage("[ERROR] Scanning anggota dibatalkan.")
            return
        
        self.handle_member_scan(member_code)

    def show_scan_input_dialog(self, title, label, info):
        """
        Generic dialog untuk input barcode dari scanner device
        
        Cara kerja:
        - Dialog dengan QLineEdit yang focused
        - User arahkan scanner ke barcode/QR
        - Scanner input langsung ke field (HID)
        - Return value atau None jika cancel
        """
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setGeometry(100, 100, 500, 220)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Info label
        info_label = QtWidgets.QLabel(info)
        layout.addWidget(info_label)
        
        # Input field
        code_input = QtWidgets.QLineEdit()
        code_input.setPlaceholderText("Scan atau ketik kode...")
        code_input.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(code_input)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton(" OK - Lanjut")
        btn_cancel = QtWidgets.QPushButton(" Batal")
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        result = None
        
        def on_ok():
            nonlocal result
            code = code_input.text().strip()
            if not code:
                QtWidgets.QMessageBox.warning(dialog, "Peringatan", "Kode tidak boleh kosong!")
                return
            result = code
            dialog.accept()
        
        def on_cancel():
            dialog.reject()
        
        btn_ok.setAutoDefault(True)
        btn_ok.setDefault(True)
        btn_cancel.setAutoDefault(False)
        btn_ok.clicked.connect(on_ok)
        btn_cancel.clicked.connect(on_cancel)
        code_input.returnPressed.connect(on_ok)
        
        # Set focus dan show dialog
        code_input.setFocus()
        QtCore.QTimer.singleShot(0, code_input.setFocus)
        dialog.exec_()
        
        return result

    def handle_member_scan(self, member_code):
        """Handle member scan result untuk Peminjaman/Pengembalian"""
        if not member_code:
            self.status.showMessage("Scan anggota dibatalkan.")
            return

        c = self.db.conn.cursor()
        c.execute("SELECT id, nama FROM members WHERE barcode=? OR nama=?", (member_code, member_code))
        member = c.fetchone()
        if not member:
            QtWidgets.QMessageBox.warning(self, "Gagal", f"Anggota dengan kode '{member_code}' tidak ditemukan.")
            return

        # Check if QR code is expired (berlaku 3 tahun)
        is_expired, expiry_msg = self.db.is_qr_expired(member_code)
        if is_expired:
            QtWidgets.QMessageBox.warning(
                self, 
                "QR Expired", 
                f"QR ini sudah tidak berlaku!\n\n{expiry_msg}\n\nSilakan daftar ulang dengan QR baru."
            )
            return

        self.current_member_id = member[0]
        member_name = member[1]
        self.status.showMessage(f"Anggota '{member_name}' terdeteksi.")
        
        if self.scan_mode == "borrow":
            # Untuk peminjaman: scan 2 buku (buku kedua opsional)
            self.borrow_books_multiple(member_name)
        else:
            # Untuk pengembalian: scan 3 buku (buku kedua dan ketiga opsional)
            self.return_books_multiple(member_name)

    def load_fines(self):
        """Load tabel denda yang belum dibayar"""
        try:
            fines = self.db.get_unpaid_fines()
            print(f"DEBUG: load_fines() called - found {len(fines)} fines")
            
            if fines is None:
                fines = []
            
            self.fines_table.setColumnCount(7)
            self.fines_table.setHorizontalHeaderLabels(["ID Peminjaman", "Nama", "Rayon", "Kamar", "Informasi Denda", "Jumlah Denda", "Denda Dibuat Oleh"])
            self.fines_table.setRowCount(len(fines))
            
            for r, fine in enumerate(fines):
                borrow_id, nama, rayon, kamar, denda, judul, tanggal_pinjam, tanggal_kembali, member_id = fine
                
                # Informasi denda: judul buku + tanggal kembali
                info_denda = f"{judul} (Kembali: {tanggal_kembali[:10] if tanggal_kembali else '-'})"
                denda_str = f"Rp {denda:,}" if denda > 0 else "Rp 0"
                
                self.fines_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(borrow_id)))
                self.fines_table.setItem(r, 1, QtWidgets.QTableWidgetItem(nama if nama else "-"))
                self.fines_table.setItem(r, 2, QtWidgets.QTableWidgetItem(rayon if rayon else "-"))
                self.fines_table.setItem(r, 3, QtWidgets.QTableWidgetItem(kamar if kamar else "-"))
                self.fines_table.setItem(r, 4, QtWidgets.QTableWidgetItem(info_denda))
                self.fines_table.setItem(r, 5, QtWidgets.QTableWidgetItem(denda_str))
                audit = self.db.get_transaction_audit(borrow_id)
                self.fines_table.setItem(r, 6, QtWidgets.QTableWidgetItem(audit[2] or "-"))
                
                # Highlight denda yang besar
                if denda > 10000:
                    for col in range(7):
                        item = self.fines_table.item(r, col)
                        if item:
                            item.setBackground(QtGui.QColor(255, 200, 200))  # Light red
            
            self.fines_table.resizeColumnsToContents()
            self.status.showMessage(f"Total denda belum dibayar: {len(fines)} | Klik kanan untuk pembayaran")
            print(f"DEBUG: load_fines() completed successfully - table updated with {len(fines)} rows")
        except Exception as e:
            print(f"ERROR in load_fines(): {e}")
            import traceback
            traceback.print_exc()

    def show_fines_context_menu(self, position):
        """Tampilkan context menu untuk pembayaran denda"""
        index = self.fines_table.indexAt(position)
        if not index.isValid():
            return
        
        row = index.row()
        borrow_id_item = self.fines_table.item(row, 0)
        nama_item = self.fines_table.item(row, 1)
        denda_item = self.fines_table.item(row, 5)
        
        if not (borrow_id_item and nama_item and denda_item):
            return
        
        borrow_id = int(borrow_id_item.text())
        nama = nama_item.text()
        denda_str = denda_item.text()
        
        menu = QtWidgets.QMenu()
        action_bayar = menu.addAction("[OK] Tandai Denda Sudah Dibayar")
        
        action = menu.exec_(self.fines_table.mapToGlobal(position))
        
        if action == action_bayar:
            reply = QtWidgets.QMessageBox.question(self, "Konfirmasi Pembayaran",
                f"Tandai denda {nama} ({denda_str}) sebagai LUNAS?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            
            if reply == QtWidgets.QMessageBox.Yes:
                try:
                    self.db.mark_fine_as_paid(borrow_id, self._current_operator())
                    QtWidgets.QMessageBox.information(self, "Sukses", f"Denda untuk {nama} sudah ditandai LUNAS")
                    self.load_fines()
                    self.load_paid_fines()
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Gagal update denda:\n{e}")

    def load_paid_fines(self):
        """Load tabel denda yang sudah dibayar"""
        try:
            paid_fines = self.db.get_paid_fines()
            print(f"DEBUG: load_paid_fines() called - found {len(paid_fines)} paid fines")
            
            if paid_fines is None:
                paid_fines = []
            
            self.paid_fines_table.setColumnCount(7)
            self.paid_fines_table.setHorizontalHeaderLabels(["ID Peminjaman", "Nama", "Rayon", "Kamar", "Informasi Denda", "Tanggal Dibayar", "Dibayar Oleh"])
            self.paid_fines_table.setRowCount(len(paid_fines))
            
            for r, fine in enumerate(paid_fines):
                borrow_id, nama, rayon, kamar, denda, judul, tanggal_pinjam, tanggal_kembali, member_id = fine
                
                # Informasi denda: judul buku + tanggal kembali
                info_denda = f"{judul} (Kembali: {tanggal_kembali[:10] if tanggal_kembali else '-'})"
                # Untuk paid fines, gunakan tanggal kembali sebagai "tanggal pembayaran"
                tgl_bayar = tanggal_kembali[:10] if tanggal_kembali else "-"
                
                self.paid_fines_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(borrow_id)))
                self.paid_fines_table.setItem(r, 1, QtWidgets.QTableWidgetItem(nama if nama else "-"))
                self.paid_fines_table.setItem(r, 2, QtWidgets.QTableWidgetItem(rayon if rayon else "-"))
                self.paid_fines_table.setItem(r, 3, QtWidgets.QTableWidgetItem(kamar if kamar else "-"))
                self.paid_fines_table.setItem(r, 4, QtWidgets.QTableWidgetItem(info_denda))
                self.paid_fines_table.setItem(r, 5, QtWidgets.QTableWidgetItem(tgl_bayar))
                audit = self.db.get_transaction_audit(borrow_id)
                self.paid_fines_table.setItem(r, 6, QtWidgets.QTableWidgetItem(audit[3] or "-"))
                
                # Highlight paid (green background)
                for col in range(7):
                    item = self.paid_fines_table.item(r, col)
                    if item:
                        item.setBackground(QtGui.QColor(200, 230, 200))  # Light green
            
            self.paid_fines_table.resizeColumnsToContents()
            print(f"DEBUG: load_paid_fines() completed successfully - table updated with {len(paid_fines)} rows")
        except Exception as e:
            print(f"ERROR in load_paid_fines(): {e}")
            import traceback
            traceback.print_exc()

    def refresh_all_fines(self):
        """Refresh kedua tabel denda"""
        self.load_fines()
        self.load_paid_fines()

    def borrow_books_multiple(self, member_name):
        """Handle peminjaman maksimal 2 buku"""
        unpaid_denda = self.db.get_member_unpaid_fines(self.current_member_id)
        if unpaid_denda > 0:
            QtWidgets.QMessageBox.warning(
                self,
                "Denda Belum Dibayar",
                f"Anggota {member_name} memiliki denda belum dibayar sebesar Rp {unpaid_denda:,}.\n"
                "Peminjaman tidak dapat dilakukan sebelum denda dilunasi."
            )
            self.status.showMessage("Peminjaman dibatalkan - denda belum dibayar.")
            return

        active_borrows = self.db.get_member_active_borrow_count(self.current_member_id)
        available_slots = 2 - active_borrows
        if available_slots <= 0:
            QtWidgets.QMessageBox.information(
                self,
                "Batas Peminjaman Tercapai",
                f"Anggota {member_name} sedang meminjam {active_borrows} buku "
                "dan sudah mencapai batas maksimal 2 buku.\n"
                "Kembalikan buku terlebih dahulu sebelum meminjam lagi."
            )
            self.status.showMessage("Peminjaman dibatalkan - batas 2 buku aktif tercapai.")
            return
        
        books_borrowed = []
        
        for book_num in range(1, available_slots + 1):
            book_code = self.show_scan_input_dialog(
                title=f"Scan Buku - Peminjaman ({book_num}/2)",
                label="Kode Buku",
                info=f"Scan barcode buku ke-{book_num} untuk dipinjam.\n\n"
                     f"Anggota: {member_name}\n"
                     f"Buku ke-{book_num} "
                     f"{'(OPSIONAL - tekan Cancel jika hanya 1 buku)' if book_num > 1 else '(WAJIB)'}"
            )
            
            if not book_code:
                if book_num == 1:
                    self.status.showMessage("Peminjaman dibatalkan - Buku ke-1 tidak dipilih.")
                    return
                else:
                    # Buku ke-2 opsional, jika dibatalkan cukup selesaikan dengan buku ke-1
                    self.status.showMessage(f"Peminjaman selesai dengan 1 buku untuk {member_name}")
                    break
            
            # Cari buku
            c = self.db.conn.cursor()
            c.execute("SELECT id, judul, stok FROM books WHERE kode_buku=? OR barcode=?", (book_code, book_code))
            book = c.fetchone()
            if not book:
                QtWidgets.QMessageBox.warning(self, "Gagal", f"Buku dengan kode '{book_code}' tidak ditemukan.")
                self.status.showMessage(f"Buku tidak ditemukan: {book_code}")
                return
            
            book_id, book_title, stok = book
            
            # Check stock
            if stok <= 0:
                QtWidgets.QMessageBox.warning(self, "Gagal", f"Stok buku '{book_title}' habis!")
                self.status.showMessage(f"Stok buku '{book_title}' habis")
                return
            
            # Proses peminjaman
            try:
                self.db.borrow_book(book_id, self.current_member_id, self._current_operator())
                books_borrowed.append((book_title, stok - 1))
                self.status.showMessage(f"Buku {book_num} berhasil ditambahkan: {book_title}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Gagal memproses peminjaman buku {book_num}:\n{str(e)}")
                self.status.showMessage(f"Error: {e}")
                import traceback
                traceback.print_exc()
                return
        
        # Tampilkan summary
        if books_borrowed:
            summary = f"PEMINJAMAN BERHASIL untuk {member_name}\n\n"
            for i, (title, remaining_stok) in enumerate(books_borrowed, 1):
                summary += f"Buku {i}: {title}\n"
            summary += f"\nTotal buku: {len(books_borrowed)}"
            
            QtWidgets.QMessageBox.information(self, "Berhasil", summary)
            try:
                self.load_borrows()
            except Exception as e:
                print(f"Error loading borrows: {e}")
                import traceback
                traceback.print_exc()
            try:
                self.load_returns()  # Update tabel pengembalian juga
            except Exception as e:
                print(f"Error loading returns: {e}")
                import traceback
                traceback.print_exc()
            try:
                self.load_books()
            except Exception as e:
                print(f"Error loading books: {e}")
                import traceback
                traceback.print_exc()
            try:
                self.refresh_dashboard()
            except Exception as e:
                print(f"Error refreshing dashboard: {e}")
                import traceback
                traceback.print_exc()

    def return_books_multiple(self, member_name):
        """Handle pengembalian maksimal 2 buku (buku ke-1 wajib, buku ke-2 opsional)."""
        books_returned = []

        for book_num in [1, 2]:
            book_code = self.show_scan_input_dialog(
                title=f"Scan Buku - Pengembalian ({book_num}/2)",
                label="Kode Buku",
                info=f"Scan barcode buku ke-{book_num} untuk dikembalikan.\n\n"
                     f"Anggota: {member_name}\n"
                     f"Buku ke-{book_num} {'(OPSIONAL - tekan Cancel jika tidak ada lagi)' if book_num == 2 else '(WAJIB)'}"
            )

            if not book_code:
                if book_num == 1:
                    self.status.showMessage("Pengembalian dibatalkan - Buku ke-1 tidak dipilih.")
                    return
                else:
                    # Buku ke-2 opsional, jika dibatalkan cukup selesaikan dengan buku sebelumnya
                    self.status.showMessage(f"Pengembalian selesai dengan {book_num - 1} buku untuk {member_name}")
                    break

            # Cari buku
            c = self.db.conn.cursor()
            c.execute("SELECT id, judul, stok FROM books WHERE kode_buku=? OR barcode=?", (book_code, book_code))
            book = c.fetchone()
            if not book:
                QtWidgets.QMessageBox.warning(self, "Gagal", f"Buku dengan kode '{book_code}' tidak ditemukan.")
                self.status.showMessage(f"Buku tidak ditemukan: {book_code}")
                return

            book_id, book_title, stok = book

            # Proses pengembalian
            try:
                denda = self.db.return_book(
                    book_id,
                    self._current_operator(),
                    member_id=self.current_member_id
                )
                books_returned.append((book_title, stok + 1, denda))
                self.status.showMessage(f"Buku {book_num} berhasil dikembalikan: {book_title}")
            except ValueError as ve:
                QtWidgets.QMessageBox.warning(self, "Peringatan", f"Buku {book_num}: {str(ve)}")
                self.status.showMessage(f"Warning: {ve}")
                return
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Gagal memproses pengembalian buku {book_num}:\n{str(e)}")
                self.status.showMessage(f"Error: {e}")
                import traceback
                traceback.print_exc()
                return

        # Tampilkan summary
        if books_returned:
            summary = f"PENGEMBALIAN BERHASIL untuk {member_name}\n\n"
            total_denda = 0
            for i, (title, remaining_stok, denda) in enumerate(books_returned, 1):
                summary += f"Buku {i}: {title} (Stok: {remaining_stok})\n"
                if denda > 0:
                    summary += f"  └─ Denda: Rp {denda:,.0f}\n"
                    total_denda += denda

            summary += f"\nTotal buku: {len(books_returned)}"
            if total_denda > 0:
                summary += f"\nTotal Denda: Rp {total_denda:,.0f}"

            QtWidgets.QMessageBox.information(self, "Berhasil", summary)
            try:
                self.load_returns()
            except Exception as e:
                print(f"Error loading returns: {e}")
                import traceback
                traceback.print_exc()
            try:
                self.load_borrows()  # Update tabel peminjaman juga
            except Exception as e:
                print(f"Error loading borrows: {e}")
                import traceback
                traceback.print_exc()
            try:
                self.load_books()
            except Exception as e:
                print(f"Error loading books: {e}")
                import traceback
                traceback.print_exc()
            try:
                self.refresh_dashboard()
            except Exception as e:
                print(f"Error refreshing dashboard: {e}")
                import traceback
                traceback.print_exc()

    def handle_book_scan(self, book_code):
        """Handle book scan result untuk Peminjaman/Pengembalian"""
        if not book_code:
            self.status.showMessage("[ERROR] Scan buku dibatalkan.")
            return

        c = self.db.conn.cursor()
        c.execute("SELECT id, judul, stok FROM books WHERE kode_buku=? OR barcode=?", (book_code, book_code))
        book = c.fetchone()
        if not book:
            QtWidgets.QMessageBox.warning(self, "[ERROR] Gagal", f"Buku dengan kode '{book_code}' tidak ditemukan.")
            self.status.showMessage(f"[ERROR] Buku tidak ditemukan: {book_code}")
            return

        book_id, book_title, stok = book
        mode_label = "Peminjaman" if self.scan_mode == "borrow" else "Pengembalian"
        
        try:
            if self.scan_mode == "borrow":
                # Check stock
                if stok <= 0:
                    QtWidgets.QMessageBox.warning(self, "[ERROR] Gagal", f"Stok buku '{book_title}' habis!")
                    self.status.showMessage(f"[ERROR] Stok buku '{book_title}' habis")
                    return
                
                self.db.borrow_book(book_id, self.current_member_id, self._current_operator())
                msg = f"[SUCCESS] Buku berhasil dipinjam!\n\nBuku: {book_title}\nStok tersisa: {stok - 1}"
                self.status.showMessage(f"[SUCCESS] Peminjaman berhasil: {book_title}")
            else:
                # Pengembalian - hitung dan tampilkan denda jika ada
                denda = self.db.return_book(
                    book_id,
                    self._current_operator(),
                    member_id=self.current_member_id
                )
                msg = f"[SUCCESS] Buku berhasil dikembalikan!\n\nBuku: {book_title}\nStok sekarang: {stok + 1}"
                
                # Tambahkan informasi denda jika ada
                if denda > 0:
                    # Hitung hari terlambat
                    c = self.db.conn.cursor()
                    c.execute('SELECT tanggal_pinjam, diperpanjang FROM borrows WHERE book_id=? AND status=1 ORDER BY id DESC LIMIT 1', (book_id,))
                    borrow = c.fetchone()
                    if borrow:
                        tanggal_pinjam = borrow[0]
                        batas_dt = self.db.borrow_deadline(tanggal_pinjam, borrow[1])
                        hari_terlambat = (datetime.now() - batas_dt).days + (1 if (datetime.now() - batas_dt).seconds > 0 else 0)
                        msg += f"\n\n[WARN] DENDA KETERLAMBATAN\nHari Terlambat: {hari_terlambat} hari\nDenda: Rp {denda:,.0f}"
                
                self.status.showMessage(f"[SUCCESS] Pengembalian berhasil: {book_title}")

            QtWidgets.QMessageBox.information(self, "[SUCCESS] Sukses", msg)
            self.load_borrows()
            self.load_books()
            self.load_returns()  # Refresh tab pengembalian
            self.refresh_dashboard()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "[ERROR] Error", f"Gagal memproses {mode_label.lower()}:\n{e}")
            self.status.showMessage(f"[ERROR] Error: {e}")
    # -------------------- EXPORT EXCEL -----------------
    def export_excel(self, tipe):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            QtWidgets.QMessageBox.warning(self, "Error", "Package 'openpyxl' belum diinstall.\nJalankan: pip install openpyxl")
            return
        
        import os
        from pathlib import Path
        
        # Create laporan folder di user home directory untuk compatibility
        if hasattr(sys, '_MEIPASS'):
            # Running dari executable (pyinstaller/NSIS)
            laporan_dir = os.path.join(str(Path.home()), "A Latee Library", "laporan")
        else:
            # Running dari source
            laporan_dir = "laporan"
        
        os.makedirs(laporan_dir, exist_ok=True)
            
        wb = openpyxl.Workbook()
        ws = wb.active
        
        # Style untuk header
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        header_alignment = Alignment(horizontal="center", vertical="center")

        if tipe == "books":
            ws.title = "Buku"
            headers = ["ID", "Kode", "Kategori", "Judul", "Penulis", "Penerbit", "Barcode", "Stok", "Status", "Jumlah Dipinjam"]
            ws.append(headers)
            
            # Apply header style
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            
            # Export data buku sesuai struktur tabel UI
            for row in self.db.list_books():
                ws.append(row)
            
            # Auto-adjust column width
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            fname = "laporan_buku.xlsx"
            # Jika file dengan nama yang sama sudah diexport hari ini, tambahkan timestamp
            try:
                if os.path.exists(os.path.join(laporan_dir, fname)):
                    mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(laporan_dir, fname)))
                    if mtime.date() == datetime.now().date():
                        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        fname = fname.replace(".xlsx", f"_{stamp}.xlsx")
            except Exception:
                pass
            fname = os.path.join(laporan_dir, fname)
            msg = f"Data buku berhasil diexport ke {os.path.basename(fname)}"

        elif tipe == "visitors":
            ws.title = "Pengunjung"
            headers = ["ID", "Nama", "Rayon", "Kamar", "Fingerprint", "Tanggal", "Jam", "Waktu"]
            ws.append(headers)
            
            # Apply header style
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            
            # Export data pengunjung dengan kamar dari tabel visitors
            c = self.db.conn.cursor()
            c.execute("""
                SELECT vv.id, v.nama, v.rayon, v.kamar, v.fingerprint_id, vv.waktu_kunjungan
                FROM visitor_visits vv
                JOIN visitors v ON v.id = vv.visitor_id
                ORDER BY vv.id DESC
            """)
            for row in c.fetchall():
                id_v, nama, rayon, kamar, fingerprint, waktu_iso = row
                
                # Parse waktu
                try:
                    dt = datetime.fromisoformat(waktu_iso)
                    tanggal = dt.strftime("%d-%m-%Y")
                    jam = dt.strftime("%H:%M:%S")
                    waktu_status = self.get_waktu_kunjungan(dt.strftime("%H"))
                except:
                    tanggal = "-"
                    jam = "-"
                    waktu_status = "-"
                
                # Waktu column will contain the period label (Siang/Malam/Luar Jam)
                ws.append([id_v, nama, rayon if rayon else "-", kamar if kamar else "-", fingerprint if fingerprint else "-", tanggal, jam, waktu_status])
            
            # Auto-adjust column width
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            fname = "laporan_pengunjung.xlsx"
            # Jika file dengan nama yang sama sudah diexport hari ini, tambahkan timestamp
            try:
                if os.path.exists(os.path.join(laporan_dir, fname)):
                    mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(laporan_dir, fname)))
                    if mtime.date() == datetime.now().date():
                        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        fname = fname.replace(".xlsx", f"_{stamp}.xlsx")
            except Exception:
                pass
            fname = os.path.join(laporan_dir, fname)
            msg = f"Data pengunjung berhasil diexport ke {os.path.basename(fname)}"

        elif tipe == "members":
            ws.title = "Anggota"
            headers = ["ID", "Nama", "Rayon", "Kamar", "QR ID", "Barcode"]
            ws.append(headers)
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            c = self.db.conn.cursor()
            c.execute('''SELECT m.id, m.nama, m.rayon, m.kamar,
                                COALESCE(m.qr_id, p.qr_id), m.barcode
                         FROM members m
                         LEFT JOIN pending_qr_codes p ON m.barcode=p.barcode
                         ORDER BY m.id DESC''')
            for row in c.fetchall():
                ws.append(list(row))
            fname = os.path.join(laporan_dir, "laporan_anggota.xlsx")
            msg = f"Data anggota berhasil diexport ke {os.path.basename(fname)}"

        elif tipe in {"fines", "paid_fines"}:
            paid = tipe == "paid_fines"
            ws.title = "Denda Dibayar" if paid else "Denda Belum Dibayar"
            headers = ["ID Peminjaman", "Nama", "Rayon", "Kamar", "Informasi Denda", "Jumlah Denda", "Status", "Dibuat Oleh", "Dibayar Oleh"]
            ws.append(headers)
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            c = self.db.conn.cursor()
            condition = ("b.status=1 AND b.denda=0 AND b.denda_dibayar_oleh IS NOT NULL"
                         if paid else "b.status=1 AND b.denda>0")
            c.execute(f'''SELECT b.id, m.nama, m.rayon, m.kamar, bk.judul,
                                 b.denda, b.tanggal_kembali,
                                 b.denda_dibuat_oleh, b.denda_dibayar_oleh
                          FROM borrows b
                          LEFT JOIN members m ON b.member_id=m.id
                          LEFT JOIN books bk ON b.book_id=bk.id
                          WHERE {condition}
                          ORDER BY b.tanggal_kembali DESC''')
            for row in c.fetchall():
                borrow_id, nama, rayon, kamar, judul, denda, tanggal_kembali, dibuat_oleh, dibayar_oleh = row
                info = f"{judul} (Kembali: {tanggal_kembali[:10] if tanggal_kembali else '-'})"
                ws.append([borrow_id, nama or "-", rayon or "-", kamar or "-", info, f"Rp {denda or 0:,}", "SUDAH DIBAYAR" if paid else "BELUM DIBAYAR", dibuat_oleh or "-", dibayar_oleh or "-"])
            if not paid:
                c.execute('''SELECT b.id, m.nama, m.rayon, m.kamar, bk.judul,
                                    b.tanggal_pinjam, b.diperpanjang, b.dibuat_oleh
                             FROM borrows b
                             LEFT JOIN members m ON b.member_id=m.id
                             LEFT JOIN books bk ON b.book_id=bk.id
                             WHERE b.status=0
                             ORDER BY b.tanggal_pinjam DESC''')
                for borrow_id, nama, rayon, kamar, judul, tanggal_pinjam, diperpanjang, dibuat_oleh in c.fetchall():
                    _, denda = self.db.calculate_fine(tanggal_pinjam, diperpanjang)
                    if denda <= 0:
                        continue
                    deadline = self.db.borrow_deadline(tanggal_pinjam, diperpanjang)
                    info = f"{judul} (Jatuh tempo: {deadline.strftime('%d-%m-%Y')})"
                    ws.append([
                        borrow_id, nama or "-", rayon or "-", kamar or "-", info,
                        f"Rp {denda:,}", "BERJALAN (ESTIMASI)", dibuat_oleh or "Sistem", "-"
                    ])
            fname = os.path.join(laporan_dir, "laporan_denda_dibayar.xlsx" if paid else "laporan_denda_belum_dibayar.xlsx")
            msg = f"Laporan denda berhasil diexport ke {os.path.basename(fname)}"

        elif tipe == "sales":
            ws.title = "Penjualan"
            headers = ["ID Penjualan", "Tanggal", "Dibuat Oleh", "Judul Buku", "Penulis", "Jumlah", "Harga", "Subtotal", "Total"]
            ws.append(headers)
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            c = self.db.conn.cursor()
            c.execute('''SELECT s.id, s.created_at, s.dibuat_oleh, p.judul, p.penulis,
                                i.jumlah, COALESCE(i.harga_asli, i.harga),
                                (i.jumlah * COALESCE(i.harga_asli, i.harga)),
                                (SELECT SUM(si.jumlah * COALESCE(si.harga_asli, si.harga))
                                 FROM sale_items si WHERE si.sale_id=s.id)
                         FROM sales s
                         JOIN sale_items i ON i.sale_id=s.id
                         JOIN sale_products p ON p.id=i.product_id
                         ORDER BY s.id DESC''')
            for row in c.fetchall():
                ws.append(list(row))
            fname = os.path.join(laporan_dir, "laporan_penjualan.xlsx")
            msg = f"Data penjualan berhasil diexport ke {os.path.basename(fname)}"

        else:  # borrows
            ws.title = "Peminjaman"
            headers = ["ID", "Judul Buku", "Nama Peminjam", "Rayon", "Kamar", "Tanggal Pinjam", "Batas Waktu", "Status", "Tanggal Kembali", "Diperpanjang", "Denda", "Dibuat Oleh", "Dikembalikan Oleh"]
            ws.append(headers)
            
            # Apply header style
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
            
            # Export data peminjaman dengan kamar dari tabel members
            c = self.db.conn.cursor()
            try:
                c.execute('''SELECT b.id, bk.judul, m.nama, m.rayon, m.kamar, b.tanggal_pinjam, b.tanggal_kembali, b.status, b.diperpanjang, b.denda, b.dibuat_oleh, b.dikembalikan_oleh
                            FROM borrows b
                            LEFT JOIN books bk ON b.book_id=bk.id
                            LEFT JOIN members m ON b.member_id=m.id
                            ORDER BY b.id DESC''')
                rows = c.fetchall()
            except Exception as e:
                # Fallback: jika ada error, try tanpa LEFT JOIN
                c.execute('''SELECT id, book_id, member_id, tanggal_pinjam, tanggal_kembali, status, diperpanjang, denda
                            FROM borrows
                            ORDER BY id DESC''')
                rows = c.fetchall()
            
            for row in rows:
                try:
                    # Check panjang row untuk handle fallback query
                    if len(row) == 12:
                        # Normal query dengan JOIN
                        id_v, judul, nama, rayon, kamar, tanggal_pinjam, tanggal_kembali, status, diperpanjang, denda, dibuat_oleh, dikembalikan_oleh = row
                    else:
                        # Fallback query tanpa JOIN
                        id_v, book_id, member_id, tanggal_pinjam, tanggal_kembali, status, diperpanjang, denda = row
                        # Get book dan member info
                        book_row = self.db.get_book(book_id) if book_id else None
                        member_row = self.db.get_member(member_id) if member_id else None
                        judul = book_row[3] if book_row else "-"  # judul is at index 3
                        nama = member_row[1] if member_row else "-"  # nama is at index 1
                        rayon = member_row[2] if member_row and len(member_row) > 2 else "-"
                        kamar = member_row[3] if member_row and len(member_row) > 3 else "-"
                        dibuat_oleh = "-"
                        dikembalikan_oleh = "-"
                    
                    # Hitung batas waktu
                    try:
                        if tanggal_pinjam:
                            batas_dt = self.db.borrow_deadline(tanggal_pinjam, diperpanjang)
                            batas_str = batas_dt.strftime("%d-%m-%Y")
                        else:
                            batas_str = "-"
                    except:
                        batas_str = "-"
                    
                    # Tentukan status string sesuai label pada menu peminjaman
                    if status == 1:
                        status_str = "DIKEMBALIKAN"
                    elif diperpanjang == 1:
                        status_str = "DIPERPANJANG"
                    elif batas_str != "-" and datetime.now() > batas_dt:
                        status_str = "TERLAMBAT"
                    else:
                        status_str = "AMAN"
                    
                    # Tentukan diperpanjang
                    diperpanjang_str = "Ya" if diperpanjang == 1 else "Tidak"
                    
                    # Format denda
                    denda_str = f"Rp {denda:,}" if denda and denda > 0 else "Rp 0"
                    
                    ws.append([id_v, judul, nama, rayon if rayon else "-", kamar if kamar else "-", tanggal_pinjam[:10] if tanggal_pinjam else "-", batas_str, status_str,
                              tanggal_kembali[:10] if tanggal_kembali else "-", diperpanjang_str, denda_str, dibuat_oleh or "-", dikembalikan_oleh or "-"])
                except Exception as e:
                    # Skip row yang error
                    continue
            
            # Auto-adjust column width
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            fname = "laporan_peminjaman.xlsx"
            # Jika file dengan nama yang sama sudah diexport hari ini, tambahkan timestamp
            try:
                if os.path.exists(os.path.join(laporan_dir, fname)):
                    mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(laporan_dir, fname)))
                    if mtime.date() == datetime.now().date():
                        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        fname = fname.replace(".xlsx", f"_{stamp}.xlsx")
            except Exception:
                pass
            fname = os.path.join(laporan_dir, fname)
            msg = f"Data peminjaman berhasil diexport ke {os.path.basename(fname)}"

        for report_sheet in wb.worksheets:
            for column in report_sheet.columns:
                values = [len(str(cell.value or "")) for cell in column]
                if values:
                    report_sheet.column_dimensions[column[0].column_letter].width = min(max(values) + 2, 50)

        wb.save(fname)
        # Tampilkan satu pesan sukses saja (hindari duplikat)
        QtWidgets.QMessageBox.information(self, "Berhasil", msg)
        self.status.showMessage(f"[SUCCESS] Laporan {tipe} disimpan sebagai {fname}")

    # -------------------- EXPORT GRAFIK STATISTIK -----------------
    def export_grafik_statistik(self):
        """Export grafik statistik pengunjung dan peminjaman ke PNG"""
        try:
            import matplotlib.pyplot as plt
            import os
            from pathlib import Path
        except ImportError:
            QtWidgets.QMessageBox.warning(self, "Error", "Package 'matplotlib' belum diinstall.\nJalankan: pip install matplotlib")
            return
        
        # Create laporan folder
        if hasattr(sys, '_MEIPASS'):
            laporan_dir = os.path.join(str(Path.home()), "A Latee Library", "laporan")
        else:
            laporan_dir = "laporan"
        
        os.makedirs(laporan_dir, exist_ok=True)
        
        try:
            # Get data dari database
            year = datetime.now().year
            visitors = self.db.visitors_per_month(year)
            borrows = self.db.borrows_per_month(year)
            months = range(1, 13)
            
            # Create figure dengan 2 subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
            fig.suptitle(f'Statistik A Latee Library - Tahun {year}', fontsize=16, fontweight='bold')
            
            # Plot 1: Pengunjung dan Peminjaman gabung
            visitor_data = [visitors.get(m, 0) for m in months]
            borrow_data = [borrows.get(m, 0) for m in months]
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
            
            ax1.plot(months, visitor_data, marker='o', label='Pengunjung', linewidth=2, color='#2E86AB')
            ax1.plot(months, borrow_data, marker='s', label='Peminjaman', linewidth=2, color='#A23B72')
            ax1.set_xlabel('Bulan', fontweight='bold')
            ax1.set_ylabel('Jumlah', fontweight='bold')
            ax1.set_title('Perbandingan Pengunjung vs Peminjaman', fontweight='bold')
            ax1.set_xticks(months)
            ax1.set_xticklabels(month_names)
            ax1.legend(loc='upper left')
            ax1.grid(True, alpha=0.3)
            
            # Plot 2: Bar chart perbandingan
            x_pos = range(len(month_names))
            width = 0.35
            ax2.bar([p - width/2 for p in x_pos], visitor_data, width, label='Pengunjung', color='#2E86AB', alpha=0.8)
            ax2.bar([p + width/2 for p in x_pos], borrow_data, width, label='Peminjaman', color='#A23B72', alpha=0.8)
            ax2.set_xlabel('Bulan', fontweight='bold')
            ax2.set_ylabel('Jumlah', fontweight='bold')
            ax2.set_title('Statistik Bulanan', fontweight='bold')
            ax2.set_xticks(x_pos)
            ax2.set_xticklabels(month_names)
            ax2.legend()
            ax2.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            
            # Save dengan timestamp
            fname = os.path.join(laporan_dir, f"grafik_statistik_{year}.png")
            if os.path.exists(fname):
                mtime = datetime.fromtimestamp(os.path.getmtime(fname))
                if mtime.date() == datetime.now().date():
                    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    fname = fname.replace(".png", f"_{stamp}.png")
            
            plt.savefig(fname, dpi=150, bbox_inches='tight')
            plt.close()
            
            QtWidgets.QMessageBox.information(
                self, "[SUCCESS] Berhasil", 
                f"Grafik statistik berhasil diexport ke:\n{os.path.basename(fname)}"
            )
            self.status.showMessage(f"[SUCCESS] Grafik statistik disimpan sebagai {os.path.basename(fname)}")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "[ERROR] Error", f"Gagal export grafik:\n{e}")
            self.status.showMessage(f"[ERROR] Error export grafik: {e}")


# =======================================================
# ============== AUTH DIALOGS & RUN APP =================
# =======================================================

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login Pustakawan A Latee Library")
        self.setModal(True)
        self.resize(500, 420)

        layout = QtWidgets.QVBoxLayout(self)
        
        # Add logo at top
        logo_label = QtWidgets.QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "LOGO.png")
        if os.path.exists(logo_path):
            pixmap = QtGui.QPixmap(logo_path)
            pixmap = pixmap.scaledToHeight(100, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)
        
        # Title
        title = QtWidgets.QLabel("A Latee Library")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)
        
        form = QtWidgets.QFormLayout()
        self.in_username = QtWidgets.QLineEdit()
        self.in_password = QtWidgets.QLineEdit()
        self.in_password.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("Username:", self.in_username)
        form.addRow("Password:", self.in_password)
        layout.addLayout(form)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_credentials(self):
        return self.in_username.text().strip(), self.in_password.text()


class RegisterDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Daftar Pustakawan Baru A Latee Library")
        self.setModal(True)
        self.resize(520, 500)

        layout = QtWidgets.QVBoxLayout(self)
        
        # Add logo at top
        logo_label = QtWidgets.QLabel()
        # Try multiple paths to find LOGO.png
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "assets", "LOGO.png"),
            os.path.join(os.getcwd(), "assets", "LOGO.png"),
            "assets/LOGO.png"
        ]
        logo_path = None
        for path in possible_paths:
            if os.path.exists(path):
                logo_path = path
                break
        
        if logo_path:
            pixmap = QtGui.QPixmap(logo_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaledToHeight(100, Qt.SmoothTransformation)
                logo_label.setPixmap(pixmap)
                logo_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(logo_label)
        
        # Title
        title = QtWidgets.QLabel("A Latee Library")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)
        
        form = QtWidgets.QFormLayout()
        self.in_username = QtWidgets.QLineEdit()
        self.in_fullname = QtWidgets.QLineEdit()
        self.in_password = QtWidgets.QLineEdit()
        self.in_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.in_password2 = QtWidgets.QLineEdit()
        self.in_password2.setEchoMode(QtWidgets.QLineEdit.Password)

        form.addRow("Username:", self.in_username)
        form.addRow("Nama Lengkap:", self.in_fullname)
        form.addRow("Password:", self.in_password)
        form.addRow("Konfirmasi Password:", self.in_password2)
        layout.addLayout(form)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        u = self.in_username.text().strip()
        p1 = self.in_password.text()
        p2 = self.in_password2.text()
        if not u or not p1:
            QtWidgets.QMessageBox.warning(self, "Data kurang", "Username dan password tidak boleh kosong")
            return
        if p1 != p2:
            QtWidgets.QMessageBox.warning(self, "Password mismatch", "Password dan konfirmasi tidak cocok")
            return
        # If parent provides a db, we can check duplicates here; otherwise accept and let caller handle
        parent_db = None
        if hasattr(self, 'parent') and self.parent() and hasattr(self.parent(), 'db'):
            parent_db = self.parent().db
        if parent_db:
            if parent_db.get_user_by_username(u):
                QtWidgets.QMessageBox.warning(self, "Sudah Terdaftar", "Username tersebut sudah memiliki akun.")
                return
            if self.in_fullname.text().strip() and parent_db.get_user_by_username(self.in_fullname.text().strip()):
                # This check is probably incorrect (checking username against fullname) so instead query by fullname
                c = parent_db.conn.cursor()
                c.execute('SELECT id FROM users WHERE LOWER(full_name)=LOWER(?)', (self.in_fullname.text().strip(),))
                if c.fetchone():
                    QtWidgets.QMessageBox.warning(self, "Sudah Terdaftar", "Nama lengkap tersebut sudah memiliki akun.")
                    return
        self.accept()

    def get_data(self):
        return self.in_username.text().strip(), self.in_fullname.text().strip(), self.in_password.text()


def get_asset_path(filename):
    """Get absolute path to asset file, works both in dev and packaged exe"""
    # For PyInstaller, sys._MEIPASS contains the bundle directory
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'assets', filename)
    # For development, use relative path
    return os.path.join(os.path.dirname(__file__), 'assets', filename)


def add_logo_to_qr(qr_path, logo_path=None):
    """
    Add logo PNG to center of QR code with triangle white background
    
    Parameters:
    - qr_path: Path to QR code image
    - logo_path: Path to logo image (default: LOGO.png from assets)
    
    Returns:
    - qr_path (same path, modified in place)
    """
    try:
        if logo_path is None:
            logo_path = get_asset_path('LOGO.png')
        
        # Open QR code image
        qr_img = Image.open(qr_path).convert('RGBA')
        
        # Open logo image
        if not os.path.exists(logo_path):
            return qr_path
        
        logo_img = Image.open(logo_path).convert('RGBA')
        
        # Calculate dimensions
        qr_width, qr_height = qr_img.size
        
        # Calculate logo size based on QR dimensions
        # Logo akan ~22% dari lebar QR (slightly larger for clarity)
        target_logo_width = int(qr_width * 0.22)
        
        # Resize logo maintaining aspect ratio asli (0.89)
        original_width, original_height = logo_img.size
        aspect_ratio = original_height / original_width  # ~0.89
        new_logo_height = int(target_logo_width * aspect_ratio)
        logo_img = logo_img.resize((target_logo_width, new_logo_height), Image.Resampling.LANCZOS)
        
        # Enhance logo quality without blur - for clear scanning
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Sharpness(logo_img)
        logo_img = enhancer.enhance(1.6)  # Balanced sharpness for clarity
        enhancer = ImageEnhance.Contrast(logo_img)
        logo_img = enhancer.enhance(1.4)  # Balanced contrast for crisp details
        enhancer = ImageEnhance.Brightness(logo_img)
        logo_img = enhancer.enhance(1.35)  # Brightness for vibrant appearance
        
        # Create triangle background matching logo's actual height ratio
        # Triangle width 1.4x of logo width (for proper padding)
        tri_width = int(logo_img.size[0] * 1.4)
        # Triangle height: cut bottom slightly for more upward appearance
        tri_height = int(tri_width * 0.80)  # More compact, bottom cut off slightly
        
        # Create triangle image with white fill
        tri_img = Image.new('RGBA', (tri_width, tri_height), (0, 0, 0, 0))
        
        from PIL import ImageDraw
        draw = ImageDraw.Draw(tri_img)
        
        # Draw white filled triangle (pointing up)
        points = [
            (tri_width // 2, 0),           # Top point
            (0, tri_height),               # Bottom left
            (tri_width, tri_height)        # Bottom right
        ]
        draw.polygon(points, fill=(255, 255, 255, 255))
        
        # Calculate position to paste logo in center of triangle (precisely centered)
        logo_x = (tri_width - logo_img.size[0]) // 2
        logo_y = (tri_height - logo_img.size[1]) // 2
        
        # Ensure logo is properly centered and not cut off
        # Clip coordinates to valid range
        logo_x = max(0, logo_x)
        logo_y = max(0, logo_y)
        
        # Paste logo onto triangle
        tri_img.paste(logo_img, (logo_x, logo_y), logo_img)
        
        # Calculate center position for triangle placement on QR code (precisely centered)
        qr_center_x = (qr_width - tri_width) // 2
        qr_center_y = (qr_height - tri_height) // 2
        
        # Paste triangle with logo onto QR code
        qr_img.paste(tri_img, (qr_center_x, qr_center_y), tri_img)
        
        # Convert back to RGB and save
        final_img = Image.new('RGB', qr_img.size, (255, 255, 255))
        final_img.paste(qr_img, (0, 0), qr_img)
        final_img.save(qr_path)
        
        return qr_path
    except Exception as e:
        # If error occurs, return original QR path without logo
        print(f"[WARN] Warning: Could not add logo to QR - {e}")
        return qr_path


class AuthWindow(QtWidgets.QWidget):
    """Full-window authentication flow with Login / Register / Reset pages.

    On successful authentication, AuthWindow will open MainWindow(db) and close itself.
    """
    def __init__(self, db, start_page='login'):
        super().__init__()
        self.db = db
        self.setWindowTitle("Autentikasi Pustakawan")
        self.setMinimumSize(620, 520)
        
        # Set window icon
        icon_path = get_asset_path('app_icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        layout = QtWidgets.QVBoxLayout(self)
        self.stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.stack)

        # Pages
        self.login_page = self._create_login_page()
        self.register_page = self._create_register_page()
        self.reset_page = self._create_reset_page()

        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.register_page)
        self.stack.addWidget(self.reset_page)

        if start_page == 'register':
            self.stack.setCurrentWidget(self.register_page)
        else:
            self.stack.setCurrentWidget(self.login_page)

    def _create_login_page(self):
        w = QtWidgets.QWidget()
        w.setObjectName("authPage")
        w.setStyleSheet("""
            QWidget#authPage {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f7fbff, stop:1 #eef4ff);
            }
            QFrame#authCard {
                background-color: #ffffff;
                border: 1px solid #dce7f2;
                border-radius: 18px;
                max-width: 380px;
            }
            QLabel#authTitle {
                font-family: "Trebuchet MS", sans-serif;
                font-size: 22px;
                font-weight: 700;
                color: #243447;
            }
            QPushButton#authPrimary {
                background-color: #2a6fde;
                color: white;
                border: none;
                border-radius: 999px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 600;
                min-height: 36px;
                max-width: 260px;
            }
            QPushButton#authPrimary:hover {
                background-color: #2158b8;
            }
            QPushButton#authLink {
                background: transparent;
                color: #2a6fde;
                border: none;
                text-align: center;
                font-size: 12px;
                padding: 8px 0;
            }
            QLineEdit {
                border: 1px solid #d0d8e2;
                border-radius: 10px;
                padding: 8px 12px;
                min-height: 34px;
                font-size: 14px;
                max-width: 300px;
            }
            QLineEdit:focus {
                border: 1px solid #2a6fde;
            }
        """)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(28, 28, 28, 28)

        card = QtWidgets.QFrame()
        card.setObjectName("authCard")
        card.setMinimumWidth(480)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignCenter)

        logo_path = get_asset_path('LOGO.png')
        if os.path.exists(logo_path):
            pix = QtGui.QPixmap(logo_path)
            if not pix.isNull():
                logo_lbl = QtWidgets.QLabel()
                logo_lbl.setAlignment(Qt.AlignCenter)
                logo_lbl.setPixmap(pix.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                card_layout.addWidget(logo_lbl)

        title = QtWidgets.QLabel("Masuk Pustakawan")
        title.setObjectName("authTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        self.l_username = QtWidgets.QLineEdit()
        self.l_password = QtWidgets.QLineEdit()
        self.l_password.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("Username", self.l_username)
        form.addRow("Password", self.l_password)
        card_layout.addLayout(form)

        btn_login = QtWidgets.QPushButton("Login")
        btn_login.setObjectName("authPrimary")
        # Ensure button style is explicit so global stylesheet doesn't override shape
        btn_login.setStyleSheet("""
            QPushButton {
                background-color: #2a6fde;
                color: white;
                border: none;
                border-radius: 999px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 600;
                min-height: 36px;
                max-width: 260px;
            }
            QPushButton:hover { background-color: #2158b8; }
        """)
        btn_login.clicked.connect(self._on_login)
        self.l_username.returnPressed.connect(self._on_login)
        self.l_password.returnPressed.connect(self._on_login)
        card_layout.addWidget(btn_login, alignment=Qt.AlignCenter)

        btn_qr_login = QtWidgets.QPushButton("Scan QR Kartu Pustakawan")
        btn_qr_login.setObjectName("authLink")
        btn_qr_login.clicked.connect(self._scan_qr_login)
        card_layout.addWidget(btn_qr_login, alignment=Qt.AlignCenter)

        links = QtWidgets.QHBoxLayout()
        link_register = QtWidgets.QPushButton("Belum punya akun? Daftar")
        link_register.setObjectName("authLink")
        link_register.clicked.connect(lambda: self.stack.setCurrentWidget(self.register_page))
        link_forgot = QtWidgets.QPushButton("Lupa username/password")
        link_forgot.setObjectName("authLink")
        link_forgot.clicked.connect(lambda: self.stack.setCurrentWidget(self.reset_page))
        links.addWidget(link_register)
        links.addStretch()
        links.addWidget(link_forgot)
        card_layout.addLayout(links)

        v.addWidget(card, alignment=Qt.AlignCenter)
        return w

    def _scan_qr_login(self):
        """Baca QR dari scanner hardware USB, lalu login ke akun yang sesuai."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Scan QR Kartu Pustakawan")
        dialog.setModal(True)
        dialog.setFixedSize(430, 210)
        layout = QtWidgets.QVBoxLayout(dialog)
        status = QtWidgets.QLabel(
            "Arahkan scanner QR/barcode hardware ke kartu pustakawan.\n"
            "Hasil scan akan masuk otomatis ke kolom di bawah."
        )
        status.setAlignment(Qt.AlignCenter)
        status.setWordWrap(True)
        layout.addWidget(status)

        barcode_input = QtWidgets.QLineEdit()
        barcode_input.setPlaceholderText("Scan QR kartu pustakawan di sini")
        barcode_input.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(barcode_input)

        button_layout = QtWidgets.QHBoxLayout()
        scan_button = QtWidgets.QPushButton("Login dengan QR")
        cancel_button = QtWidgets.QPushButton("Batal")
        button_layout.addWidget(scan_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def finish_scan():
            code = barcode_input.text().strip()
            if not code:
                QtWidgets.QMessageBox.warning(dialog, "QR Kosong", "Arahkan scanner ke kartu pustakawan terlebih dahulu.")
                return
            dialog.accept()

        scan_button.clicked.connect(finish_scan)
        barcode_input.returnPressed.connect(finish_scan)
        cancel_button.clicked.connect(dialog.reject)
        barcode_input.setFocus()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            code = barcode_input.text().strip()
            user = self.db.get_user_by_barcode(code)
            if user:
                self._open_main(user)
            else:
                QtWidgets.QMessageBox.warning(
                    self, "QR Tidak Terdaftar",
                    "QR Code ini tidak terdaftar sebagai kartu pustakawan."
                )

    def _create_register_page(self):
        w = QtWidgets.QWidget()
        w.setObjectName("authPage")
        w.setStyleSheet("""
            QWidget#authPage {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f7fbff, stop:1 #eef4ff);
            }
            QFrame#authCard {
                background-color: #ffffff;
                border: 1px solid #dce7f2;
                border-radius: 18px;
                max-width: 380px;
            }
            QLabel#authTitle {
                font-family: "Trebuchet MS", sans-serif;
                font-size: 20px;
                font-weight: 700;
                color: #243447;
            }
            QPushButton#authPrimary {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 999px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 600;
                min-height: 36px;
                max-width: 260px;
            }
            QPushButton#authPrimary:hover {
                background-color: #219150;
            }
            QPushButton#authLink {
                background: transparent;
                color: #2a6fde;
                border: none;
                text-align: center;
                font-size: 12px;
                padding: 8px 0;
            }
            QLineEdit {
                border: 1px solid #d0d8e2;
                border-radius: 10px;
                padding: 8px 12px;
                min-height: 34px;
                font-size: 14px;
                max-width: 300px;
            }
            QLineEdit:focus {
                border: 1px solid #27ae60;
            }
        """)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(28, 28, 28, 28)

        card = QtWidgets.QFrame()
        card.setObjectName("authCard")
        card.setMinimumWidth(480)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignCenter)

        logo_path = get_asset_path('LOGO.png')
        if os.path.exists(logo_path):
            pix = QtGui.QPixmap(logo_path)
            if not pix.isNull():
                logo_lbl = QtWidgets.QLabel()
                logo_lbl.setAlignment(Qt.AlignCenter)
                logo_lbl.setPixmap(pix.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                card_layout.addWidget(logo_lbl)

        title = QtWidgets.QLabel("Daftar Akun Pustakawan")
        title.setObjectName("authTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        self.r_username = QtWidgets.QLineEdit()
        self.r_fullname = QtWidgets.QLineEdit()
        self.r_password = QtWidgets.QLineEdit()
        self.r_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.r_password2 = QtWidgets.QLineEdit()
        self.r_password2.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("Username", self.r_username)
        form.addRow("Nama Lengkap", self.r_fullname)
        form.addRow("Password", self.r_password)
        form.addRow("Konfirmasi", self.r_password2)
        card_layout.addLayout(form)

        btn_reg = QtWidgets.QPushButton("Daftar")
        btn_reg.setObjectName("authPrimary")
        btn_reg.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 999px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 600;
                min-height: 36px;
                max-width: 260px;
            }
            QPushButton:hover { background-color: #219150; }
        """)
        btn_reg.clicked.connect(self._on_register)
        self.r_password2.returnPressed.connect(self._on_register)
        card_layout.addWidget(btn_reg, alignment=Qt.AlignCenter)

        link_login = QtWidgets.QPushButton("Sudah punya akun? Login")
        link_login.setObjectName("authLink")
        link_login.clicked.connect(lambda: self.stack.setCurrentWidget(self.login_page))
        card_layout.addWidget(link_login, alignment=Qt.AlignCenter)

        v.addWidget(card, alignment=Qt.AlignCenter)
        return w

    def _create_reset_page(self):
        w = QtWidgets.QWidget()
        w.setObjectName("authPage")
        w.setStyleSheet("""
            QWidget#authPage {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f7fbff, stop:1 #eef4ff);
            }
            QFrame#authCard {
                background-color: #ffffff;
                border: 1px solid #dce7f2;
                border-radius: 18px;
                max-width: 380px;
            }
            QLabel#authTitle {
                font-family: "Trebuchet MS", sans-serif;
                font-size: 20px;
                font-weight: 700;
                color: #243447;
            }
            QPushButton#authPrimary {
                background-color: #2a6fde;
                color: white;
                border: none;
                border-radius: 999px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 600;
                min-height: 36px;
                max-width: 260px;
            }
            QPushButton#authPrimary:hover {
                background-color: #2158b8;
            }
            QPushButton#authLink {
                background: transparent;
                color: #2a6fde;
                border: none;
                text-align: center;
                font-size: 12px;
                padding: 8px 0;
            }
            QLineEdit {
                border: 1px solid #d0d8e2;
                border-radius: 10px;
                padding: 8px 12px;
                min-height: 34px;
                font-size: 14px;
                max-width: 300px;
            }
            QLineEdit:focus {
                border: 1px solid #2a6fde;
            }
        """)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(28, 28, 28, 28)

        card = QtWidgets.QFrame()
        card.setObjectName("authCard")
        card.setMinimumWidth(480)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignCenter)

        logo_path = get_asset_path('LOGO.png')
        if os.path.exists(logo_path):
            pix = QtGui.QPixmap(logo_path)
            if not pix.isNull():
                logo_lbl = QtWidgets.QLabel()
                logo_lbl.setAlignment(Qt.AlignCenter)
                logo_lbl.setPixmap(pix.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                card_layout.addWidget(logo_lbl)

        title = QtWidgets.QLabel("Ganti Password")
        title.setObjectName("authTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        self.rs_username = QtWidgets.QLineEdit()
        self.rs_newpassword = QtWidgets.QLineEdit()
        self.rs_newpassword.setEchoMode(QtWidgets.QLineEdit.Password)
        self.rs_newpassword2 = QtWidgets.QLineEdit()
        self.rs_newpassword2.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("Username", self.rs_username)
        form.addRow("Password Baru", self.rs_newpassword)
        form.addRow("Konfirmasi", self.rs_newpassword2)
        card_layout.addLayout(form)

        btn_reset = QtWidgets.QPushButton("Ganti Password")
        btn_reset.setObjectName("authPrimary")
        btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #2a6fde;
                color: white;
                border: none;
                border-radius: 999px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 600;
                min-height: 36px;
                max-width: 260px;
            }
            QPushButton:hover { background-color: #2158b8; }
        """)
        btn_reset.clicked.connect(self._on_reset_password)
        self.rs_newpassword2.returnPressed.connect(self._on_reset_password)
        card_layout.addWidget(btn_reset, alignment=Qt.AlignCenter)

        link_login = QtWidgets.QPushButton("Kembali ke Login")
        link_login.setObjectName("authLink")
        link_login.clicked.connect(lambda: self.stack.setCurrentWidget(self.login_page))
        card_layout.addWidget(link_login, alignment=Qt.AlignCenter)

        v.addWidget(card, alignment=Qt.AlignCenter)
        return w

    def _on_login(self):
        try:
            username = self.l_username.text().strip()
            password = self.l_password.text()
            user = self.db.authenticate_user(username, password)
            if user:
                # Open main window
                self._open_main(user)
            else:
                QtWidgets.QMessageBox.warning(self, "Gagal Login", "Username atau password salah.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error Login", f"Terjadi kesalahan saat login:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def _on_register(self):
        u = self.r_username.text().strip()
        full = self.r_fullname.text().strip()
        p1 = self.r_password.text()
        p2 = self.r_password2.text()
        if not u or not p1:
            QtWidgets.QMessageBox.warning(self, "Data kurang", "Username dan password tidak boleh kosong")
            return
        if p1 != p2:
            QtWidgets.QMessageBox.warning(self, "Password mismatch", "Password dan konfirmasi tidak cocok")
            return
        
        # Check admin limit first (friendly UI message)
        if len(self.db.list_users()) >= 15:
            QtWidgets.QMessageBox.warning(self, "Batas Akun Tercapai",
                                          "Maaf, jumlah akun pustakawan maksimal 15. Tidak dapat membuat akun baru.")
            return
        
        try:
            # Check duplicates explicitly to show friendly messages
            if self.db.get_user_by_username(u):
                QtWidgets.QMessageBox.warning(self, "Sudah Terdaftar", "Username tersebut sudah memiliki akun.")
                return
            if full:
                c = self.db.conn.cursor()
                c.execute('SELECT id FROM users WHERE LOWER(full_name)=LOWER(?)', (full,))
                if c.fetchone():
                    QtWidgets.QMessageBox.warning(self, "Sudah Terdaftar", "Nama lengkap tersebut sudah memiliki akun.")
                    return

            self.db.add_user(u, p1, full)
            user = self.db.get_user_by_username(u)
            if user is None:
                raise ValueError("Gagal mengambil data user setelah pembuatan. Silakan login kembali.")
            QtWidgets.QMessageBox.information(self, "Berhasil", "Akun berhasil dibuat. Anda akan diarahkan ke aplikasi.")
            self._open_main(user)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Gagal", f"Gagal membuat akun: {e}")

    def _on_reset_password(self):
        u = self.rs_username.text().strip()
        p1 = self.rs_newpassword.text()
        p2 = self.rs_newpassword2.text()
        if not u or not p1:
            QtWidgets.QMessageBox.warning(self, "Data kurang", "Isi username dan password baru")
            return
        if p1 != p2:
            QtWidgets.QMessageBox.warning(self, "Password mismatch", "Password dan konfirmasi tidak cocok")
            return
        # Check user exists
        user = self.db.get_user_by_username(u)
        if not user:
            QtWidgets.QMessageBox.warning(self, "Tidak ditemukan", "Username tidak ditemukan")
            return
        # Update password
        try:
            self.db.update_user_password(u, p1)
            QtWidgets.QMessageBox.information(self, "Berhasil", "Password berhasil diubah. Silakan login dengan password baru.")
            self.stack.setCurrentWidget(self.login_page)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Gagal", f"Gagal mengganti password: {e}")

    def _open_main(self, user):
        if user is None:
            QtWidgets.QMessageBox.critical(self, "Error", "Data user tidak valid. Silakan login kembali.")
            return
        try:
            app = QtWidgets.QApplication.instance()
            if app is None:
                raise RuntimeError("Aplikasi Qt tidak tersedia.")

            previous_main = getattr(app, "_previous_main_window", None)
            if previous_main is not None:
                try:
                    if hasattr(previous_main, "cleanup_resources"):
                        previous_main.cleanup_resources()
                    previous_main.close()
                except Exception:
                    pass
                try:
                    del app._previous_main_window
                except Exception:
                    pass

            main_win = MainWindow(db=self.db)
            main_win.current_user = user
            main_win.update_avatar_display()
            app._active_window = main_win
            main_win.show()
            self.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal membuka aplikasi: {e}")
            import traceback
            traceback.print_exc()


def main():
    import traceback
    try:
        app = QtWidgets.QApplication(sys.argv)

        # Sinkronkan waktu transaksi sebelum database dan jendela aplikasi dibuat.
        synchronize_indonesia_time()
        
        # Apply modern stylesheet
        try:
            apply_modern_stylesheet(app)
        except Exception as e:
            print(f"[WARNING] Failed to apply modern stylesheet: {e}")
        
        # Ensure application icon is set early (works both in dev and packaged exe)
        try:
            icon_path = get_asset_path('app_icon.ico')
            if os.path.exists(icon_path):
                app.setWindowIcon(QtGui.QIcon(icon_path))
        except Exception:
            pass

        # Initialize DB first so we can check for existing users
        db = Database()
        
        # Create default user 'admin' if no users exist
        if not db.list_users():
            try:
                db.add_user('admin', 'admin123', full_name='Administrator', role='administrator')
                print("[OK] User default 'admin' berhasil dibuat")
            except Exception as e:
                print(f"[WARNING] Tidak dapat membuat user default: {e}")

        # Show AuthWindow (full-window login/register/reset) instead of modal dialogs
        auth = None
        try:
            auth = AuthWindow(db, start_page='register' if not db.list_users() else 'login')
            app._active_window = auth
            auth.show()
            # AuthWindow will create and show MainWindow after successful auth
            sys.exit(app.exec_())
        except Exception as e:
            print(f"Authentication window error: {e}")
            traceback.print_exc()
            if auth:
                auth.close()
            return
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"Error: {e}\n\n{traceback.format_exc()}", "Fatal Error", 0)


if __name__ == "__main__":
    main()