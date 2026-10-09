"""Windows-aware palettes and one consistent outline icon family."""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QFileDialog, QToolButton


PATHS = {
    "open": '<path d="M3 7h6l2 2h10v10H3z"/><path d="M3 7V5h7l2 2"/>',
    "save": '<path d="M5 3h12l4 4v14H3V3z"/><path d="M7 3v7h9V3"/><path d="M7 21v-8h10v8"/>',
    "redact": '<rect x="3" y="6" width="18" height="12" rx="1"/><path d="M6 10h12M6 14h9"/>',
    "undo": '<path d="M9 5 4 10l5 5"/><path d="M4 10h10a6 6 0 0 1 0 12"/>',
    "redo": '<path d="m15 5 5 5-5 5"/><path d="M20 10H10a6 6 0 0 0 0 12"/>',
    "metadata": '<path d="M4 3h11l5 5v13H4z"/><path d="M15 3v5h5"/><circle cx="12" cy="15" r="4"/><path d="M12 13v.1M12 15v2"/>',
    "left": '<path d="M4 10a8 8 0 1 1 2 7"/><path d="M4 4v6h6"/>',
    "right": '<path d="M20 10a8 8 0 1 0-2 7"/><path d="M20 4v6h-6"/>',
    "first": '<path d="M5 5v14M18 5l-9 7 9 7"/>',
    "prev": '<path d="M17 5l-9 7 9 7"/>',
    "next": '<path d="M7 5l9 7-9 7"/>',
    "last": '<path d="M19 5v14M6 5l9 7-9 7"/>',
    "single": '<rect x="6" y="3" width="12" height="18" rx="1"/>',
    "continuous": '<rect x="6" y="2" width="12" height="9" rx="1"/><rect x="6" y="13" width="12" height="9" rx="1"/>',
    "options": '<circle cx="12" cy="5" r="1.8" fill="{color}" stroke="none"/><circle cx="12" cy="12" r="1.8" fill="{color}" stroke="none"/><circle cx="12" cy="19" r="1.8" fill="{color}" stroke="none"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "up": '<path d="m5 14 7-7 7 7M12 7v14"/>',
    "new_folder": '<path d="M3 7h6l2 2h10v11H3z"/><path d="M13 15h6M16 12v6"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h1M3 12h1M3 18h1"/>',
    "details": '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 9h18M9 9v11"/>',
}


def icon(name: str, color: str = "#293241") -> QIcon:
    paths = PATHS[name].replace("{color}", color)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    from PySide6.QtGui import QPainter
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def theme_file_dialog(dialog: QFileDialog, dark: bool) -> None:
    """Use readable navigation icons in Qt's themed file chooser."""
    color = "#edf1f7" if dark else "#1d2633"
    for object_name, icon_name in (
        ("backButton", "prev"), ("forwardButton", "next"),
        ("toParentButton", "up"), ("newFolderButton", "new_folder"),
        ("listModeButton", "list"), ("detailModeButton", "details"),
    ):
        button = dialog.findChild(QToolButton, object_name)
        if button is not None:
            button.setIcon(icon(icon_name, color))


