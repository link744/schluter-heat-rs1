# Schluter DITRA-HEAT-E-RS1 Integration for Home Assistant - Work in Progress - ALPHA not guranteed to work - there be dragons


Control your Schluter DITRA-HEAT-E-RS1 WiFi floor heating thermostats from Home Assistant!

**Compatible with:** Schluter DITRA-HEAT-E-RS1 WiFi Thermostat Controller

## Features

- ✅ **Temperature Control**: Set and monitor floor temperatures
- ✅ **Multiple Thermostats**: Control all your zones from one place
- ✅ **Preset Modes**: Home, Away, and Schedule modes
- ✅ **Real-time Status**: See current temperature and heating status
- ✅ **Energy Monitoring**: Track heating time and power consumption
- ✅ **GFCI Safety Monitoring**: Real-time safety status
- ✅ **Energy Dashboard**: Integration with HA Energy Dashboard
- ✅ **TOU Optimization**: Perfect for Time-of-Use automations

## Installation

> **Note:** Don't `git clone` directly into `custom_components/` — HA looks
> for the manifest one folder deep, and this repo nests it under
> `schluter_heat/`. Clone, then copy the folder in, as shown below.

1. Clone the repo:

   ```bash
   git clone https://github.com/link744/schluter-heat-rs1.git ~/schluter-heat-rs1
   ```

2. Copy the `schluter_heat` folder into your Home Assistant
   `custom_components` directory, e.g. `/home/link744/homeassconfig/custom_components`:

   ```bash
   cp -r ~/schluter-heat-rs1/schluter_heat /home/link744/homeassconfig/custom_components/
   ```

   Verify it landed:

   ```bash
   ls /home/link744/homeassconfig/custom_components/schluter_heat
   # Expected: __init__.py  api.py  climate.py  config_flow.py
   #           const.py     manifest.json  sensor.py  strings.json
   ```

3. Restart Home Assistant (HA OS: **Settings → System → Restart** at the
   bottom of the page; container/venv: restart the service, e.g.
   `sudo systemctl restart home-assistant`).

4. Check it loaded — **Settings → Devices & Services → Add Integration** and
   search for **Schluter DITRA-HEAT-E-RS1**. If the name appears, it loaded.
   If not, check **Settings → System → Logs** for lines mentioning
   `schluter_heat`.

> **Upgrades:** `cd` into the cloned folder, run `git pull`, then copy the
> folder over the old one:
>
> ```bash
> cp -r ~/schluter-heat-rs1/schluter_heat/ /home/link744/homeassconfig/custom_components/schluter_heat/
> ```
>
> then restart HA.

## Configuration

### Super Easy Setup (1 minute!)

**Step 1: Get your refresh token** (30 seconds)

1. Go to https://schluterditraheat.com and log in
2. Press `F12` to open console
3. Go to Network -> attribute -> Session-Id
4. Copy that

**Step 2: Add integration** (30 seconds)

1. In Home Assistant: **Settings** → **Devices & Services** → **Add Integration**
2. Search "Schluter DITRA-HEAT-E-RS1"
3. Paste your Session-Id token
4. If you have multiple locations, select which one
5. Done!

**We automatically detect your locations - no manual lookup needed!**

Your thermostats will appear as climate entities!

## Usage

### Available Entities

Each RS1 thermostat provides:

**Climate Entity:**
- `climate.{name}` - Thermostat control

**Sensor Entities:**
- `sensor.{name}_heating_output` - Current heating percentage (0-100%) from controller
- `sensor.{name}_heating_time_today` - Total hours of heating today (calculated)
- `sensor.{name}_gfci_status` - Safety monitoring from controller (ok/error)
- `sensor.{name}_estimated_power` - Estimated power consumption in Watts*

*Power is **estimated** based on heating % (from controller) × floor area (you configure). The RS1 controllers don't have built-in power meters. Accuracy: ±5-10%, sufficient for trends and automation.

### Basic Control

Each thermostat appears as a climate entity:
- `climate.kitchen_floor` (example)
- `climate.bathroom_floor` (example)

Control them like any other thermostat:
```yaml
service: climate.set_temperature
target:
  entity_id: climate.kitchen_floor
data:
  temperature: 22
```

