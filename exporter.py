#!/usr/bin/env python3

"""Prometheus exporter for Mijia temperature and humidity sensors"""

# Imports
import signal
import sys
import os
import time
import subprocess
import json
from prometheus_client import start_http_server, Gauge, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR

# Number of seconds between 2 metrics collection
COLLECT_INTERVAL = os.getenv('EXPORTER_COLLECT_INTERVAL', 60)
# Port for metrics server
PORT = os.getenv('EXPORTER_PORT', 8000)

# Read sensors configuration
CONFIG_PATH = os.getenv('CONFIG_PATH', '/etc/mijia-sensor-exporter.json')
with open(CONFIG_PATH, 'r') as fd:
    SENSORS = json.load(fd)


def run_cmd(cmd):
    ps = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    result = ps.communicate()[0].decode('utf-8').strip()
    return result


def parse_temperature_humidity_hex_to_plaintext(data_hex):
    """
    >>> parse_temperature_humidity_hex_to_plaintext(
    ... "Notification handle = 0x000e value: " +
    ... "54 3d 32 38 2e 33 20 48 3d 35 34 2e 31 00"
    ... )
    'T=28.3 H=54.1'
    """
    hex_value = data_hex[data_hex.find(':') + 2:]
    if hex_value.endswith("00"):
        hex_value = hex_value[:-3]
    hex_value = hex_value.split(' ')
    return ''.join([str(chr(int(x, 16))) for x in hex_value])


def parse_temperature_humidity_plaintext_to_numeric(data_plaintext):
    """
    >>> r = parse_temperature_humidity_plaintext_to_numeric("T=28.3 H=54.1")
    >>> r == {'temperature': 28.3, 'humidity': 54.1}
    True
    """
    data_plaintext_splitted = data_plaintext.split(' ')
    return {
        'temperature': float(data_plaintext_splitted[0].split('=')[1]),
        'humidity': float(data_plaintext_splitted[1].split('=')[1])
    }


def parse_battery_level_hex_to_numeric(battery_raw):
    """
    >>> parse_battery_level_hex_to_numeric('60')
    93.75
    """
    return 100 * float(battery_raw) / 64.0


def pull_measures(mac_addr):
    """Get measures from a sensor"""
    # Checking temperature and humidity
    cmd = "timeout 60 gatttool -b " + mac_addr + \
          " --char-write-req --handle=0x10 -n 0100 --listen" + \
          " | head -n 2 | tail -n 1"
    data_raw = run_cmd(cmd)
    if not data_raw.startswith("Notification handle = "):
        raise IOError(data_raw)
    data_hex = parse_temperature_humidity_hex_to_plaintext(data_raw)
    measures = parse_temperature_humidity_plaintext_to_numeric(data_hex)

    # Checking the battery level
    cmd = "timeout 60 gatttool -b " + mac_addr + \
          " --char-read --handle=0x18"
    battery_raw = run_cmd(cmd).split(':')[-1].strip()
    battery = parse_battery_level_hex_to_numeric(battery_raw)
    measures['battery_level'] = battery
    return measures


def check_probes(addresses):
    """Check that a list of sensors are responding"""
    for address in addresses:
        pull_measures(address)
        print('Sensor ' + address + ' is ok')


def exit_handler(sig, frame):
    # Define handler for stop signals
    print('Terminating...')
    sys.exit(0)


def main():
    """Main function"""
    # Remove unwanted Prometheus metrics
    [REGISTRY.unregister(c) for c in [PROCESS_COLLECTOR, PLATFORM_COLLECTOR,
                                      REGISTRY._names_to_collectors['python_gc_objects_collected_total']]]

    # Start Prometheus exporter server
    start_http_server(PORT)

    # Register metrics
    temperature_gauge = Gauge('mijia_temperature', 'Temperature', ['mac', 'area', 'area_type'])
    humidity_gauge = Gauge('mijia_humidity', 'Humidity', ['mac', 'area', 'area_type'])
    battery_gauge = Gauge('mijia_battery_level', 'Percentage of remaining battery', ['mac', 'area', 'area_type'])

    # Loop forever
    while True:

        # Loop on sensors
        for sensor in SENSORS:
            # Get measures
            measures = pull_measures(sensor['mac'])

            # Update metrics
            temperature_gauge.labels(
                mac=sensor['mac'], area=sensor['area'], area_type=sensor['area_type']
            ).set(measures['temperature'])
            humidity_gauge.labels(
                mac=sensor['mac'], area=sensor['area'], area_type=sensor['area_type']
            ).set(measures['humidity'])
            battery_gauge.labels(
                mac=sensor['mac'], area=sensor['area'], area_type=sensor['area_type']
            ).set(measures['battery_level'])

        # Wait beforce next metrics collection
        time.sleep(COLLECT_INTERVAL)


if __name__ == '__main__':
    # Catch several signals
    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)
    # Start application
    print('Checking sensors once before starting the webserver.')
    check_probes([sensor['mac'] for sensor in SENSORS])
    print('Starting !')
    main()
