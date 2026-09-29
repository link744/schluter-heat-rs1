# Schluter DITRA-HEAT-E-RS1 Integration for Home Assistant - Work in Progress - ALPHA not guranteed to work - there be dragons

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)


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

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

No HACS needed — just copy the `schluter_heat` folder into your Home Assistant
`custom_components` directory. Full walkthrough for Ubuntu Linux below.

#### 1. Find your Home Assistant config directory

`custom_components` lives inside Home Assistant's configuration directory,
whose location depends on how you installed HA:

| Install method | Typical config directory |
|---|---|
| Home Assistant OS (default install) | `/config` |
| Home Assistant Container / venv (e.g. via `docker`, systemd, or manual) | `~/.homeassistant` or wherever you point `--config` |

For an existing container/venv install, ask HA itself — in the HA UI go to
**Settings → System → About** and note the *"Configuration folder"* path.
Or on a venv/container install, check your service file or startup command
for `--config /path/to/config`.

In this example the config directory is `/home/link744/homeassconfig`, so the
target is `/home/link744/homeassconfig/custom_components`.

#### 2. Download the integration (on Ubuntu)

Open a terminal (`Ctrl+Alt+T`) and run:

**Option A — Download the latest release zip (simplest):**

```bash
# Pick a release tag from the GitHub Releases page, e.g. v1.0.0
TAG="v1.0.0"
curl -L -o /tmp/schluter-heat-rs1.zip \
  "https://github.com/link744/schluter-heat-rs1/archive/refs/tags/${TAG}.zip"
```

(If you don't have `curl` yet: `sudo apt update && sudo apt install -y curl`)

**Option B — Clone the latest main branch with git:**

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/link744/schluter-heat-rs1.git /tmp/schluter-heat-rs1
```

**Option C — Download the whole repo as a zip from the GitHub web UI:**

Open https://github.com/link744/schluter-heat-rs1 → green **Code** button →
**Download ZIP** → unzip in a terminal:

```bash
cd ~/Downloads
unzip schluter-heat-rs1-main.zip
```

#### 3. Copy the `schluter_heat` folder into `custom_components`

Create the folder (if it doesn't exist) and copy the integration folder in:

```bash
CONF_DIR=/home/link744/homeassconfig
mkdir -p "$CONF_DIR/custom_components"
```

From **Option A** (zip):

```bash
unzip -o /tmp/schluter-heat-rs1.zip -d /tmp/
cp -r /tmp/schluter-heat-rs1-*/schluter_heat \
      /home/link744/homeassconfig/custom_components/
```

From **Option B** (git clone):

```bash
cp -r /tmp/schluter-heat-rs1/schluter_heat \
      /home/link744/homeassconfig/custom_components/
```

From **Option C** (web zip):

```bash
cp -r ~/Downloads/schluter-heat-rs1-main/schluter_heat \
      /home/link744/homeassconfig/custom_components/
```

Verify the layout — the folder must be `custom_components/schluter_heat/`
(underscore), **not** `custom_components/schluter-heat-rs1/`:

```bash
ls "$CONF_DIR/custom_components/schluter_heat"
# Expected: __init__.py  api.py  climate.py  config_flow.py
#           const.py     manifest.json  sensor.py  strings.json
```

> **Upgrades (manual installs):** re-run the same download + `cp -r` on top of
> the old folder (`cp -r .../schluter_heat/ "$CONF_DIR/custom_components/schluter_heat/"`),
> then restart HA. There are no other steps.

#### 4. Restart Home Assistant

- **HA OS:** Settings → System → **Restart** (bottom of the page).
- **Container/venv:** restart the service, e.g.
  `sudo systemctl restart home-assistant` (or restart the container /
  run `python3 -m homeassistant` again).

#### 5. Check it loaded

1. **Settings → Devices & Services → Add Integration** — search for
   **Schluter DITRA-HEAT-E-RS1**. If the integration name appears, it loaded.
2. If it does **not** appear, check **Settings → System → Logs** for any line
   mentioning `schluter_heat` (missing files, import errors, wrong folder
   name) and fix, then restart again.
3. You can also force-load it without a full restart:
   **Settings → Devices & Services → Reload** next to the integration
   once it is installed.

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
- Check that your email and password are correct
- Try logging into schluterditraheat.com to verify credentials

### "Cannot connect" error
- Check your internet connection
- Verify the Schluter API is accessible (try visiting schluterditraheat.com)

### "No devices found" error
- Verify your Location ID is correct
- Make sure you have thermostats configured in your Schluter account

### Integration doesn't appear
- Make sure you restarted Home Assistant after installation
- Check the logs for any error messages

### Integration requires reauthentication
- Your session has expired (happens every 30-90 days)
- Click "Configure" and enter your credentials again
- Takes only 15 seconds!

## Support

- **Issues**: [GitHub Issues](https://github.com/your-username/schluter-heat/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/schluter-heat/discussions)

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
