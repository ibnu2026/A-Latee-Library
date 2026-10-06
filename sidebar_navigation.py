"""
Sidebar Navigation Component untuk Library Application
Sidebar modern dengan icon dan animasi smooth
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal

class SidebarNavigation(QtWidgets.QWidget):
    """Sidebar navigation dengan smooth transitions dan modern design"""
    
    # Signals untuk navigasi
    tab_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarWidget")
        self.tab_buttons = []
        self.nav_buttons_by_tab = {}
        self.active_button = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize sidebar UI"""
        self.setFixedWidth(250)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Scroll area untuk buttons (fullheight - no header)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #2c3e50;
                border: none;
                font-family: "Trebuchet MS", sans-serif;
            }
            QScrollBar:vertical {
                background-color: #34495e;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background-color: #7f8c8d;
                border-radius: 4px;
            }
        """)
        
        container = QtWidgets.QWidget()
        container.setStyleSheet("""
            background-color: #2c3e50;
            font-family: "Trebuchet MS", sans-serif;
        """)
        self.buttons_layout = QtWidgets.QVBoxLayout(container)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(0)
        
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)  # Add with stretch factor to take all available space
    
    def add_nav_item(self, icon, label, tab_index):
        """Tambah item navigasi ke sidebar"""
        btn = QtWidgets.QToolButton()
        btn.setText(label if not icon else f"{icon} {label}")
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn.setCheckable(True)
        btn.setProperty("tab_index", tab_index)
        btn.setFixedHeight(50)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked: self._on_button_clicked(btn))
        
        self.tab_buttons.append((btn, tab_index))
        self.nav_buttons_by_tab[tab_index] = btn
        # Remove stretch if exists, add button, then add stretch back
        while self.buttons_layout.count() > 0 and self.buttons_layout.itemAt(self.buttons_layout.count() - 1).spacerItem():
            self.buttons_layout.removeItem(self.buttons_layout.itemAt(self.buttons_layout.count() - 1))
        
        self.buttons_layout.addWidget(btn)
        self.buttons_layout.addStretch()  # Always keep stretch at the end
        
        return btn
    
    def _on_button_clicked(self, button):
        """Handle button click dengan active state"""
        if self.active_button:
            self.active_button.setProperty("active", "false")
            self.active_button.style().unpolish(self.active_button)
            self.active_button.style().polish(self.active_button)
        
        self.active_button = button
        button.setProperty("active", "true")
        button.style().unpolish(button)
        button.style().polish(button)
        
        tab_index = button.property("tab_index")
        self.tab_changed.emit(tab_index)
    
    def set_active_tab(self, tab_index):
        """Set active tab berdasarkan index"""
        for btn, idx in self.tab_buttons:
            if idx == tab_index:
                if self.active_button:
                    self.active_button.setProperty("active", "false")
                    self.active_button.style().unpolish(self.active_button)
                    self.active_button.style().polish(self.active_button)
                
                self.active_button = btn
                btn.setProperty("active", "true")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                break

    def set_nav_item_visible(self, tab_index, visible):
        """Sembunyikan atau tampilkan item sidebar berdasarkan tab index"""
        button = self.nav_buttons_by_tab.get(tab_index)
        if button is None:
            return
        button.setVisible(visible)
        if not visible and self.active_button is button:
            self.active_button = None
    
    def set_user_label(self, username):
        """Update user label di sidebar"""
        self.user_label.setText(f"👤 {username}")
    
    def clear_nav_items(self):
        """Clear semua navigation items"""
        for btn, _ in self.tab_buttons:
            btn.deleteLater()
        self.tab_buttons.clear()
        self.active_button = None


class ModernMainWindow(QtWidgets.QMainWindow):
    """Main window dengan sidebar layout"""
    
    def __init__(self):
        super().__init__()
        self.sidebar = None
        self.content_widget = None
        self.setup_sidebar_layout()
    
    def setup_sidebar_layout(self):
        """Setup layout dengan sidebar di sebelah kiri"""
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QtWidgets.QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar di sebelah kiri
        self.sidebar = SidebarNavigation()
        main_layout.addWidget(self.sidebar)
        
        # Content area di sebelah kanan
        self.content_widget = QtWidgets.QWidget()
        self.content_widget.setStyleSheet("background-color: white;")
        content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        main_layout.addWidget(self.content_widget, 1)
    
    def get_content_layout(self):
        """Get main content layout untuk tambah widgets"""
        if self.content_widget:
            return self.content_widget.layout()
        return None
