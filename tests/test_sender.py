# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

from types import SimpleNamespace

from mouthpad_gestural_interface.sender import NORDIC_VID, side_band_ports


def port(device, vid=NORDIC_VID, location=None, serial_number="_mouthpad_C57568_"):
    return SimpleNamespace(device=device, vid=vid, location=location,
                           serial_number=serial_number)


def test_the_proto_cdc_port_is_picked_by_its_interface_number():
    ports = [port("/dev/ttyACM0", location="1-1:1.0"),
             port("/dev/ttyACM1", location="1-1:1.2")]
    assert side_band_ports(ports) == ["/dev/ttyACM1"]


def test_windows_interface_locations_are_understood():
    ports = [port("COM5", location="1-2:x.0"), port("COM9", location="1-2:x.2")]
    assert side_band_ports(ports) == ["COM9"]


def test_without_interface_numbers_the_later_named_port_of_a_device_is_picked():
    # macOS reports no interface number but names each port after it.
    ports = [port("/dev/cu.usbmodem11101", location="1-1"),
             port("/dev/cu.usbmodem11103", location="1-1")]
    assert side_band_ports(ports) == ["/dev/cu.usbmodem11103"]


def test_other_usb_serial_devices_are_ignored():
    ports = [port("/dev/cu.usbserial-1", vid=0x0403)]
    assert side_band_ports(ports) == []
