"""Main desktop window."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite, sqrt
from pathlib import Path

import pymupdf
from PySide6.QtCore import QPoint, QSettings, QStandardPaths, QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QSlider,
    QTabBar, QTabWidget, QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from .appearance import apply_theme, icon, resolve_dark, theme_file_dialog
from .document import PdfDocument, STYLES
from .i18n import default_language, translate
from .metadata_dialog import MetadataEditorDialog
from .redaction_style_icon import redaction_style_icon
from .search import OCR_LANGUAGES, _tessdata_directory, find_matches, ocr_language_status, system_ocr_language
from .viewer import PdfViewer


@dataclass
class DocumentTab:
    document: PdfDocument
    viewer: PdfViewer
    matches: list[tuple[int, pymupdf.Rect]] = field(default_factory=list)
    match_index: int = -1
    search_text: str = ""
    search_pages: dict[int, list[dict]] = field(default_factory=dict)


class TabBarWithPlus(QTabBar):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.plus_button = QToolButton(self)
        self.plus_button.setObjectName("newTabButton")
        self.plus_button.setText("+")
        self.plus_button.setAutoRaise(True)
        self.plus_button.setFixedSize(25, 25)

    def _place_plus_button(self) -> None:
        if not hasattr(self, "plus_button"):
            return
        if self.count() == 0:
            self.plus_button.hide()
            return
        last = self.tabRect(self.count() - 1)
        x = last.right() + 4
        y = max(0, (self.height() - self.plus_button.height()) // 2)
        self.plus_button.move(x, y)
        self.plus_button.setVisible(x + self.plus_button.width() <= self.width())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place_plus_button()

    def tabLayoutChange(self) -> None:
        super().tabLayoutChange()
        self._place_plus_button()

    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        self._place_plus_button()

    def tabRemoved(self, index: int) -> None:
        super().tabRemoved(index)
        self._place_plus_button()


class MainWindow(QMainWindow):
    def __init__(self, initial_path: str | None = None) -> None:
        super().__init__()
        self.settings = QSettings("BlurOut PDF", "BlurOut PDF")
        previous_settings = QSettings("Rectveil", "Rectveil")
        for key in ("language", "redaction_style", "appearance", "last_open_directory", "last_save_directory"):
            if not self.settings.contains(key) and previous_settings.contains(key):
                self.settings.setValue(key, previous_settings.value(key))
        saved_language = self.settings.value("language", "auto")
        self.language = default_language() if saved_language == "auto" else str(saved_language)
        self.ocr_language = str(self.settings.value("ocr_language", "auto"))
        if self.ocr_language not in ("auto", *OCR_LANGUAGES):
            self.ocr_language = "auto"
        self.style_name = str(self.settings.value("redaction_style", "black"))
        if self.style_name not in STYLES:
            self.style_name = "black"
        self.appearance_name = str(self.settings.value("appearance", "system"))
        if self.appearance_name not in ("system", "light", "dark"):
            self.appearance_name = "system"
        self.dark = resolve_dark(QApplication.instance(), self.appearance_name)
        self._placeholder_document = PdfDocument()
        self._placeholder_viewer = PdfViewer(self._placeholder_document)
        self.document = self._placeholder_document
        self.viewer = self._placeholder_viewer
        self._document_tabs: dict[PdfViewer, DocumentTab] = {}
        self._active_tab: DocumentTab | None = None
        self.tabs = QTabWidget(self)
        self.tab_bar = TabBarWithPlus(self.tabs)
        self.tabs.setTabBar(self.tab_bar)
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.addTab(self._placeholder_viewer, self.t("no_document_tab"))
        self.tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.new_tab_button = self.tab_bar.plus_button
        self.new_tab_button.clicked.connect(self.open_dialog)
        self.main_content = QWidget(self)
        self.main_layout = QVBoxLayout(self.main_content)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(self.main_content)
        self._wire_viewer(self._placeholder_viewer)
        self.matches: list[tuple[int, pymupdf.Rect]] = []
        self.match_index = -1
        self._make_menu()
        self._make_toolbar()
        self._make_bottom_bar()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._translate_ui()
        self._apply_theme()
        QApplication.instance().styleHints().colorSchemeChanged.connect(self._on_color_scheme_changed)
        self._refresh_enabled()
        self._on_tab_changed(self.tabs.currentIndex())
        self.setMinimumSize(max(760, self.bottom.sizeHint().width()), 520)
        self.resize(1180, 800)
        self.statusBar().showMessage(self.t("ready"))
        if initial_path:
            self.open_path(initial_path)

    def t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _wire_viewer(self, viewer: PdfViewer) -> None:
        viewer.redaction_drawn.connect(self._add_redaction)
        viewer.redaction_edited.connect(self._redaction_edited)
        viewer.current_page_changed.connect(self._set_page_number)
        viewer.zoom_requested.connect(self._set_zoom)

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index) if index >= 0 else None
        context = self._document_tabs.get(widget) if widget is not None else None
        if context is None:
            self._active_tab = None
            self.document = self._placeholder_document
            self.viewer = self._placeholder_viewer
            self.matches = []
            self.match_index = -1
            self.search_field.blockSignals(True)
            self.search_field.clear()
            self.search_field.blockSignals(False)
            self.viewer.matches = []
        else:
            self._active_tab = context
            self.document = context.document
            self.viewer = context.viewer
            self.matches = context.matches
            self.match_index = context.match_index
            self.viewer.matches = context.matches
            self.search_field.blockSignals(True)
            self.search_field.setText(context.search_text)
            self.search_field.blockSignals(False)
            self._update_search(navigate=False)
        if context is None:
            self.search_count.clear()
            self.search_prev.setEnabled(False)
            self.search_next.setEnabled(False)
        self.viewer.redaction_mode = self.redact_action.isChecked()
        for canvas in self.viewer.canvases:
            canvas.setCursor(
                Qt.CursorShape.CrossCursor if self.viewer.redaction_mode else Qt.CursorShape.ArrowCursor,
            )
            canvas.update()
        self._set_page_number(self.viewer.current_page)
        self.single_button.setChecked(self.viewer.layout_mode == "single")
        self.continuous_button.setChecked(self.viewer.layout_mode == "continuous")
        percent = round(self.viewer.scale * 100)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(percent)
        self.zoom_slider.blockSignals(False)
        self.zoom_list.blockSignals(True)
        self.zoom_list.setCurrentText(f"{percent}%")
        self.zoom_list.blockSignals(False)
        self._refresh_enabled()
        self._update_title()
        self.statusBar().showMessage(
            str(self.document.path) if self.document.path else self.t("ready"),
        )

    def close_tab(self, index: int) -> None:
        widget = self.tabs.widget(index)
        context = self._document_tabs.get(widget)
        if context is None:
            return
        self.tabs.setCurrentIndex(index)
        if not self._confirm_discard():
            return
        self._document_tabs.pop(context.viewer, None)
        context.document.close()
        self.tabs.removeTab(index)
        context.viewer.deleteLater()
        if not self._document_tabs:
            placeholder_index = self.tabs.addTab(self._placeholder_viewer, self.t("no_document_tab"))
            self.tabs.tabBar().setTabButton(placeholder_index, QTabBar.ButtonPosition.RightSide, None)
            self.tabs.setCurrentIndex(placeholder_index)
        self._refresh_enabled()

    def _make_menu(self) -> None:
        bar = self.menuBar()
        self.file_menu = bar.addMenu("")
        self.open_action = self.file_menu.addAction("")
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_dialog)
        self.save_action = self.file_menu.addAction("")
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save)
        self.save_as_action = self.file_menu.addAction("")
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self.save_as)
        self.metadata_action = self.file_menu.addAction("")
        self.metadata_action.triggered.connect(self._edit_metadata)
        self.file_menu.addSeparator()
        self.exit_action = self.file_menu.addAction("")
        self.exit_action.triggered.connect(self.close)

        self.edit_menu = bar.addMenu("")
        self.undo_action = QAction("", self)
        self.edit_menu.addAction(self.undo_action)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self._undo_content)
        self.redo_action = QAction("", self)
        self.edit_menu.addAction(self.redo_action)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self._redo_content)

        self.settings_menu = bar.addMenu("")
        self.language_menu = self.settings_menu.addMenu("")
        language_group = QActionGroup(self)
        language_group.setExclusive(True)
        self.pl_action = self.language_menu.addAction("")
        self.en_action = self.language_menu.addAction("")
        for action in (self.pl_action, self.en_action):
            action.setCheckable(True)
            language_group.addAction(action)
        self.pl_action.triggered.connect(lambda: self.set_language("pl"))
        self.en_action.triggered.connect(lambda: self.set_language("en"))

        self.appearance_menu = self.settings_menu.addMenu("")
        appearance_group = QActionGroup(self)
        appearance_group.setExclusive(True)
        self.appearance_actions = {}
        for name in ("system", "light", "dark"):
            action = self.appearance_menu.addAction("")
            action.setCheckable(True)
            appearance_group.addAction(action)
            action.triggered.connect(lambda checked=False, value=name: self.set_appearance(value))
            self.appearance_actions[name] = action

        self.style_menu = self.settings_menu.addMenu("")
        style_group = QActionGroup(self)
        style_group.setExclusive(True)
        self.style_actions = {}
        for name in STYLES:
            action = self.style_menu.addAction("")
            action.setCheckable(True)
            style_group.addAction(action)
            action.triggered.connect(lambda checked=False, value=name: self.set_style(value))
            self.style_actions[name] = action

        self.ocr_menu = self.settings_menu.addMenu("")
        self.ocr_menu.aboutToShow.connect(self._refresh_ocr_menu)
        ocr_group = QActionGroup(self)
        ocr_group.setExclusive(True)
        self.ocr_actions = {}
        for name in ("auto", *OCR_LANGUAGES):
            action = self.ocr_menu.addAction("")
            action.setCheckable(True)
            ocr_group.addAction(action)
            action.triggered.connect(lambda checked=False, value=name: self.set_ocr_language(value))
            self.ocr_actions[name] = action
        self.settings_menu.addSeparator()
        self.toolbar_action = self.settings_menu.addAction("")
        self.toolbar_action.setCheckable(True)
        self.toolbar_action.setChecked(True)
        self.toolbar_action.triggered.connect(lambda checked: self.edit_toolbar.setVisible(checked))

        search = QWidget(bar)
        self.search_widget = search
        row = QHBoxLayout(search)
        row.setContentsMargins(4, 0, 5, 0)
        row.setSpacing(2)
        self.search_field = QLineEdit()
        self.search_field.setFixedWidth(210)
        self.search_field.returnPressed.connect(lambda: self.step_match(1))
        self.search_field.textChanged.connect(self._update_search)
        row.addWidget(self.search_field)
        self.search_count = QLabel("")
        self.search_count.setMinimumWidth(42)
        self.search_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.search_count)
        self.search_prev = self._button("prev", self.step_previous_match)
        self.search_next = self._button("next", lambda: self.step_match(1))
        row.addWidget(self.search_prev)
        row.addWidget(self.search_next)
        self.search_options = self._button("options")
        self.search_options.setIconSize(QSize(20, 20))
        self.search_options.setArrowType(Qt.ArrowType.NoArrow)
        self.search_options.setStyleSheet(
            "QToolButton::menu-indicator { image: none; width: 0px; }",
        )
        self.search_options.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.search_menu = QMenu(self)
        self.case_action = self.search_menu.addAction("")
        self.whole_action = self.search_menu.addAction("")
        self.diacritics_action = self.search_menu.addAction("")
        for action in (self.case_action, self.whole_action, self.diacritics_action):
            action.setCheckable(True)
            action.triggered.connect(self._update_search)
        self.search_options.setMenu(self.search_menu)
        row.addWidget(self.search_options)
        self.search_clear = self._button("close", self.search_field.clear)
        row.addWidget(self.search_clear)
        bar.setCornerWidget(search, Qt.Corner.TopRightCorner)
        find_action = QAction(self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self._focus_search)
        self.addAction(find_action)

    def _make_toolbar(self) -> None:
        self.edit_toolbar = QToolBar(self)
        self.edit_toolbar.setMovable(False)
        self.edit_toolbar.setIconSize(QSize(22, 22))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.edit_toolbar)
        self.redact_action = QAction("", self)
        self.redact_action.setCheckable(True)
        self.redact_action.toggled.connect(self._toggle_redaction_mode)
        self.redact_button = QToolButton(self.edit_toolbar)
        self.redact_button.setObjectName("redactButton")
        self.redact_button.setCheckable(True)
        self.redact_button.setAutoRaise(True)
        self.redact_button.setMinimumHeight(34)
        redact_row = QHBoxLayout(self.redact_button)
        redact_row.setContentsMargins(7, 2, 7, 2)
        redact_row.setSpacing(6)
        self.redact_label = QLabel(self.redact_button)
        self.redact_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        redact_row.addWidget(self.redact_label)
        self.redact_icon_label = QLabel(self.redact_button)
        self.redact_icon_label.setFixedSize(48, 26)
        self.redact_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.redact_icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        redact_row.addWidget(self.redact_icon_label)
        self.redact_button.toggled.connect(self.redact_action.setChecked)
        self.redact_action.toggled.connect(self.redact_button.setChecked)
        self.edit_toolbar.addWidget(self.redact_button)
        self.edit_toolbar.addAction(self.undo_action)
        self.edit_toolbar.addAction(self.redo_action)
        self.edit_toolbar.addSeparator()
        self.edit_toolbar.addAction(self.metadata_action)
        self.edit_toolbar.addSeparator()
        self.left_action = self.edit_toolbar.addAction("")
        self.right_action = self.edit_toolbar.addAction("")
        self.left_action.triggered.connect(lambda: self._rotate(-90))
        self.right_action.triggered.connect(lambda: self._rotate(90))
        for action in (self.undo_action, self.redo_action, self.metadata_action,
                       self.left_action, self.right_action):
            control = self.edit_toolbar.widgetForAction(action)
            if isinstance(control, QToolButton):
                control.setObjectName("toolbarControl")

    def _install_tab_close_button(self, index: int) -> None:
        close_button = QToolButton(self.tab_bar)
        close_button.setObjectName("tabCloseButton")
        close_button.setText("×")
        close_button.setAutoRaise(True)
        close_button.setFixedSize(18, 18)
        self.tab_bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, close_button)
        close_button.clicked.connect(lambda _checked=False, button=close_button: self._close_button_clicked(button))

    def _close_button_clicked(self, button: QToolButton) -> None:
        for index in range(self.tabs.count()):
            if self.tab_bar.tabButton(index, QTabBar.ButtonPosition.RightSide) is button:
                self.tabs.tabCloseRequested.emit(index)
                return

    def _make_bottom_bar(self) -> None:
        self.bottom = QFrame()
        self.bottom.setObjectName("bottomBar")
        row = QHBoxLayout(self.bottom)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(2)
        self.page_controls = QWidget(self.bottom)
        page_row = QHBoxLayout(self.page_controls)
        page_row.setContentsMargins(0, 0, 0, 0)
        page_row.setSpacing(2)
        self.first_button = self._button("first", lambda: self.viewer.go_to_page(0))
        self.prev_button = self._button("prev", lambda: self.viewer.go_to_page(self.viewer.current_page - 1))
        self.next_button = self._button("next", lambda: self.viewer.go_to_page(self.viewer.current_page + 1))
        self.last_button = self._button("last", lambda: self.viewer.go_to_page(self.document.page_count - 1))
        self.page_field = QLineEdit()
        self.page_field.setFixedWidth(66)
        self.page_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_field.returnPressed.connect(self._jump_to_page)
        for widget in (self.first_button, self.prev_button, self.page_field, self.next_button, self.last_button):
            page_row.addWidget(widget)

        self.zoom_controls = QWidget(self.bottom)
        zoom_row = QHBoxLayout(self.zoom_controls)
        zoom_row.setContentsMargins(0, 0, 0, 0)
        zoom_row.setSpacing(2)
        self.single_button = self._button("single", lambda: self._set_layout("single"))
        self.continuous_button = self._button("continuous", lambda: self._set_layout("continuous"))
        for button in (self.single_button, self.continuous_button):
            button.setCheckable(True)
            zoom_row.addWidget(button)
        self.continuous_button.setChecked(True)
        zoom_row.addSpacing(12)
        self.zoom_list = QComboBox()
        self.zoom_list.setEditable(True)
        self.zoom_list.setFixedWidth(130)
        for value in ("50%", "75%", "100%", "125%", "150%", "200%", "300%", "400%", "500%"):
            self.zoom_list.addItem(value)
        self.zoom_list.addItem(self.t("actual_size"))
        self.zoom_list.addItem(self.t("fit_page"))
        self.zoom_list.addItem(self.t("fit_width"))
        self.zoom_list.setCurrentText("125%")
        self.zoom_list.activated.connect(self._zoom_from_combo)
        self.zoom_list.lineEdit().returnPressed.connect(self._zoom_from_combo)
        zoom_row.addWidget(self.zoom_list)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(25, 500)
        self.zoom_slider.setValue(125)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.valueChanged.connect(lambda value: self._set_zoom(value / 100))
        zoom_row.addWidget(self.zoom_slider)

        self.left_balance = QWidget(self.bottom)
        self.left_balance.setFixedWidth(self.zoom_controls.sizeHint().width())
        row.addWidget(self.left_balance)
        row.addStretch(1)
        row.addWidget(self.page_controls)
        row.addStretch(1)
        row.addWidget(self.zoom_controls)
        self.main_layout.addWidget(self.bottom)

        self.ocr_notice = QLabel(self)
        self.statusBar().addPermanentWidget(self.ocr_notice)
        self._refresh_ocr_status()

    def _button(self, icon_name: str, callback=None) -> QToolButton:
        button = QToolButton(self)
        button.setIcon(icon(icon_name))
        if callback:
            button.clicked.connect(callback)
        return button

    def _apply_theme(self) -> None:
        apply_theme(QApplication.instance(), self.dark)
        self.left_balance.setFixedWidth(self.zoom_controls.sizeHint().width())
        self.setMinimumWidth(max(760, self.bottom.sizeHint().width()))
        color = "#e7edf6" if self.dark else "#293241"
        for button, name in ((self.search_prev, "prev"), (self.search_next, "next"),
                             (self.search_options, "options"), (self.search_clear, "close"), (self.first_button, "first"),
                             (self.prev_button, "prev"), (self.next_button, "next"),
                             (self.last_button, "last"), (self.single_button, "single"),
                             (self.continuous_button, "continuous")):
            button.setIcon(icon(name, color))
        for action, name in ((self.undo_action, "undo"), (self.redo_action, "redo"), (self.left_action, "left"),
                             (self.right_action, "right")):
            action.setIcon(icon(name, color))
        self.metadata_action.setIcon(icon("metadata", color))
        self._update_redact_presentation()

    def _update_redact_presentation(self) -> None:
        preview = redaction_style_icon(self.style_name, self.dark)
        self.redact_icon_label.setPixmap(preview.pixmap(QSize(44, 22)))
        color = "#ffffff" if self.redact_button.isChecked() else ("#edf1f7" if self.dark else "#1d2633")
        self.redact_label.setStyleSheet(f"color: {color};")
        self.redact_label.adjustSize()
        self.redact_button.layout().invalidate()
        self.redact_button.setFixedWidth(self.redact_button.layout().sizeHint().width())

    def _on_color_scheme_changed(self, scheme) -> None:
        if self.appearance_name == "system":
            self.dark = resolve_dark(QApplication.instance(), "system")
            self._apply_theme()

    def _translate_ui(self) -> None:
        for target, key in ((self.file_menu, "file"), (self.open_action, "open"),
                            (self.save_action, "save"), (self.save_as_action, "save_as"),
                            (self.metadata_action, "edit_metadata"),
                            (self.exit_action, "exit"), (self.edit_menu, "edit_menu"),
                            (self.undo_action, "undo"), (self.redo_action, "redo"),
                            (self.settings_menu, "settings"),
                            (self.language_menu, "language"), (self.pl_action, "polish"),
                            (self.en_action, "english"), (self.appearance_menu, "appearance"),
                            (self.style_menu, "style"), (self.ocr_menu, "ocr_language"),
                            (self.toolbar_action, "show_toolbar"), (self.case_action, "case"),
                            (self.whole_action, "whole"), (self.diacritics_action, "diacritics"),
                            (self.redact_action, "redact"), (self.undo_action, "undo_redaction"), (self.left_action, "rotate_left"),
                            (self.right_action, "rotate_right")):
            if isinstance(target, QMenu):
                target.setTitle(self.t(key))
            else:
                target.setText(self.t(key))
        for name, action in self.style_actions.items():
            action.setText(self.t(name))
            action.setChecked(self.style_name == name)
        for name, action in self.appearance_actions.items():
            action.setText(self.t(f"appearance_{name}"))
            action.setChecked(self.appearance_name == name)
        self._refresh_ocr_menu()
        self._refresh_ocr_status()
        self.redact_label.setText(self.t("redact"))
        self.redact_button.setAccessibleName(self.t("redact"))
        self.redact_button.setToolTip(self.t("redact"))
        self._update_redact_presentation()
        self.pl_action.setChecked(self.language == "pl")
        self.en_action.setChecked(self.language == "en")
        self.search_field.setPlaceholderText(self.t("find_placeholder"))
        self.new_tab_button.setToolTip(self.t("open_new_tab"))
        if self.tabs.indexOf(self._placeholder_viewer) >= 0:
            self.tabs.setTabText(self.tabs.indexOf(self._placeholder_viewer), self.t("no_document_tab"))
        for button, key in ((self.search_prev, "previous_match"), (self.search_next, "next_match"),
                            (self.search_options, "search_options"), (self.search_clear, "close_search"), (self.first_button, "first"),
                            (self.prev_button, "previous"), (self.next_button, "next"),
                            (self.last_button, "last"), (self.single_button, "single"),
                            (self.continuous_button, "continuous")):
            button.setToolTip(self.t(key))
        for index, key in ((9, "actual_size"), (10, "fit_page"), (11, "fit_width")):
            self.zoom_list.setItemText(index, self.t(key))
        self.zoom_list.setToolTip(self.t("zoom"))
        self._set_page_number(self.viewer.current_page)
        self._update_title()

    def _refresh_enabled(self) -> None:
        has_document = self.document.is_open
        for control in (self.save_action, self.save_as_action, self.metadata_action, self.redact_action,
                        self.redact_button, self.left_action, self.right_action, self.first_button,
                        self.prev_button, self.page_field, self.next_button, self.last_button,
                        self.single_button, self.continuous_button, self.zoom_list,
                        self.zoom_slider, self.search_field):
            control.setEnabled(has_document)
        self._refresh_history_actions()
        self._set_page_number(self.viewer.current_page)

    def _update_title(self) -> None:
        if self._active_tab is None or self.document.path is None:
            self.setWindowTitle("BlurOut PDF")
            return
        name = self.document.path.name
        prefix = "*" if self.document.dirty else ""
        index = self.tabs.indexOf(self.viewer)
        if index >= 0:
            self.tabs.setTabText(index, f"{prefix}{name}")
            self.tabs.setTabToolTip(index, str(self.document.path))
        self.setWindowTitle(f"{prefix}{name} — BlurOut PDF")

    def set_language(self, language: str) -> None:
        self.language = language
        self.settings.setValue("language", language)
        self._translate_ui()

    def _refresh_ocr_menu(self) -> None:
        tessdata = _tessdata_directory()
        system_name = OCR_LANGUAGES[system_ocr_language()]
        for name, action in self.ocr_actions.items():
            if name == "auto":
                action.setText(self.t("ocr_auto", model=system_name))
                action.setEnabled(True)
            else:
                available = tessdata is not None and (tessdata / f"{name}.traineddata").is_file()
                action.setText(OCR_LANGUAGES[name])
                action.setEnabled(available)
                action.setVisible(available or name == self.ocr_language)
            action.setChecked(name == self.ocr_language)

    def _refresh_ocr_status(self) -> None:
        _active, missing = ocr_language_status(self.ocr_language)
        if missing == "eng":
            message = self.t("ocr_unavailable")
        elif missing:
            message = self.t("ocr_fallback", model=OCR_LANGUAGES[missing])
        else:
            message = ""
        self.ocr_notice.setText(message)
        self.ocr_notice.setToolTip(message)
        self.ocr_notice.setVisible(bool(message))

    def set_ocr_language(self, language: str) -> None:
        if language not in ("auto", *OCR_LANGUAGES):
            raise ValueError(language)
        self.ocr_language = language
        self.settings.setValue("ocr_language", language)
        for context in self._document_tabs.values():
            context.search_pages.clear()
        self._refresh_ocr_menu()
        self._refresh_ocr_status()
        if self.document.is_open:
            self._update_search(navigate=False)

    def set_appearance(self, appearance: str) -> None:
        if appearance not in ("system", "light", "dark"):
            raise ValueError(appearance)
        self.appearance_name = appearance
        self.settings.setValue("appearance", appearance)
        for name, action in self.appearance_actions.items():
            action.setChecked(name == appearance)
        self.dark = resolve_dark(QApplication.instance(), appearance)
        self._apply_theme()

    def set_style(self, style: str) -> None:
        self.style_name = style
        self.settings.setValue("redaction_style", style)
        for name, action in self.style_actions.items():
            action.setChecked(name == style)
        self._update_redact_presentation()

    def _edit_metadata(self) -> None:
        if not self.document.is_open:
            return
        dialog = MetadataEditorDialog(
            self,
            self.t,
            self.document.metadata_values(),
            self.document.technical_metadata(),
            self.document.xml_metadata_text(),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.document.apply_metadata_edits(
            dialog.standard_values,
            dialog.updated_xmp_xml,
            dialog.clear_all_requested,
        )
        self._update_title()
        self.statusBar().showMessage(self.t("metadata_applied"))

    def _toggle_redaction_mode(self, enabled: bool) -> None:
        self.viewer.redaction_mode = enabled
        self._update_redact_presentation()
        for canvas in self.viewer.canvases:
            canvas.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)
        if enabled:
            self.statusBar().showMessage(self.t("drag_hint"))

    def _add_redaction(self, index: int, rect: pymupdf.Rect) -> None:
        try:
            self.document.add_redaction(index, rect, self.style_name)
        except Exception as error:
            QMessageBox.critical(self, self.t("error"), self.t("redaction_error", error=error))
            return
        self.viewer.canvases[index].update()
        self._update_search()
        self._refresh_history_actions()
        self._update_title()
        self.statusBar().showMessage(self.t("redaction_added"))

    def _redaction_edited(self, index: int) -> None:
        self.viewer.canvases[index].update()
        self._update_search()
        self._refresh_history_actions()
        self._update_title()
        self.statusBar().showMessage(self.t("redaction_updated"))

    def _refresh_history_actions(self) -> None:
        has_document = self.document.is_open
        self.undo_action.setEnabled(has_document and self.document.can_undo)
        self.redo_action.setEnabled(has_document and self.document.can_redo)

    def _undo_content(self, *_args) -> None:
        for index in self.document.undo():
            self.viewer.refresh_page(index)
        self._update_search()
        self._refresh_history_actions()
        self._update_title()

    def _redo_content(self, *_args) -> None:
        for index in self.document.redo():
            self.viewer.refresh_page(index)
        self._update_search()
        self._refresh_history_actions()
        self._update_title()

    def _rotate(self, degrees: int) -> None:
        if not self.document.is_open:
            return
        index = self.viewer.current_page
        self.document.rotate(index, degrees)
        self.viewer.refresh_page(index)
        self._refresh_history_actions()
        self._update_title()

    def _initial_directory(self, setting_key: str, fallback: str | Path | None = None) -> str:
        remembered_value = self.settings.value(setting_key, "", type=str)
        if remembered_value:
            remembered = Path(remembered_value)
            if remembered.is_dir():
                return str(remembered)

        if fallback is not None:
            candidate = Path(fallback)
            if candidate.is_file():
                candidate = candidate.parent
            if candidate.is_dir():
                return str(candidate)

        documents = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation))
        if documents.is_dir():
            return str(documents)
        return str(Path.home())

    def open_dialog(self) -> None:
        initial_directory = self._initial_directory("last_open_directory")
        dialog = QFileDialog(self, self.t("open_pdf"), initial_directory, self.t("pdf_filter"))
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        theme_file_dialog(dialog, self.dark)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        for path in dialog.selectedFiles():
            self.open_path(path)

    def open_path(self, path: str) -> None:
        resolved_path = Path(path).resolve()
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            context = self._document_tabs.get(widget)
            if context and context.document.path and context.document.path.resolve() == resolved_path:
                self.tabs.setCurrentIndex(index)
                return

        document = PdfDocument()
        try:
            opened = document.open(path)
            if not opened:
                password, accepted = QInputDialog.getText(self, self.t("password"), self.t("password_prompt"), QLineEdit.EchoMode.Password)
                if not accepted:
                    document.close()
                    return
                if not document.open(path, password):
                    raise ValueError(self.t("incorrect_password"))
        except Exception as error:
            document.close()
            QMessageBox.critical(self, self.t("error"), self.t("open_error", error=error))
            return
        self.settings.setValue("last_open_directory", str(Path(path).resolve().parent))
        viewer = PdfViewer(document)
        context = DocumentTab(document, viewer)
        self._wire_viewer(viewer)
        self._document_tabs[viewer] = context
        placeholder_index = self.tabs.indexOf(self._placeholder_viewer)
        if placeholder_index >= 0:
            self.tabs.removeTab(placeholder_index)
        index = self.tabs.addTab(viewer, document.path.name if document.path else resolved_path.name)
        self._install_tab_close_button(index)
        self.tabs.setTabToolTip(index, str(document.path or resolved_path))
        self.tabs.setCurrentIndex(index)
        self.statusBar().showMessage(str(document.path))

    def save(self) -> bool:
        if self.document.path is None:
            return False
        return self._save_to(self.document.path)

    def save_as(self) -> bool:
        if not self.document.is_open:
            return False
        initial_directory = self._initial_directory("last_save_directory", self.document.path.parent)
        suggested = str(Path(initial_directory) / f"{self.document.path.stem}-redacted.pdf")
        dialog = QFileDialog(self, self.t("save_pdf"), suggested, self.t("pdf_filter"))
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setDefaultSuffix("pdf")
        theme_file_dialog(dialog, self.dark)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        selected = dialog.selectedFiles()
        if not selected:
            return False
        path = selected[0]
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        return self._save_to(path)

    def _save_to(self, path: str | Path) -> bool:
        destination = Path(path).resolve()
        for context in self._document_tabs.values():
            if context is not self._active_tab and context.document.path:
                if context.document.path.resolve() == destination:
                    QMessageBox.critical(self, self.t("error"), self.t("save_target_open"))
                    return False
        try:
            self.document.save(destination)
        except Exception as error:
            QMessageBox.critical(self, self.t("error"), self.t("save_error", error=error))
            return False
        self.settings.setValue("last_save_directory", str(Path(path).resolve().parent))
        self.viewer.cache.clear()
        self.viewer.redaction_cache.clear()
        self.viewer.rebuild()
        if self._active_tab:
            self._active_tab.search_pages.clear()
        self._toggle_redaction_mode(self.redact_action.isChecked())
        self._update_search()
        self._refresh_enabled()
        self._update_title()
        self.statusBar().showMessage(self.t("saved", path=path))
        return True

    def _confirm_discard(self) -> bool:
        if not self.document.dirty:
            return True
        answer = QMessageBox.question(self, self.t("unsaved"), self.t("unsaved_prompt"),
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        for index in range(self.tabs.count()):
            context = self._document_tabs.get(self.tabs.widget(index))
            if context is None or not context.document.dirty:
                continue
            self.tabs.setCurrentIndex(index)
            if not self._confirm_discard():
                event.ignore()
                return
        for context in self._document_tabs.values():
            context.document.close()
        self._placeholder_document.close()
        event.accept()

    def _set_page_number(self, index: int) -> None:
        self.page_field.setText(self.t("page_of", current=index + 1 if self.document.is_open else 0,
                                      total=self.document.page_count))

    def _jump_to_page(self) -> None:
        try:
            number = int(self.page_field.text().split("/")[0])
            self.viewer.go_to_page(number - 1)
        except ValueError:
            self._set_page_number(self.viewer.current_page)

    def _set_layout(self, mode: str) -> None:
        self.viewer.set_layout_mode(mode)
        self.single_button.setChecked(mode == "single")
        self.continuous_button.setChecked(mode == "continuous")

    def _set_zoom(self, scale: float, anchor_global: QPoint | None = None) -> None:
        self.viewer.set_scale(scale, anchor_global)
        percent = round(self.viewer.scale * 100)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(percent)
        self.zoom_slider.blockSignals(False)
        self.zoom_list.blockSignals(True)
        self.zoom_list.setCurrentText(f"{percent}%")
        self.zoom_list.blockSignals(False)

    def _zoom_from_combo(self) -> None:
        choice = self.zoom_list.currentText().strip()
        if choice == self.t("fit_width"):
            page_width, _ = self.document.display_size(self.viewer.current_page)
            self._set_zoom((self.viewer.viewport().width() - 35) / page_width)
        elif choice == self.t("fit_page"):
            width, height = self.document.display_size(self.viewer.current_page)
            self._set_zoom(min((self.viewer.viewport().width() - 35) / width,
                               (self.viewer.viewport().height() - 35) / height))
        elif choice == self.t("actual_size"):
            self._set_zoom(self._actual_size_scale())
        else:
            try:
                self._set_zoom(float(choice.replace("%", "").replace(",", ".")) / 100)
            except ValueError:
                self._set_zoom(self.viewer.scale)

    def _actual_size_scale(self) -> float:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return 96 / 72

        physical_dpi = (float(screen.physicalDotsPerInchX()),
                        float(screen.physicalDotsPerInchY()))
        if all(isfinite(dpi) and 30 <= dpi <= 1000 for dpi in physical_dpi):
            dpi = sqrt(physical_dpi[0] * physical_dpi[1])
        else:
            logical_dpi = (float(screen.logicalDotsPerInchX()),
                           float(screen.logicalDotsPerInchY()))
            if all(isfinite(value) and 30 <= value <= 1000 for value in logical_dpi):
                dpi = sqrt(logical_dpi[0] * logical_dpi[1])
            else:
                dpi = 96
        return dpi / 72

    def _focus_search(self) -> None:
        self.search_field.setFocus()
        self.search_field.selectAll()

    def _update_search(self, *_args, navigate: bool = True) -> None:
        if self.document.pdf is None:
            return
        if self._active_tab:
            self._active_tab.search_text = self.search_field.text()
        previous_index = self.match_index
        hidden_areas: dict[int, list[pymupdf.Rect]] = {}
        for redaction in self.document.redactions:
            hidden_areas.setdefault(redaction.page_index, []).append(pymupdf.Rect(redaction.rect))
        self.matches = find_matches(self.document.pdf, self.search_field.text(),
                                    self.case_action.isChecked(), self.whole_action.isChecked(),
                                    self.diacritics_action.isChecked(), hidden_areas,
                                    self._active_tab.search_pages if self._active_tab else None,
                                    self.ocr_language)
        self.viewer.matches = self.matches
        if self._active_tab:
            self._active_tab.matches = self.matches
        for canvas in self.viewer.canvases:
            canvas.update()
        self.search_prev.setEnabled(bool(self.matches))
        self.search_next.setEnabled(bool(self.matches))
        if self.matches:
            if navigate:
                self.match_index = -1
                self.step_match(1)
            else:
                self.match_index = min(max(previous_index, 0), len(self.matches) - 1)
                if self._active_tab:
                    self._active_tab.match_index = self.match_index
                self.search_count.setText(f"{self.match_index + 1}/{len(self.matches)}")
        else:
            self.match_index = -1
            if self._active_tab:
                self._active_tab.match_index = -1
            self.search_count.setText("0/0" if self.search_field.text().strip() else "")
        if not self.matches and self.search_field.text().strip() and navigate:
            self.statusBar().showMessage(self.t("no_results"))
        elif not self.search_field.text().strip() and navigate:
            self.statusBar().showMessage(str(self.document.path) if self.document.path else self.t("ready"))

    def step_previous_match(self) -> None:
        self.step_match(-1)

    def step_match(self, direction: int) -> None:
        if not self.matches:
            return
        self.match_index = (self.match_index + direction) % len(self.matches)
        if self._active_tab:
            self._active_tab.match_index = self.match_index
        self.search_count.setText(f"{self.match_index + 1}/{len(self.matches)}")
        index, rect = self.matches[self.match_index]
        self.viewer.show_match(index, rect)
        self.statusBar().showMessage(self.t("matches", current=self.match_index + 1, total=len(self.matches)))
