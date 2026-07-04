import os

import pytest

from vorta.source_availability import check_profile_sources_available
from vorta.store.models import BackupProfileModel, RepoModel, SourceFileModel
from test_constants import TEST_SOURCE_DIR, TEST_TEMP_DIR


def test_sources_available_when_paths_exist(qapp):
    profile = BackupProfileModel.get(name='Default')
    SourceFileModel.delete().where(SourceFileModel.profile == profile).execute()

    repo_path = os.path.join(TEST_TEMP_DIR, 'enduser_repo')
    os.makedirs(repo_path, exist_ok=True)
    os.makedirs(TEST_SOURCE_DIR, exist_ok=True)

    local_repo = RepoModel(url=repo_path, encryption='none')
    local_repo.save()
    profile.repo = local_repo.id
    profile.save()

    SourceFileModel.create(dir=TEST_SOURCE_DIR, profile=profile, path_isdir=True)

    available, message = check_profile_sources_available(profile)
    assert available is True
    assert message == 'Ready to back up.'


def test_sources_unavailable_when_source_missing(qapp):
    profile = BackupProfileModel.get(name='Default')
    SourceFileModel.delete().where(SourceFileModel.profile == profile).execute()

    repo_path = os.path.join(TEST_TEMP_DIR, 'enduser_repo_missing_source')
    os.makedirs(repo_path, exist_ok=True)

    local_repo = RepoModel(url=repo_path, encryption='none')
    local_repo.save()
    profile.repo = local_repo.id
    profile.save()

    missing_path = os.path.join(TEST_TEMP_DIR, 'missing-backup-source')
    SourceFileModel.create(dir=missing_path, profile=profile, path_isdir=True)

    available, message = check_profile_sources_available(profile)
    assert available is False
    assert message == 'Connect your backup drive to continue.'


def test_sources_unavailable_when_local_repo_missing(qapp):
    profile = BackupProfileModel.get(name='Default')
    SourceFileModel.delete().where(SourceFileModel.profile == profile).execute()

    os.makedirs(TEST_SOURCE_DIR, exist_ok=True)
    SourceFileModel.create(dir=TEST_SOURCE_DIR, profile=profile, path_isdir=True)

    missing_repo = os.path.join(TEST_TEMP_DIR, 'missing-repo-path')
    local_repo = RepoModel(url=missing_repo, encryption='none')
    local_repo.save()
    profile.repo = local_repo.id
    profile.save()

    available, message = check_profile_sources_available(profile)
    assert available is False
    assert message == 'Connect your backup drive to continue.'


def test_remote_repo_without_sources_is_available(qapp):
    profile = BackupProfileModel.get(name='Default')
    SourceFileModel.delete().where(SourceFileModel.profile == profile).execute()

    remote_repo = RepoModel(url='user@example.com:repo', encryption='none')
    remote_repo.save()
    profile.repo = remote_repo.id
    profile.save()

    available, message = check_profile_sources_available(profile)
    assert available is True
    assert message == 'Ready to back up.'
