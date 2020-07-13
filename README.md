# mijia-sensor-exporter

This is a Prometheus exporter for Xiaomi Mijia bluetooth temperature and humidity sensor.

## Setup

You need to enable a connection to your Bluetooth sensors. Find them using `hcitool lescan`. Then

```
hcitool lecc MAC_ADDR
```

/!\ /!\ Ensure `/etc/bluetooth/main.conf` contains this line

```
DisablePlugins=pnat
```

If not, add it and reboot your server.

## Configuration

### Sensors

The exporter read the list of sensors to probe from a JSON configuration file. Its default path is `/etc/mijia-sensor-exporter.json` and its structure is :

```json
[
  {
    "mac": "MAC_ADDR_1",
    "area_type": "indoor",
    "area": "bedroom"
  },
  {
    "mac": "MAC_ADDR_2",
    "area_type": "outdoor",
    "area": "balcony"
  }
]
```

Each sensor have following attributes :

- `mac` which is the bluetooth MAC address
- `area_type` a tag add to the metrics, used to differenciate indoor and outdoor sensors
- `area` a tag add to the metrics, used for the room name for example

### Exporter

The script also read some environment variables to configure itself.

- `EXPORTER_COLLECT_INTERVAL` : number of seconds between 2 metrics collection from sensors (default is `60`)
- `EXPORTER_PORT` : port number to listen on (default is `8000`)
- `CONFIG_PATH` : path to sensors configuration file (default is `/etc/mijia-sensor-exporter.json`)

## Credit

Thanks to @sdenel (Simon DENEL), this Prometheus exporter is adapted from [his work](https://github.com/sdenel/xiaomi-mijia-bluetooth-to-prometheus).
