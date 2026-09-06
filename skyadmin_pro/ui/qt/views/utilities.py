"""Qt Utilities port: translator plus read-only snippet list with copy.

Translator directions come from ``services.translate`` and translation
runs off the GUI thread via the async bridge. Snippets render from
``services.snippets`` with saved overrides applied; the copy button uses
the Qt clipboard.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def _snippet_items(db) -> list[dict]:
    from skyadmin_pro.services.snippets import SNIPPET_SECTIONS, apply_snippet_overrides, load_snippet_overrides

    try:
        overrides = load_snippet_overrides(db.get_setting)
    except Exception:
        overrides = {}
    items: list[dict] = []
    for section in ("client", "supplier", "service", "checklist"):
        try:
            snippets = apply_snippet_overrides(section, (overrides or {}).get(section) or {})
        except Exception:
            snippets = SNIPPET_SECTIONS.get(section, ())
        for snippet in snippets:
            items.append(
                {
                    "section": section,
                    "label": snippet.label,
                    "text": snippet.text,
                }
            )
    return items


def build_page(db, paths=None):
    from PySide6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QPushButton,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    from skyadmin_pro.services.translate import DEFAULT_DIRECTION, TRANSLATE_DIRECTIONS
    from skyadmin_pro.ui.qt import async_bridge, theme_bridge

    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(
        theme_bridge.tokens.CONTENT_PAD,
        theme_bridge.tokens.CONTENT_PAD,
        theme_bridge.tokens.CONTENT_PAD,
        theme_bridge.tokens.CONTENT_PAD,
    )

    title = QLabel("Utilities")
    title.setObjectName("qt-shell-title")
    outer.addWidget(title)

    tabs = QTabWidget()
    outer.addWidget(tabs, 1)
    page._tabs = tabs

    # Translator tab.
    translator_tab = QWidget()
    translator_layout = QVBoxLayout(translator_tab)
    direction = QComboBox()
    direction.setObjectName("translator_direction")
    direction.addItems([item[0] for item in TRANSLATE_DIRECTIONS])
    try:
        direction.setCurrentText(DEFAULT_DIRECTION)
    except Exception:
        pass
    translator_layout.addWidget(direction)
    source = QTextEdit()
    source.setObjectName("translator_source")
    source.setPlaceholderText("Paste text to translate…")
    translator_layout.addWidget(source, 1)
    translator_buttons = QHBoxLayout()
    translate_btn = QPushButton("Translate")
    translate_btn.setObjectName("translator_translate")
    copy_btn = QPushButton("Copy result")
    copy_btn.setObjectName("translator_copy")
    translator_buttons.addWidget(translate_btn)
    translator_buttons.addWidget(copy_btn)
    translator_buttons.addStretch(1)
    translator_layout.addLayout(translator_buttons)
    output = QTextEdit()
    output.setObjectName("translator_output")
    output.setReadOnly(True)
    output.setPlaceholderText("Translation appears here.")
    translator_layout.addWidget(output, 1)
    translator_status = QLabel("")
    translator_status.setObjectName("translator_status")
    translator_status.setWordWrap(True)
    translator_layout.addWidget(translator_status)
    tabs.addTab(translator_tab, "Translator")
    page._translator_source = source
    page._translator_direction = direction
    page._translator_translate = translate_btn
    page._translator_copy = copy_btn
    page._translator_output = output
    page._translator_status = translator_status

    def _translate() -> None:
        text = source.toPlainText().strip()
        if not text:
            translator_status.setText("Paste text first.")
            return
        label = direction.currentText()
        translate_btn.setEnabled(False)
        translator_status.setText("Translating…")

        def work():
            from skyadmin_pro.services import translate as translate_svc

            src, target = translate_svc.direction_codes(label)
            return translate_svc.translate_text(text, src, target)

        def on_success(result) -> None:
            output.setPlainText(str(result or "").strip())
            translator_status.setText("Translated.")

        def on_error(message: str) -> None:
            translator_status.setText(str(message))
            log.warning("Qt translator failed: %s", message)

        def _done() -> None:
            translate_btn.setEnabled(True)

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error, finally_fn=_done)

    def _copy_output() -> None:
        from PySide6.QtWidgets import QApplication

        text = output.toPlainText().strip()
        if not text:
            translator_status.setText("Nothing to copy yet.")
            return
        try:
            clipboard = QApplication.clipboard()
            if clipboard is None:
                raise RuntimeError("Clipboard unavailable.")
            clipboard.setText(text)
        except Exception as exc:
            translator_status.setText(str(exc))
            return
        translator_status.setText("Copied to the clipboard.")

    translate_btn.clicked.connect(_translate)
    copy_btn.clicked.connect(_copy_output)

    # Snippets tab.
    snippets_tab = QWidget()
    snippets_layout = QVBoxLayout(snippets_tab)
    snippet_list = QListWidget()
    snippet_list.setObjectName("snippet_list")
    snippet_list.setEditTriggers(snippet_list.EditTrigger.NoEditTriggers)
    snippets_layout.addWidget(snippet_list, 1)
    snippet_buttons = QHBoxLayout()
    snippet_copy = QPushButton("Copy snippet")
    snippet_copy.setObjectName("snippet_copy")
    snippet_buttons.addWidget(snippet_copy)
    snippet_buttons.addStretch(1)
    snippets_layout.addLayout(snippet_buttons)
    snippet_status = QLabel("")
    snippet_status.setObjectName("snippet_status")
    snippet_status.setWordWrap(True)
    snippets_layout.addWidget(snippet_status)
    tabs.addTab(snippets_tab, "Snippets")
    page._snippet_list = snippet_list
    page._snippet_copy = snippet_copy
    page._snippet_status = snippet_status
    page._snippet_items: list[dict] = []

    def load_snippets() -> None:
        def work():
            return _snippet_items(db)

        def on_success(items) -> None:
            try:
                page._snippet_items = list(items)
                snippet_list.clear()
                for item in page._snippet_items:
                    snippet_list.addItem(f"[{item['section']}] {item['label']}")
                snippet_status.setText(f"{len(page._snippet_items)} message(s).")
            except Exception:
                log.exception("Qt snippets render failed")

        def on_error(message: str) -> None:
            snippet_status.setText(str(message))
            log.warning("Qt snippets load failed: %s", message)

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error)

    def _copy_snippet() -> None:
        from PySide6.QtWidgets import QApplication

        row = snippet_list.currentRow()
        if row < 0 or row >= len(page._snippet_items):
            snippet_status.setText("Select a message first.")
            return
        text = page._snippet_items[row].get("text") or ""
        if not text.strip():
            snippet_status.setText("Select a message first.")
            return
        try:
            clipboard = QApplication.clipboard()
            if clipboard is None:
                raise RuntimeError("Clipboard unavailable.")
            clipboard.setText(text)
        except Exception as exc:
            snippet_status.setText(str(exc))
            return
        snippet_status.setText(f"Copied: {page._snippet_items[row].get('label') or ''}")

    snippet_copy.clicked.connect(_copy_snippet)

    def refresh() -> None:
        load_snippets()

    page.refresh = refresh  # type: ignore[attr-defined]
    load_snippets()
    page.setProperty("qt_view_id", "utilities")
    return page
