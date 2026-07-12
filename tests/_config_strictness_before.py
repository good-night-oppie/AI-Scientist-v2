# Proves: on baseline Config (no helios field), an untyped `helios:` key
# raises ConfigKeyError at the exact merge in config.py:170-171. Run BEFORE Step 3.
#
# Re-runnable at review time via the mandatory command:
#   git stash push -- ai_scientist/treesearch/utils/config.py \
#     && python3 tests/_config_strictness_before.py ; git stash pop
# (the stash removes the helios field again to reproduce the baseline).
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omegaconf import OmegaConf
from omegaconf.errors import ConfigKeyError

from ai_scientist.treesearch.utils.config import Config

schema = OmegaConf.structured(Config)
try:
    OmegaConf.merge(schema, OmegaConf.create({"helios": {"enabled": True}}))
    print("UNEXPECTED: no error — Config already has a helios field")
    sys.exit(1)
except ConfigKeyError as e:
    print("BASELINE RAISES ConfigKeyError:", str(e).splitlines()[0])
    sys.exit(0)
