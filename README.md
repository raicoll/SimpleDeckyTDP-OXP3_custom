# SimpleDeckyTDP for ONEXPLAYER 3 (CachyOS)

**English** | [한국어](README.ko.md) | [日本語](README.ja.md) | [繁體中文](README.zh-Hant.md)

This is a personal fork of [SimpleDeckyTDP](https://github.com/aarron-lee/SimpleDeckyTDP) by Aarron Lee. All of the original TDP, GPU and CPU features come from that project; this fork only adds what I needed to run CachyOS on the ONEXPLAYER 3. It is not affiliated with the original project, so please do not report issues from this build there.

I did some work to run CachyOS on the ONEXPLAYER 3, and I'm sharing the source and binaries.

After Decky Loader is installed, run the script below to install:

```bash
curl -L https://github.com/raicoll/SimpleDeckyTDP-OXP3_custom/raw/main/install.sh | bash
```

**Added on top of the original SimpleDeckyTDP**

- TDP control integration
- Fan speed control integration

**Other additions**

- Brightness and volume control (already in the Quick Settings panel, but added here as well)
- Sound card switching (makes switching easier when you use several USB audio devices)

## What is different in this fork

- **Fan control (ONEXPLAYER 3 only).** A 4-step slider under the TDP slider: Quiet, Auto, Standard and Max, with the current RPM and an approximate target RPM.
  - Quiet stops the fan at 50°C or below and spins it at the lowest speed above that.
  - Auto hands the fan back to the embedded controller (EC).
  - Standard follows the CPU temperature along a curve (about 1100 RPM at 45°C up to about 4800 RPM at 82°C). The speed changes gradually, and it only slows down based on the hottest reading of the last 60 seconds, because the sensor jumps by 3-4°C even under a steady load. So it does not keep switching between loud and quiet near a threshold.
  - Max is about 4700 RPM; above 80°C the fan goes higher (about 4800 RPM and up).
  - Safety rules: the target is never set above 180 (values of 185 and up stop the fan on this model), the fan is forced to maximum above 80°C, and the EC is set back to auto when the plugin unloads.
- **Optional overheat TDP limiter.** From 80°C the TDP is lowered step by step until the CPU is back at 75°C (never below a floor you choose), and restored slowly once it cools to 72°C. Long sessions at 85-100°C made a USB-C wireless audio dongle keep disconnecting, while going all the way down to 70°C costs too much in demanding games. Saved profiles are not changed; the TDP slider shows the applied value while it is limited.
- **Quick controls.** CPU temperature and package power, screen brightness, volume, mute and audio output device, in a compact layout with an icon next to each slider.
- **View Options.** Toggles to show or hide each part of the panel (CPU summary, brightness and volume, output device, TDP controls and their details), to put the TDP controls first, and to move this plugin's tab to the top of the Quick Access menu.
- **Own Quick Access tab** placed right above the Decky tab.
- **40 W maximum TDP on the ONEXPLAYER 3.** The firmware reports 25 W, so the original plugin would cap the slider there. To use another limit, set `INTEL_MAX_TDP_SETTING` in `$HOME/homebrew/settings/SimpleDeckyTDP/settings.json`.
- **Translations** for English, Korean, Japanese, Simplified Chinese and Traditional Chinese.
- **OTA updates are disabled**, so installing an update from the original project cannot replace this build by accident.

The fan control, brightness and audio features work without extra setup. Fan control is enabled only when the DMI product name is exactly `ONEXPLAYER 3`; on other devices the plugin behaves like the original apart from the quick controls.

## Notes on the ONEXPLAYER 3

- The `oxpec` kernel driver does not support this model yet, so the fan is controlled through the ACPI EC with the `ec_sys` module. The plugin loads it with `write_support=1` by itself; no kernel parameters are needed. While the fan is in manual mode the plugin also sets the EC's turbo button takeover bit (register 0xEB, bit 0x40, as the `oxpec` driver does on the OneXPlayer 2 and X1); without it the EC keeps overwriting the fan speed with its own curve.
- Do not run PowerTools or another TDP plugin at the same time; disable it in Decky first. The install script warns you if PowerTools is installed.
- If Handheld Daemon (HHD) or another tool also controls the fan, turn its fan control off so the two do not fight over the EC.
- Steam's own brightness slider does not work on this panel, which is why a brightness slider is included here.
- The Steam performance overlay reads power from the CPU's power sensor, so it shows the TDP set by this plugin without any extra patch.
- Changing the output device here also changes Steam's own output device, so the volume buttons control the device you picked.
- **Known issue:** after booting, it takes about a minute before the screen shows anything. As of October 5, 2026 there does not seem to be a fix for this.

## Removing this fork

When the original SimpleDeckyTDP supports the ONEXPLAYER 3, remove this build and install the original from the Decky store:

```bash
sudo rm -rf $HOME/homebrew/plugins/SimpleDeckyTDP
sudo systemctl restart plugin_loader.service
```

Settings are kept in `$HOME/homebrew/settings/SimpleDeckyTDP` and are compatible with the original plugin.

---

*The original SimpleDeckyTDP README follows. Its install commands install the original plugin, not this fork.*

# SimpleDeckyTDP (original README)

[![](https://img.shields.io/github/downloads/aarron-lee/SimpleDeckyTDP/total.svg)](https://github.com/aarron-lee/SimpleDeckyTDP/releases)

This is a Linux TDP Decky Plugin with support for AMD and experimental Intel support

- [Features](#features)
- [Compatibility](#compatibility)
- [Requirements](#requirements)
- [Installation](#install)
  - [Prerequisites](#prerequisites)
  - [Quick Install / Update](#quick-install--update)
  - [SteamOS Installation](#steamos-installation)
  - [Manual Install](#manual-install)
- [Manual Build](#manual-build)
- [Uninstall Instructions](#uninstall-instructions)
- [Advanced Configuration](#advanced-configuration)
  - [Desktop App](#desktop-app)
  - [Custom Device Settings](#custom-device-settings)
  - [CPU Boost Controls](#are-there-cpu-boost-controls)
- [Troubleshooting](#troubleshooting)
  - [Steam Deck Troubleshooting](#steam-deck-troubleshooting)
  - [ROG Ally Troubleshooting](#rog-ally-troubleshooting)
  - [Ryzenadj Troubleshooting](#ryzenadj-troubleshooting)
- [Attribution](#attribution)

![plugin image](./img/recent.jpg)

## Features

- per game TDP Profiles (and optional separate AC Power Profiles)
  - custom TDP limits
- Power Governor and Energy Performance Preference controls
- GPU Controls
  - GPU Controls are not available on Intel
- SMT control
- CPU Boost control\*
  - note, AMD devices require a newer kernel for CPU boost controls
  - CPU boost controls appear automatically if it's available
- set TDP on AC Power events and suspend-resume events
- TDP Polling - useful for devices that change TDP in the background
- Desktop App - see [Desktop App Section](#desktop-app) for more details
- Legion Go TDP via WMI calls (allows for TDP control with secure boot)
- ROG Ally TDP via WMI calls (allows for TDP control with secure boot)
- (For ROG Ally) Battery Charge Limit
- etc

## Compatibility

Tested on SteamOS, ChimeraOS, NobaraOS, SteamFork, and Bazzite.

Other distros not tested. Intel support is experimental and still a work in progress.

Currently NOT compatible with Nvidia or other discrete GPU systems, this plugin is currently for APUs only

## Requirements

### AMD

This plugin builds + ships ryzenadj for TDP control, but will prioritize any pre-installed ryzenadj binary that can be located in your PATH. ChimeraOS, Bazzite Deck Edition, and NobaraOS Deck edition, should already have ryzenadj pre-installed.

Certain devices, such as the Steam Deck, Legion Go + S, ROG Ally, and Ally X, do not need ryzenadj for TDP control.

### Intel (experimental)

Intel support was built for the `intel_pstate` scaling driver, and is still an experimental work in progress.

To check if your system is compatible, run the following in terminal:

```bash
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_driver
```

If the scaling is `intel_pstate`, then your device should be compatible

# Install

### Prerequisites

Decky Loader must already be installed.

### Quick Install / Update

Run the following in terminal, then reboot. Note that this works both for installing or updating the plugin

```
curl -L https://github.com/aarron-lee/SimpleDeckyTDP/raw/main/install.sh | bash
```

### Install An Older Version

Run the following in terminal, then reboot. Make sure to change the version number


```bash
# example: install v1.0.0
curl -L https://github.com/aarron-lee/SimpleDeckyTDP/raw/main/install.sh | VERSION=v1.0.0 sh
```

### Manual Install

Download the latest release from the [releases page](https://github.com/aarron-lee/SimpleDeckyTDP/releases)

Unzip the zip file, and move the `SimpleDeckyTDP` folder to your `$HOME/homebrew/plugins` directory

then run:

```
sudo systemctl restart plugin_loader.service
```

## Manual build

Dependencies:

- Node.js v16.14+ and pnpm installed
- fully functional ryzenadj

```bash
git clone https://github.com/aarron-lee/SimpleDeckyTDP.git

cd SimpleDeckyTDP

# if pnpm not already installed
npm install -g pnpm

pnpm install
pnpm update @decky/ui --latest
pnpm run build
```

Afterwards, you can place the entire `SimpleDeckyTDP` folder in the `~/homebrew/plugins` directly, then restart your plugin service

```bash
sudo systemctl restart plugin_loader.service
```

### Uninstall Instructions

In Desktop mode, run the following in terminal:

```bash
sudo rm -rf $HOME/homebrew/plugins/SimpleDeckyTDP
sudo systemctl restart plugin_loader.service
```

## Advanced configuration

### Desktop App

(Experimental) [SimpleDeckyTDP-Desktop App](https://github.com/aarron-lee/SimpleDeckyTDP-Desktop) - Desktop port of SimpleDeckyTDP

Intel support is still a work in progress for the Desktop app

- Note: the Desktop app does not have full feature parity with the Decky Plugin. Certain features cannot be implemented yet, such as:
  - per-game profiles
  - AC Profiles (in the Desktop app, AC Profiles are only supported on select devices)
  - etc

The Desktop App also should not be used simultaneously with the SimpleDeckyTDP decky plugin, you should only use one or the other at any given time.

This is because 2-way communication between the plugin and Desktop app is currently not possible.

### Are there CPU boost controls?

Note, CPU Boost should generally be disabled for the ROG Ally and Ally X, CPU boost is known to cause excessive power draw on the Ally and Ally X

CPU Boost controls require a scaling-driver that supports CPU boost. Many distros, by default, use `amd-pstate-epp` as the scaling driver. You must be on a newer kernel for to get CPU Boost controls on `amd-pstate-epp`

CPU boost controls will appear automatically if they're available

If you previously changed to amd_pstate=passive for to get CPU boost controls on BazziteOS, you can revert it via the following:

```
rpm-ostree kargs --delete-if-present=amd_pstate=passive
```

## Troubleshooting

### TDP Control is not working

First try updating the plugin to the latest version.

```
# update script
curl -L https://github.com/aarron-lee/SimpleDeckyTDP/raw/main/install.sh | bash
```

If this doesn't fix your issue, next try deleting your `$HOME/homebrew/settings/SimpleDeckyTDP/settings.json` file, and rebooting.

If neither works, please create a github issue.

### Buggy behavior after upgrading the plugin to a new version

If you see buggy behavior after upgrading to a new version of the plugin, it might be due to some bad values in an older settings file.

Try deleting the `$HOME/homebrew/settings/SimpleDeckyTDP/settings.json` file.

Note that this will delete any of your saved TDP profiles, so you could optionally copy it somewhere else to keep it as a backup instead.

### My eGPU is being affected by TDP settings

The Steam GPU slider reportedly affects eGPUs, if you are using an eGPU you should disable Steam's GPU toggle.

### Steam Deck troubleshooting

Valve changed the scaling driver from `acpi-cpufreq` to `amd-pstate-epp` in SteamOS version 3.7.5.

This change reportedly causes issues with EPP and CPU boost controls if you already had SDTDP installed. The solution is to fully reset the SDTDP settings via deleting the settings file.

NOTE: this will reset any per-game profiles you have previously made.

```bash
# run this to remove the old settings.json
rm $HOME/homebrew/settings/SimpleDeckyTDP/settings.json
```

### ROG Ally Troubleshooting

The ROG ally has some known issues related to CPU Boost and SMT.

- Suspend often gets borked if you disable SMT
  - SDTDP ships a workaround for the SMT bug on the Ally and Ally X, where it will temporarily turn on SMT before suspend
- CPU boost is reportedly misconfigured on the Ally and causes excessive power usage, disabling CPU boost is recommended

#### Rog Ally Extreme Power Save (aka MCU Powersave)

After enabling Extreme Powersave mode (aka MCU powersave), make sure you're on the latest MCU firmware (319 if original ROG Ally, 314 for the Ally X).

If you encounter issues with suspend, or back buttons not working after suspend-resume, it is likely due to your MCU firmware not being up to date, or your distro shipping old Asus-linux kernel modules.

### Legion Go Troubleshooting

The Legion Go requires using Lenovo's built-in WMI methods for device stability.

This use the Legion Go driver that adds TDP controls in the kernel.

This should also work for the Legion Go S.

### Ryzenadj troubleshooting

Note, SimpleDeckyTDP now ships it's own bundled ryzenadj, but by default the plugin will try to use ryzenadj that is already on the system. if `which ryzenadj` in terminal outputs a value, that will be used by the plugin.

The bundled ryzenadj can be found at `$HOME/homebrew/plugins/SimpleDeckyTDP/bin/ryzenadj`

To test your ryzenadj, try the following:

```
$ sudo ryzenadj -a 14000 -b 14000 -c 14000
```

the command above sets 14W TDP. You should see the following if sucessful:

```
Sucessfully set stapm_limit to 14000
Sucessfully set fast_limit to 14000
Sucessfully set slow_limit to 14000
```

If you don't see the success messages, your ryzenadj is most likely not working or configured for your device.

You can also test by running the following:

```
$ sudo ryzenadj -i
```

This should print out a table that looks something like the following:

```
CPU Family: Rembrandt
SMU BIOS Interface Version: 18
Version: v0.13.0
PM Table Version: 450005
|        Name         |   Value   |     Parameter      |
|---------------------|-----------|--------------------|
| STAPM LIMIT         |     8.000 | stapm-limit        |
| STAPM VALUE         |     0.062 |                    |
```

If you see an error, you may need to set `iomem=relaxed` as a boot parameter for your kernel, or disable secure boot.

Note that if you have SELinux + early lockdown enabled, ryzenadj will not work when trying to set TDP.

For Bazzite users, you can enable `iomem=relaxed` via running the following:

```bash
# for Bazzite users
rpm-ostree kargs --append-if-missing=iomem=relaxed
```

If you later want to remove the karg, run:

```bash
# for Bazzite users
rpm-ostree kargs --delete-if-present="iomem=relaxed"
```

# Attribution

Thanks to the following for making this plugin possible:

- [PowerControl](https://github.com/mengmeet/PowerControl/)
- [hhd-adjustor](https://github.com/hhd-dev/adjustor/)
- [hhd-hwinfo](https://github.com/hhd-dev/hwinfo)
- [decky loader](https://github.com/SteamDeckHomebrew/decky-loader/)
- [ryzenadj](https://github.com/FlyGoat/RyzenAdj)

As well as a big shoutout to SteamFork folks for troubleshooting and testing Intel support
