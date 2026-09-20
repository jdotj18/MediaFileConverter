"""Main UI"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..backend.convert import ConversionWorker, Settings
from ..backend.formats import SUPPORTED_EXTS, job_kind
from ..backend.formats import label as format_label
from ..backend.media import MediaInfo, format_bytes, format_duration, probe
from .widgets import Card, Segmented, SettingRow

COLUMNS = ["FILE", "CONVERT TO", "SIZE", "STATUS", ""]


@dataclass
class Row:

    id: int
    info: MediaInfo
    target: str
    status: str = "ready"
    percent: int = 0
    output: str | None = None
    error: str | None = None


class ConvertTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.setAcceptDrops(True)

        self.settings = Settings()
        self.rows: dict[int, Row] = {}
        self.output_dir: Path | None = None
        self.worker: ConversionWorker | None = None
        self._next_id = 1

        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 20)
        outer.setSpacing(18)
        outer.addLayout(self._build_main(), 1)
        outer.addWidget(self._build_sidebar(), 0)

        self._update_visibility()

    # layout

    def _build_main(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(14)

        column.addWidget(self._build_drop_zone(), 1)
        column.addWidget(self._build_table(), 1)

        self.overall = QProgressBar()
        self.overall.setRange(0, 100)
        self.overall.setValue(0)
        self.overall.setFormat("Nothing queued")
        column.addWidget(self.overall)

        column.addLayout(self._build_buttons())
        return column

    def _build_drop_zone(self) -> QFrame:
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("dropZone")
        self.drop_zone.setProperty("active", "false")

        title = QLabel("Drop files here")
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignCenter)

        sub = QLabel("Video, audio and images")
        sub.setObjectName("muted")
        sub.setAlignment(Qt.AlignCenter)

        browse = QPushButton("Choose files")
        browse.setObjectName("primary")
        browse.clicked.connect(self.choose_files)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(browse)
        button_row.addStretch(1)

        layout = QVBoxLayout(self.drop_zone)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addSpacing(12)
        layout.addLayout(button_row)
        layout.addStretch(1)
        return self.drop_zone

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(58)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for index, width in ((1, 120), (2, 92), (3, 176), (4, 44)):
            header.setSectionResizeMode(index, QHeaderView.Fixed)
            self.table.setColumnWidth(index, width)
        return self.table

    def _build_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        self.add_button = QPushButton("Add files")
        self.add_button.clicked.connect(self.choose_files)

        self.convert_button = QPushButton("Convert && Download")
        self.convert_button.setObjectName("primary")
        self.convert_button.clicked.connect(self.start)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("danger")
        self.cancel_button.clicked.connect(self.cancel)
        self.cancel_button.setVisible(False)

        self.clear_button = QPushButton("Clear all")
        self.clear_button.setObjectName("link")
        self.clear_button.clicked.connect(self.clear_all)

        row.addWidget(self.add_button)
        row.addWidget(self.convert_button)
        row.addWidget(self.cancel_button)
        row.addStretch(1)
        row.addWidget(self.clear_button)
        return row

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(320)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # file destination
        destination = Card("Save to")
        self.destination_label = QLabel("Same folder as each original")
        self.destination_label.setWordWrap(True)

        choose = QPushButton("Choose folder")
        choose.clicked.connect(self.choose_output_dir)
        reset = QPushButton("Reset")
        reset.setObjectName("link")
        reset.clicked.connect(self.reset_output_dir)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(choose)
        buttons.addWidget(reset)
        buttons.addStretch(1)

        destination.add(self.destination_label)
        destination.add_layout(buttons)
        layout.addWidget(destination)

        layout.addWidget(self._build_video_card())
        layout.addWidget(self._build_audio_card())
        layout.addWidget(self._build_image_card())
        layout.addStretch(1)
        return sidebar

    def _build_video_card(self) -> Card:
        card = Card("Video")
        self.video_card = card

        resolution = Segmented(
            [("original", "Original"), ("1080p", "1080p"), ("720p", "720p"), ("480p", "480p")],
            self.settings.video.resolution,
        )
        resolution.changed.connect(
            lambda v: setattr(self.settings.video, "resolution", v)
        )

        quality = Segmented(
            [("high", "High"), ("balanced", "Balanced"), ("small", "Small")],
            self.settings.video.quality,
        )
        quality.changed.connect(lambda v: setattr(self.settings.video, "quality", v))

        fps = Segmented(
            [("original", "Original"), ("60", "60"), ("30", "30"), ("24", "24")],
            self.settings.video.fps,
        )
        fps.changed.connect(lambda v: setattr(self.settings.video, "fps", v))

        keep_audio = QCheckBox()
        keep_audio.setChecked(True)
        keep_audio.toggled.connect(
            lambda on: setattr(self.settings.video, "preserve_audio", on)
        )

        card.add(SettingRow("Resolution", resolution, "Never upscales"))
        card.add(SettingRow("Quality", quality))
        card.add(SettingRow("Frame rate", fps))
        card.add(SettingRow("Preserve audio", keep_audio))
        return card

    def _build_audio_card(self) -> Card:
        card = Card("Audio")
        self.audio_card = card

        bitrate = Segmented(
            [("320", "320"), ("256", "256"), ("192", "192"), ("128", "128")],
            self.settings.audio.bitrate,
        )
        bitrate.changed.connect(lambda v: setattr(self.settings.audio, "bitrate", v))

        metadata = QCheckBox()
        metadata.setChecked(True)
        metadata.toggled.connect(
            lambda on: setattr(self.settings.audio, "preserve_metadata", on)
        )

        card.add(SettingRow("Bitrate", bitrate, "kbps"))
        card.add(SettingRow("Preserve metadata", metadata, "Title, artist and album tags"))
        return card

    def _build_image_card(self) -> Card:
        card = Card("Image")
        self.image_card = card

        self.quality_value = QLabel(str(self.settings.image.quality))
        slider = QSlider(Qt.Horizontal)
        slider.setRange(1, 100)
        slider.setValue(self.settings.image.quality)
        slider.valueChanged.connect(self._on_image_quality)

        preserve = QCheckBox()
        preserve.setChecked(True)
        preserve.toggled.connect(self._on_preserve_dimensions)

        self.width_box = QSpinBox()
        self.width_box.setRange(0, 20000)
        self.width_box.setSpecialValueText("auto")
        self.width_box.setFixedWidth(82)
        self.width_box.valueChanged.connect(
            lambda v: setattr(self.settings.image, "width", v or None)
        )

        self.height_box = QSpinBox()
        self.height_box.setRange(0, 20000)
        self.height_box.setSpecialValueText("auto")
        self.height_box.setFixedWidth(82)
        self.height_box.valueChanged.connect(
            lambda v: setattr(self.settings.image, "height", v or None)
        )

        size_row = QWidget()
        size_layout = QHBoxLayout(size_row)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(8)
        size_layout.addWidget(self.width_box)
        size_layout.addWidget(QLabel("x"))
        size_layout.addWidget(self.height_box)

        self.aspect_box = QCheckBox()
        self.aspect_box.setChecked(True)
        self.aspect_box.toggled.connect(
            lambda on: setattr(self.settings.image, "maintain_aspect", on)
        )

        self.size_row_widget = SettingRow("Width and height", size_row, "Leave one on auto")
        self.aspect_row_widget = SettingRow("Maintain aspect ratio", self.aspect_box)
        self.size_row_widget.setVisible(False)
        self.aspect_row_widget.setVisible(False)

        card.add(SettingRow("Quality", self.quality_value, "JPEG and WEBP output"))
        card.add(slider)
        card.add(SettingRow("Preserve dimensions", preserve))
        card.add(self.size_row_widget)
        card.add(self.aspect_row_widget)
        return card

    # settings

    def _on_image_quality(self, value: int) -> None:
        self.settings.image.quality = value
        self.quality_value.setText(str(value))

    def _on_preserve_dimensions(self, on: bool) -> None:
        self.settings.image.preserve_dimensions = on
        self.size_row_widget.setVisible(not on)
        self.aspect_row_widget.setVisible(not on)

    # drag & drop

    def _set_drop_active(self, active: bool) -> None:
        self.drop_zone.setProperty("active", "true" if active else "false")
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            self._set_drop_active(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._set_drop_active(False)

    def dropEvent(self, event) -> None:
        self._set_drop_active(False)
        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if paths:
            self.add_paths(paths)
            event.acceptProposedAction()

    # queue

    def choose_files(self) -> None:
        patterns = " ".join(f"*.{ext}" for ext in SUPPORTED_EXTS)
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose files to convert",
            "",
            f"Media files ({patterns});;All files (*)",
        )
        if paths:
            self.add_paths(paths)

    def add_paths(self, paths: list[str]) -> None:
        known = {str(row.info.path) for row in self.rows.values()}
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for path in paths:
                if path in known:
                    continue
                known.add(path)
                self._add_row(probe(path))
        finally:
            QApplication.restoreOverrideCursor()
        self._update_visibility()

    def _add_row(self, info: MediaInfo) -> None:
        row = Row(
            id=self._next_id,
            info=info,
            target=info.outputs[0] if info.outputs else "",
            status="ready" if info.supported else "error",
            error=None if info.supported else info.error,
        )
        self._next_id += 1
        self.rows[row.id] = row

        index = self.table.rowCount()
        self.table.insertRow(index)

        #columns

        # c0 - name and details, row id stored on item
        name_item = QTableWidgetItem(info.name)
        name_item.setData(Qt.UserRole, row.id)
        details = [format_label(info.ext)]
        if info.width and info.height:
            details.append(f"{info.width}x{info.height}")
        if info.duration:
            details.append(format_duration(info.duration))
        name_item.setToolTip(str(info.path))
        self.table.setItem(index, 0, name_item)

        detail_text = row.error if row.error else "  ·  ".join(details)
        name_item.setText(f"{info.name}\n{detail_text}")

        # c1 - possible conversions
        combo = QComboBox()
        if info.outputs:
            for output in info.outputs:
                combo.addItem(format_label(output), output)
            combo.currentIndexChanged.connect(
                lambda _, rid=row.id, box=combo: self._set_target(rid, box.currentData())
            )
        else:
            combo.addItem("-")
            combo.setEnabled(False)
        self.table.setCellWidget(index, 1, combo)

        # c2 - size
        size_item = QTableWidgetItem(format_bytes(info.size))
        self.table.setItem(index, 2, size_item)

        # c3 - status and progress bar
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setFormat("Ready" if info.supported else "Unsupported")
        self.table.setCellWidget(index, 3, bar)

        # c4 - remove
        remove = QPushButton("x")
        remove.setObjectName("iconButton")
        remove.setCursor(Qt.PointingHandCursor)
        remove.clicked.connect(lambda _, rid=row.id: self.remove_row(rid))
        self.table.setCellWidget(index, 4, remove)

    def _set_target(self, row_id: int, target: str) -> None:
        row = self.rows.get(row_id)
        if row is None or row.target == target:
            return
        row.target = target
        if row.status in ("done", "error", "cancelled"):
            row.status = "ready"
            row.percent = 0
            row.error = None
            row.output = None
            self._paint(row_id)
        self._update_visibility()

    def _index_of(self, row_id: int) -> int | None:
        """Table positions shift when rows are removed, so look the id up."""
        for index in range(self.table.rowCount()):
            item = self.table.item(index, 0)
            if item and item.data(Qt.UserRole) == row_id:
                return index
        return None

    def remove_row(self, row_id: int) -> None:
        index = self._index_of(row_id)
        if index is not None:
            self.table.removeRow(index)
        self.rows.pop(row_id, None)
        self._update_visibility()

    def clear_all(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.table.setRowCount(0)
        self.rows.clear()
        self._update_visibility()

    #  conversion

    def pending(self) -> list[Row]:
        return [
            row
            for row in self.rows.values()
            if row.info.supported and row.target and row.status != "done"
        ]

    def start(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        jobs = [(row.id, row.info, row.target) for row in self.pending()]
        if not jobs:
            return

        self.convert_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.add_button.setEnabled(False)
        self.clear_button.setEnabled(False)

        for row_id, _, _ in jobs:
            row = self.rows[row_id]
            row.status = "queued"
            row.percent = 0
            row.error = None
            self._paint(row_id)

        self.worker = ConversionWorker(jobs, self.settings, self.output_dir)
        self.worker.job_started.connect(self._on_started)
        self.worker.job_progress.connect(self._on_progress)
        self.worker.job_done.connect(self._on_done)
        self.worker.job_failed.connect(self._on_failed)
        self.worker.all_finished.connect(self._on_all_finished)
        self.worker.start()

    def cancel(self) -> None:
        if self.worker:
            self.worker.cancel()

    def _on_started(self, row_id: int) -> None:
        row = self.rows.get(row_id)
        if row:
            row.status = "running"
            self._paint(row_id)

    def _on_progress(self, row_id: int, percent: int) -> None:
        row = self.rows.get(row_id)
        if row:
            row.status = "running"
            row.percent = percent
            self._paint(row_id)

    def _on_done(self, row_id: int, output: str) -> None:
        row = self.rows.get(row_id)
        if row:
            row.status = "done"
            row.percent = 100
            row.output = output
            self._paint(row_id)
        self._update_overall()

    def _on_failed(self, row_id: int, message: str) -> None:
        row = self.rows.get(row_id)
        if row:
            row.status = "error"
            row.percent = 0
            row.error = message
            self._paint(row_id)
        self._update_overall()

    def _on_all_finished(self) -> None:
        self.cancel_button.setVisible(False)
        self.add_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        for row in self.rows.values():
            if row.status in ("queued", "running"):
                row.status = "cancelled"
                self._paint(row.id)
        self._update_visibility()

    # paint

    def _paint(self, row_id: int) -> None:
        row = self.rows.get(row_id)
        index = self._index_of(row_id)
        if row is None or index is None:
            return

        bar = self.table.cellWidget(index, 3)
        if not isinstance(bar, QProgressBar):
            return

        if row.status == "done":
            name, value, text, tip = "done", 100, "Done", row.output or ""
        elif row.status == "error":
            name, value, text, tip = "failed", 0, "Failed", row.error or ""
        elif row.status == "running":
            name, value, text, tip = "", row.percent, "%p%", ""
        elif row.status == "cancelled":
            name, value, text, tip = "", 0, "Cancelled", ""
        else:
            label = "Queued" if row.status == "queued" else "Ready"
            name, value, text, tip = "", 0, label, ""

        #restyling repaints whole widget, only on status change
        if bar.objectName() != name:
            bar.setObjectName(name)
            bar.style().unpolish(bar)
            bar.style().polish(bar)

        if bar.format() != text:
            bar.setFormat(text)
        bar.setValue(value)
        bar.setToolTip(tip)

        self._update_overall()

    def _update_overall(self) -> None:
        usable = [row for row in self.rows.values() if row.info.supported]
        if not usable:
            self.overall.setValue(0)
            self.overall.setFormat("Nothing queued")
            return
        total = sum(100 if row.status == "done" else row.percent for row in usable)
        done = sum(1 for row in usable if row.status == "done")
        text = f"{done} of {len(usable)} finished  -  %p%"
        if self.overall.format() != text:
            self.overall.setFormat(text)
        self.overall.setValue(round(total / len(usable)))

    def _update_visibility(self) -> None:
        has_rows = bool(self.rows)
        self.drop_zone.setVisible(not has_rows)
        self.table.setVisible(has_rows)
        self.overall.setVisible(has_rows)
        self.clear_button.setVisible(has_rows)

        kinds = {
            job_kind(row.info.ext, row.target)
            for row in self.rows.values()
            if row.info.supported and row.target
        }
        self.video_card.setVisible("video" in kinds)
        self.audio_card.setVisible("audio" in kinds)
        self.image_card.setVisible("image" in kinds)

        self.convert_button.setEnabled(bool(self.pending()))
        self._update_overall()

    # I/O

    def choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose an output folder")
        if folder:
            self.output_dir = Path(folder)
            self.destination_label.setText(folder)

    def reset_output_dir(self) -> None:
        self.output_dir = None
        self.destination_label.setText("Same folder as each original")
