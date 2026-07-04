import os

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout

from vorta.store.models import BackupProfileModel, RepoModel, SettingsModel, SourceFileModel
from vorta.views.simple_window import SimpleWindow
from test_constants import TEST_SOURCE_DIR, TEST_TEMP_DIR


@pytest.fixture
def enduser_profile(qapp):
    profile = BackupProfileModel.get(name='Default')
    SourceFileModel.delete().where(SourceFileModel.profile == profile).execute()

    repo_path = os.path.join(TEST_TEMP_DIR, 'simple_window_repo')
    os.makedirs(repo_path, exist_ok=True)
    os.makedirs(TEST_SOURCE_DIR, exist_ok=True)

    local_repo = RepoModel(url=repo_path, encryption='none')
    local_repo.save()
    profile.repo = local_repo.id
    profile.save()

    SourceFileModel.create(dir=TEST_SOURCE_DIR, profile=profile, path_isdir=True)

    SettingsModel.update({SettingsModel.str_value: str(profile.id)}).where(
        SettingsModel.key == 'enduser_profile_id'
    ).execute()

    enduser_setting = SettingsModel.get(key='enduser_mode')
    enduser_setting.value = False
    enduser_setting.save()

    return profile


def test_simple_window_shows_ready_state(qapp, qtbot, enduser_profile):
    window = SimpleWindow(qapp)
    window.show()
    qtbot.addWidget(window)

    assert window.statusLabel.text() == 'Ready to back up.'
    assert window.createStartBtn.isEnabled()


def test_simple_window_disables_backup_when_drive_missing(qapp, qtbot, enduser_profile, monkeypatch):
    monkeypatch.setattr('os.path.exists', lambda path: False)

    window = SimpleWindow(qapp)
    window.show()
    qtbot.addWidget(window)

    window.refresh_availability()
    assert window.createStartBtn.isEnabled() is False
    assert window.statusLabel.text() == 'Connect your backup drive to continue.'


def test_apply_enduser_mode_shows_simple_window(qapp, qtbot, enduser_profile):
    setting = SettingsModel.get(key='enduser_mode')
    setting.value = True
    setting.save()

    qapp.apply_enduser_mode()

    assert qapp.simple_window is not None
    assert qapp.simple_window.isVisible()
    assert qapp.main_window.isVisible() is False


def test_misc_tab_toggle_enduser_mode(qapp, qtbot, enduser_profile):
    misc_tab = qapp.main_window.miscTab
    qapp.main_window.toggle_misc_visibility()

    checkbox = None
    for index in range(misc_tab.checkboxLayout.count()):
        item = misc_tab.checkboxLayout.itemAt(index, QFormLayout.ItemRole.FieldRole)
        if item is not None:
            widget = item.itemAt(0).widget()
            if widget is not None and widget.text() == 'Use simplified end-user interface':
                checkbox = widget
                break

    assert checkbox is not None
    assert checkbox.isChecked() is False

    pos = Qt.QPoint(2, int(checkbox.height() / 2))
    qtbot.mouseClick(checkbox, Qt.MouseButton.LeftButton, pos=pos)

    assert SettingsModel.get(key='enduser_mode').value is True
    assert SettingsModel.get(key='enduser_profile_id').str_value == str(enduser_profile.id)
    assert qapp.simple_window is not None
    assert qapp.simple_window.isVisible()
