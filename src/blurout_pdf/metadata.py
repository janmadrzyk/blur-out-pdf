"""Helpers for editing the text values stored in a PDF's XMP metadata."""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import re
import xml.etree.ElementTree as ET


METADATA_FIELDS = (
    "title", "author", "subject", "keywords", "creator", "producer",
    "creationDate", "modDate", "trapped",
)


@dataclass(frozen=True)
class XmpValue:
    locator: tuple[tuple[int, ...], str | None]
    label: str
    value: str


def _parse_xmp(xml: str) -> ET.Element:
    for _, (prefix, uri) in ET.iterparse(StringIO(xml), events=("start-ns",)):
        if prefix in {"xml", "xmlns"} or re.fullmatch(r"ns\d+", prefix or ""):
            continue
        ET.register_namespace(prefix or "", uri)
    return ET.fromstring(xml)


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def extract_xmp_values(xml: str) -> list[XmpValue]:
    """Return editable element-text and attribute values with stable locators."""
    if not xml.strip():
        return []
    root = _parse_xmp(xml)
    values: list[XmpValue] = []

    def visit(element: ET.Element, path: tuple[int, ...], names: tuple[str, ...]) -> None:
        if element.text and element.text.strip():
            values.append(XmpValue((path, None), " / ".join(names), element.text.strip()))
        for key, value in element.attrib.items():
            if value.strip():
                label = " / ".join((*names, f"@{_local_name(key)}"))
                values.append(XmpValue((path, key), label, value.strip()))
        for index, child in enumerate(list(element)):
            if isinstance(child.tag, str):
                visit(child, (*path, index), (*names, _local_name(child.tag)))

    visit(root, (), (_local_name(root.tag),))
    return values


def update_xmp_values(xml: str, values: list[XmpValue]) -> str:
    """Update values in parsed XMP while retaining its XML structure."""
    root = _parse_xmp(xml)
    for item in values:
        path, attribute = item.locator
        element = root
        for index in path:
            element = list(element)[index]
        if attribute is None:
            original = element.text or ""
            leading = original[:len(original) - len(original.lstrip())]
            trailing = original[len(original.rstrip()):]
            element.text = f"{leading}{item.value}{trailing}"
        else:
            original = element.attrib.get(attribute, "")
            leading = original[:len(original) - len(original.lstrip())]
            trailing = original[len(original.rstrip()):]
            element.set(attribute, f"{leading}{item.value}{trailing}")
    return ET.tostring(root, encoding="unicode")
