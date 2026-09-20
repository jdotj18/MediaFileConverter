"""Homepage"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from .convert_tab import ConvertTab
from .youtube_tab import YouTubeTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Converter")
        self.resize(1120, 780)
        self.setMinimumSize(960, 640)

        self.convert_tab = ConvertTab()
        self.youtube_tab = YouTubeTab()

        tabs = QTabWidget()
        tabs.addTab(self.convert_tab, "Convert")
        tabs.addTab(self.youtube_tab, "YouTube Downloader")
        self.setCentralWidget(tabs)

    def closeEvent(self, event) -> None:
        """avoid hang on exit"""
        worker = self.convert_tab.worker
        if worker and worker.isRunning():
            worker.cancel()
            worker.wait(3000)

        download = self.youtube_tab.download_worker
        if download and download.isRunning():
            download.cancel()
            download.wait(3000)

        #qt crashes if thread still running at close
        lookup = self.youtube_tab.info_worker
        if lookup and lookup.isRunning():
            lookup.wait(3000)

        event.accept()