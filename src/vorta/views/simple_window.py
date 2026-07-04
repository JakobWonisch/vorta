import logging
import sys

from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from vorta.source_availability import check_profile_sources_available
from vorta.utils import get_asset, is_system_tray_available
from vorta.views.partials.loading_button import LoadingButton
from vorta.views.utils import get_colored_icon

logger = logging.getLogger(__name__)

POLL_INTERVAL_MS = 2000


class SimpleWindow(QMainWindow):
    """Minimal backup window for end-user mode."""

    def __init__(self, parent=None):
        super().__init__()
        self.app = parent
        self.setWindowTitle(self.tr('Vorta Backup'))
        self.setWindowIcon(get_colored_icon('icon'))
        if sys.platform.startswith('linux'):
            self.app.setDesktopFileName('com.borgbase.Vorta')
        self.setWindowFlags(QtCore.Qt.WindowType.WindowCloseButtonHint | QtCore.Qt.WindowType.WindowMinimizeButtonHint)
        self.setMinimumSize(420, 280)
        self.resize(480, 320)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.addStretch()
        self.advancedButton = QToolButton()
        self.advancedButton.setToolTip(self.tr('Advanced settings'))
        self.advancedButton.setIcon(get_colored_icon('settings_wheel'))
        self.advancedButton.setAutoRaise(True)
        self.advancedButton.clicked.connect(self.app.open_advanced_window_action)
        header.addWidget(self.advancedButton)
        root.addLayout(header)

        self.statusLabel = QLabel()
        status_font = QFont()
        status_font.setPointSize(status_font.pointSize() + 2)
        self.statusLabel.setFont(status_font)
        self.statusLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.statusLabel.setWordWrap(True)
        root.addWidget(self.statusLabel)

        self.createStartBtn = LoadingButton(self.tr('Back up'))
        self.createStartBtn.setMinimumHeight(44)
        self.createStartBtn.setGif(get_asset('icons/loading'))
        self.createStartBtn.clicked.connect(self._start_backup)
        root.addWidget(self.createStartBtn)

        details_layout = QGridLayout()
        details_layout.setColumnStretch(1, 1)

        self.progressText = QLabel()
        self.progressText.setWordWrap(True)
        self.progressText.setOpenExternalLinks(True)
        details_layout.addWidget(self.progressText, 0, 0, 1, 2)

        self.cancelButton = QPushButton(self.tr('Cancel'))
        self.cancelButton.setEnabled(False)
        self.cancelButton.clicked.connect(self.app.backup_cancelled_event.emit)
        details_layout.addWidget(self.cancelButton, 1, 0, Qt.AlignmentFlag.AlignTop)

        self.logText = QLabel()
        self.logText.setWordWrap(True)
        self.logText.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        details_layout.addWidget(self.logText, 1, 1, Qt.AlignmentFlag.AlignTop)

        root.addLayout(details_layout)
        root.addStretch()

        self.app.backup_started_event.connect(self.backup_started_event)
        self.app.backup_finished_event.connect(self.backup_finished_event)
        self.app.backup_log_event.connect(self.set_log)
        self.app.backup_progress_event.connect(self.set_progress)
        self.app.backup_cancelled_event.connect(self.backup_cancelled_event)

        self._palette_connection = self.app.paletteChanged.connect(lambda p: self.set_icons())
        self.destroyed.connect(self._on_destroyed)

        self._availability_timer = QtCore.QTimer(self)
        self._availability_timer.setInterval(POLL_INTERVAL_MS)
        self._availability_timer.timeout.connect(self.refresh_availability)
        self._availability_timer.start()

        if self.app.jobs_manager.is_worker_running():
            self.createStartBtn.setEnabled(False)
            self.createStartBtn.start()
            self.cancelButton.setEnabled(True)

        self.set_icons()
        self.refresh_availability()

    def profile(self):
        return self.app.get_enduser_profile()

    def set_icons(self):
        self.advancedButton.setIcon(get_colored_icon('settings_wheel'))

    def _on_destroyed(self):
        try:
            self.app.paletteChanged.disconnect(self._palette_connection)
        except (TypeError, RuntimeError):
            pass

    def refresh_availability(self):
        if self.app.jobs_manager.is_worker_running():
            return

        available, message = check_profile_sources_available(self.profile())
        if message:
            self.statusLabel.setText(message)
        self._set_backup_enabled(available)

    def _set_backup_enabled(self, enabled: bool):
        self.createStartBtn.setEnabled(enabled and not self.app.jobs_manager.is_worker_running())

    def _start_backup(self):
        profile = self.profile()
        self.app.create_backup_action(profile_id=profile.id)

    def _format_progress(self, text: str) -> str:
        if text.startswith('['):
            closing = text.find(']')
            if closing != -1:
                return text[closing + 1 :].strip()
        return text

    def set_progress(self, text=''):
        self.progressText.setText(self._format_progress(text))
        self.progressText.repaint()

    def set_log(self, text='', context=None):
        if text and len(text) > 300:
            text = text[:300] + '...'
        self.logText.setText(text)
        self.logText.repaint()

    def _toggle_buttons(self, create_enabled=True):
        if create_enabled:
            self.createStartBtn.stop()
        else:
            self.createStartBtn.start()
        self.refresh_availability()
        self.cancelButton.setEnabled(not create_enabled)
        self.cancelButton.repaint()

    def backup_started_event(self):
        self._toggle_buttons(create_enabled=False)
        self.statusLabel.setText(self.tr('Backing up… (do not disconnect the drive)'))
        self.set_log('')

    def backup_finished_event(self):
        if not self.app.jobs_manager.is_worker_running():
            self._toggle_buttons(create_enabled=True)
            self.refresh_availability()

    def backup_cancelled_event(self):
        self._toggle_buttons(create_enabled=True)
        self.set_log(self.tr('Task cancelled'))
        self.refresh_availability()

    def closeEvent(self, event):
        if not is_system_tray_available():
            self.app.quit()
        event.accept()
