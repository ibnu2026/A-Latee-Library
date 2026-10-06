"""
QR Generation System - Generate QR codes in bulk, then link to member data
Sistem ini memungkinkan:
1. Generate QR codes dalam jumlah banyak
2. Simpan QR di table (status: pending input)
3. Right-click → Input Data Anggota untuk mengisi nama, kamar, dll
4. Auto-link dengan peminjaman/pengembalian
"""

import os
import uuid
import qrcode
import sys
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PIL import Image


def get_asset_path(filename):
    """Get absolute path to asset file, works both in dev and packaged exe"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'assets', filename)
    return os.path.join(os.path.dirname(__file__), 'assets', filename)


class QRGenerationDialog(QtWidgets.QDialog):
    """Dialog untuk generate QR codes dalam jumlah banyak"""
    
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Generate QR Codes Massal")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel("Buat QR Codes Baru")
        title.setStyleSheet("font-size:16px; font-weight:bold;")
        layout.addWidget(title)
        
        # Explanation
        info = QtWidgets.QLabel(
            "Masukkan jumlah QR code yang ingin dibuat.\n"
            "QR akan tersimpan dan siap untuk input data anggota.\n\n"
            "⚠️ Pastikan ada ruang kosong untuk menyimpan file QR"
        )
        info.setStyleSheet("color: #666; font-size:11px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Input quantity
        form = QtWidgets.QFormLayout()
        self.spin_quantity = QtWidgets.QSpinBox()
        self.spin_quantity.setMinimum(1)
        self.spin_quantity.setMaximum(500)
        self.spin_quantity.setValue(10)
        form.addRow("Jumlah QR:", self.spin_quantity)
        layout.addLayout(form)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_generate = QtWidgets.QPushButton("Generate")
        btn_generate.setStyleSheet("background: #28a745; color: white; font-weight: bold; padding: 8px;")
        btn_generate.clicked.connect(self._on_generate)
        btn_cancel = QtWidgets.QPushButton("Batal")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_generate)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.result_message = ""
    
    def _on_generate(self):
        """Generate QR codes dan langsung print kartu"""
        import os
        from pathlib import Path
        
        quantity = self.spin_quantity.value()
        
        try:
            generated_count = 0
            
            # Create qrcodes folder di Documents atau user home directory untuk NSIS compatibility
            if hasattr(sys, '_MEIPASS'):
                # Running dari executable (pyinstaller/NSIS)
                qr_dir = os.path.join(str(Path.home()), "@ Latee Library", "qrcodes")
            else:
                # Running dari source
                qr_dir = "qrcodes"
            
            os.makedirs(qr_dir, exist_ok=True)
            
            for i in range(quantity):
                barcode = str(uuid.uuid4())[:12]
                filename = os.path.join(qr_dir, f"{barcode}.png")
                
                # Generate QR code with highest error correction for logo compatibility
                qr = qrcode.QRCode(
                    version=None,  # Auto-detect version based on data
                    error_correction=qrcode.constants.ERROR_CORRECT_H,  # Maximum error correction for logo
                    box_size=16,
                    border=2
                )
                qr.add_data(barcode)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                img.save(filename)
                
                # Simpan ke database (pending status)
                self._save_pending_qr(barcode)
                
                generated_count += 1
            
            self.result_message = f"[OK] Berhasil membuat {generated_count} QR codes!"
            QtWidgets.QMessageBox.information(
                self, "Sukses",
                f"[OK] Berhasil membuat {generated_count} QR codes!\n\n"
                f"File QR tersimpan di folder 'qrcodes'\n\n"
                f"Langkah selanjutnya:\n"
                f"1. Gunakan QR code untuk membuat kartu sendiri\n"
                f"2. Klik kanan QR di tabel untuk Input Data Anggota\n"
                f"3. Klik 'Aktifkan QR' setelah data diisi"
            )
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal generate QR: {e}")
    
    
    def _save_pending_qr(self, barcode):
        """Simpan QR code ke database dengan status pending"""
        # Ini akan di-implement di Database class
        if self.db and hasattr(self.db, 'add_pending_qr'):
            self.db.add_pending_qr(barcode)


class MemberDataInputDialog(QtWidgets.QDialog):
    """Dialog untuk input/edit data anggota dari QR yang sudah dibuat"""
    
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
    
    def __init__(self, parent=None, db=None, barcode=None, member_id=None, edit_mode=False):
        super().__init__(parent)
        self.db = db
        self.barcode = barcode
        self.member_id = member_id
        self.edit_mode = edit_mode
        
        if edit_mode:
            self.setWindowTitle("Edit Data Anggota")
            title_text = "Edit Data Anggota"
        else:
            self.setWindowTitle("Input Data Anggota")
            title_text = "Data Anggota Baru"
        
        self.setModal(True)
        self.setMinimumWidth(450)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel(title_text)
        title.setStyleSheet("font-size:14px; font-weight:bold;")
        layout.addWidget(title)
        
        # Barcode display
        barcode_label = QtWidgets.QLabel(f"Barcode: {barcode}")
        barcode_label.setStyleSheet("color: #0066cc; font-weight: bold; padding: 8px; background: #f0f0f0; border-radius: 4px;")
        layout.addWidget(barcode_label)
        
        # Form - 3 fields: Nama, Rayon, Nomor Kamar
        form = QtWidgets.QFormLayout()
        
        # 1. Nama
        self.in_nama = QtWidgets.QLineEdit()
        self.in_nama.setPlaceholderText("Nama lengkap anggota")
        form.addRow("Nama:", self.in_nama)
        
        # 2. Rayon (ComboBox)
        self.combo_rayon = QtWidgets.QComboBox()
        self.combo_rayon.addItems(self.RAYONS)
        form.addRow("Rayon:", self.combo_rayon)
        
        # 3. Nomor Kamar
        self.in_kamar = QtWidgets.QLineEdit()
        self.in_kamar.setPlaceholderText("Contoh: 101, 102, A1, dll")
        form.addRow("Nomor Kamar:", self.in_kamar)
        
        layout.addLayout(form)
        
        # Load data jika edit mode
        if edit_mode and member_id and db:
            self._load_member_data(member_id)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_save = QtWidgets.QPushButton("Simpan")
        btn_save.setStyleSheet("background: #28a745; color: white; font-weight: bold; padding: 8px;")
        btn_save.clicked.connect(self._on_save)
        btn_cancel = QtWidgets.QPushButton("Batal")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
    
    def _load_member_data(self, member_id):
        """Load data anggota untuk edit"""
        try:
            if not self.db:
                return
            
            c = self.db.conn.cursor()
            c.execute("SELECT nama, rayon, kamar FROM members WHERE id = ?", (member_id,))
            row = c.fetchone()
            
            if row:
                nama, rayon, kamar = row
                self.in_nama.setText(nama or "")
                
                # Set rayon combo (handle None values)
                if rayon and rayon in self.RAYONS:
                    idx = self.RAYONS.index(rayon)
                    self.combo_rayon.setCurrentIndex(idx)
                else:
                    self.combo_rayon.setCurrentIndex(0)
                
                self.in_kamar.setText(kamar or "")
        except Exception as e:
            print(f"Error loading member data: {e}")
    
    def _on_save(self):
        """Simpan/Update data anggota - Nama, Rayon, Nomor Kamar"""
        nama = self.in_nama.text().strip()
        rayon = self.combo_rayon.currentText()
        kamar = self.in_kamar.text().strip()
        
        # Validasi
        if not nama or not kamar:
            QtWidgets.QMessageBox.warning(self, "Validasi", "Nama dan Nomor Kamar wajib diisi!")
            return
        
        try:
            if self.edit_mode and self.member_id:
                # Update existing member
                if self.db and hasattr(self.db, 'update_member'):
                    self.db.update_member(self.member_id, nama=nama, rayon=rayon, kamar=kamar)
                    QtWidgets.QMessageBox.information(
                        self, "Sukses",
                        f"Data anggota berhasil diperbarui!\n\n"
                        f"Nama: {nama}\n"
                        f"Rayon: {rayon}\n"
                        f"Nomor Kamar: {kamar}"
                    )
                    self.accept()
            else:
                # Create new member
                if self.db and hasattr(self.db, 'create_member_from_qr'):
                    member_id = self.db.create_member_from_qr(
                        barcode=self.barcode,
                        nis="",
                        nama=nama,
                        kamar=kamar,
                        tempat=None,
                        tgl_lahir=None,
                        alamat="",
                        rayon=rayon
                    )
                    QtWidgets.QMessageBox.information(
                        self, "Sukses",
                        f"Data anggota berhasil disimpan!\n\n"
                        f"Nama: {nama}\n"
                        f"Rayon: {rayon}\n"
                        f"Nomor Kamar: {kamar}\n\n"
                        f"Kartu anggota sudah siap untuk dicetak."
                    )
                    self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal menyimpan data: {e}")
    
    def get_data(self):
        """Return data yang diinput - Nama, Rayon, Nomor Kamar"""
        return {
            'nama': self.in_nama.text().strip(),
            'rayon': self.combo_rayon.currentText(),
            'kamar': self.in_kamar.text().strip(),
        }