def apply_theme(app: QApplication, dark: bool) -> None:
    background = "#171b22" if dark else "#f3f5f8"
    surface = "#222832" if dark else "#ffffff"
    text = "#edf1f7" if dark else "#1d2633"
    border = "#414a59" if dark else "#cbd3de"
    hover = "#303d4b" if dark else "#e8eef5"
    palette = app.palette()
    for role, color in (
        (QPalette.ColorRole.Window, background),
        (QPalette.ColorRole.WindowText, text),
        (QPalette.ColorRole.Base, surface),
        (QPalette.ColorRole.AlternateBase, hover),
        (QPalette.ColorRole.Text, text),
        (QPalette.ColorRole.Button, surface),
        (QPalette.ColorRole.ButtonText, text),
        (QPalette.ColorRole.ToolTipBase, surface),
        (QPalette.ColorRole.ToolTipText, text),
        (QPalette.ColorRole.Highlight, "#2d77bf"),
        (QPalette.ColorRole.HighlightedText, "#ffffff"),
    ):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(f"""
        QMainWindow, QScrollArea, QStatusBar {{ background: {background}; color: {text}; }}
        QDialog {{ background: {background}; color: {text}; }}
        QDialog QPushButton {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 2px; padding: 5px 10px; }}
        QDialog QPushButton:hover {{ background: {hover}; }}
        QDialog QAbstractItemView {{ background: {surface}; color: {text}; selection-background-color: #2d77bf; selection-color: #ffffff; }}
        QDialog QHeaderView::section {{ background: {hover}; color: {text}; border: 1px solid {border}; padding: 4px; }}
        QDialog#metadataDialog, QScrollArea#metadataScroll, QWidget#metadataContent {{ background: {background}; color: {text}; }}
        QDialog#metadataDialog QGroupBox {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 4px; margin-top: 16px; padding: 10px 8px 8px; }}
        QDialog#metadataDialog QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; background: {surface}; color: {text}; }}
        QWidget {{ color: {text}; font-family: 'Segoe UI'; font-size: 10pt; }}
        QMenuBar, QMenu, QToolBar, QFrame#bottomBar {{ background: {surface}; color: {text}; }}
        QTabWidget {{ background: {background}; }}
        QTabWidget::pane {{ background: {surface}; border: 1px solid {border}; }}
        QTabBar {{ background: {background}; qproperty-drawBase: 0; }}
        QTabBar::tab {{ background: {surface}; color: {text}; border: 1px solid {border}; border-bottom: none; padding: 6px 10px; }}
        QTabBar::tab:selected {{ background: {hover}; color: {text}; }}
        QTabBar::tab:hover:!selected {{ background: {hover}; }}
        QTabBar QToolButton#newTabButton {{ color: {text}; background: {surface}; border: 1px solid {border}; border-radius: 2px; padding: 0; font-size: 15pt; }}
        QTabBar QToolButton#newTabButton:hover {{ background: {hover}; }}
        QTabBar QToolButton#tabCloseButton {{ color: {text}; background: transparent; border: 0; border-radius: 2px; padding: 0; font-size: 11pt; }}
        QTabBar QToolButton#tabCloseButton:hover {{ background: {hover}; }}
        QMenuBar::item:selected, QMenu::item:selected, QToolButton:hover, QPushButton:hover {{ background: {hover}; }}
        QLineEdit, QComboBox, QSpinBox {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 5px; padding: 4px 6px; }}
        QToolButton, QPushButton {{ background: transparent; border: 1px solid transparent; border-radius: 5px; padding: 4px; }}
        QToolBar QToolButton#toolbarControl, QToolBar QToolButton#redactButton {{ background: {surface}; border: 1px solid {border}; border-radius: 2px; padding: 4px; }}
        QToolBar QToolButton#toolbarControl:hover, QToolBar QToolButton#redactButton:hover {{ background: {hover}; }}
        QToolButton:checked, QPushButton:checked {{ background: #2d77bf; color: white; }}
        QToolBar QToolButton#redactButton:checked {{ background: #2d77bf; color: white; }}
        QMenu {{ border: 1px solid {border}; padding: 4px; }}
        QMenu::item {{ padding: 5px 20px; }}
        QSlider::groove:horizontal {{ height: 4px; background: {border}; border-radius: 2px; }}
        QSlider::handle:horizontal {{ width: 14px; margin: -6px 0; background: #2d77bf; border-radius: 7px; }}
        QScrollBar:vertical {{ background: {background}; width: 12px; margin: 0; }}
        QScrollBar:horizontal {{ background: {background}; height: 12px; margin: 0; }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: {border}; border-radius: 5px; min-width: 24px; min-height: 24px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """)


def system_dark(app: QApplication) -> bool:
    return app.styleHints().colorScheme() == Qt.ColorScheme.Dark


def resolve_dark(app: QApplication, preference: str) -> bool:
    """Resolve an appearance preference to the palette's dark-mode flag."""
    if preference == "dark":
        return True
    if preference == "light":
        return False
    return system_dark(app)
