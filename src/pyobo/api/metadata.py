# -*- coding: utf-8 -*-

"""High-level API for metadata."""

import logging
from functools import lru_cache
from typing import Mapping

from .utils import get_version
from ..getters import get
from ..identifier_utils import wrap_norm_prefix
from ..utils.cache import cached_json
from ..utils.path import prefix_cache_join

__all__ = [
    'get_metadata',
]

logger = logging.getLogger(__name__)


@lru_cache()
@wrap_norm_prefix
def get_metadata(prefix: str, force: bool = False) -> Mapping[str, str]:
    path = prefix_cache_join(prefix, name='metadata.json', version=get_version(prefix))

    @cached_json(path=path, force=force)
    def _get_json() -> Mapping[str, str]:
        if force:
            logger.info('[%s] forcing reload for metadata', prefix)
        else:
            logger.info('[%s] no cached metadata found. getting from OBO loader', prefix)
        obo = get(prefix, force=force)
        return obo.get_metadata()

    return _get_json()
