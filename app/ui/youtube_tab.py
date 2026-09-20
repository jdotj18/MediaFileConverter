"""YouTube download UI"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..backend.media import format_duration
from ..backend.youtube import (
    Cancelled,
    build_options,
    download,
    fetch_info,
    fetch_thumbnail,
    is_valid_url,
)
from .widgets import Card, Segmented, SettingRow


class InfoWorker(QThread):
    """check video w/o freezing program"""

    ok = Signal(dict, object)
    failed = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            info = fetch_info(self.url)
            self.ok.emit(info, fetch_thumbnail(info.get("thumbnail")))
        except Exception as exc:
            self.failed.emit(str(exc))


class DownloadWorker(QThread):
    progress = Signal(int, str)
    done = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, url, mode, height, bitrate, folder, parent=None):
        super().__init__(parent)
        self.url = url
        self.mode = mode
        self.height = height
        self.bitrate = bitrate
        self.folder = folder
        self._cancelled = False
        self._phase = 0
        self._highest = 0

    def cancel(self) -> None:
        self._cancelled = True

    def _emit(self, percent: int, stage: str) -> None:
        self._highest = max(self._highest, percent)
        self.progress.emit(self._highest, stage)

    def _on_progress(self, data: dict) -> None:
        if self._cancelled:
            raise Cancelled()

        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            got = data.get("downloaded_bytes") or 0
            fraction = (got / total) if total else 0

            #mp4 pulls two streams, each gets slice of bar
            if self.mode == "mp3":
                low, high, stage = 0, 80, "Downloading audio"
            elif self._phase == 0:
                low, high, stage = 0, 55, "Downloading video"
            else:
                low, high, stage = 55, 88, "Downloading audio"

            self._emit(int(low + (high - low) * fraction), stage)

        elif data.get("status") == "finished":
            self._phase += 1

    def _on_postprocess(self, data: dict) -> None:
        if self._cancelled:
            raise Cancelled()
        if data.get("status") != "started":
            return
        name = data.get("postprocessor", "")
        if "ExtractAudio" in name:
            self._emit(88, "Converting to MP3")
        elif "Merger" in name:
            self._emit(92, "Merging video and audio")
        else:
            self._emit(95, "Finishing up")

    def run(self) -> None:
        try:
            options = build_options(
                self.mode,
                self.height,
                self.bitrate,
                self.folder,
                [self._on_progress],
                [self._on_postprocess],
            )
            path = download(options, self.url)
            self.progress.emit(100, "Finished")
            self.done.emit(path or "")
        except Exception as exc:
            # flag check
            if self._cancelled:
                self.cancelled.emit()
            else:
                self.failed.emit(str(exc))


def reveal(path: str) -> None:
    target = Path(path)
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", str(target)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(target)])
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.parent)))


class YouTubeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")

        self.info: dict | None = None
        self.info_worker: InfoWorker | None = None
        self.download_worker: DownloadWorker | None = None
        self.output_path: str | None = None
        self.folder = QStandardPaths.writableLocation(
            QStandardPaths.DownloadLocation
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 20)
        outer.setSpacing(18)
        outer.addLayout(self._build_main(), 1)
        outer.addWidget(self._build_sidebar(), 0)

    # layout

    def _build_main(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(14)

        link_card = Card("Video link")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.textChanged.connect(self._on_url_changed)
        self.url_input.returnPressed.connect(self.look_up)

        self.lookup_button = QPushButton("Look up")
        self.lookup_button.setObjectName("primary")
        self.lookup_button.setEnabled(False)
        self.lookup_button.clicked.connect(self.look_up)

        link_row = QHBoxLayout()
        link_row.setSpacing(10)
        link_row.addWidget(self.url_input, 1)
        link_row.addWidget(self.lookup_button)
        link_card.add_layout(link_row)

        self.message = QLabel("")
        self.message.setObjectName("error")
        self.message.setWordWrap(True)
        self.message.setVisible(False)

        self.info_card = Card()
        self.thumbnail = QLabel()
        self.thumbnail.setObjectName("thumbnail")
        self.thumbnail.setFixedSize(176, 99)
        self.thumbnail.setScaledContents(True)

        self.title_label = QLabel()
        self.title_label.setObjectName("heading")
        self.title_label.setWordWrap(True)
        self.channel_label = QLabel()
        self.channel_label.setObjectName("muted")

        details = QVBoxLayout()
        details.setSpacing(4)
        details.addWidget(self.title_label)
        details.addWidget(self.channel_label)
        details.addStretch(1)

        info_row = QHBoxLayout()
        info_row.setSpacing(16)
        info_row.addWidget(self.thumbnail, 0, Qt.AlignTop)
        info_row.addLayout(details, 1)
        self.info_card.add_layout(info_row)
        self.info_card.setVisible(False)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)

        self.open_button = QPushButton("Open file")
        self.open_button.clicked.connect(self._open_file)
        self.reveal_button = QPushButton("Show in folder")
        self.reveal_button.setObjectName("link")
        self.reveal_button.clicked.connect(self._reveal_file)
        self.open_button.setVisible(False)
        self.reveal_button.setVisible(False)

        self.download_button = QPushButton("Download MP4")
        self.download_button.setObjectName("primary")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.start_download)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("danger")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel_download)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(self.download_button)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.open_button)
        actions.addWidget(self.reveal_button)
        actions.addStretch(1)

        disclaimer = QLabel(
            "Only download videos you own or that are licensed for reuse, "
            "and follow YouTube's Terms of Service."
        )
        disclaimer.setObjectName("muted")
        disclaimer.setWordWrap(True)

        column.addWidget(link_card)
        column.addWidget(self.message)
        column.addWidget(self.info_card)
        column.addWidget(self.progress)
        column.addLayout(actions)
        column.addStretch(1)
        column.addWidget(disclaimer)
        return column

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(320)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        format_card = Card("Format")
        self.mode = "mp4"
        mode_picker = Segmented([("mp4", "MP4 video"), ("mp3", "MP3 audio")], "mp4")
        mode_picker.changed.connect(self._on_mode_changed)

        self.quality_box = QComboBox()
        self.quality_box.addItem("Best available", None)
        self.quality_box.setFixedWidth(140)

        self.bitrate_picker = Segmented(
            [("320", "320"), ("256", "256"), ("192", "192"), ("128", "128")], "192"
        )

        self.quality_row = SettingRow("Quality", self.quality_box)
        self.bitrate_row = SettingRow("Bitrate", self.bitrate_picker, "kbps")
        self.bitrate_row.setVisible(False)

        format_card.add(SettingRow("Download as", mode_picker))
        format_card.add(self.quality_row)
        format_card.add(self.bitrate_row)

        folder_card = Card("Save to")
        self.folder_label = QLabel(self.folder)
        self.folder_label.setWordWrap(True)
        choose = QPushButton("Choose folder")
        choose.clicked.connect(self.choose_folder)

        folder_buttons = QHBoxLayout()
        folder_buttons.addWidget(choose)
        folder_buttons.addStretch(1)

        folder_card.add(self.folder_label)
        folder_card.add_layout(folder_buttons)

        layout.addWidget(format_card)
        layout.addWidget(folder_card)
        layout.addStretch(1)
        return sidebar

    # behaviour

    def _on_url_changed(self, text: str) -> None:
        self.lookup_button.setEnabled(is_valid_url(text))

    def _on_mode_changed(self, mode: str) -> None:
        self.mode = mode
        self.quality_row.setVisible(mode == "mp4")
        self.bitrate_row.setVisible(mode == "mp3")
        self.download_button.setText(
            "Download MP4" if mode == "mp4" else "Download MP3"
        )

    def _show_message(self, text: str) -> None:
        self.message.setText(text)
        self.message.setVisible(bool(text))

    def look_up(self) -> None:
        #enter key gets past disabled button
        if self.info_worker and self.info_worker.isRunning():
            return
        url = self.url_input.text().strip()
        if not is_valid_url(url):
            return
        self._show_message("")
        self.info_card.setVisible(False)
        self.progress.setVisible(False)
        self.lookup_button.setEnabled(False)
        self.lookup_button.setText("Loading...")

        self.info_worker = InfoWorker(url)
        self.info_worker.ok.connect(self._on_info)
        self.info_worker.failed.connect(self._on_info_failed)
        self.info_worker.start()

    def _on_info(self, info: dict, thumbnail) -> None:
        self.info = info
        self.lookup_button.setText("Look up")
        self.lookup_button.setEnabled(True)

        self.title_label.setText(info["title"])
        extra = f"  ·  up to {info['heights'][0]}p" if info["heights"] else ""
        self.channel_label.setText(
            f"{info['channel']}  ·  {format_duration(info['duration'])}{extra}"
        )

        if thumbnail:
            pixmap = QPixmap()
            pixmap.loadFromData(thumbnail)
            self.thumbnail.setPixmap(pixmap)
            self.thumbnail.setVisible(True)
        else:
            self.thumbnail.setVisible(False)

        self.quality_box.clear()
        if info["heights"]:
            for height in info["heights"]:
                self.quality_box.addItem(f"{height}p", height)
            default = next((h for h in info["heights"] if h <= 1080), info["heights"][0])
            self.quality_box.setCurrentIndex(info["heights"].index(default))
        else:
            self.quality_box.addItem("Best available", None)

        self.info_card.setVisible(True)
        self.download_button.setEnabled(True)

    def _on_info_failed(self, message: str) -> None:
        self.lookup_button.setText("Look up")
        self.lookup_button.setEnabled(True)
        self._show_message(message)

    def start_download(self) -> None:
        if not self.info:
            return
        self._show_message("")
        self.output_path = None
        self.open_button.setVisible(False)
        self.reveal_button.setVisible(False)

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.progress.setFormat("Preparing  -  %p%")
        self.download_button.setEnabled(False)
        self.cancel_button.setVisible(True)

        self.download_worker = DownloadWorker(
            self.info["url"],
            self.mode,
            self.quality_box.currentData(),
            self.bitrate_picker.value(),
            self.folder,
        )
        self.download_worker.progress.connect(self._on_download_progress)
        self.download_worker.done.connect(self._on_download_done)
        self.download_worker.failed.connect(self._on_download_failed)
        self.download_worker.cancelled.connect(self._on_download_cancelled)
        self.download_worker.start()

    def cancel_download(self) -> None:
        if self.download_worker:
            self.download_worker.cancel()

    def _on_download_progress(self, percent: int, stage: str) -> None:
        text = f"{stage}  -  %p%"
        if self.progress.format() != text:
            self.progress.setFormat(text)
        self.progress.setValue(percent)

    def _reset_buttons(self) -> None:
        self.download_button.setEnabled(True)
        self.cancel_button.setVisible(False)

    def _on_download_done(self, path: str) -> None:
        self._reset_buttons()
        self.output_path = path or None
        self.progress.setValue(100)
        self.progress.setFormat("Saved")
        self.open_button.setVisible(bool(path))
        self.reveal_button.setVisible(bool(path))

    def _on_download_failed(self, message: str) -> None:
        self._reset_buttons()
        self.progress.setVisible(False)
        self._show_message(message)

    def _on_download_cancelled(self) -> None:
        self._reset_buttons()
        self.progress.setValue(0)
        self.progress.setFormat("Cancelled")

    def _open_file(self) -> None:
        if self.output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_path))

    def _reveal_file(self) -> None:
        if self.output_path:
            reveal(self.output_path)

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a download folder")
        if folder:
            self.folder = folder
            self.folder_label.setText(folder)
