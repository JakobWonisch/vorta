"""Check whether backup source paths and local repositories are reachable."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from vorta.i18n import trans_late
from vorta.store.models import SourceFileModel

if TYPE_CHECKING:
    from vorta.store.models import BackupProfileModel


def check_profile_sources_available(profile: BackupProfileModel) -> tuple[bool, str | None]:
    """
    Return whether all configured source folders and a local repo path exist.

    Returns
    -------
    tuple[bool, str | None]
        (available, plain-language reason when unavailable)
    """
    sources = list(SourceFileModel.select().where(SourceFileModel.profile == profile))
    missing_sources = [source.dir for source in sources if not os.path.exists(os.path.expanduser(source.dir))]

    if missing_sources:
        return False, trans_late('SimpleWindow', 'Connect your backup drive to continue.')

    if profile.repo is None:
        return False, trans_late('SimpleWindow', 'Backup is not configured yet.')

    if not profile.repo.is_remote_repo() and not os.path.exists(profile.repo.url):
        return False, trans_late('SimpleWindow', 'Connect your backup drive to continue.')

    return True, trans_late('SimpleWindow', 'Ready to back up.')
