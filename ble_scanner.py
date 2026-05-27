import asyncio
import json
import struct
from datetime import datetime
from bleak import BleakScanner
from TheengsDecoder import decodeBLE as dble
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os

# InfluxDB Configuration
INFLUXDB_URL = "<INFLUXDB_URL>"
INFLUXDB_TOKEN = "<INFLUXDB_TOKEN>"
INFLUXDB_ORG = "<INFLUXDB_ORG>"
INFLUXDB_BUCKET = ">INFLUXDB_BUCKET>"

# Initialize InfluxDB Client
influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# Load MAC address list
def load_mac_list(filepath):
    if not os.path.exists(filepath):
        print(f"⚠️ MAC list file not found: {filepath}")
        return set()
    try:
        with open(filepath, "r") as f:
            return {
                line.strip().lower().replace(":", "")
                for line in f
                if line.strip()
            }
    except Exception as e:
        print(f"❌ Failed to load MAC list: {e}")
        return set()

MAC_LIST_PATH = "/home/tai/mac_list.txt"
ALLOWED_MACS = load_mac_list(MAC_LIST_PATH)

# Write data to InfluxDB
def log_to_influx(data):
    timestamp = datetime.now()
    try:
        point = (
            Point("th_sensor")
            .tag("device", data["mac"])
            .tag("model", data.get("model_id", "unknown"))
            .field("temperature", float(data["tempc"]))
            .field("humidity", float(data["hum"]))
            .field("battery", int(data["batt"]))
            .field("voltage", float(data["volt"]))
            .field("rssi", int(data["rssi"]))
        )
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        print(f"✓ Logged to InfluxDB at {timestamp.isoformat()}")
    except Exception as e:
        print(f"❌ Failed to write to InfluxDB: {e}")

# BLE advertisement callback
def detection_callback(device, advertisement_data):
    device_mac = device.address.lower().replace(":", "")
    if device_mac not in ALLOWED_MACS:
        return

    print(f"📡 {device.address} Advertisement: {advertisement_data}")
    data_json = {}

    if advertisement_data.service_data:
        uuid_full = list(advertisement_data.service_data.keys())[0]
        data_json['servicedatauuid'] = uuid_full[4:8]
        data_json['servicedata'] = list(advertisement_data.service_data.values())[0].hex()

    if advertisement_data.manufacturer_data:
        mfg_id = struct.pack('<H', list(advertisement_data.manufacturer_data.keys())[0]).hex()
        mfg_data = list(advertisement_data.manufacturer_data.values())[0].hex()
        data_json['manufacturerdata'] = mfg_id + mfg_data

    if advertisement_data.local_name:
        data_json['name'] = advertisement_data.local_name

    if data_json:
        data_json["id"] = device.address
        data_json["rssi"] = advertisement_data.rssi
        try:
            decoded = dble(json.dumps(data_json))
            if decoded:
                parsed = json.loads(decoded)
                print("---------------------------------------------------------")
                print(f"{parsed['name']}: {parsed['tempc']}°C, {parsed['hum']}% RH, {parsed['batt']}% battery, {parsed['volt']}V")
                print("---------------------------------------------------------")
                log_to_influx(parsed)
        except Exception as e:
            print(f"❌ Failed to decode advertisement: {e}")

# Periodic scan loop with auto-restart
async def scan_loop():
    while True:
        scanner = BleakScanner(detection_callback=detection_callback)
        try:
            print("🔍 Starting BLE scan...")
            await scanner.start()
            await asyncio.sleep(300)  # Scan for 5 minutes
            await scanner.stop()
            print("♻️ Restarting BLE scanner...")
        except Exception as e:
            print(f"⚠️ Error in scanner loop: {e}")
            try:
                await scanner.stop()
            except:
                pass
            await asyncio.sleep(10)

# Entrypoint
async def main():
    try:
        await scan_loop()
    except KeyboardInterrupt:
        print("🛑 Stopping due to keyboard interrupt")
    except Exception as e:
        print(f"❌ Unhandled exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())

