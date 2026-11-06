# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

"""Generated protobuf bindings for the reduced gesture proto.

protoc emits the ``*_pb2`` modules with flat top-level cross-imports
(``import Gestures_pb2``), so this directory is put on ``sys.path`` and the
modules are imported flat — the same module objects the generated code reaches.
Importing them package-qualified as well would register each descriptor file
twice and trip protobuf's "already in the pool" guard.

The modules are bound as attributes of this package, so callers can
``from mouthpad_gestural_interface._pb import MouthwareMessage_pb2``.

Run ``make proto`` (or ``make`` in the package root) to (re)generate these.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import Gestures_pb2  # noqa: E402,F401
import GestureInject_pb2  # noqa: E402,F401
import MouthwareMessage_pb2  # noqa: E402,F401
