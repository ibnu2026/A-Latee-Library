"""
Modern UI Setup untuk Library Application dengan Sidebar Navigation
File ini berisi setup_ui() yang sudah dimodifikasi untuk menggunakan sidebar
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import re


class TextScaleController(QtCore.QObject):
    FONT_SIZE_PATTERN = re.compile(r"(font-size\s*:\s*)(\d+(?:\.\d+)?)(px|pt)", re.IGNORECASE)

    def __init__(self, main_window, scale_label, smaller_button, larger_button):
        super().__init__(main_window)
        self.app = QtWidgets.QApplication.instance()
        self.settings = QtCore.QSettings("LateeLibrary", "Library")
        self.scale_label = scale_label
        self.base_app_stylesheet = self.app.styleSheet()
        try:
            initial_scale = float(self.settings.value("ui/text_scale", 1.0))
        except (TypeError, ValueError):
            initial_scale = 1.0

        smaller_button.clicked.connect(lambda: self.set_scale(self.scale - 0.1))
        larger_button.clicked.connect(lambda: self.set_scale(self.scale + 0.1))
        self.app.installEventFilter(self)
        self.set_scale(initial_scale)

    def _scale_stylesheet(self, stylesheet):
        def replace_size(match):
            size = float(match.group(2)) * self.scale
            return f"{match.group(1)}{size:.1f}{match.group(3)}"

        return self.FONT_SIZE_PATTERN.sub(replace_size, stylesheet)

    def _capture_widget_base(self, widget):
        if widget.property("_text_scale_style") is None:
            widget.setProperty("_text_scale_style", widget.styleSheet())
        if widget.property("_text_scale_font") is None:
            widget.setProperty("_text_scale_font", QtGui.QFont(widget.font()))

    def _apply_widget_scale(self, widget):
        self._capture_widget_base(widget)
        widget.setStyleSheet(self._scale_stylesheet(widget.property("_text_scale_style")))
        base_font = widget.property("_text_scale_font")
        scaled_font = QtGui.QFont(base_font)
        if base_font.pointSizeF() > 0:
            scaled_font.setPointSizeF(max(7.0, base_font.pointSizeF() * self.scale))
        elif base_font.pixelSize() > 0:
            scaled_font.setPixelSize(max(9, round(base_font.pixelSize() * self.scale)))
        widget.setFont(scaled_font)

    def set_scale(self, scale):
        self.scale = round(max(0.8, min(1.5, scale)), 1)
        widgets = self.app.allWidgets()
        for widget in widgets:
            self._capture_widget_base(widget)
        self.app.setStyleSheet(self._scale_stylesheet(self.base_app_stylesheet))
        for widget in widgets:
            self._apply_widget_scale(widget)
        self.scale_label.setText(f"{round(self.scale * 100)}%")
        self.settings.setValue("ui/text_scale", self.scale)

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Show and isinstance(watched, QtWidgets.QWidget):
            self._apply_widget_scale(watched)
        return False

def setup_modern_ui(main_window):
    """
    Setup UI modern dengan sidebar di sebelah kiri dan navbar di atas
    Main window layout:
    ┌─────────────────────────────────────────┐
    │    NAVBAR (TOP) - Title + Avatar        │
    ├──────────────┬────────────────────────────┤
    │              │                            │
    │   SIDEBAR    │    MAIN CONTENT            │
    │  (LEFT)      │    (TABS + DIALOGS)        │
    │              │                            │
    ├──────────────┴────────────────────────────┤
    │           STATUS BAR (BOTTOM)             │
    └─────────────────────────────────────────┘
    """
    
    # Set main window properties
    main_window.setWindowTitle("@ Latee Library - Sistem Manajemen Perpustakaan")
    main_window.setMinimumSize(1400, 800)
    
    # Central widget dengan main layout
    central = QtWidgets.QWidget()
    main_window.setCentralWidget(central)
    main_layout = QtWidgets.QVBoxLayout(central)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)
    
    # ============ NAVBAR (TOP) ============
    navbar_widget = QtWidgets.QWidget()
    navbar_widget.setObjectName("NavbarWidget")
    navbar_widget.setStyleSheet("""
        #NavbarWidget {
            background-color: #2c3e50;
            border-bottom: 2px solid #34495e;
            padding: 0px;
            font-family: "Trebuchet MS", sans-serif;
        }
    """)
    navbar_widget.setFixedHeight(65)
    
    navbar_layout = QtWidgets.QHBoxLayout(navbar_widget)
    navbar_layout.setContentsMargins(15, 10, 15, 10)
    navbar_layout.setSpacing(15)
    
    # Title/Logo
    title = QtWidgets.QLabel("A Latee Library")
    title.setObjectName("NavbarTitle")
    title.setStyleSheet("""
        #NavbarTitle {
            font-size: 13px;
            font-weight: bold;
            color: #ecf0f1;
            padding-left: 10px;
            background-color: transparent;
            font-family: "Trebuchet MS", sans-serif;
        }
    """)
    navbar_layout.addWidget(title)
    
    # Spacer
    navbar_layout.addStretch()

    main_window.text_size_smaller = QtWidgets.QToolButton()
    main_window.text_size_smaller.setText("A-")
    main_window.text_size_smaller.setToolTip("Perkecil semua teks")
    main_window.text_size_smaller.setAccessibleName("Perkecil semua teks")
    main_window.text_size_smaller.setAutoRaise(False)
    main_window.text_size_smaller.setCursor(Qt.PointingHandCursor)
    main_window.text_size_smaller.setFixedSize(40, 36)
    main_window.text_size_smaller.setStyleSheet("QToolButton { color: #f8fafc; background-color: #40566d; border: 1px solid #526a81; border-radius: 4px; font-weight: bold; } QToolButton:hover { background-color: #2563eb; border-color: #60a5fa; } QToolButton:pressed { background-color: #1d4ed8; }")
    navbar_layout.addWidget(main_window.text_size_smaller)

    main_window.text_scale_label = QtWidgets.QLabel("100%")
    main_window.text_scale_label.setStyleSheet("color: #f8fafc; background-color: transparent; font-weight: bold;")
    main_window.text_scale_label.setAlignment(Qt.AlignCenter)
    main_window.text_scale_label.setMinimumWidth(42)
    navbar_layout.addWidget(main_window.text_scale_label)

    main_window.text_size_larger = QtWidgets.QToolButton()
    main_window.text_size_larger.setText("A+")
    main_window.text_size_larger.setToolTip("Perbesar semua teks")
    main_window.text_size_larger.setAccessibleName("Perbesar semua teks")
    main_window.text_size_larger.setAutoRaise(False)
    main_window.text_size_larger.setCursor(Qt.PointingHandCursor)
    main_window.text_size_larger.setFixedSize(40, 36)
    main_window.text_size_larger.setStyleSheet("QToolButton { color: #f8fafc; background-color: #40566d; border: 1px solid #526a81; border-radius: 4px; font-weight: bold; } QToolButton:hover { background-color: #2563eb; border-color: #60a5fa; } QToolButton:pressed { background-color: #1d4ed8; }")
    navbar_layout.addWidget(main_window.text_size_larger)
    
    # User info section (name and position) - with proper container
    user_info_container = QtWidgets.QWidget()
    user_info_container.setStyleSheet("""
        QWidget {
            background-color: #2c3e50;
            font-family: "Trebuchet MS", sans-serif;
        }
    """)
    user_info_layout = QtWidgets.QVBoxLayout(user_info_container)
    user_info_layout.setContentsMargins(0, 0, 15, 0)
    user_info_layout.setSpacing(1)
    
    main_window.navbar_user_name = QtWidgets.QLabel("Username")
    main_window.navbar_user_name.setStyleSheet("""
        QLabel {
            color: #ecf0f1;
            font-size: 13px;
            font-weight: bold;
            background-color: transparent;
            font-family: "Trebuchet MS", sans-serif;
        }
    """)
    main_window.navbar_user_name.setAlignment(Qt.AlignRight)
    user_info_layout.addWidget(main_window.navbar_user_name)
    
    main_window.navbar_user_position = QtWidgets.QLabel("Pustakawan")
    main_window.navbar_user_position.setStyleSheet("""
        QLabel {
            color: #95a5a6;
            font-size: 11px;
            background-color: transparent;
            font-family: "Trebuchet MS", sans-serif;
        }
    """)
    main_window.navbar_user_position.setAlignment(Qt.AlignRight)
    user_info_layout.addWidget(main_window.navbar_user_position)
    
    navbar_layout.addWidget(user_info_container)
    
    # User avatar + button
    main_window.avatar_button = QtWidgets.QToolButton()
    main_window.avatar_button.setCursor(Qt.PointingHandCursor)
    main_window.avatar_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
    main_window.avatar_button.setFixedSize(48, 48)
    main_window.avatar_button.setIconSize(QtCore.QSize(44, 44))
    main_window.avatar_button.setStyleSheet("""
        QToolButton {
            border: 2px solid #3498db;
            background: white;
            border-radius: 24px;
        }
        QToolButton:hover {
            border: 2px solid #2980b9;
        }
    """)
    main_window.avatar_button.clicked.connect(main_window.on_avatar_clicked)
    navbar_layout.addWidget(main_window.avatar_button)
    
    main_layout.addWidget(navbar_widget)
    
    # ============ MAIN CONTENT AREA (FULLSCREEN) ============
    content_area = QtWidgets.QWidget()
    content_layout = QtWidgets.QHBoxLayout(content_area)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(0)
    
    # ============ SIDEBAR (LEFT) - FULLHEIGHT ============
    from sidebar_navigation import SidebarNavigation
    main_window.sidebar = SidebarNavigation()
    main_window.sidebar.avatar_button = main_window.avatar_button
    content_layout.addWidget(main_window.sidebar)
    
    # ============ MAIN CONTENT (RIGHT) ============
    right_content = QtWidgets.QWidget()
    right_layout = QtWidgets.QVBoxLayout(right_content)
    right_layout.setContentsMargins(15, 15, 15, 15)
    right_layout.setSpacing(10)
    
    # Tab widget (content tabs) - hide tab bar display since we use sidebar for navigation
    main_window.tabs = QtWidgets.QTabWidget()
    main_window.tabs.tabBar().hide()  # Hide the tab bar at top
    main_window.tabs.setStyleSheet("""
        QTabWidget::pane { border: none; }
    """)
    right_layout.addWidget(main_window.tabs)
    
    content_layout.addWidget(right_content, 1)
    main_layout.addWidget(content_area, 1)
    
    # ============ SETUP STATUS BAR ============
    main_window.status = main_window.statusBar()
    main_window.status.setStyleSheet("""
        QStatusBar {
            background-color: white;
            color: #555;
            border-top: 1px solid #e0e0e0;
            padding: 5px 10px;
        }
    """)
    main_window.status.showMessage("Ready")
    
    # ============ SETUP TAB ITEMS (Isi dari setup_ui asli) ============
    # Ini adalah isi tab-tab yang sama seperti sebelumnya
    
    # Setup tabs dari file asli (memanggil method yang sudah ada)
    _setup_tabs_content(main_window)
    
    # ============ SETUP SIDEBAR NAVIGATION ============
    _setup_sidebar_items(main_window)
    
    # Update avatar
    main_window.current_user = None
    main_window.update_avatar_display()


def _setup_sidebar_items(main_window):
    """Setup navigation items di sidebar"""
    nav_items = [
        ("Dashboard", 0),
        ("Buku", 1),
        ("Penjualan", 2),
        ("Anggota", 3),
        ("Pengunjung", 4),
        ("Peminjaman", 5),
        ("Pengembalian", 6),
        ("Denda", 7),
        ("Laporan", 8),
        ("User", 9),
        ("Database", 10),
    ]
    
    for label, tab_index in nav_items:
        main_window.sidebar.add_nav_item("", label, tab_index)
    
    # Connect sidebar signals to tab changes
    main_window.sidebar.tab_changed.connect(lambda tab_idx: main_window.tabs.setCurrentIndex(tab_idx))
    
    # Connect tab changes to sidebar updates
    main_window.tabs.currentChanged.connect(lambda idx: main_window.sidebar.set_active_tab(idx))
    
    # Set first tab as active
    main_window.sidebar.set_active_tab(0)


def _setup_tabs_content(main_window):
    """Setup content untuk semua tabs (dari setup_ui asli)"""
    
    # ========== DASHBOARD ==========
    tab_dash = QtWidgets.QWidget()
    main_window.tabs.addTab(tab_dash, "Dashboard")
    dash = QtWidgets.QVBoxLayout(tab_dash)
    dash.setSpacing(16)
    dash.setContentsMargins(10, 10, 10, 10)

    stats = QtWidgets.QHBoxLayout()
    stats.setSpacing(14)
    stats.setContentsMargins(0, 0, 0, 0)

    def _create_stat_card_widget(label_text):
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 18px;
                padding: 16px;
            }
            QFrame:hover {
                background-color: #f8fbff;
                border-color: #93c5fd;
            }
        """)
        card.setMinimumHeight(120)
        card.setMaximumWidth(260)
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        value = QtWidgets.QLabel("0")
        value.setAlignment(Qt.AlignCenter)
        value.setStyleSheet("""
            font-size: 32px;
            font-weight: 700;
            color: #1d4ed8;
        """)
        title = QtWidgets.QLabel(label_text)
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet("""
            font-size: 13px;
            color: #334155;
            font-weight: 600;
        """)
        layout.addWidget(value)
        layout.addWidget(title)
        return card, value

    card_books, main_window.lbl_books = _create_stat_card_widget("Buku")
    card_members, main_window.lbl_members = _create_stat_card_widget("Anggota")
    card_borrows, main_window.lbl_borrows = _create_stat_card_widget("Dipinjam")
    card_visitors, main_window.lbl_visitors = _create_stat_card_widget("Pengunjung Hari Ini")

    stats.addWidget(card_books)
    stats.addWidget(card_members)
    stats.addWidget(card_borrows)
    stats.addWidget(card_visitors)
    dash.addLayout(stats)

    main_window._make_stat_card_clickable(card_books, 1)
    main_window._make_stat_card_clickable(card_members, 3)
    main_window._make_stat_card_clickable(card_borrows, 5)
    main_window._make_stat_card_clickable(card_visitors, 4)
    
    # Chart
    try:
        from LibraryDekstopApp import LineChart
        main_window.chart = LineChart(main_window.db)
        dash.addWidget(main_window.chart, 1)
    except Exception:
        main_window.chart = None
        dash.addStretch(1)
    
    main_window.refresh_dashboard()
    
    # ========== BUKU ==========
    tab_books = QtWidgets.QWidget()
    main_window.tabs.addTab(tab_books, "Buku")
    v_books = QtWidgets.QVBoxLayout(tab_books)
    
    form = QtWidgets.QFormLayout()
    form.setSpacing(10)
    form.setContentsMargins(10, 10, 10, 10)
    
    main_window.in_kode = QtWidgets.QLineEdit()
    main_window.in_kategori = QtWidgets.QLineEdit()
    main_window.in_judul = QtWidgets.QLineEdit()
    main_window.in_penulis = QtWidgets.QLineEdit()
    main_window.in_penerbit = QtWidgets.QLineEdit()
    main_window.in_stok = QtWidgets.QSpinBox()
    main_window.in_stok.setRange(1, 500)
    
    form.addRow("Kode Buku:", main_window.in_kode)
    form.addRow("Kategori:", main_window.in_kategori)
    form.addRow("Judul:", main_window.in_judul)
    form.addRow("Penulis:", main_window.in_penulis)
    form.addRow("Penerbit:", main_window.in_penerbit)
    form.addRow("Stok:", main_window.in_stok)
    v_books.addLayout(form)
    
    # Buttons
    hbtn = QtWidgets.QHBoxLayout()
    main_window.btn_add_book = QtWidgets.QPushButton(" Tambah / Perbarui")
    main_window.btn_scan_book_barcode = QtWidgets.QPushButton(" Scan Barcode")
    main_window.btn_import_excel = QtWidgets.QPushButton(" Import Excel")
    main_window.btn_template_excel = QtWidgets.QPushButton(" Format Excel")
    main_window.btn_refresh_books = QtWidgets.QPushButton(" Refresh")
    main_window.btn_delete_selected_books = QtWidgets.QPushButton(" Hapus Terpilih")
    
    for b in [main_window.btn_add_book, main_window.btn_scan_book_barcode,
              main_window.btn_import_excel, main_window.btn_template_excel,
              main_window.btn_refresh_books, main_window.btn_delete_selected_books]:
        b.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        hbtn.addWidget(b)
    hbtn.addStretch()
    v_books.addLayout(hbtn)
    
    # Search
    search_layout = QtWidgets.QHBoxLayout()
    search_layout.addWidget(QtWidgets.QLabel(" Cari:"))
    main_window.in_search_buku = QtWidgets.QLineEdit()
    main_window.in_search_buku.setPlaceholderText("Kode, judul, penulis...")
    search_layout.addWidget(main_window.in_search_buku)
    search_layout.addWidget(QtWidgets.QLabel("| Kategori:"))
    main_window.combo_kategori_filter = QtWidgets.QComboBox()
    main_window.combo_kategori_filter.addItem("Semua", None)
    search_layout.addWidget(main_window.combo_kategori_filter)
    search_layout.addStretch()
    v_books.addLayout(search_layout)
    
    # Table
    main_window.books_table = QtWidgets.QTableWidget()
    main_window.books_table.setContextMenuPolicy(Qt.CustomContextMenu)
    main_window.books_table.customContextMenuRequested.connect(main_window.show_book_context_menu)
    v_books.addWidget(main_window.books_table)
    
    # Connect signals
    main_window.btn_add_book.clicked.connect(main_window.add_or_update_book)
    main_window.btn_scan_book_barcode.clicked.connect(main_window.start_scan_barcode_for_book)
    main_window.btn_import_excel.clicked.connect(main_window.import_books_from_excel)
    main_window.btn_template_excel.clicked.connect(main_window.show_excel_template)
    main_window.btn_refresh_books.clicked.connect(main_window.load_books)
    main_window.btn_delete_selected_books.clicked.connect(main_window.delete_selected_books)
    main_window.in_search_buku.textChanged.connect(main_window.search_books_ui)
    main_window.combo_kategori_filter.currentIndexChanged.connect(main_window.filter_books_by_kategori)
    
    main_window.load_books()

    # ========== PENJUALAN BAZAR ==========
    main_window.setup_sales_tab()
    
    # ========== ANGGOTA (Simplified) ==========
    tab_members = QtWidgets.QWidget()
    main_window.tabs.addTab(tab_members, "Anggota")
    v_members = QtWidgets.QVBoxLayout(tab_members)
    
    # Generate QR section
    group_qr = QtWidgets.QGroupBox(" Generate QR Codes")
    v_qr = QtWidgets.QVBoxLayout(group_qr)
    qr_actions = QtWidgets.QHBoxLayout()
    main_window.btn_gen_qr = QtWidgets.QPushButton("Generate QR & Kartu")
    main_window.btn_gen_qr.clicked.connect(main_window.generate_qr_bulk)
    qr_actions.addWidget(main_window.btn_gen_qr)
    main_window.btn_refresh_pending = QtWidgets.QPushButton(" Refresh")
    main_window.btn_refresh_pending.clicked.connect(main_window.load_pending_qr_codes)
    qr_actions.addWidget(main_window.btn_refresh_pending)
    main_window.btn_members = QtWidgets.QPushButton(" Anggota Terdaftar")
    main_window.btn_members.clicked.connect(main_window.show_members_dialog)
    main_window.btn_members.setStyleSheet("""
        QPushButton {
            background-color: #27ae60;
            color: white;
            padding: 10px;
            border-radius: 4px;
            font-weight: 600;
        }
        QPushButton:hover { background-color: #229954; }
    """)
    qr_actions.addWidget(main_window.btn_members)
    v_qr.addLayout(qr_actions)
    v_members.addWidget(group_qr)
    
    # Pending QR section
    group_pending = QtWidgets.QGroupBox(" QR Codes Pending")
    v_pending = QtWidgets.QVBoxLayout(group_pending)
    search_pending = QtWidgets.QHBoxLayout()
    search_pending.addWidget(QtWidgets.QLabel(" Cari QR: "))
    main_window.in_search_pending_qr = QtWidgets.QLineEdit()
    main_window.in_search_pending_qr.setPlaceholderText("ID, QR ID, barcode, nama, rayon, kamar, atau status...")
    search_pending.addWidget(main_window.in_search_pending_qr)
    search_pending.addStretch()
    v_pending.addLayout(search_pending)
    main_window.in_search_pending_qr.textChanged.connect(main_window.search_pending_qr_codes)
    main_window.pending_qr_table = QtWidgets.QTableWidget()
    main_window.pending_qr_table.setContextMenuPolicy(Qt.CustomContextMenu)
    main_window.pending_qr_table.customContextMenuRequested.connect(main_window.show_pending_qr_context_menu)
    v_pending.addWidget(main_window.pending_qr_table)
    v_members.addWidget(group_pending)
    
    main_window.load_pending_qr_codes()
    
    # ========== PENGUNJUNG ==========
    tab_vis = QtWidgets.QWidget()
    main_window.tabs.addTab(tab_vis, "Pengunjung")
    v_vis = QtWidgets.QVBoxLayout(tab_vis)
    
    # Device status
    main_window.device_status_label = QtWidgets.QLabel(" Fingerprint Scanner: Ready")
    main_window.device_status_label.setStyleSheet("color: #27ae60; font-weight: bold; padding: 5px;")
    v_vis.addWidget(main_window.device_status_label)
    
    # Buttons
    btn_layout = QtWidgets.QHBoxLayout()
    main_window.btn_register = QtWidgets.QPushButton(" Daftar Baru")
    main_window.btn_register.setStyleSheet("background: #27ae60;")
    main_window.btn_registered = QtWidgets.QPushButton(" Terdaftar")
    main_window.btn_scan_old = QtWidgets.QPushButton(" Scan")
    main_window.btn_refresh_vis = QtWidgets.QPushButton(" Refresh")
    main_window.btn_visitor_info = QtWidgets.QPushButton(" Info Pengunjung")
    main_window.btn_visitor_info.setStyleSheet(
        "background: #2563eb; color: white; border: none; border-radius: 6px; padding: 9px 16px; font-weight: 700;"
    )
    
    main_window.btn_register.clicked.connect(main_window.show_visitor_registration_dialog)
    main_window.btn_registered.clicked.connect(main_window.show_registered_visitors_dialog)
    main_window.btn_scan_old.clicked.connect(main_window.show_scan_old_visitor_dialog)
    main_window.btn_refresh_vis.clicked.connect(main_window.load_visitors)
    main_window.btn_visitor_info.clicked.connect(main_window.show_visitor_info_dialog)
    
    for btn in [main_window.btn_register, main_window.btn_registered, main_window.btn_scan_old, main_window.btn_refresh_vis, main_window.btn_visitor_info]:
        btn_layout.addWidget(btn)
    btn_layout.addStretch()
    v_vis.addLayout(btn_layout)
    
    # Search
    search_vis = QtWidgets.QHBoxLayout()
    search_vis.addWidget(QtWidgets.QLabel(" Cari:"))
    main_window.in_search_visitor = QtWidgets.QLineEdit()
    main_window.in_search_visitor.setPlaceholderText("Nama pengunjung...")
    search_vis.addWidget(main_window.in_search_visitor)
    search_vis.addStretch()
    v_vis.addLayout(search_vis)
    
    main_window.in_search_visitor.textChanged.connect(main_window.search_visitors_ui)
    
    # Table
    main_window.vis_table = QtWidgets.QTableWidget()
    v_vis.addWidget(main_window.vis_table)
    
    main_window.load_visitors()
    
    # ========== PEMINJAMAN ==========
    tab_pinjam = QtWidgets.QWidget()
    main_window.tabs.addTab(tab_pinjam, "Peminjaman")
    v_pin = QtWidgets.QVBoxLayout(tab_pinjam)
    
    main_window.btn_pinjam = QtWidgets.QPushButton(" Scan Buku untuk Dipinjam")
    main_window.btn_pinjam.setStyleSheet("background: #3498db; color: white; padding: 10px; font-weight: 600;")
    main_window.btn_pinjam.clicked.connect(lambda: main_window.start_scan("borrow"))
    borrow_actions = QtWidgets.QHBoxLayout()
    main_window.btn_borrower_info = QtWidgets.QPushButton(" Info Peminjaman")
    main_window.btn_borrower_info.setStyleSheet(
        "background: #2563eb; color: white; border: none; border-radius: 6px; padding: 9px 16px; font-weight: 700;"
    )
    main_window.btn_borrower_info.clicked.connect(main_window.show_borrower_info_dialog)
    borrow_actions.addWidget(main_window.btn_pinjam)
    borrow_actions.addWidget(main_window.btn_borrower_info)
    borrow_actions.addStretch()
    v_pin.addLayout(borrow_actions)
    
    # Search
    search_pinjam = QtWidgets.QHBoxLayout()
    search_pinjam.addWidget(QtWidgets.QLabel(" Cari:"))
    main_window.in_search_pinjam = QtWidgets.QLineEdit()
    main_window.in_search_pinjam.setPlaceholderText("Nama atau judul buku...")
    search_pinjam.addWidget(main_window.in_search_pinjam)
    search_pinjam.addStretch()
    v_pin.addLayout(search_pinjam)
    main_window.in_search_pinjam.textChanged.connect(main_window.search_borrows_ui)

    # Tables with splitter
    splitter = QtWidgets.QSplitter(Qt.Vertical)
    
    container1 = QtWidgets.QWidget()
    layout1 = QtWidgets.QVBoxLayout(container1)
    label1 = QtWidgets.QLabel(" Peminjaman Aktif")
    label1.setStyleSheet("font-weight: bold; color: #e74c3c;")
    layout1.addWidget(label1)
    main_window.borrow_table = QtWidgets.QTableWidget()
    main_window.borrow_table.setContextMenuPolicy(Qt.CustomContextMenu)
    main_window.borrow_table.customContextMenuRequested.connect(main_window.show_borrow_context_menu)
    layout1.addWidget(main_window.borrow_table)
    layout1.setContentsMargins(0, 0, 0, 0)
    
    container2 = QtWidgets.QWidget()
    layout2 = QtWidgets.QVBoxLayout(container2)
    label2 = QtWidgets.QLabel(" Peminjaman Selesai")
    label2.setStyleSheet("font-weight: bold; color: #27ae60;")
    layout2.addWidget(label2)
    main_window.borrow_completed_table = QtWidgets.QTableWidget()
    layout2.addWidget(main_window.borrow_completed_table)
    layout2.setContentsMargins(0, 0, 0, 0)
    
    splitter.addWidget(container1)
    splitter.addWidget(container2)
    splitter.setSizes([400, 300])
    v_pin.addWidget(splitter)
    
    main_window.load_borrows()
    
    # ========== PENGEMBALIAN ==========
    tab_kembali = QtWidgets.QWidget()
    main_window.tabs.addTab(tab_kembali, "Pengembalian")
    v_kem = QtWidgets.QVBoxLayout(tab_kembali)
    
    main_window.btn_kembali = QtWidgets.QPushButton(" Scan Buku untuk Dikembalikan")
    main_window.btn_kembali.setStyleSheet("background: #f39c12; color: white; padding: 10px; font-weight: 600;")
    main_window.btn_kembali.clicked.connect(lambda: main_window.start_scan("return"))
    v_kem.addWidget(main_window.btn_kembali)
    
    # Search
    search_kembali = QtWidgets.QHBoxLayout()
    search_kembali.addWidget(QtWidgets.QLabel(" Cari:"))
    main_window.in_search_kembali = QtWidgets.QLineEdit()
    main_window.in_search_kembali.setPlaceholderText("Nama atau judul buku...")
    search_kembali.addWidget(main_window.in_search_kembali)
    search_kembali.addStretch()
    v_kem.addLayout(search_kembali)
    main_window.in_search_kembali.textChanged.connect(main_window.search_returns_ui)
    
    # Splitter
    splitter_kembali = QtWidgets.QSplitter(Qt.Vertical)
    
    container3 = QtWidgets.QWidget()
    layout3 = QtWidgets.QVBoxLayout(container3)
    label3 = QtWidgets.QLabel(" Menunggu Pengembalian")
    label3.setStyleSheet("font-weight: bold; color: #ff6600;")
    layout3.addWidget(label3)
    main_window.returns_pending_table = QtWidgets.QTableWidget()
    layout3.addWidget(main_window.returns_pending_table)
    layout3.setContentsMargins(0, 0, 0, 0)
    
    container4 = QtWidgets.QWidget()
    layout4 = QtWidgets.QVBoxLayout(container4)
    label4 = QtWidgets.QLabel(" Pengembalian Selesai")
    label4.setStyleSheet("font-weight: bold; color: #27ae60;")
    layout4.addWidget(label4)
    main_window.returns_completed_table = QtWidgets.QTableWidget()
    layout4.addWidget(main_window.returns_completed_table)
    layout4.setContentsMargins(0, 0, 0, 0)
    
    splitter_kembali.addWidget(container3)
    splitter_kembali.addWidget(container4)
    splitter_kembali.setSizes([300, 300])
    v_kem.addWidget(splitter_kembali)
    
    main_window.load_returns()
    
    # ========== DENDA ==========
    tab_denda = QtWidgets.QWidget()
    main_window.tabs.addTab(tab_denda, " Denda")
    v_denda = QtWidgets.QVBoxLayout(tab_denda)
    
    denda_header = QtWidgets.QHBoxLayout()
    denda_title = QtWidgets.QLabel(" Manajemen Denda")
    denda_title.setStyleSheet("font-weight: bold; font-size: 13px;")
    main_window.btn_refresh_denda = QtWidgets.QPushButton(" Refresh")
    main_window.btn_refresh_denda.clicked.connect(main_window.refresh_all_fines)
    denda_header.addWidget(denda_title)
    denda_header.addStretch()
    denda_header.addWidget(main_window.btn_refresh_denda)
    v_denda.addLayout(denda_header)
    
    splitter_denda = QtWidgets.QSplitter(Qt.Vertical)
    
    container5 = QtWidgets.QWidget()
    layout5 = QtWidgets.QVBoxLayout(container5)
    label5 = QtWidgets.QLabel(" Denda Belum Dibayar")
    label5.setStyleSheet("font-weight: bold; color: #e74c3c;")
    layout5.addWidget(label5)
    main_window.fines_table = QtWidgets.QTableWidget()
    main_window.fines_table.setContextMenuPolicy(Qt.CustomContextMenu)
    main_window.fines_table.customContextMenuRequested.connect(main_window.show_fines_context_menu)
    layout5.addWidget(main_window.fines_table)
    layout5.setContentsMargins(0, 0, 0, 0)
    
    container6 = QtWidgets.QWidget()
    layout6 = QtWidgets.QVBoxLayout(container6)
    label6 = QtWidgets.QLabel(" Denda Sudah Dibayar")
    label6.setStyleSheet("font-weight: bold; color: #27ae60;")
    layout6.addWidget(label6)
    main_window.paid_fines_table = QtWidgets.QTableWidget()
    layout6.addWidget(main_window.paid_fines_table)
    layout6.setContentsMargins(0, 0, 0, 0)
    
    splitter_denda.addWidget(container5)
    splitter_denda.addWidget(container6)
    splitter_denda.setSizes([400, 300])
    v_denda.addWidget(splitter_denda)
    
    main_window.load_fines()
    main_window.load_paid_fines()
    
    # ========== LAPORAN ==========
    tab_laporan = QtWidgets.QWidget()
    main_window.tabs.addTab(tab_laporan, " Laporan")
    v_lap = QtWidgets.QVBoxLayout(tab_laporan)
    v_lap.setContentsMargins(18, 18, 18, 18)
    v_lap.setSpacing(16)

    report_title = QtWidgets.QLabel("Laporan dan Analitik")
    report_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1e293b;")
    v_lap.addWidget(report_title)

    report_data_group = QtWidgets.QGroupBox("Export Data")
    report_data_group.setStyleSheet("""
        QGroupBox {
            background-color: #ffffff;
            border: 1px solid #dbe4ee;
            border-radius: 10px;
            margin-top: 12px;
            padding: 16px 12px 12px 12px;
            font-weight: 700;
            color: #334155;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 6px;
            background-color: #ffffff;
        }
    """)
    report_data_grid = QtWidgets.QGridLayout(report_data_group)
    report_data_grid.setContentsMargins(12, 18, 12, 12)
    report_data_grid.setHorizontalSpacing(12)
    report_data_grid.setVerticalSpacing(12)
    
    main_window.btn_export_books = QtWidgets.QPushButton(" Export Data Buku")
    main_window.btn_export_members = QtWidgets.QPushButton(" Export Data Anggota")
    main_window.btn_export_visitors = QtWidgets.QPushButton(" Export Data Pengunjung")
    main_window.btn_export_borrows = QtWidgets.QPushButton(" Export Data Peminjaman")
    main_window.btn_export_fines = QtWidgets.QPushButton(" Export Denda")
    main_window.btn_export_paid_fines = QtWidgets.QPushButton(" Export Denda Dibayar")
    main_window.btn_export_sales = QtWidgets.QPushButton(" Export Penjualan")
    main_window.btn_export_grafik = QtWidgets.QPushButton(" Export Grafik")
    
    report_buttons = [main_window.btn_export_books, main_window.btn_export_members,
                main_window.btn_export_visitors, main_window.btn_export_borrows,
                main_window.btn_export_fines, main_window.btn_export_paid_fines,
                main_window.btn_export_sales]
    for btn in report_buttons:
        btn.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc;
                color: #1e293b;
                border: 1px solid #cbd5e1;
                padding: 13px 16px;
                border-radius: 7px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton:hover { background-color: #e0f2fe; border-color: #38bdf8; }
        """)
    for index, btn in enumerate(report_buttons):
        report_data_grid.addWidget(btn, index // 2, index % 2)

    v_lap.addWidget(report_data_group)

    report_visual_group = QtWidgets.QGroupBox("Visualisasi")
    report_visual_group.setStyleSheet(report_data_group.styleSheet())
    report_visual_layout = QtWidgets.QVBoxLayout(report_visual_group)
    report_visual_layout.setContentsMargins(12, 18, 12, 12)
    main_window.btn_export_grafik.setStyleSheet("""
        QPushButton {
            background-color: #2563eb;
            color: white;
            border: none;
            padding: 13px 16px;
            border-radius: 7px;
            font-weight: 700;
            text-align: left;
        }
        QPushButton:hover { background-color: #1d4ed8; }
    """)
    report_visual_layout.addWidget(main_window.btn_export_grafik)
    v_lap.addWidget(report_visual_group)
    
    main_window.btn_export_books.clicked.connect(lambda: main_window.export_excel("books"))
    main_window.btn_export_members.clicked.connect(lambda: main_window.export_excel("members"))
    main_window.btn_export_visitors.clicked.connect(lambda: main_window.export_excel("visitors"))
    main_window.btn_export_borrows.clicked.connect(lambda: main_window.export_excel("borrows"))
    main_window.btn_export_fines.clicked.connect(lambda: main_window.export_excel("fines"))
    main_window.btn_export_paid_fines.clicked.connect(lambda: main_window.export_excel("paid_fines"))
    main_window.btn_export_sales.clicked.connect(lambda: main_window.export_excel("sales"))
    main_window.btn_export_grafik.clicked.connect(main_window.export_grafik_statistik)
    
    v_lap.addStretch()

    # ========== USER MANAGEMENT (ADMIN ONLY) ==========
    tab_users = QtWidgets.QWidget()
    main_window.tabs.addTab(tab_users, "User")
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
            background-color: #2563eb;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 18px;
            font-weight: 700;
        }
        QPushButton:hover { background-color: #1d4ed8; }
    """)
    btn_add_user.clicked.connect(main_window.show_add_user_dialog)
    header_users.addWidget(btn_add_user)
    v_users.addLayout(header_users)

    filter_users = QtWidgets.QHBoxLayout()
    filter_users.setSpacing(10)
    filter_users.setContentsMargins(0, 0, 0, 0)

    search_label = QtWidgets.QLabel("Cari User:")
    search_label.setStyleSheet("font-weight: 600; color: #334155;")
    filter_users.addWidget(search_label)

    main_window.user_search_input = QtWidgets.QLineEdit()
    main_window.user_search_input.setPlaceholderText("username, nama lengkap, atau role")
    main_window.user_search_input.setStyleSheet("padding: 10px; border: 1px solid #cbd5e1; border-radius: 10px;")
    main_window.user_search_input.textChanged.connect(main_window.filter_users_table)
    filter_users.addWidget(main_window.user_search_input, 1)

    btn_refresh = QtWidgets.QPushButton("Refresh")
    btn_refresh.setFixedWidth(110)
    btn_refresh.setStyleSheet("""
        QPushButton {
            background-color: #f8fafc;
            color: #334155;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            padding: 10px;
            font-weight: 600;
        }
        QPushButton:hover { background-color: #e2e8f0; }
    """)
    btn_refresh.clicked.connect(main_window.load_users_table)
    filter_users.addWidget(btn_refresh)
    btn_delete_users = QtWidgets.QPushButton("Hapus Terpilih")
    btn_delete_users.clicked.connect(main_window.delete_selected_users)
    filter_users.addWidget(btn_delete_users)

    v_users.addLayout(filter_users)

    main_window.users_table = QtWidgets.QTableWidget()
    main_window.users_table.setColumnCount(5)
    main_window.users_table.setHorizontalHeaderLabels(["ID", "Username", "Nama Lengkap", "Role", "Aksi"])
    main_window.users_table.setAlternatingRowColors(True)
    main_window.users_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    main_window.users_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    main_window.users_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    main_window.users_table.setContextMenuPolicy(Qt.CustomContextMenu)
    main_window.users_table.customContextMenuRequested.connect(main_window.show_user_context_menu)
    main_window.users_table.verticalHeader().setVisible(False)
    main_window.users_table.setShowGrid(False)
    header = main_window.users_table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
    header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
    header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
    header.setSectionResizeMode(3, QtWidgets.QHeaderView.Interactive)
    header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
    main_window.users_table.setColumnWidth(3, 170)
    main_window.users_table.setColumnWidth(4, 200)
    main_window.users_table.setSortingEnabled(True)
    main_window.users_table.setStyleSheet("""
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
    v_users.addWidget(main_window.users_table)

    main_window.load_users_table()
    main_window.setup_database_tab()
    main_window.tabs.setTabVisible(9, False)
    main_window.tabs.setTabVisible(10, False)
    main_window.text_scale_controller = TextScaleController(
        main_window,
        main_window.text_scale_label,
        main_window.text_size_smaller,
        main_window.text_size_larger,
    )
