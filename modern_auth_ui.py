"""
Modern Login & Register UI untuk Library Application
Desain elegan dengan gradients, shadows, dan smooth transitions
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

MODERN_AUTH_STYLESHEET = """
/* ============ GENERAL ============ */
QWidget {
    background-color: #f5f7fa;
}

/* ============ FORM CONTAINER ============ */
#FormContainer {
    background-color: white;
    border-radius: 12px;
    border: none;
}

/* ============ INPUT FIELDS ============ */
QLineEdit {
    background-color: #f8f9fa;
    color: #333333;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 14px;
    selection-background-color: #3498db;
    min-height: 44px;
}

QLineEdit:focus {
    border: 2px solid #3498db;
    background-color: white;
}

QLineEdit:hover {
    border: 2px solid #bdc3c7;
}

/* ============ LABELS ============ */
QLabel#TitleLabel {
    font-size: 28px;
    font-weight: bold;
    color: #2c3e50;
}

QLabel#SubtitleLabel {
    font-size: 14px;
    color: #7f8c8d;
}

QLabel#FormLabel {
    font-size: 12px;
    font-weight: 600;
    color: #333333;
}

QLabel#InfoLabel {
    font-size: 11px;
    color: #666666;
}

QLabel#ErrorLabel {
    font-size: 12px;
    color: #e74c3c;
    font-weight: 500;
}

/* ============ BUTTONS ============ */
QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 20px;
    font-weight: 600;
    font-size: 12px;
    min-height: 40px;
}

QPushButton:hover {
    background-color: #2980b9;
}

QPushButton:pressed {
    background-color: #1a5276;
}

QPushButton:disabled {
    background-color: #bdc3c7;
}

QPushButton#PrimaryButton {
    background-color: #3498db;
}

QPushButton#SecondaryButton {
    background: transparent;
    color: #3498db;
    border: 2px solid #3498db;
}

QPushButton#SecondaryButton:hover {
    background-color: #ecf0f1;
}

QPushButton#SuccessButton {
    background-color: #27ae60;
}

QPushButton#SuccessButton:hover {
    background-color: #229954;
}

/* ============ CHECKBOX ============ */
QCheckBox {
    font-size: 11px;
    color: #333;
    spacing: 5px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 2px solid #bdc3c7;
}

QCheckBox::indicator:unchecked {
    background-color: white;
}

QCheckBox::indicator:checked {
    background-color: #3498db;
    border: 2px solid #3498db;
}

