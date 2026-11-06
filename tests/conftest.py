# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

import os
import sys

# Make the package importable without an install (tests run from the repo tree).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
