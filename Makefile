# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

# Regenerate the Python protobuf bindings from the reduced proto source.
#
# Uses grpcio-tools' bundled protoc, so no separate protoc binary is required
# and it works identically on Linux / macOS / Windows. Install the toolchain
# with `pip install -r requirements.txt` (or `pip install .[dev]`) first.

PROTO_DIR := src/proto
PY_OUT    := src/mouthpad_gestural_interface/_pb
PROTOC    := python -m grpc_tools.protoc

.PHONY: all proto clean

all: proto

proto:
	$(PROTOC) -I=$(PROTO_DIR) --python_out=$(PY_OUT) $(PROTO_DIR)/*.proto

clean:
	rm -f $(PY_OUT)/*_pb2.py
