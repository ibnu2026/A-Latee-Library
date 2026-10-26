"""
Modern Dark Theme Stylesheet untuk Library Application
Desain elegan dengan sidebar, gradients, dan shadows
"""

MODERN_STYLESHEET = """
/* ============ GENERAL ============ */
* {
    margin: 0;
    padding: 0;
    font-family: "Trebuchet MS", sans-serif;
}

QMainWindow {
    background-color: #f5f5f5;
    font-family: "Trebuchet MS", sans-serif;
}

QWidget {
    background-color: #f5f5f5;
    color: #333333;
    font-family: "Trebuchet MS", sans-serif;
}

/* ============ HEADER ============ */
#HeaderWidget {
    background-color: white;
    border-bottom: 2px solid #e0e0e0;
    padding: 12px 20px;
    min-height: 70px;
}

#HeaderTitle {
    font-size: 22px;
    font-weight: bold;
    color: #1a1a1a;
}

/* ============ SIDEBAR ============ */
#SidebarWidget {
    background-color: #2c3e50;
    border-right: 1px solid #1a252f;
    font-family: "Trebuchet MS", sans-serif;
}

#SidebarWidget QToolButton {
    background-color: transparent;
    color: #ecf0f1;
    border: none;
    padding: 15px 20px;
    text-align: left;
    font-size: 12px;
    font-weight: 500;
    border-left: 4px solid transparent;
    margin: 2px 0px;
    transition: all 0.3s ease;
    font-family: "Trebuchet MS", sans-serif;
}

#SidebarWidget QToolButton:hover {
    background-color: #34495e;
    color: #3498db;
    border-left: 4px solid #3498db;
}

#SidebarWidget QToolButton:pressed {
    background-color: #1a252f;
}

#SidebarWidget QToolButton[active="true"] {
    background-color: #34495e;
    color: #3498db;
    border-left: 4px solid #3498db;
    font-weight: 600;
}

#SidebarLogo {
    color: #ecf0f1;
    font-size: 14px;
    font-weight: bold;
    text-align: center;
    padding: 20px;
    border-bottom: 1px solid #34495e;
}

/* ============ TABS ============ */
QTabWidget::pane {
    border: none;
    background-color: #f5f5f5;
}

QTabBar {
    background-color: transparent;
    border: none;
}

QTabBar::tab {
    background-color: #e8e8e8;
    color: #555;
    min-width: 88px;
    padding: 8px 12px;
    margin-right: 2px;
    border: none;
    font-weight: 500;
    border-bottom: 3px solid transparent;
}

QTabBar::tab:hover {
    background-color: #d0d0d0;
    color: #333;
}

QTabBar::tab:selected {
    background-color: white;
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
}

QTabWidget > QWidget {
    background-color: white;
}

/* ============ BUTTONS ============ */
QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: 500;
    font-size: 11px;
}

QPushButton:hover {
    background-color: #2980b9;
}

QPushButton:pressed {
    background-color: #1a5276;
}

QPushButton:disabled {
    background-color: #bdc3c7;
    color: #95a5a6;
}

/* Primary buttons */
QPushButton#btn_add {
    background-color: #27ae60;
}

QPushButton#btn_add:hover {
    background-color: #229954;
}

/* Success buttons */
QPushButton#btn_success {
    background-color: #27ae60;
}

/* Danger buttons */
QPushButton#btn_danger {
    background-color: #e74c3c;
}

QPushButton#btn_danger:hover {
    background-color: #c0392b;
}

/* Warning buttons */
QPushButton#btn_warning {
    background-color: #f39c12;
}

QPushButton#btn_warning:hover {
    background-color: #d68910;
}

/* ============ INPUT FIELDS ============ */
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: white;
    color: #333333;
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 11px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #3498db;
    background-color: #f9f9f9;
}

QComboBox::drop-down {
    border: none;
}

QComboBox::down-arrow {
    image: none;
    width: 0px;
}

/* ============ TABLES ============ */
QTableWidget {
    background-color: white;
    alternate-background-color: #f8f9fa;
    gridline-color: #ecf0f1;
    border: 1px solid #bdc3c7;
    border-radius: 4px;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #3498db;
    color: white;
}

QHeaderView::section {
    background-color: #2c3e50;
    color: white;
    padding: 6px;
    border: none;
    font-weight: 600;
    font-size: 11px;
}

/* ============ LABELS ============ */
QLabel {
    color: #333333;
}

QLabel#StatusLabel {
    color: #7f8c8d;
    font-size: 10px;
}

/* ============ STATUS BAR ============ */
QStatusBar {
    background-color: white;
    color: #555;
    border-top: 1px solid #e0e0e0;
    padding: 5px;
    font-size: 10px;
}

/* ============ GROUPBOX ============ */
QGroupBox {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
    color: #2c3e50;
    font-weight: 600;
    font-size: 11px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}

/* ============ SCROLL BAR ============ */
QScrollBar:vertical {
    background-color: #ecf0f1;
    width: 12px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #95a5a6;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #7f8c8d;
}

QScrollBar:horizontal {
    background-color: #ecf0f1;
    height: 12px;
    border: none;
}

QScrollBar::handle:horizontal {
    background-color: #95a5a6;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #7f8c8d;
}

/* ============ DIALOG ============ */
QDialog {
    background-color: white;
}

QDialog QLabel {
    color: #333;
}

QDialog QPushButton {
    min-width: 80px;
}

/* ============ MENU ============ */
QMenu {
    background-color: #ffffff;
    color: #243447;
    border: 1px solid #dce7f2;
    border-radius: 10px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 14px;
    border-radius: 6px;
    min-width: 160px;
}

QMenu::item:selected {
    background-color: #eef5ff;
    color: #2a6fde;
}

QMenu::separator {
    height: 1px;
    background-color: #e7edf3;
    margin: 6px 0;
}

QMenuBar {
    background-color: white;
    color: #333;
    border-bottom: 1px solid #e0e0e0;
}

QMenuBar::item:selected {
    background-color: #f0f0f0;
}
"""

def apply_modern_stylesheet(app):
    """Apply modern stylesheet ke QApplication"""
    app.setStyle('Fusion')
    app.setStyleSheet(MODERN_STYLESHEET)
