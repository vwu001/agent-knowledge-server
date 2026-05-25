"""
End-to-end integration tests are skipped by default because they require
the real embedding stack and local model downloads.
"""

import os
import pytest


INTEGRATION = os.environ.get("LOCAL_KNOWLEDGE_INTEGRATION") == "1"
skip_unless_integration = pytest.mark.skipif(
    not INTEGRATION,
    reason="Set LOCAL_KNOWLEDGE_INTEGRATION=1 to run integration tests",
)
