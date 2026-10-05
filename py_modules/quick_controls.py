# Quick controls: CPU temperature / package power, screen brightness,
# volume, mute and audio output selection.
#
# Brightness is written to /sys/class/backlight directly because Steam's own
# brightness slider is disabled for panels it does not recognise (ONEXPLAYER 3).
# Audio goes through pactl against the desktop user's PipeWire session, since
# the plugin backend runs as root.
import glob
import json
import os
import pwd
import subprocess
import time

import decky_plugin

_last_energy = None  # (timestamp, microjoules)


def _user_runtime_dir():
  try:
    uid = pwd.getpwnam(decky_plugin.DECKY_USER).pw_uid
  except (KeyError, AttributeError):
    uid = 1000
  return f"/run/user/{uid}"


def _pactl(*args, timeout=4):
  runtime_dir = _user_runtime_dir()
  env = dict(os.environ)
  env["XDG_RUNTIME_DIR"] = runtime_dir
  env["PULSE_SERVER"] = f"unix:{runtime_dir}/pulse/native"
  r = subprocess.run(["pactl", *args], capture_output=True, text=True, timeout=timeout, env=env)
  return r.stdout


def _cpu_temp():
  for h in glob.glob("/sys/class/hwmon/hwmon*"):
    try:
      if open(h + "/name").read().strip() in ("coretemp", "k10temp"):
        vals = [int(open(f).read()) for f in glob.glob(h + "/temp*_input")]
        if vals:
          return round(max(vals) / 1000)
    except OSError:
      pass
  return None


def _package_power():
  """Average package power (W) since the previous call, from the RAPL energy counter."""
  global _last_energy
  try:
    e = int(open("/sys/class/powercap/intel-rapl:0/energy_uj").read())
  except (OSError, ValueError):
    return None
  now = time.monotonic()
  prev, _last_energy = _last_energy, (now, e)
  if not prev or now - prev[0] < 0.5 or e < prev[1]:
    return None
  return round((e - prev[1]) / 1e6 / (now - prev[0]), 1)


def _backlight():
  paths = sorted(glob.glob("/sys/class/backlight/*"))
  for p in paths:
    if os.path.basename(p) == "intel_backlight":
      return p
  return paths[0] if paths else None


def _brightness_get():
  p = _backlight()
  if not p:
    return None
  raw = int(open(p + "/brightness").read())
  mx = int(open(p + "/max_brightness").read())
  # perceptual curve: slider % = sqrt(raw / max)
  return max(1, min(100, round(100 * (raw / mx) ** 0.5)))


def get_state():
  state = {"temp": _cpu_temp(), "power": _package_power(), "brightness": None,
           "volume": 0, "muted": False, "sink": "", "sinks": []}
  try:
    state["brightness"] = _brightness_get()
  except (OSError, ValueError) as e:
    decky_plugin.logger.error(f"quick_controls brightness {e}")
  try:
    default = _pactl("get-default-sink").strip()
    sinks = json.loads(_pactl("--format=json", "list", "sinks"))
    state["sink"] = default
    for s in sinks:
      ports = s.get("ports", [])
      # hide HDMI/DP outputs with nothing attached (unless it is the current output)
      if ports and all(p.get("availability") == "not available" for p in ports) and s["name"] != default:
        continue
      label = s.get("description") or ""
      if not label or label == "(null)":
        label = s.get("properties", {}).get("device.product.name") or s["name"]
      label = label.replace("Core Ultra Processors (Series 3) HD Audio ", "")
      state["sinks"].append({"name": s["name"], "label": label, "description": s.get("description") or ""})
      if s["name"] == default:
        vols = list(s.get("volume", {}).values())
        if vols:
          state["volume"] = int(vols[0]["value_percent"].rstrip("%"))
        state["muted"] = bool(s.get("mute"))
  except Exception as e:  # keep the panel alive even if audio is unavailable
    decky_plugin.logger.error(f"quick_controls audio {e}")
  return state


def set_brightness(percent):
  p = _backlight()
  if not p:
    return False
  mx = int(open(p + "/max_brightness").read())
  percent = max(1, min(100, int(percent)))
  raw = max(1, round(mx * (percent / 100) ** 2))
  with open(p + "/brightness", "w") as f:
    f.write(str(raw))
  return True


def set_volume(percent):
  percent = max(0, min(100, int(percent)))
  _pactl("set-sink-volume", "@DEFAULT_SINK@", f"{percent}%")
  if percent > 0:
    _pactl("set-sink-mute", "@DEFAULT_SINK@", "0")
  return True


def set_mute(muted):
  _pactl("set-sink-mute", "@DEFAULT_SINK@", "1" if muted else "0")
  return True


def set_output(name):
  names = [s["name"] for s in json.loads(_pactl("--format=json", "list", "sinks"))]
  if name not in names:
    return False
  _pactl("set-default-sink", name)
  # move streams that are already playing to the new output
  for line in _pactl("list", "short", "sink-inputs").splitlines():
    idx = line.split("\t")[0]
    if idx.isdigit():
      _pactl("move-sink-input", idx, name)
  return True
