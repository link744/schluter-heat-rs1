# Installation & Setup Guide

## Install the Integration

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

3. Restart Home Assistant (HA OS: **Settings → System → Restart**;
   container/venv: restart the service, e.g.
   `sudo systemctl restart home-assistant`).

**Upgrading later:** `cd` into the cloned folder, `git pull`, re-run the
`cp -r` from step 2 on top of the old folder, then restart HA.

---

### Step 2: Add to Home Assistant

That's it! Just one field:

1. **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Schluter DITRA-HEAT-E-RS1"**
4. Enter your **Session-Id** (see *Getting your Session-Id* below)
5. If you have multiple locations, select which one to add
6. Click **Submit**

### Getting your Session-Id

1. Go to https://schluterditraheat.com and log in
2. Press `F12` to open the browser dev console
3. Go to **Network** tab and find the `Session-Id` header/attribute
4. Copy it and paste it into the integration setup

**Note:** The Session-Id is the same value the website uses to log in —
Home Assistant uses it directly against the Schluter API and never stores
your account password.

✅ Done! Your thermostats will now appear as climate entities.

**We automatically detect your locations - no need to dig through URLs!**

---

## Security Note

### What Happens to Your Session-Id?

- ✅ Sent directly to Schluter's API (over HTTPS)
- ✅ Used only as the `session-id` header for API calls
- ✅ Your account password is never asked for or stored
- ✅ Only the Session-Id is saved in Home Assistant

This is the **same value** the Schluter website uses when you log in.

---

## Verification

### Check Integration is Working

1. Go to **Settings** → **Devices & Services**
2. You should see "Schluter DITRA-HEAT" with your thermostats listed
3. Click on it to see all your devices

### Check Entities

1. Go to **Developer Tools** → **States**
2. Filter for `climate.`
3. You should see your thermostats (e.g., `climate.kitchen_floor`)
4. Check that:
   - `current_temperature` shows a value
   - `target_temperature` shows a value
   - `hvac_action` shows heating/idle/off

### Test Control

Try changing temperature:
1. Go to **Settings** → **Devices & Services** → **Schluter DITRA-HEAT**
2. Click on one of your thermostats
3. Adjust the temperature slider
4. Check your physical thermostat - it should update!

---

## Troubleshooting

### Error: "Invalid authentication"

**Problem**: Session-Id is expired or was copied wrong

**Solutions**:
1. Re-grab a fresh Session-Id from the browser console (see *Getting your
   Session-Id* above)
2. Make sure you copied the whole value with no extra spaces

### Error: "Cannot connect"

**Problem**: Can't reach Schluter API

**Solutions**:
1. Check your internet connection
2. Try visiting https://schluterditraheat.com to verify it's accessible
3. Check Home Assistant logs for more details
4. Wait a few minutes and try again (server might be temporarily down)

### Error: "No devices found"

**Problem**: Selected location has no devices configured

**Solutions**:
1. Make sure you have RS1 thermostats configured in your Schluter account
2. Log into https://schluterditraheat.com and verify your thermostats appear
3. If you have multiple locations, try selecting a different one during setup

### Integration doesn't show up

**Problem**: Installation incomplete

**Solutions**:
1. Verify the repo is cloned inside `custom_components/` and `custom_components/schluter-heat-rs1/schluter_heat/` has the Python files
2. Check the logs: **Settings** → **System** → **Logs**
3. Restart Home Assistant
4. Clear browser cache (Ctrl+Shift+R)

### Entities not updating

**Problem**: Communication issue or expired session

**Solutions**:
1. Check the integration status in **Devices & Services**
2. Click "Reload" on the integration
3. If that doesn't work, you may need to reauthenticate (paste a fresh Session-Id)
4. Look at logs for error messages

### Temperature changes don't work

**Problem**: API call failing

**Solutions**:
1. Check internet connection
2. Verify thermostat is online in Schluter app
3. Check Home Assistant logs for API errors
4. Try reloading the integration

---

## Advanced Configuration

### Customize Entity Names

1. **Settings** → **Devices & Services** → **Schluter DITRA-HEAT**
2. Click on a thermostat
3. Click the gear icon (⚙️)
4. Change "Name" and "Entity ID"

### Customize Polling Interval

By default, the integration polls every 30 seconds. To change:

Edit `const.py` and change:
```python
SCAN_INTERVAL: Final = 60  # Change to 60 seconds
```

Then restart Home Assistant.

### Multiple Locations

If you have thermostats in multiple locations:
1. Add the integration multiple times
2. Use a different Location ID each time
3. Each will show up as a separate integration

---

## Getting Help

### Before Asking for Help

1. Check the logs:
   - **Settings** → **System** → **Logs**
   - Look for errors mentioning `schluter_heat`
2. Try reloading the integration
3. Try removing and re-adding with a fresh Session-Id

### Where to Get Help

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community support
- **Home Assistant Community**: General HA help

### What to Include

When reporting issues, include:
1. Home Assistant version
2. Integration version
3. Number of thermostats
4. Error messages from logs
5. Steps to reproduce the problem

---

## Upgrade Guide

### Keeping Up to Date

```bash
cd <where-you-cloned>/schluter-heat-rs1
git pull
```

Then restart Home Assistant.

---

## Uninstallation

To remove the integration:

1. **Settings** → **Devices & Services**
2. Find "Schluter DITRA-HEAT"
3. Click ⋮ (three dots) → **Delete**
4. Confirm removal
5. (Optional) Delete the cloned `schluter-heat-rs1/` folder from `custom_components/`
6. Restart Home Assistant

---

## Next Steps

Once installed, check out:
- **[README.md](README.md)** - Feature overview and examples

Happy automating! 🏠🔥
