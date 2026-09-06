"""Qt Document Hub port (Qt6 shell).

Mirrors the CustomTkinter hub (``ui/views/document_hub/view.py``): a
QTabWidget with the same six tools. The Qt port drops the 3-second
visible-only polling loop — each tab has a Refresh button that reloads
its file list on demand. Folder/file dialogs open only from button
clicks, never at build time. Run buttons execute the existing
``services.file_ops`` / ``services.workflow`` functions off the GUI
thread via ``run_background_q`` and report through a status label.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from skyadmin_pro.config import (
    DOCUMENT_TYPES,
    FINANCIAL_DOC_CATEGORIES,
    FOLDER_PORTAL_BACKUP,
    FOLDER_READY,
    FOLDER_STAGING,
    SETTING_PORTAL_URL,
)

log = logging.getLogger(__name__)

TAB_TITLES = ("Renamer", "Image to PDF", "Agent Bundle", "Portal", "Archive", "Financial")


def _file_rows(files: list[Path], folder_key: str = "folder") -> tuple[list[Path], list[dict]]:
    ordered = sorted(files, key=lambda item: item.name)
    rows = []
    for path in ordered:
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        entry = {"name": path.name, "size": str(size)}
        if folder_key:
            entry[folder_key] = path.parent.name
        rows.append(entry)
    return ordered, rows


def build_page(db, paths):
    """Build the Document Hub page widget (no polling; Refresh reloads)."""
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

    from skyadmin_pro.services import file_ops
    from skyadmin_pro.services.workflow import copy_to_clipboard, open_portal_and_copy_path
    from skyadmin_pro.ui.qt.async_bridge import run_background_q
    from skyadmin_pro.ui.qt.widgets import make_table, set_table_rows

    staging_dir = paths.staging if paths is not None else Path.cwd()
    ready_dir = paths.ready_to_upload if paths is not None else Path.cwd()
    archive_dir = paths.archive if paths is not None else Path.cwd()

    page = QWidget()
    outer = QVBoxLayout(page)
    title = QLabel("Document Hub")
    title.setObjectName("qt-shell-title")
    outer.addWidget(title)
    subtitle = QLabel("Rename, convert, merge, and archive client documents.")
    subtitle.setObjectName("qt-shell-subtitle")
    subtitle.setWordWrap(True)
    outer.addWidget(subtitle)

    tabs = QTabWidget()
    outer.addWidget(tabs, 1)
    hub: dict[str, QWidget] = {}

    def _set_status(tab: QWidget, message: str) -> None:
        tab._status.setText(str(message))

    def _selected_index(tab: QWidget) -> int | None:
        files = tab._files
        if not files:
            return None
        try:
            selected = tab._table.selectionModel().selectedRows()
            if selected:
                row = int(selected[0].row())
                if 0 <= row < len(files):
                    return row
        except Exception:
            pass
        return 0

    def _add_source_bar(tab: QWidget, layout: QVBoxLayout, initial: Path, on_browse: str) -> None:
        bar = QHBoxLayout()
        path_label = QLineEdit(str(initial))
        path_label.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        refresh_btn = QPushButton("Refresh")
        bar.addWidget(path_label, 1)
        bar.addWidget(browse_btn)
        bar.addWidget(refresh_btn)
        layout.addLayout(bar)
        tab._dir_label = path_label
        tab._browse_btn = browse_btn
        tab._refresh_btn = refresh_btn
        tab._browse_kind = on_browse

    def _wire_source_bar(tab: QWidget) -> None:
        from PySide6.QtWidgets import QFileDialog

        def _browse() -> None:
            start = tab._dir_label.text() or str(Path.cwd())
            if tab._browse_kind == "files":
                picked, _ = QFileDialog.getOpenFileNames(tab, "Select files", start)
                if picked:
                    tab.add_paths([Path(item) for item in picked])
                return
            picked = QFileDialog.getExistingDirectory(tab, "Select folder", start)
            if picked:
                tab._dir_label.setText(picked)
                tab.reload()

        tab._browse_btn.clicked.connect(_browse)
        tab._refresh_btn.clicked.connect(tab.reload)

    def _new_tab(title_text: str) -> tuple[QWidget, QVBoxLayout]:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        status = QLabel("")
        status.setWordWrap(True)
        status.setObjectName("qt-shell-subtitle")
        tab._status = status
        tab._files = []
        tabs.addTab(tab, title_text)
        hub[title_text] = tab
        return tab, layout

    def _finish_tab(tab: QWidget, layout: QVBoxLayout, run_label: str, run_fn) -> None:
        run_row = QHBoxLayout()
        run_btn = QPushButton(run_label)
        run_row.addWidget(run_btn)
        run_row.addStretch(1)
        layout.addLayout(run_row)
        layout.addWidget(tab._status)
        tab._run_btn = run_btn
        tab._run = run_fn
        run_btn.clicked.connect(run_fn)

    # -- Smart Renamer ----------------------------------------------------
    renamer, renamer_layout = _new_tab("Renamer")
    _add_source_bar(renamer, renamer_layout, staging_dir, "dir")
    renamer._table = make_table()
    renamer_layout.addWidget(renamer._table, 1)
    renamer_opts = QHBoxLayout()
    renamer_client = QLineEdit()
    renamer_client.setPlaceholderText("Client name")
    renamer_type = QComboBox()
    renamer_type.addItems(list(DOCUMENT_TYPES))
    renamer_opts.addWidget(QLabel("Client:"))
    renamer_opts.addWidget(renamer_client, 1)
    renamer_opts.addWidget(QLabel("Type:"))
    renamer_opts.addWidget(renamer_type)
    renamer_layout.addLayout(renamer_opts)
    renamer._client_edit = renamer_client
    renamer._type_combo = renamer_type

    def _renamer_reload() -> None:
        folder = Path(renamer._dir_label.text())
        files, _sig = file_ops.list_files_with_signature(folder)
        ordered, rows = _file_rows(files)
        renamer._files = ordered
        set_table_rows(renamer._table, (("name", "Name"), ("size", "Size")), rows)
        _set_status(renamer, f"{len(ordered)} file(s) in {folder.name}.")

    def _renamer_run() -> None:
        index = _selected_index(renamer)
        client = renamer._client_edit.text().strip()
        if index is None:
            _set_status(renamer, "No files to rename — pick a folder with files first.")
            return
        if not client:
            _set_status(renamer, "Enter a client name first.")
            return
        source = renamer._files[index]
        doc_type = renamer._type_combo.currentText()
        try:
            new_name = file_ops.build_smart_filename(
                client_name=client, document_type=doc_type, suffix=source.suffix or ".pdf"
            )
        except Exception as exc:
            _set_status(renamer, f"Could not build the new name: {exc}")
            return
        _set_status(renamer, f"Renaming {source.name}...")
        renamer._run_btn.setEnabled(False)

        def work():
            dest = file_ops.move_file(source, ready_dir, new_name)
            client_id = db.get_or_create_client(client)
            db.record_document(
                client_id=client_id,
                document_type=doc_type,
                file_name=dest.name,
                file_path=str(dest.resolve()),
            )
            return dest

        def on_success(dest) -> None:
            _renamer_reload()
            _set_status(renamer, f"Saved as {dest.name} in {FOLDER_READY}.")

        def on_error(message: str) -> None:
            _set_status(renamer, f"Rename failed: {message}")

        def finally_fn() -> None:
            renamer._run_btn.setEnabled(True)

        run_background_q(renamer, work=work, on_success=on_success, on_error=on_error, finally_fn=finally_fn)

    renamer.reload = _renamer_reload  # type: ignore[attr-defined]
    _wire_source_bar(renamer)
    _finish_tab(renamer, renamer_layout, f"Rename & move to {FOLDER_READY}", _renamer_run)
    _renamer_reload()

    # -- Image to PDF -----------------------------------------------------
    converter, converter_layout = _new_tab("Image to PDF")
    _add_source_bar(converter, converter_layout, staging_dir, "dir")
    converter._table = make_table()
    converter_layout.addWidget(converter._table, 1)
    converter_opts = QHBoxLayout()
    converter_combine = QCheckBox("Combine all images into one PDF")
    converter_opts.addWidget(converter_combine)
    converter_opts.addStretch(1)
    converter_layout.addLayout(converter_opts)
    converter._combine = converter_combine

    def _converter_reload() -> None:
        folder = Path(converter._dir_label.text())
        files, _sig = file_ops.list_files_with_signature(folder)
        images = [path for path in files if file_ops.is_image(path)]
        ordered, rows = _file_rows(images)
        converter._files = ordered
        set_table_rows(converter._table, (("name", "Name"), ("size", "Size")), rows)
        _set_status(converter, f"{len(ordered)} image(s) in {folder.name}.")

    def _converter_run() -> None:
        images = [path for path in converter._files if path.is_file()]
        if not images:
            _set_status(converter, "No images to convert — pick a folder with JPG/PNG files first.")
            return
        combine = bool(converter._combine.isChecked())
        _set_status(converter, f"Converting {len(images)} image(s)...")
        converter._run_btn.setEnabled(False)

        def work():
            return file_ops.images_to_pdf(images, staging_dir, combine=combine)

        def on_success(outputs) -> None:
            names = ", ".join(path.name for path in outputs)
            _converter_reload()
            _set_status(converter, f"Saved to {FOLDER_STAGING}: {names}.")

        def on_error(message: str) -> None:
            lowered = message.lower()
            if "pillow" in lowered or "pil" in lowered or "no module" in lowered:
                _set_status(converter, "Image conversion needs Pillow (pip install Pillow).")
            else:
                _set_status(converter, f"Conversion failed: {message}")

        def finally_fn() -> None:
            converter._run_btn.setEnabled(True)

        run_background_q(converter, work=work, on_success=on_success, on_error=on_error, finally_fn=finally_fn)

    converter.reload = _converter_reload  # type: ignore[attr-defined]
    _wire_source_bar(converter)
    _finish_tab(converter, converter_layout, "Convert to PDF", _converter_run)
    _converter_reload()

    # -- Agent Bundle -----------------------------------------------------
    merger, merger_layout = _new_tab("Agent Bundle")
    merger_queue: list[Path] = []
    merger_bar = QHBoxLayout()
    merger_add_files = QPushButton("Add PDFs...")
    merger_add_folder = QPushButton("Add folder...")
    merger_clear = QPushButton("Clear list")
    merger_bar.addWidget(merger_add_files)
    merger_bar.addWidget(merger_add_folder)
    merger_bar.addWidget(merger_clear)
    merger_bar.addStretch(1)
    merger_layout.addLayout(merger_bar)
    merger._table = make_table()
    merger_layout.addWidget(merger._table, 1)
    merger_opts = QHBoxLayout()
    merger_output = QLineEdit(f"{date.today().strftime('%Y%m%d')}_AgentBundle.pdf")
    merger_output.setPlaceholderText("Output name")
    merger_dest = QComboBox()
    merger_dest.addItems([FOLDER_READY, FOLDER_STAGING])
    merger_opts.addWidget(QLabel("Output:"))
    merger_opts.addWidget(merger_output, 1)
    merger_opts.addWidget(QLabel("Save to:"))
    merger_opts.addWidget(merger_dest)
    merger_layout.addLayout(merger_opts)
    merger._output_edit = merger_output
    merger._dest_combo = merger_dest

    def _merger_render() -> None:
        ordered, rows = _file_rows(list(merger_queue))
        merger._files = ordered
        set_table_rows(merger._table, (("name", "Name"), ("folder", "Folder")), rows)
        _set_status(merger, f"{len(ordered)} PDF(s) queued.")

    def _merger_add_paths(paths_in: list[Path]) -> None:
        pdfs = [path for path in paths_in if path.is_file() and file_ops.is_pdf(path)]
        skipped = len(paths_in) - len(pdfs)
        merger_queue.extend(pdfs)
        _merger_render()
        if skipped:
            _set_status(merger, f"Added {len(pdfs)} PDF(s), skipped {skipped} non-PDF file(s).")

    def _merger_add_folder() -> None:
        from PySide6.QtWidgets import QFileDialog

        picked = QFileDialog.getExistingDirectory(merger, "Select folder with PDFs", str(staging_dir))
        if picked:
            folder = Path(picked)
            _merger_add_paths(list(file_ops.list_files(folder)))

    def _merger_add_files() -> None:
        from PySide6.QtWidgets import QFileDialog

        picked, _ = QFileDialog.getOpenFileNames(merger, "Select PDF files", str(staging_dir), "PDF files (*.pdf)")
        if picked:
            _merger_add_paths([Path(item) for item in picked])

    def _merger_clear() -> None:
        merger_queue.clear()
        _merger_render()

    def _merger_run() -> None:
        sources = [path for path in merger_queue if path.is_file()]
        if not sources:
            _set_status(merger, "Add at least one PDF file to merge.")
            return
        name = merger._output_edit.text().strip() or f"{date.today().strftime('%Y%m%d')}_AgentBundle.pdf"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        dest_dir = ready_dir if merger._dest_combo.currentText() == FOLDER_READY else staging_dir
        target = dest_dir / name
        _set_status(merger, f"Merging {len(sources)} PDF(s)...")
        merger._run_btn.setEnabled(False)

        def work():
            return file_ops.merge_pdfs(sources, target)

        def on_success(output) -> None:
            _set_status(merger, f"Bundle saved as {output.name}.")

        def on_error(message: str) -> None:
            lowered = message.lower()
            if "pypdf" in lowered or "no module" in lowered:
                _set_status(merger, "PDF merge needs pypdf (pip install pypdf).")
            else:
                _set_status(merger, f"Merge failed: {message}")

        def finally_fn() -> None:
            merger._run_btn.setEnabled(True)

        run_background_q(merger, work=work, on_success=on_success, on_error=on_error, finally_fn=finally_fn)

    merger.reload = _merger_render  # type: ignore[attr-defined]
    merger.add_paths = _merger_add_paths  # type: ignore[attr-defined]
    merger_add_files.clicked.connect(_merger_add_files)
    merger_add_folder.clicked.connect(_merger_add_folder)
    merger_clear.clicked.connect(_merger_clear)
    _finish_tab(merger, merger_layout, "Merge into one PDF", _merger_run)
    _merger_render()

    # -- Portal Upload ----------------------------------------------------
    portal, portal_layout = _new_tab("Portal")
    _add_source_bar(portal, portal_layout, ready_dir, "dir")
    portal._table = make_table()
    portal_layout.addWidget(portal._table, 1)
    portal_opts = QHBoxLayout()
    portal_url = QLineEdit()
    portal_url.setPlaceholderText("Portal URL (from Settings)")
    try:
        portal_url.setText((db.get_setting(SETTING_PORTAL_URL) or "") if db is not None else "")
    except Exception:
        pass
    portal_opts.addWidget(QLabel("Portal URL:"))
    portal_opts.addWidget(portal_url, 1)
    portal_layout.addLayout(portal_opts)
    portal._url_edit = portal_url

    def _portal_reload() -> None:
        folder = Path(portal._dir_label.text())
        files, _sig = file_ops.list_files_with_signature(folder)
        ordered, rows = _file_rows(files)
        portal._files = ordered
        set_table_rows(portal._table, (("name", "Name"), ("size", "Size")), rows)
        _set_status(portal, f"{len(ordered)} file(s) ready to upload.")

    def _portal_run() -> None:
        index = _selected_index(portal)
        if index is None:
            _set_status(portal, "No files in Ready to Upload yet.")
            return
        source = portal._files[index]
        url = portal._url_edit.text().strip()
        if not url:
            _set_status(portal, "Set the portal URL in Settings first.")
            return
        _set_status(portal, f"Preparing {source.name}...")
        portal._run_btn.setEnabled(False)

        def work():
            backup = file_ops.backup_file(source, archive_dir / FOLDER_PORTAL_BACKUP)
            try:
                absolute = open_portal_and_copy_path(source, url)
            except Exception as exc:
                return ("backup-only", backup, str(exc))
            try:
                copy_to_clipboard(absolute)
            except Exception:
                pass
            return ("ok", backup, absolute)

        def on_success(result) -> None:
            kind, backup, detail = result
            if kind == "ok":
                _set_status(portal, f"Backup saved to {backup.name}. Portal opened — paste with Ctrl+V.\n{detail}")
            else:
                _set_status(portal, f"Backup saved to {backup.name}. Portal step skipped: {detail}")

        def on_error(message: str) -> None:
            _set_status(portal, f"Portal step failed: {message}")

        def finally_fn() -> None:
            portal._run_btn.setEnabled(True)

        run_background_q(portal, work=work, on_success=on_success, on_error=on_error, finally_fn=finally_fn)

    portal.reload = _portal_reload  # type: ignore[attr-defined]
    _wire_source_bar(portal)
    _finish_tab(portal, portal_layout, "Open Portal & copy path", _portal_run)
    _portal_reload()

    # -- Archive & Clean --------------------------------------------------
    archiver, archiver_layout = _new_tab("Archive")
    _add_source_bar(archiver, archiver_layout, archive_dir, "dir")
    archiver._table = make_table()
    archiver_layout.addWidget(archiver._table, 1)
    archiver_dest = QLabel("")
    archiver_dest.setWordWrap(True)
    archiver_dest.setObjectName("qt-shell-subtitle")
    archiver_layout.addWidget(archiver_dest)
    archiver._dest_label = archiver_dest

    def _archiver_reload() -> None:
        ready, _ready_sig = file_ops.list_files_with_signature(ready_dir)
        staging, _staging_sig = file_ops.list_files_with_signature(staging_dir)
        combined = list(ready) + list(staging)
        ordered, rows = _file_rows(combined)
        archiver._files = ordered
        set_table_rows(archiver._table, (("name", "Name"), ("folder", "Folder")), rows)
        try:
            folder = file_ops.month_archive_folder(Path(archiver._dir_label.text()))
        except Exception:
            folder = file_ops.month_archive_folder(archive_dir)
        archiver._dest_label.setText(
            f"Ready: {len(ready)} file(s). Staging: {len(staging)} file(s). Archive destination: {folder}."
        )
        _set_status(archiver, f"{len(ordered)} file(s) awaiting archive.")

    def _archiver_run() -> None:
        _archiver_reload()
        if not archiver._files:
            _set_status(archiver, "Both folders are already empty.")
            return
        total = len(archiver._files)
        _set_status(archiver, f"Archiving {total} file(s)...")
        archiver._run_btn.setEnabled(False)

        def work():
            return file_ops.archive_ready_and_clean_staging(paths)

        def on_success(result) -> None:
            _archiver_reload()
            if result.errors:
                extra = " Some files could not be moved: " + "; ".join(result.errors)
                _set_status(archiver, f"Archived {result.total_moved} file(s) to {result.month_folder.name}.{extra}")
            else:
                _set_status(
                    archiver,
                    f"Archived {len(result.moved_ready)} ready file(s) and "
                    f"{len(result.moved_staging)} staging file(s) to {result.month_folder.name}.",
                )

        def on_error(message: str) -> None:
            _set_status(archiver, f"Archive failed: {message}")

        def finally_fn() -> None:
            archiver._run_btn.setEnabled(True)

        run_background_q(archiver, work=work, on_success=on_success, on_error=on_error, finally_fn=finally_fn)

    archiver.reload = _archiver_reload  # type: ignore[attr-defined]
    _wire_source_bar(archiver)
    _finish_tab(archiver, archiver_layout, "Archive Ready files & clean Staging", _archiver_run)
    _archiver_reload()

    # -- Financial Docs ---------------------------------------------------
    financial, financial_layout = _new_tab("Financial")
    financial_bar = QHBoxLayout()
    financial_folder = QLineEdit("")
    financial_folder.setReadOnly(True)
    financial_folder.setPlaceholderText("All folders (optional filter)")
    financial_browse = QPushButton("Browse folder...")
    financial_clear_filter = QPushButton("Clear")
    financial_bar.addWidget(financial_folder, 1)
    financial_bar.addWidget(financial_browse)
    financial_bar.addWidget(financial_clear_filter)
    financial_layout.addLayout(financial_bar)
    financial._folder_filter = financial_folder
    financial_opts = QHBoxLayout()
    financial_search = QLineEdit()
    financial_search.setPlaceholderText("File name, description...")
    financial_cat = QComboBox()
    financial_cat.addItems(["All", *list(FINANCIAL_DOC_CATEGORIES)])
    financial_refresh = QPushButton("Refresh")
    financial_opts.addWidget(QLabel("Search:"))
    financial_opts.addWidget(financial_search, 1)
    financial_opts.addWidget(QLabel("Category:"))
    financial_opts.addWidget(financial_cat)
    financial_opts.addWidget(financial_refresh)
    financial_layout.addLayout(financial_opts)
    financial._table = make_table()
    financial_layout.addWidget(financial._table, 1)
    financial._search_edit = financial_search
    financial._cat_combo = financial_cat
    financial._docs: list[dict] = []

    _fin_columns = (
        ("client_name", "Client"),
        ("doc_date", "Date"),
        ("category", "Category"),
        ("file_name", "File Name"),
        ("amount", "Amount"),
        ("description", "Description"),
    )

    def _financial_apply(rows: list[dict]) -> None:
        folder_filter = financial._folder_filter.text().strip()
        if folder_filter:
            prefix = str(Path(folder_filter).resolve())
            kept = []
            for doc in rows:
                for key in ("stored_path", "file_path"):
                    candidate = str(doc.get(key) or "")
                    if candidate and (candidate == prefix or candidate.startswith(prefix)):
                        kept.append(doc)
                        break
                    try:
                        if candidate and str(Path(candidate).resolve()).startswith(prefix):
                            if doc not in kept:
                                kept.append(doc)
                            break
                    except Exception:
                        continue
            rows = kept
        rows = rows[:200]
        financial._docs = rows
        table_rows = [
            {
                "client_name": doc.get("client_name", ""),
                "doc_date": doc.get("doc_date") or "",
                "category": doc.get("category") or "",
                "file_name": doc.get("file_name") or "",
                "amount": doc.get("amount") or "",
                "description": doc.get("description") or "",
            }
            for doc in rows
        ]
        set_table_rows(financial._table, _fin_columns, table_rows)
        _set_status(financial, f"{len(rows)} document(s).")

    def _financial_reload() -> None:
        keyword = financial._search_edit.text().strip()
        category = financial._cat_combo.currentText()
        try:
            rows = db.search_financial_documents(keyword) if keyword else db.all_financial_documents()
        except Exception as exc:
            _set_status(financial, f"Search failed: {exc}")
            return
        if category != "All":
            rows = [row for row in rows if row.get("category") == category]
        _financial_apply(rows)

    def _financial_run() -> None:
        keyword = financial._search_edit.text().strip()
        category = financial._cat_combo.currentText()
        _set_status(financial, "Searching...")
        financial._run_btn.setEnabled(False)

        def work():
            rows = db.search_financial_documents(keyword) if keyword else db.all_financial_documents()
            if category != "All":
                rows = [row for row in rows if row.get("category") == category]
            return rows

        def on_success(rows) -> None:
            _financial_apply(list(rows))

        def on_error(message: str) -> None:
            _set_status(financial, f"Search failed: {message}")

        def finally_fn() -> None:
            financial._run_btn.setEnabled(True)

        run_background_q(financial, work=work, on_success=on_success, on_error=on_error, finally_fn=finally_fn)

    def _financial_browse() -> None:
        from PySide6.QtWidgets import QFileDialog

        picked = QFileDialog.getExistingDirectory(financial, "Filter by folder", str(staging_dir))
        if picked:
            financial._folder_filter.setText(picked)
            _financial_reload()

    def _financial_clear_filter() -> None:
        financial._folder_filter.setText("")
        _financial_reload()

    financial.reload = _financial_reload  # type: ignore[attr-defined]
    financial_browse.clicked.connect(_financial_browse)
    financial_clear_filter.clicked.connect(_financial_clear_filter)
    financial_refresh.clicked.connect(_financial_reload)
    _finish_tab(financial, financial_layout, "Search", _financial_run)
    _financial_reload()

    def refresh() -> None:
        current = tabs.currentWidget()
        reload = getattr(current, "reload", None)
        if callable(reload):
            try:
                reload()
            except Exception:
                log.exception("Qt document hub refresh failed")

    page.refresh = refresh  # type: ignore[attr-defined]
    page._hub = hub  # type: ignore[attr-defined]
    page._tabs = tabs  # type: ignore[attr-defined]
    page.setProperty("qt_view_id", "document_hub")
    return page
