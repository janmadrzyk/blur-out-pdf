"""Create a reproducible README screenshot from a generated sample PDF."""

from pathlib import Path

import pymupdf
from PySide6.QtWidgets import QApplication

from blurout_pdf.window import MainWindow


def main() -> None:
    output = Path("docs/assets/ui-preview.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    sample = Path("build/preview.pdf")
    sample.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=595, height=842)
        page.draw_rect(pymupdf.Rect(0, 0, 595, 110), color=None, fill=(0.08, 0.16, 0.25))
        page.insert_text((42, 53), "CLIENT DOSSIER", fontsize=25, color=(1, 1, 1))
        page.insert_text((42, 83), "Prepared for sharing", fontsize=11, color=(0.77, 0.84, 0.9))
        page.insert_text((42, 160), "Reference ID: QZ-4819-73", fontsize=16)
        page.insert_text((42, 205), "Project: Northshore Office", fontsize=13)
        page.insert_text((42, 240), "Status: Draft", fontsize=13)
        page.draw_line((42, 265), (553, 265), color=(0.8, 0.84, 0.88))
        page.insert_text((42, 305), "Review notes", fontsize=16)
        page.insert_text((42, 342), "Only the selected area is removed from the saved PDF.", fontsize=11)
        page.insert_text((42, 365), "The remaining text stays readable and searchable.", fontsize=11)
        pdf.save(sample)

    app = QApplication([])
    window = MainWindow(str(sample))
    window.language = "pl"
    window._translate_ui()
    window._set_zoom(1.0)
    secret = window.document.page(0).search_for("QZ-4819-73")[0]
    window.document.add_redaction(0, window.document.page_to_display(0, secret), "black")
    window.redact_action.setChecked(True)
    window.viewer.canvases[0].update()
    window.resize(1180, 800)
    window.show()
    app.processEvents()
    window.grab().save(str(output))
    window.document.redactions.clear()
    window.close()


if __name__ == "__main__":
    main()
