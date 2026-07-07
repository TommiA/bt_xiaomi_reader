import json
from unittest.mock import MagicMock, mock_open, patch

import pytest

import ble_scanner

def test_load_mac_list():
    fake_file = "AA:BB:CC:DD:EE:FF\n11:22:33:44:55:66\n"

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=fake_file)):
            result = ble_scanner.load_mac_list("dummy.txt")

    assert result == {
        "aabbccddeeff",
        "112233445566",
    }
    
def test_load_mac_list_missing():
    with patch("os.path.exists", return_value=False):
        result = ble_scanner.load_mac_list("missing.txt")

    assert result == set()
    
def test_load_mac_list_exception():
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", side_effect=Exception("Boom")):
            result = ble_scanner.load_mac_list("dummy")

    assert result == set()

def test_log_to_influx_writes_point(monkeypatch):
    fake_write = MagicMock()

    monkeypatch.setattr(ble_scanner, "write_api", fake_write)

    sample = {
        "mac": "AA:BB",
        "model_id": "LYWSD03MMC",
        "tempc": 21.5,
        "hum": 55,
        "batt": 80,
        "volt": 3.01,
        "rssi": -62,
    }

    ble_scanner.log_to_influx(sample)

    fake_write.write.assert_called_once()
    
class FakeDevice:

    address = "AA:BB:CC:DD:EE:FF"

class FakeAdvertisement:

    rssi = -60
    local_name = "Sensor"

    service_data = {
        "0000181a-0000-1000-8000-00805f9b34fb": bytes.fromhex("01020304")
    }

    manufacturer_data = {
        0x004C: bytes.fromhex("0102")
    }
    
def test_detection_callback_ignores_unknown(monkeypatch):

    monkeypatch.setattr(
        ble_scanner,
        "ALLOWED_MACS",
        {"112233445566"},
    )

    fake_decode = MagicMock()

    monkeypatch.setattr(
        ble_scanner,
        "dble",
        fake_decode,
    )

    ble_scanner.detection_callback(
        FakeDevice(),
        FakeAdvertisement(),
    )

    fake_decode.assert_not_called()
    
def test_detection_callback_decodes(monkeypatch):

    monkeypatch.setattr(
        ble_scanner,
        "ALLOWED_MACS",
        {"aabbccddeeff"},
    )

    decoded = json.dumps({
        "name": "Sensor",
        "mac": "AA:BB",
        "tempc": 22,
        "hum": 40,
        "batt": 99,
        "volt": 3.02,
        "rssi": -60,
    })

    decode_mock = MagicMock(return_value=decoded)
    influx_mock = MagicMock()

    monkeypatch.setattr(ble_scanner, "dble", decode_mock)
    monkeypatch.setattr(ble_scanner, "log_to_influx", influx_mock)

    ble_scanner.detection_callback(
        FakeDevice(),
        FakeAdvertisement(),
    )

    decode_mock.assert_called_once()
    influx_mock.assert_called_once()
    
def test_detection_callback_decoder_failure(monkeypatch):

    monkeypatch.setattr(
        ble_scanner,
        "ALLOWED_MACS",
        {"aabbccddeeff"},
    )

    monkeypatch.setattr(
        ble_scanner,
        "dble",
        MagicMock(side_effect=Exception("Decode failed")),
    )

    monkeypatch.setattr(
        ble_scanner,
        "log_to_influx",
        MagicMock(),
    )

    # Should not raise
    ble_scanner.detection_callback(
        FakeDevice(),
        FakeAdvertisement(),
    )
    
import asyncio

@pytest.mark.asyncio
async def test_scan_loop(monkeypatch):

    scanner = MagicMock()

    scanner.start = MagicMock()
    scanner.stop = MagicMock()

    monkeypatch.setattr(
        ble_scanner,
        "BleakScanner",
        MagicMock(return_value=scanner),
    )

    async def fake_sleep(seconds):
        raise KeyboardInterrupt()

    monkeypatch.setattr(
        asyncio,
        "sleep",
        fake_sleep,
    )

    with pytest.raises(KeyboardInterrupt):
        await ble_scanner.scan_loop()

    scanner.start.assert_called_once()