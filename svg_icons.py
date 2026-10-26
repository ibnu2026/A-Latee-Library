"""
SVG Icons untuk Library Application
Semua icons dalam format SVG untuk kualitas terbaik
"""

SVG_ICONS = {
    # Dashboard & Navigation
    "dashboard": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="8" height="8" rx="1"/>
        <rect x="13" y="3" width="8" height="8" rx="1"/>
        <rect x="3" y="13" width="8" height="8" rx="1"/>
        <rect x="13" y="13" width="8" height="8" rx="1"/>
    </svg>''',
    
    "books": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 6h16v12c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V6z"/>
        <path d="M4 6V4c0-1.1.9-2 2-2h12c1.1 0 2 .9 2 2v2"/>
        <line x1="4" y1="9" x2="20" y2="9" stroke="currentColor" stroke-width="2"/>
    </svg>''',
    
    "members": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="8" r="4"/>
        <path d="M4 20c0-3.31 3.58-6 8-6s8 2.69 8 6"/>
    </svg>''',
    
    "visitors": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <circle cx="9" cy="8" r="3.5"/>
        <path d="M2 20c0-3 2.69-5 7-5s7 2 7 5"/>
        <circle cx="17" cy="10" r="2.5"/>
        <path d="M14 20c0-2 1.34-3 3-3s3 1 3 3"/>
    </svg>''',
    
    "borrow": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 6h16v12c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V6z"/>
        <path d="M8 6V3h8v3"/>
        <line x1="10" y1="10" x2="14" y2="10" stroke="currentColor" stroke-width="2"/>
        <line x1="10" y1="14" x2="14" y2="14" stroke="currentColor" stroke-width="2"/>
    </svg>''',
    
    "return": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 6h16v12c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V6z"/>
        <path d="M8 6V3h8v3"/>
        <path d="M8 12l3 3 5-5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>''',
    
    "fines": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/>
        <path d="M12 7v5l3 2" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
        <circle cx="7" cy="5" r="1.5"/>
        <circle cx="17" cy="5" r="1.5"/>
    </svg>''',
    
    "report": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="2"/>
        <line x1="3" y1="9" x2="21" y2="9" stroke="currentColor" stroke-width="2"/>
        <line x1="9" y1="3" x2="9" y2="21" stroke="currentColor" stroke-width="2"/>
    </svg>''',
    
    # Action buttons
    "add": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <line x1="12" y1="5" x2="12" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>''',
    
    "search": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" xmlns="http://www.w3.org/2000/svg">
        <circle cx="11" cy="11" r="8"/>
        <path d="M21 21l-4.35-4.35"/>
    </svg>''',
    
    "refresh": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 12a8 8 0 0 1 15.477-2.604M20 12a8 8 0 0 1-15.477 2.604"/>
        <polyline points="8 16 4 12 8 8"/>
        <polyline points="16 8 20 12 16 16"/>
    </svg>''',
    
    "delete": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 6h18M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2M10 10v8M14 10v8M5 6h14l-1 12c0 1-1 2-2 2H8c-1 0-2-1-2-2L5 6z"/>
    </svg>''',
    
    "edit": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z"/>
        <path d="M20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
    </svg>''',
    
    "save": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M17 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4z"/>
        <path d="M12 19c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4z"/>
        <polyline points="7 3 7 9 17 9" fill="none" stroke="white" stroke-width="1"/>
    </svg>''',
    
    "close": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>''',
    
    # Authentication
    "login": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 12c0-4.97 4.03-9 9-9s9 4.03 9 9-4.03 9-9 9-9-4.03-9-9zm9-7c-3.87 0-7 3.13-7 7s3.13 7 7 7 7-3.13 7-7-3.13-7-7-7z"/>
        <path d="M12 5v9M16 14l-4 4-4-4"/>
    </svg>''',
    
    "user": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="8" r="4"/>
        <path d="M12 14c-6 0-8 3-8 5v3h16v-3c0-2-2-5-8-5z"/>
    </svg>''',
    
    "password": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="11" width="18" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="2"/>
        <path d="M7 11V7c0-2.76 2.24-5 5-5s5 2.24 5 5v4"/>
        <circle cx="12" cy="16" r="1.5"/>
    </svg>''',
    
    "eye": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 5c-5 0-9.27 3.11-11 7.5 1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zm0 12.5c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z"/>
    </svg>''',
    
    # Status icons
    "success": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
        <polyline points="9 16 5 12 6.41 10.59 9 13.17 17.59 4.59 19 6" stroke="white" stroke-width="2" fill="none"/>
    </svg>''',
    
    "error": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="#ff4444"/>
        <line x1="12" y1="7" x2="12" y2="13" stroke="white" stroke-width="2" stroke-linecap="round"/>
        <circle cx="12" cy="16" r="1" fill="white"/>
    </svg>''',
    
    "warning": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L2 20h20L12 2zm0 16h-1v-1h1v1zm0-3h-1V8h1v7z" fill="#ffaa00"/>
    </svg>''',
    
    # File operations
    "upload": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" xmlns="http://www.w3.org/2000/svg">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>''',
    
    "download": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" xmlns="http://www.w3.org/2000/svg">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>''',
    
    "folder": '''<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
    </svg>''',
}

def get_svg_icon(icon_name, size=24, color="currentColor"):
    """Get SVG icon as QIcon
    
    Parameters:
    - icon_name: nama dari icon (key di SVG_ICONS dict)
    - size: ukuran dalam pixels (default 24)
    - color: warna SVG (default currentColor)
    
    Returns:
    - QtGui.QIcon
    """
    from PyQt5 import QtGui, QtCore
    
    if icon_name not in SVG_ICONS:
        return QtGui.QIcon()
    
    svg_str = SVG_ICONS[icon_name].replace('currentColor', color)
    
    # Create SVG pixmap
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)
    
    painter = QtGui.QPainter(pixmap)
    
    # Parse dan draw SVG (simplified)
    # Gunakan QSvgRenderer untuk render SVG
    try:
        from PyQt5.QtSvg import QSvgRenderer
        renderer = QSvgRenderer()
        renderer.load(svg_str.encode())
        renderer.render(painter)
    except:
        # Fallback jika QSvg tidak tersedia
        pass
    
    painter.end()
    return QtGui.QIcon(pixmap)


def create_icon_button(icon_name, text="", tooltip="", size=24, parent=None):
    """Create QPushButton dengan SVG icon
    
    Parameters:
    - icon_name: nama icon
    - text: button text
    - tooltip: tooltip text
    - size: icon size
    - parent: parent widget
    
    Returns:
    - QtWidgets.QPushButton
    """
    from PyQt5 import QtWidgets, QtCore
    
    btn = QtWidgets.QPushButton(text, parent)
    
    icon = get_svg_icon(icon_name, size)
    if not icon.isNull():
        btn.setIcon(icon)
        btn.setIconSize(QtCore.QSize(size, size))
    
    if tooltip:
        btn.setToolTip(tooltip)
    
    return btn
