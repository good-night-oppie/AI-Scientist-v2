"""Phase-4 acceptance tests for the typed ``HeliosConfig`` on ``Config``.

Proves the two halves of the config wire:
  * the failure the typed field fixes -- an untyped sibling key raises
    ``ConfigKeyError`` under struct mode (the same mechanism that made a bare
    ``helios:`` YAML key break 100% of runs on baseline ``Config``);
  * the fix -- a typed ``Optional[HeliosConfig]`` appended LAST is accepted,
    defaults to ``None`` when the block is absent, and is itself strict.

Import closure (``config.py``) pulls omegaconf/coolname/igraph/... but NEVER
torch; it runs in the Phase-4 non-torch venv.
"""

from __future__ import annotations

import dataclasses
import os

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import ConfigKeyError

from ai_scientist.treesearch.utils.config import Config, HeliosConfig

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BFTS_YAML = os.path.join(_REPO_ROOT, "bfts_config.yaml")


def test_helios_is_dataclass_and_last_field():
    assert dataclasses.is_dataclass(HeliosConfig)
    assert dataclasses.fields(Config)[-1].name == "helios"


def test_typed_helios_accepted():
    r = OmegaConf.merge(
        OmegaConf.structured(Config),
        OmegaConf.create(
            {"helios": {"enabled": True, "store_dir": "/x", "binary_path": "/y"}}
        ),
    )
    assert r.helios.enabled is True
    assert r.helios.store_dir == "/x"
    assert r.helios.binary_path == "/y"


def test_helios_defaults_none():
    # The repo yaml carries every non-helios required top-level key; the helios
    # block is commented out, so the merged config must leave helios at its
    # default of None (the OFF signal downstream phases key on).
    r = OmegaConf.merge(OmegaConf.structured(Config), OmegaConf.load(_BFTS_YAML))
    assert r.helios is None


def test_untyped_sibling_key_rejected():
    # Struct mode still rejects unknown TOP-LEVEL keys -- this is exactly what
    # made a bare `helios:` fail on baseline Config before the typed field.
    with pytest.raises(ConfigKeyError):
        OmegaConf.merge(
            OmegaConf.structured(Config),
            OmegaConf.create({"helios_not_a_field": 1}),
        )


def test_bogus_nested_helios_key_rejected():
    # HeliosConfig is itself strict: a typo inside the block is caught, not
    # swallowed -- so an uncommented block with a bad key fails loudly.
    with pytest.raises(ConfigKeyError):
        OmegaConf.merge(
            OmegaConf.structured(Config),
            OmegaConf.create({"helios": {"not_a_field": 1}}),
        )