/* ============ DIVIDER ============ */
#DividerLabel {
    color: #bdc3c7;
}
"""


class ModernLoginDialog(QtWidgets.QDialog):
    """Modern Login Form Dialog"""
    
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Login - Latee Library")
        self.setFixedSize(680, 760)
        self.setStyleSheet(MODERN_AUTH_STYLESHEET)
        # Do not override application icon here; let QApplication provide the icon
        
        # Remove default window frame for custom look
        self.setModal(True)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Background gradient
        self.setStyleSheet(self.styleSheet() + """
            ModernLoginDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ecf0f1,
                    stop:1 #f5f7fa
                );
            }
        """)
        
        # Center container
        center_layout = QtWidgets.QVBoxLayout()
        center_layout.setContentsMargins(48, 48, 48, 48)
        center_layout.setSpacing(24)
        
        # Header
        header_layout = QtWidgets.QVBoxLayout()
        header_layout.setSpacing(10)
        
        title = QtWidgets.QLabel("📚 Latee Library")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)
        
        subtitle = QtWidgets.QLabel("Sistem Manajemen Perpustakaan")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle)
        
        center_layout.addLayout(header_layout)
        center_layout.addSpacing(20)
        
        # Form container
        form_container = QtWidgets.QWidget()
        form_container.setObjectName("FormContainer")
        form_container.setStyleSheet("""
            #FormContainer {
                background-color: white;
                border-radius: 12px;
            }
        """)
        
        form_layout = QtWidgets.QVBoxLayout(form_container)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(15)
        
        # Login form title
        form_title = QtWidgets.QLabel("Masuk ke Akun Anda")
        form_title.setObjectName("TitleLabel")
        form_title.setStyleSheet("font-size: 20px; letter-spacing: 0.4px;")
        form_layout.addWidget(form_title)
        form_layout.addSpacing(10)
        
        # Username field
        username_label = QtWidgets.QLabel("Username")
        username_label.setObjectName("FormLabel")
        form_layout.addWidget(username_label)
        
        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Masukkan username...")
        form_layout.addWidget(self.username_input)
        
        # Password field
        password_label = QtWidgets.QLabel("Password")
        password_label.setObjectName("FormLabel")
        form_layout.addWidget(password_label)
        
        password_layout = QtWidgets.QHBoxLayout()
        password_layout.setSpacing(5)
        
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Masukkan password...")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        password_layout.addWidget(self.password_input)
        
        # Show/Hide password button
        self.show_password_btn = QtWidgets.QPushButton("👁")
        self.show_password_btn.setFixedWidth(40)
        self.show_password_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.show_password_btn)
        
        form_layout.addLayout(password_layout)
        
        # Remember me checkbox
        self.remember_checkbox = QtWidgets.QCheckBox("Ingat saya")
        form_layout.addWidget(self.remember_checkbox)
        
        # Error label
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(self.error_label)
        
        # Buttons
        button_layout = QtWidgets.QVBoxLayout()
        button_layout.setSpacing(10)
        
        login_btn = QtWidgets.QPushButton("Masuk")
        login_btn.setObjectName("PrimaryButton")
        login_btn.setMinimumHeight(50)
        login_btn.setFont(QtGui.QFont("Arial", 13, QtGui.QFont.Bold))
        login_btn.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(login_btn)
        
        form_layout.addSpacing(10)
        form_layout.addLayout(button_layout)
        
        center_layout.addWidget(form_container)
        center_layout.addStretch()
        
        # Footer
        footer_layout = QtWidgets.QVBoxLayout()
        footer_layout.setSpacing(10)
        
        divider = QtWidgets.QLabel("―――――――――――――――――――――")
        divider.setObjectName("DividerLabel")
        divider.setAlignment(Qt.AlignCenter)
        divider.setStyleSheet("font-size: 10px; color: #bdc3c7;")
        footer_layout.addWidget(divider)
        
        footer_text = QtWidgets.QLabel("Belum punya akun? Hubungi administrator")
        footer_text.setObjectName("InfoLabel")
        footer_text.setAlignment(Qt.AlignCenter)
        footer_layout.addWidget(footer_text)
        
        center_layout.addLayout(footer_layout)
        
        main_layout.addLayout(center_layout, 1)
    
    def toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.password_input.echoMode() == QtWidgets.QLineEdit.Password:
            self.password_input.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.show_password_btn.setText("🙈")
        else:
            self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
            self.show_password_btn.setText("👁")
    
    def validate_and_accept(self):
        """Validate input dan accept dialog"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username:
            self.show_error("Username tidak boleh kosong")
            return
        
        if not password:
            self.show_error("Password tidak boleh kosong")
            return
        
        if self.db and self.db.authenticate_user(username, password):
            self.accept()
        else:
            self.show_error("Username atau password salah")
    
    def show_error(self, message):
        """Show error message"""
        self.error_label.setText(message)
        # Animate error
        QtCore.QTimer.singleShot(3000, lambda: self.error_label.setText(""))
    
    def get_credentials(self):
        """Get username dan password"""
        return self.username_input.text(), self.password_input.text()


