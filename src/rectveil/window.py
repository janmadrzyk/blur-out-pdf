"""Main desktop window."""

from __future__ import annotations

from pathlib import Path

import pymupdf
from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QSlider,
    QToolBar, QToolButton, QWidget,
)

from .appearance import apply_theme, icon, system_dark
from .document import PdfDocument, STYLES
from .i18n import default_language, translate
from .search import find_matches
from .viewer import PdfViewer


class MainWindow(QMainWindow):
    def __init__(self, initial_path: str | None = None) -> None:
        super().__init__()
        self.settings = QSettings("Rectveil", "Rectveil")
        saved_language = self.settings.value("language", "auto")
        self.language = default_language() if saved_language == "auto" else str(saved_language)
        self.style_name = str(self.settings.value("redaction_style", "black"))
        if self.style_name not in STYLES:
            self.style_name = "black"
        self.dark = system_dark(QApplication.instance())
        self.document = PdfDocument()
        self.viewer = PdfViewer(self.document)
        self.setCentralWidget(self.viewer)
        self.viewer.redaction_drawn.connect(self._add_redaction)
        self.viewer.current_page_changed.connect(self._set_page_number)
        self.viewer.zoom_requested.connect(self._set_zoom)
        self.matches: list[tuple[int, pymupdf.Rect]] = []
        self.match_index = -1
        self._make_menu()
        self._make_toolbar()
        self._make_bottom_bar()
        self._translate_ui()
        self._apply_theme()
        QApplication.instance().styleHints().colorSchemeChanged.connect(self._on_color_scheme_changed)
        self._refresh_enabled()
        self.setMinimumSize(760, 520)
        self.resize(1180, 800)
        self.statusBar().showMessage(self.t("ready"))
        if initial_path:
            self.open_path(initial_path)

    def t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

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
        self.file_menu.addSeparator()
        self.exit_action = self.file_menu.addAction("")
        self.exit_action.triggered.connect(self.close)

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
        self.search_prev = self._button("prev", self.step_previous_match)
        self.search_next = self._button("next", lambda: self.step_match(1))
        row.addWidget(self.search_prev)
        row.addWidget(self.search_next)
        self.search_options = self._button("options")
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
        self.redact_action = self.edit_toolbar.addAction("")
        self.redact_action.setCheckable(True)
        self.redact_action.toggled.connect(self._toggle_redaction_mode)
        self.undo_action = self.edit_toolbar.addAction("")
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self._undo_redaction)
        self.edit_toolbar.addSeparator()
        self.left_action = self.edit_toolbar.addAction("")
        self.right_action = self.edit_toolbar.addAction("")
        self.left_action.triggered.connect(lambda: self._rotate(-90))
        self.right_action.triggered.connect(lambda: self._rotate(90))

    def _make_bottom_bar(self) -> None:
        self.bottom = QFrame()
        self.bottom.setObjectName("bottomBar")
        row = QHBoxLayout(self.bottom)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(2)
        row.addStretch(1)
        self.first_button = self._button("first", lambda: self.viewer.go_to_page(0))
        self.prev_button = self._button("prev", lambda: self.viewer.go_to_page(self.viewer.current_page - 1))
        self.next_button = self._button("next", lambda: self.viewer.go_to_page(self.viewer.current_page + 1))
        self.last_button = self._button("last", lambda: self.viewer.go_to_page(self.document.page_count - 1))
        self.page_field = QLineEdit()
        self.page_field.setFixedWidth(66)
        self.page_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_field.returnPressed.connect(self._jump_to_page)
        for widget in (self.first_button, self.prev_button, self.page_field, self.next_button, self.last_button):
            row.addWidget(widget)
        row.addStretch(1)
        self.single_button = self._button("single", lambda: self._set_layout("single"))
        self.continuous_button = self._button("continuous", lambda: self._set_layout("continuous"))
        for button in (self.single_button, self.continuous_button):
            button.setCheckable(True)
            row.addWidget(button)
        self.continuous_button.setChecked(True)
        row.addSpacing(12)
        self.zoom_list = QComboBox()
        self.zoom_list.setEditable(True)
        self.zoom_list.setFixedWidth(130)
        for value in ("50%", "75%", "100%", "125%", "150%", "200%", "300%"):
            self.zoom_list.addItem(value)
        self.zoom_list.addItem(self.t("original"))
        self.zoom_list.addItem(self.t("fit_page"))
        self.zoom_list.addItem(self.t("fit_width"))
        self.zoom_list.setCurrentText("125%")
        self.zoom_list.activated.connect(self._zoom_from_combo)
        self.zoom_list.lineEdit().returnPressed.connect(self._zoom_from_combo)
        row.addWidget(self.zoom_list)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(25, 300)
        self.zoom_slider.setValue(125)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.valueChanged.connect(lambda value: self._set_zoom(value / 100))
        row.addWidget(self.zoom_slider)
        self.statusBar().addPermanentWidget(self.bottom, 1)

    def _button(self, icon_name: str, callback=None) -> QToolButton:
        button = QToolButton(self)
        button.setIcon(icon(icon_name))
        if callback:
            button.clicked.connect(callback)
        return button

    def _apply_theme(self) -> None:
        apply_theme(QApplication.instance(), self.dark)
        color = "#e7edf6" if self.dark else "#293241"
        for button, name in ((self.search_prev, "prev"), (self.search_next, "next"),
                             (self.search_options, "options"), (self.search_clear, "close"), (self.first_button, "first"),
                             (self.prev_button, "prev"), (self.next_button, "next"),
                             (self.last_button, "last"), (self.single_button, "single"),
                             (self.continuous_button, "continuous")):
            button.setIcon(icon(name, color))
        for action, name in ((self.redact_action, "redact"), (self.undo_action, "undo"), (self.left_action, "left"),
                             (self.right_action, "right")):
            action.setIcon(icon(name, color))

    def _on_color_scheme_changed(self, scheme) -> None:
        self.dark = scheme == Qt.ColorScheme.Dark
        self._apply_theme()

    def _translate_ui(self) -> None:
        for target, key in ((self.file_menu, "file"), (self.open_action, "open"),
                            (self.save_action, "save"), (self.save_as_action, "save_as"),
                            (self.exit_action, "exit"), (self.settings_menu, "settings"),
                            (self.language_menu, "language"), (self.pl_action, "polish"),
                            (self.en_action, "english"), (self.style_menu, "style"),
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
        self.pl_action.setChecked(self.language == "pl")
        self.en_action.setChecked(self.language == "en")
        self.search_field.setPlaceholderText(self.t("find_placeholder"))
        for button, key in ((self.search_prev, "previous_match"), (self.search_next, "next_match"),
                            (self.search_options, "search_options"), (self.search_clear, "close_search"), (self.first_button, "first"),
                            (self.prev_button, "previous"), (self.next_button, "next"),
                            (self.last_button, "last"), (self.single_button, "single"),
                            (self.continuous_button, "continuous")):
            button.setToolTip(self.t(key))
        for index, key in ((7, "original"), (8, "fit_page"), (9, "fit_width")):
            self.zoom_list.setItemText(index, self.t(key))
        self.zoom_list.setToolTip(self.t("zoom"))
        self._set_page_number(self.viewer.current_page)
        self._update_title()

    def _refresh_enabled(self) -> None:
        has_document = self.document.is_open
        for control in (self.save_action, self.save_as_action, self.redact_action,
                        self.left_action, self.right_action, self.first_button,
                        self.prev_button, self.page_field, self.next_button, self.last_button,
                        self.single_button, self.continuous_button, self.zoom_list,
                        self.zoom_slider, self.search_field):
            control.setEnabled(has_document)
        self.undo_action.setEnabled(bool(self.document.redactions))
        self._set_page_number(self.viewer.current_page)

    def _update_title(self) -> None:
        name = self.document.path.name if self.document.path else "Rectveil"
        self.setWindowTitle(f"{'*' if self.document.dirty else ''}{name} — Rectveil")

    def set_language(self, language: str) -> None:
        self.language = language
        self.settings.setValue("language", language)
        self._translate_ui()

    def set_style(self, style: str) -> None:
        self.style_name = style
        self.settings.setValue("redaction_style", style)
        for name, action in self.style_actions.items():
            action.setChecked(name == style)

    def _toggle_redaction_mode(self, enabled: bool) -> None:
        self.viewer.redaction_mode = enabled
        for canvas in self.viewer.canvases:
            canvas.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)
        if enabled:
            self.statusBar().showMessage(self.t("drag_hint"))

    def _add_redaction(self, index: int, rect: pymupdf.Rect) -> None:
        self.document.add_redaction(index, rect, self.style_name)
        self.viewer.canvases[index].update()
        self.undo_action.setEnabled(bool(self.document.redactions))
        self._update_title()
        self.statusBar().showMessage(self.t("redaction_added"))

    def _undo_redaction(self) -> None:
        index = self.document.undo_last_redaction()
        if index is not None:
            self.viewer.canvases[index].update()
        self.undo_action.setEnabled(bool(self.document.redactions))
        self._update_title()

    def _rotate(self, degrees: int) -> None:
        if not self.document.is_open:
            return
        index = self.viewer.current_page
        self.document.rotate(index, degrees)
        self.viewer.refresh_page(index)
        self._update_title()

    def open_dialog(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, self.t("open_pdf"), "", self.t("pdf_filter"))
        if path:
            self.open_path(path)

    def open_path(self, path: str) -> None:
        try:
            opened = self.document.open(path)
            if not opened:
                password, accepted = QInputDialog.getText(self, self.t("password"), self.t("password_prompt"), QLineEdit.EchoMode.Password)
                if not accepted:
                    return
                self.document.open(path, password)
        except Exception as error:
            QMessageBox.critical(self, self.t("error"), self.t("open_error", error=error))
            return
        self.viewer.current_page = 0
        self.viewer.cache.clear()
        self.viewer.matches.clear()
        self.viewer.rebuild()
        self._toggle_redaction_mode(self.redact_action.isChecked())
        self.matches.clear()
        self._refresh_enabled()
        self._update_title()
        self.statusBar().showMessage(str(self.document.path))

    def save(self) -> bool:
        if self.document.path is None:
            return False
        return self._save_to(self.document.path)

    def save_as(self) -> bool:
        if not self.document.is_open:
            return False
        suggested = str(self.document.path.with_name(self.document.path.stem + "-redacted.pdf"))
        path, _ = QFileDialog.getSaveFileName(self, self.t("save_pdf"), suggested, self.t("pdf_filter"))
        if not path:
            return False
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        return self._save_to(path)

    def _save_to(self, path: str | Path) -> bool:
        try:
            self.document.save(path)
        except Exception as error:
            QMessageBox.critical(self, self.t("error"), self.t("save_error", error=error))
            return False
        self.viewer.cache.clear()
        self.viewer.rebuild()
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
        if self._confirm_discard():
            self.document.close()
            event.accept()
        else:
            event.ignore()

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

    def _set_zoom(self, scale: float) -> None:
        self.viewer.set_scale(scale)
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
        elif choice == self.t("original"):
            self._set_zoom(1.0)
        else:
            try:
                self._set_zoom(float(choice.replace("%", "").replace(",", ".")) / 100)
            except ValueError:
                self._set_zoom(self.viewer.scale)

    def _focus_search(self) -> None:
        self.search_field.setFocus()
        self.search_field.selectAll()

    def _update_search(self) -> None:
        if self.document.pdf is None:
            return
        self.matches = find_matches(self.document.pdf, self.search_field.text(),
                                    self.case_action.isChecked(), self.whole_action.isChecked(),
                                    self.diacritics_action.isChecked())
        self.viewer.matches = self.matches
        for canvas in self.viewer.canvases:
            canvas.update()
        self.match_index = -1
        if self.matches:
            self.step_match(1)
        elif self.search_field.text():
            self.statusBar().showMessage(self.t("no_results"))

    def step_previous_match(self) -> None:
        self.step_match(-1)

    def step_match(self, direction: int) -> None:
        if not self.matches:
            return
        self.match_index = (self.match_index + direction) % len(self.matches)
        index, rect = self.matches[self.match_index]
        self.viewer.show_match(index, rect)
        self.statusBar().showMessage(self.t("matches", current=self.match_index + 1, total=len(self.matches)))
