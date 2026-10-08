"""Modal editor for standard PDF metadata and XMP text values."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable
import unicodedata
import xml.etree.ElementTree as ET

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMenu, QMessageBox, QPushButton, QScrollArea, QToolButton,
    QVBoxLayout, QWidget,
)

from .metadata import METADATA_FIELDS, XmpValue, extract_xmp_values, update_xmp_values
from .appearance import icon
from .search import normalized


class MetadataEditorDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        translate: Callable[..., str],
        metadata: dict[str, str],
        technical_metadata: dict[str, str],
        xmp_xml: str,
    ) -> None:
        super().__init__(parent)
        self.t = translate
        self.setWindowTitle(self.t("edit_metadata"))
        self.resize(760, 720)
        self._original_xmp = xmp_xml
        self._clear_all = False
        self._updating_fields = False
        self._matches: list[tuple[QLineEdit, int, int]] = []
        self._match_index = -1
        self.standard_editors: dict[str, QLineEdit] = {}
        self.xmp_editors: list[tuple[XmpValue, QLineEdit]] = []
        self.xmp_values: list[XmpValue] = []
        self.xmp_error = ""

        root = QVBoxLayout(self)
        root.addWidget(QLabel(self.t("metadata_help")))

        search_row = QHBoxLayout()
        self.find_field = QLineEdit()
        self.find_field.setPlaceholderText(self.t("metadata_find"))
        self.find_field.textChanged.connect(self._refresh_matches)
        search_row.addWidget(self.find_field, 1)
        self.previous_button = QPushButton("‹")
        self.previous_button.setToolTip(self.t("previous_match"))
        self.previous_button.clicked.connect(lambda _checked=False: self._step_match(-1))
        search_row.addWidget(self.previous_button)
        self.next_button = QPushButton("›")
        self.next_button.setToolTip(self.t("next_match"))
        self.next_button.clicked.connect(lambda _checked=False: self._step_match(1))
        search_row.addWidget(self.next_button)
        self.search_options = QToolButton()
        self.search_options.setIcon(
            icon("options", "#e7edf6" if getattr(parent, "dark", False) else "#293241"),
        )
        self.search_options.setIconSize(QSize(20, 20))
        self.search_options.setArrowType(Qt.ArrowType.NoArrow)
        self.search_options.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0px; }")
        self.search_options.setToolTip(self.t("search_options"))
        self.search_options.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.search_menu = QMenu(self)
        self.case_action = self.search_menu.addAction(self.t("case"))
        self.whole_action = self.search_menu.addAction(self.t("whole"))
        self.diacritics_action = self.search_menu.addAction(self.t("diacritics"))
        for action in (self.case_action, self.whole_action, self.diacritics_action):
            action.setCheckable(True)
            action.triggered.connect(self._refresh_matches)
        self.search_options.setMenu(self.search_menu)
        search_row.addWidget(self.search_options)
        root.addLayout(search_row)

        replace_row = QHBoxLayout()
        self.replace_field = QLineEdit()
        self.replace_field.setPlaceholderText(self.t("replace_with"))
        replace_row.addWidget(self.replace_field, 1)
        self.replace_all_button = QPushButton(self.t("replace_all"))
        self.replace_all_button.clicked.connect(self._replace_all)
        replace_row.addWidget(self.replace_all_button)
        root.addLayout(replace_row)
        self.match_status = QLabel("")
        self.match_status.setAccessibleName(self.t("metadata_search_results"))
        root.addWidget(self.match_status)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        standard_box = QGroupBox(self.t("standard_metadata"))
        standard_form = QFormLayout(standard_box)
        for key in METADATA_FIELDS:
            editor = QLineEdit(metadata.get(key, ""))
            editor.textChanged.connect(self._field_changed)
            self.standard_editors[key] = editor
            standard_form.addRow(self.t(f"metadata_{key}"), editor)
        content_layout.addWidget(standard_box)

        if technical_metadata:
            technical_box = QGroupBox(self.t("technical_metadata"))
            technical_form = QFormLayout(technical_box)
            for key, value in technical_metadata.items():
                technical_form.addRow(self.t(f"metadata_{key}"), QLabel(value))
            content_layout.addWidget(technical_box)

        self.xmp_box = QGroupBox(self.t("xmp_metadata"))
        self.xmp_form = QFormLayout(self.xmp_box)
        self.xmp_placeholder = QLabel("")
        try:
            self.xmp_values = extract_xmp_values(xmp_xml)
        except (ET.ParseError, ValueError) as error:
            self.xmp_error = str(error)
            warning = QLabel(self.t("xmp_parse_error"))
            warning.setWordWrap(True)
            self.xmp_form.addRow(warning)
        for value in self.xmp_values:
            editor = QLineEdit(value.value)
            editor.textChanged.connect(self._field_changed)
            self.xmp_editors.append((value, editor))
            self.xmp_form.addRow(value.label, editor)
        if not self.xmp_values and not self.xmp_error:
            self.xmp_placeholder.setText(self.t("no_xmp_metadata"))
            self.xmp_form.addRow(self.xmp_placeholder)
        content_layout.addWidget(self.xmp_box)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        bottom = QHBoxLayout()
        self.clear_button = QPushButton(self.t("clear_metadata"))
        self.clear_button.clicked.connect(self._clear_metadata)
        bottom.addWidget(self.clear_button)
        bottom.addStretch(1)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Apply).setText(self.t("apply"))
        self.buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._accept_changes)
        self.buttons.rejected.connect(self.reject)
        bottom.addWidget(self.buttons)
        root.addLayout(bottom)

        self._all_editors = list(self.standard_editors.values()) + [editor for _, editor in self.xmp_editors]
        self._refresh_matches()

    @property
    def standard_values(self) -> dict[str, str]:
        return {key: editor.text() for key, editor in self.standard_editors.items()}

    @property
    def updated_xmp_xml(self) -> str | None:
        current = [replace(value, value=editor.text()) for value, editor in self.xmp_editors]
        if self._clear_all:
            if not any(value.value for value in current):
                return ""
            if self.xmp_error:
                return ""
            try:
                return update_xmp_values(self._original_xmp, current)
            except (ET.ParseError, ValueError, IndexError):
                return ""
        if not any(editor.text() != original.value for original, editor in self.xmp_editors):
            return None
        try:
            return update_xmp_values(self._original_xmp, current)
        except (ET.ParseError, ValueError, IndexError):
            return None

    @property
    def clear_all_requested(self) -> bool:
        return self._clear_all

    def _normalized_spans(self, text: str, query: str) -> list[tuple[int, int]]:
        match_case = self.case_action.isChecked()
        ignore_diacritics = self.diacritics_action.isChecked()
        needle = normalized(query.strip(), match_case, ignore_diacritics)
        if not needle:
            return []
        mapped: list[int] = []
        normalized_chars: list[str] = []
        for index, char in enumerate(text):
            part = normalized(char, match_case, ignore_diacritics)
            normalized_chars.append(part)
            mapped.extend([index] * len(part))
        haystack = "".join(normalized_chars)
        spans: list[tuple[int, int]] = []
        offset = 0
        while (start := haystack.find(needle, offset)) >= 0:
            end = start + len(needle)
            left_ok = start == 0 or not haystack[start - 1].isalnum()
            right_ok = end == len(haystack) or not haystack[end].isalnum()
            if not self.whole_action.isChecked() or (left_ok and right_ok):
                original_start, original_end = mapped[start], mapped[end - 1] + 1
                while original_start > 0 and unicodedata.combining(text[original_start - 1]):
                    original_start -= 1
                while original_end < len(text) and unicodedata.combining(text[original_end]):
                    original_end += 1
                if spans and original_start < spans[-1][1]:
                    spans[-1] = (spans[-1][0], max(spans[-1][1], original_end))
                else:
                    spans.append((original_start, original_end))
            offset = start + max(1, len(needle))
        return spans

    def _refresh_matches(self, *_args) -> None:
        if not hasattr(self, "_all_editors"):
            return
        self._matches = []
        query = self.find_field.text()
        if query.strip():
            for editor in self._all_editors:
                self._matches.extend((editor, start, end) for start, end in self._normalized_spans(editor.text(), query))
        self._match_index = -1
        count = len(self._matches)
        self.match_status.setText(self.t("metadata_matches", count=count) if query.strip() else "")
        self.previous_button.setEnabled(count > 0)
        self.next_button.setEnabled(count > 0)
        self.replace_all_button.setEnabled(count > 0)

    def _step_match(self, direction: int) -> None:
        if not self._matches:
            return
        self._match_index = (self._match_index + direction) % len(self._matches)
        editor, start, end = self._matches[self._match_index]
        editor.setFocus()
        editor.setSelection(start, end - start)
        self.match_status.setText(self.t("metadata_match_position", current=self._match_index + 1,
                                         total=len(self._matches)))

    def _field_changed(self, *_args) -> None:
        if not self._updating_fields:
            self._refresh_matches()

    def _replace_all(self, *_args) -> None:
        query = self.find_field.text()
        if not query.strip():
            return
        self._updating_fields = True
        replaced = 0
        for editor in self._all_editors:
            text = editor.text()
            spans = self._normalized_spans(text, query)
            if not spans:
                continue
            chunks: list[str] = []
            cursor = 0
            for start, end in spans:
                chunks.extend((text[cursor:start], self.replace_field.text()))
                cursor = end
            chunks.append(text[cursor:])
            editor.setText("".join(chunks))
            replaced += len(spans)
        self._updating_fields = False
        self._refresh_matches()
        self.match_status.setText(self.t("metadata_replaced", count=replaced))

    def _clear_metadata(self, *_args) -> None:
        self._clear_all = True
        self._updating_fields = True
        for editor in self._all_editors:
            editor.clear()
        self._updating_fields = False
        self._refresh_matches()
        self.match_status.setText(self.t("metadata_cleared"))

    def _accept_changes(self, *_args) -> None:
        if self.xmp_error and any(editor.text() for _, editor in self.xmp_editors):
            QMessageBox.warning(self, self.t("error"), self.t("xmp_parse_error"))
            return
        self.accept()
