"""Make cc_common importable when pytest is run from this package directly.

The app test runner adds lambdas/python/common to sys.path. A direct pytest
invocation from compact-configuration does not.
"""

import sys
from pathlib import Path

_COMMON = Path(__file__).resolve().parents[2] / 'common'
if str(_COMMON) not in sys.path:
    sys.path.insert(0, str(_COMMON))
