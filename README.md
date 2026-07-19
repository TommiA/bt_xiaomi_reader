# BLE Sensor Data Logger

This project captures BLE sensor data from compatible devices and logs it to InfluxDB. It's designed to run as a background service and supports filtering devices by MAC address.

## Components

### `ble_scanner.py`
Main Python script that scans for BLE advertisements, decodes sensor data (using TheengsDecoder), and writes it to InfluxDB. It supports:
- MAC address filtering via `mac_list.txt`
- Automatic restart of BLE scanner
- InfluxDB integration
- Error handling and logging

### `mac_list.txt`
Text file containing MAC addresses of allowed BLE devices (formatted as AA:BB:CC:DD:EE:FF). Only devices in this list will be processed.

### `test_ble_scanner.py`
Unit tests for the BLE scanner functionality, including:
- MAC list loading
- InfluxDB logging
- Advertisement decoding
- Device filtering

### `ble_logger.service`
Systemd service configuration that runs the BLE scanner as a background service with automatic restarts.

## Setup
1. Install dependencies: `pip install bleak TheengsDecoder influxdb-client`
2. Configure InfluxDB credentials in `ble_scanner.py`
3. Add allowed MAC addresses to `mac_list.txt`
4. Copy `ble_logger.service` to `/etc/systemd/system/`
5. Enable service: `sudo systemctl enable ble_logger.service`
6. Start service: `sudo systemctl start ble_logger.service`