### Preset Modes

**Home Mode** (manual, normal heating):
```yaml
service: climate.set_preset_mode
target:
  entity_id: climate.kitchen_floor
data:
  preset_mode: home
```

**Away Mode** (reduced heating):
```yaml
service: climate.set_preset_mode
target:
  entity_id: climate.kitchen_floor
data:
  preset_mode: away
```

**Schedule Mode** (follow programmed schedule):
```yaml
service: climate.set_preset_mode
target:
  entity_id: climate.kitchen_floor
data:
  preset_mode: schedule
```

## Example Automations

### Morning Warmup
```yaml
automation:
  - alias: "Morning Bathroom Floor Warmup"
    trigger:
      - platform: time
        at: "06:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.workday_sensor
        state: "on"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.bathroom_floor
        data:
          temperature: 24
```

### Time-of-Use Optimization
```yaml
automation:
  - alias: "Floor Heat: Reduce During On-Peak"
    trigger:
      - platform: state
        entity_id: sensor.tou_period
        to: "on_peak"
    action:
      - service: climate.set_temperature
        target:
          entity_id:
            - climate.kitchen_floor
            - climate.bathroom_floor
        data:
          temperature: >
            {{ state_attr(trigger.entity_id, 'temperature') - 2 }}
```

### Smart Away Mode
```yaml
automation:
  - alias: "Floor Heat: Away When Nobody Home"
    trigger:
      - platform: state
        entity_id: zone.home
        to: "0"
        for: "00:30:00"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: all
        data:
          preset_mode: away
```

### Weather-Based Pre-Heat
```yaml
automation:
  - alias: "Floor Heat: Cold Day Boost"
    trigger:
      - platform: numeric_state
        entity_id: weather.home
        attribute: temperature
        below: 0
    action:
      - service: climate.set_temperature
        target:
          entity_id:
            - climate.kitchen_floor
            - climate.bathroom_floor
        data:
          temperature: >
            {{ state_attr(trigger.entity_id, 'temperature') + 1 }}
```

## Available Attributes

Each climate entity provides these attributes:

- `current_temperature` - Current floor temperature
- `target_temperature` - Target temperature
- `hvac_action` - heating/idle/off
- `preset_mode` - home/away/schedule
- `setpoint_mode` - manual/schedule
- `heating_percent` - Current heating output (0-100%)
- `gfci_status` - GFCI safety status
- `air_floor_mode` - Sensor type (air/floor)

## Dashboard Card Example

```yaml
type: thermostat
entity: climate.kitchen_floor
name: Kitchen Floor
```

Or use a custom card for more details:

```yaml
type: entities
title: Floor Heating
entities:
  - entity: climate.kitchen_floor
    type: custom:simple-thermostat
    control:
      - hvac
      - preset
  - entity: climate.bathroom_floor
    type: custom:simple-thermostat
    control:
      - hvac
      - preset
```

## Troubleshooting

### "Invalid authentication" error
- Your Session-Id has expired (happens every 30-90 days)
- Re-grab a fresh one from the browser console (see **Super Easy Setup**,
  Step 1) and re-add the integration

### "Cannot connect" error
- Check your internet connection
- Verify the Schluter API is accessible (try visiting schluterditraheat.com)

### "No devices found" error
- Make sure you selected the right location during setup
- Make sure you have thermostats configured in your Schluter account

### Integration doesn't appear
- Make sure you restarted Home Assistant after installation
- Check the logs for any error messages

### Integration requires reauthentication
- Your session has expired (happens every 30-90 days)
- Click "Configure" and paste a fresh Session-Id (see **Super Easy Setup**,
  Step 1)
- Takes only 15 seconds!

## Support

- **Issues**: [GitHub Issues](https://github.com/link744/schluter-heat-rs1/issues)
- **Discussions**: [GitHub Discussions](https://github.com/link744/schluter-heat-rs1/discussions)

## Credits

Created with ❤️ for the Home Assistant community.

Special thanks to:
- Schluter Systems for creating great products
- The Home Assistant development team
- Everyone who tested and provided feedback

## License

MIT License - see LICENSE file for details

## Disclaimer

This is an unofficial integration. It is not endorsed by or affiliated with Schluter Systems.