class ModernRegisterDialog(QtWidgets.QDialog):
    """Modern Register Form Dialog"""
    
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Daftar - Latee Library")
        self.setFixedSize(720, 820)
        self.setStyleSheet(MODERN_AUTH_STYLESHEET)
        self.setModal(True)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Background
        self.setStyleSheet(self.styleSheet() + """
            ModernRegisterDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ecf0f1,
                    stop:1 #f5f7fa
                );
            }
        """)
        
        # Scroll area untuk form yang panjang
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        center_layout = QtWidgets.QVBoxLayout()
        center_layout.setContentsMargins(48, 35, 48, 35)
        center_layout.setSpacing(24)
        
        # Header
        title = QtWidgets.QLabel("Daftar Akun Baru")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; letter-spacing: 0.4px;")
        center_layout.addWidget(title)
        
        # Form container
        form_container = QtWidgets.QWidget()
        form_container.setObjectName("FormContainer")
        
        form_layout = QtWidgets.QVBoxLayout(form_container)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(15)
        
        # Username field
        username_label = QtWidgets.QLabel("Username")
        username_label.setObjectName("FormLabel")
        form_layout.addWidget(username_label)
        
        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Pilih username unik...")
        form_layout.addWidget(self.username_input)
        
        # Full name field
        fullname_label = QtWidgets.QLabel("Nama Lengkap")
        fullname_label.setObjectName("FormLabel")
        form_layout.addWidget(fullname_label)
        
        self.fullname_input = QtWidgets.QLineEdit()
        self.fullname_input.setPlaceholderText("Nama lengkap Anda...")
        form_layout.addWidget(self.fullname_input)
        
        # Password field
        password_label = QtWidgets.QLabel("Password")
        password_label.setObjectName("FormLabel")
        form_layout.addWidget(password_label)
        
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Password minimal 6 karakter...")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        form_layout.addWidget(self.password_input)
        
        # Confirm password field
        confirm_label = QtWidgets.QLabel("Konfirmasi Password")
        confirm_label.setObjectName("FormLabel")
        form_layout.addWidget(confirm_label)
        
        self.confirm_input = QtWidgets.QLineEdit()
        self.confirm_input.setPlaceholderText("Ulangi password...")
        self.confirm_input.setEchoMode(QtWidgets.QLineEdit.Password)
        form_layout.addWidget(self.confirm_input)
        
        # Info label
        info = QtWidgets.QLabel("✓ Password minimal 6 karakter\n✓ Username harus unik")
        info.setObjectName("InfoLabel")
        info.setStyleSheet("color: #27ae60; font-size: 10px;")
        form_layout.addWidget(info)
        
        # Error label
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(self.error_label)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(10)
        
        register_btn = QtWidgets.QPushButton("Daftar")
        register_btn.setObjectName("SuccessButton")
        register_btn.setMinimumHeight(52)
        register_btn.setFont(QtGui.QFont("Arial", 13, QtGui.QFont.Bold))
        register_btn.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(register_btn)
        
        cancel_btn = QtWidgets.QPushButton("Batal")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.setMinimumHeight(52)
        cancel_btn.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        form_layout.addSpacing(10)
        form_layout.addLayout(button_layout)
        
        center_layout.addWidget(form_container)
        center_layout.addStretch()
        
        scroll_container = QtWidgets.QWidget()
        scroll_container.setLayout(center_layout)
        scroll.setWidget(scroll_container)
        
        main_layout.addWidget(scroll)
    
    def validate_and_accept(self):
        """Validate input dan accept dialog"""
        username = self.username_input.text().strip()
        fullname = self.fullname_input.text().strip()
        password = self.password_input.text().strip()
        confirm = self.confirm_input.text().strip()
        
        # Validate
        if not username:
            self.show_error("Username tidak boleh kosong")
            return
        
        if not fullname:
            self.show_error("Nama lengkap tidak boleh kosong")
            return
        
        if len(password) < 6:
            self.show_error("Password minimal 6 karakter")
            return
        
        if password != confirm:
            self.show_error("Password tidak cocok")
            return
        
        # Check if username exists
        if self.db and self.db.get_user_by_username(username):
            self.show_error("Username sudah terdaftar")
            return
        
        # Register user
        try:
            if self.db:
                self.db.add_user(username, password, fullname)
                self.accept()
            else:
                self.show_error("Database tidak tersedia")
        except Exception as e:
            self.show_error(f"Error: {str(e)}")
    
    def show_error(self, message):
        """Show error message"""
        self.error_label.setText(message)
        QtCore.QTimer.singleShot(3000, lambda: self.error_label.setText(""))
    
    def get_data(self):
        """Get registration data"""
        return {
            'username': self.username_input.text(),
            'password': self.password_input.text(),
            'fullname': self.fullname_input.text()
        }
