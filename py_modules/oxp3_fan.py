# ONEXPLAYER 3 fan control through the ACPI EC (ec_sys / debugfs).
#
# The oxpec driver does not support this model, so the 256 byte EC space is
# read and written directly. Every offset and limit below was measured on an
# ONEXPLAYER 3 (Intel Core Ultra, BIOS 5.09); other models use different
# offsets, so nothing here runs unless the DMI product name matches exactly.
#
# Measured target -> RPM (manual mode):
#   0-10 stopped, 15 ~520, 20 ~730, 30 ~1120, 40 ~1500, 70 ~2430,
#   110 ~3450, 160 ~4460, 180 ~4810, 184 ~4900 (highest), 185+ the fan STOPS.
import asyncio
import glob
import json
import os
import time
import subprocess

import decky_plugin

EC_IO = "/sys/kernel/debug/ec/ec0/io"
SUPPORTED_PRODUCT = "ONEXPLAYER 3"

OFF_BOARD_TEMP = 0x60
OFF_MODE = 0x4A      # 0 = auto (EC curve), 1 = manual
OFF_TARGET = 0x4B    # manual target (0-10 stopped, 15-184 running, 185+ stopped)
OFF_RPM = 0x58       # 16 bit big endian
OFF_CPU_TEMP = 0x70
OFF_TURBO = 0xEB     # bit 0x40: turbo button taken over by the OS (oxpec "tt_toggle")
TURBO_TAKE = 0x40    # while it is clear the EC runs its own fan curve and overwrites 0x4B

TARGET_MAX = 180            # normal upper limit (UI presets)
TARGET_HARD_MAX = 184       # absolute limit used only in emergencies; 185+ stops the fan
TARGET_CEILING_FLOOR = 170  # never lower the learned ceiling below this
HEALTHY_MIN_TARGET = 150    # stall detection only runs at or above this target
STALL_RPM = 3500            # target >= 150 but RPM below this means the fan stalled
SETTLE_SECONDS = 2.5        # skip stall detection right after the target changed
PROBE_INTERVAL = 20         # emergency: raise the target by 1 every N seconds
THROTTLE_ON = 80            # optional TDP limiter starts lowering TDP at this CPU temp
THROTTLE_TARGET = 75        # ...and keeps lowering it until the CPU is back at this temp
THROTTLE_CRITICAL = 90      # lower faster above this
THROTTLE_RESUME = 72        # slowly restore TDP at or below this (73-75 holds the current cap)
TDP_STEP_SECONDS = 5
TDP_RESTORE_SECONDS = 10
TARGET_RUN_MIN = 20         # lowest target used while running
EMERGENCY_ON = 80           # CPU temp that forces maximum fan in every manual mode
EMERGENCY_OFF = 75
SILENT_MAX_TEMP = 51        # silent mode stops the fan only at 50°C or below
SILENT_RESUME = 47          # hysteresis before stopping the fan again
LOOP_INTERVAL = 1.5
FAST_LOOP_INTERVAL = 0.5    # poll faster at high targets to catch stalls quickly

# Standard mode: fan target follows a temperature curve instead of a fixed value,
# so the fan never jumps between a fixed speed and the 80°C emergency maximum.
STANDARD_CURVE = ((45, 30), (55, 50), (65, 80), (72, 110), (78, 150), (82, 180))  # (°C, target)
CURVE_TEMP_SMOOTHING = 0.3  # exponential average weight of each new reading (speeding up)
CURVE_PEAK_WINDOW = 60      # seconds; slowing down follows the hottest reading in this window
CURVE_STEP_UP = 6           # max target change per control step (~1.5 s)
CURVE_STEP_DOWN = 2

MODES = ("auto", "silent", "standard", "manual")
SETTINGS_PATH = os.path.join(os.environ.get("DECKY_PLUGIN_SETTINGS_DIR", "/tmp"), "oxp3_fan.json")

_state = {"mode": "auto", "target": 90, "emergency": False, "silent_forced": False,
          "emerg_target": TARGET_MAX, "ceiling": TARGET_HARD_MAX, "changed_t": 0.0, "probe_t": 0.0,
          "tdp_limiter": False, "tdp_floor": 20, "tdp_cap": None, "tdp_requested": None, "tdp_step_t": 0.0,
          "turbo_orig": None, "smooth_temp": None, "curve_target": None,
          "temp_history": [], "throttling": False}
_task = None


def _product_name():
  try:
    with open("/sys/class/dmi/id/product_name") as f:
      return f.read().strip()
  except OSError:
    return ""


def is_supported():
  return _product_name() == SUPPORTED_PRODUCT


def _run(*cmd):
  return subprocess.run(cmd, capture_output=True, text=True, timeout=5)


def ensure_ec_access():
  """Load ec_sys with write_support=1. Returns True when the EC is writable."""
  if not is_supported():
    return False
  try:
    if os.access(EC_IO, os.W_OK):
      return True
    if not os.path.isdir("/sys/kernel/debug/ec"):
      _run("mount", "-t", "debugfs", "none", "/sys/kernel/debug")
    _run("modprobe", "-r", "ec_sys")
    _run("modprobe", "ec_sys", "write_support=1")
    return os.access(EC_IO, os.W_OK)
  except Exception as e:
    decky_plugin.logger.error(f"oxp3_fan ensure_ec_access {e}")
    return False


def _read(off, n=1):
  with open(EC_IO, "rb", buffering=0) as f:
    f.seek(off)
    return f.read(n)


def _write(off, value):
  with open(EC_IO, "r+b", buffering=0) as f:
    f.seek(off)
    f.write(bytes([value & 0xFF]))


def _coretemp():
  for h in glob.glob("/sys/class/hwmon/hwmon*"):
    try:
      if open(h + "/name").read().strip() == "coretemp":
        vals = [int(open(p).read()) for p in glob.glob(h + "/temp*_input")]
        if vals:
          return round(max(vals) / 1000)
    except OSError:
      pass
  return None


def _actual_tdp():
  """Current RAPL long term limit in W, or None."""
  for prefix in ("/sys/devices/virtual/powercap/intel-rapl-mmio/intel-rapl-mmio:0", "/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0"):
    try:
      with open(prefix + "/constraint_0_power_limit_uw") as f:
        return round(int(f.read()) / 1e6)
    except (OSError, ValueError):
      pass
  return None


def read_status():
  status = {"supported": is_supported(), "available": False, "mode": _state["mode"], "target": _state["target"],
            "targetMin": TARGET_RUN_MIN, "targetMax": TARGET_MAX, "rpm": None, "cpuTemp": None, "boardTemp": None,
            "ecMode": None, "ecTarget": None, "emergency": _state["emergency"], "silentForced": _state["silent_forced"],
            "ceiling": _state["ceiling"], "tdpLimiter": _state["tdp_limiter"], "tdpFloor": _state["tdp_floor"],
            "tdpCap": _state["tdp_cap"], "tdpRequested": _state["tdp_requested"], "tdpActual": _actual_tdp()}
  if not status["supported"] or not os.access(EC_IO, os.R_OK):
    return status
  try:
    status["rpm"] = int.from_bytes(_read(OFF_RPM, 2), "big")
    status["cpuTemp"] = _read(OFF_CPU_TEMP)[0]
    status["boardTemp"] = _read(OFF_BOARD_TEMP)[0]
    status["ecMode"] = _read(OFF_MODE)[0]
    status["ecTarget"] = _read(OFF_TARGET)[0]
    status["available"] = True
  except OSError as e:
    decky_plugin.logger.error(f"oxp3_fan read_status {e}")
  return status


def dump_ec():
  """Raw EC space as hex (diagnostics)."""
  if not is_supported() or not os.access(EC_IO, os.R_OK):
    return ""
  return _read(0, 256).hex()


def _cpu_temp():
  """Highest of the EC and coretemp readings, or None if neither can be read."""
  temps = []
  try:
    temps.append(_read(OFF_CPU_TEMP)[0])
  except OSError:
    pass
  ct = _coretemp()
  if ct is not None:
    temps.append(ct)
  return max(temps) if temps else None


def _clamp_run(v):
  return max(TARGET_RUN_MIN, min(TARGET_MAX, int(v)))


def _curve(temp):
  pts = STANDARD_CURVE
  if temp <= pts[0][0]:
    return pts[0][1]
  for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
    if temp <= t1:
      return round(v0 + (v1 - v0) * (temp - t0) / (t1 - t0))
  return pts[-1][1]


def _standard_target(temp):
  """Fan target for standard mode.

  Design notes (tuned on an ONEXPLAYER 3; adjust here if you find better values):
  - The CPU temperature sensors jump around by about 3-4°C even under a steady
    load (seen while gaming at full fan speed for 5 minutes). A curve that
    follows the raw reading makes the fan audibly speed up and slow down all
    the time, and a fixed "slow down after the temperature drops 3°C" rule is
    still inside that noise.
  - Speeding up follows a smoothed reading (exponential average) so the fan
    reacts to real heat within a few seconds but ignores single spikes.
  - Slowing down follows the hottest reading of the last CURVE_PEAK_WINDOW
    seconds instead. Sensor noise keeps that peak steady, so the fan only
    slows down once the CPU has really been cooler for a whole minute.
    A 5°C hysteresis was also considered; the peak window handles the noise
    without making the fan stay loud after the load really ends.
  - Both directions are rate limited (CURVE_STEP_UP / CURVE_STEP_DOWN per
    control step), so even a real change sounds like a gradual ramp.
  Ideas not tried yet: a longer window for slowing down at high targets, or
  averaging the EC and coretemp readings instead of taking the maximum.
  """
  now = time.monotonic()
  hist = [(t, v) for t, v in _state["temp_history"] if now - t <= CURVE_PEAK_WINDOW]
  hist.append((now, temp))
  _state["temp_history"] = hist
  s = _state["smooth_temp"]
  s = temp if s is None else s + CURVE_TEMP_SMOOTHING * (temp - s)
  _state["smooth_temp"] = s
  up, down = _curve(s), _curve(max(v for _, v in hist))
  cur = _state["curve_target"]
  if cur is None:
    want = up
  elif up > cur:
    want = min(up, cur + CURVE_STEP_UP)
  elif down < cur:
    want = max(down, cur - CURVE_STEP_DOWN)
  else:
    want = cur
  want = _clamp_run(want)
  _state["curve_target"] = want
  return want


def _desired(temp):
  """Return (ec_mode, target). All safety rules are applied here."""
  mode = _state["mode"]
  if mode == "auto" or temp is None:  # without a temperature, leave it to the EC
    return 0, None

  if temp >= EMERGENCY_ON:
    if not _state["emergency"]:
      _state["emergency"] = True
      _state["emerg_target"] = min(TARGET_MAX, _state["ceiling"])
      _state["probe_t"] = time.monotonic()
  elif temp < EMERGENCY_OFF:
    _state["emergency"] = False
    _state["ceiling"] = TARGET_HARD_MAX  # try the full range again next time
  if _state["emergency"]:
    # 80°C+: go to the limit, then probe +1 at a time up to 184 while it stays hot and the fan stays healthy
    now = time.monotonic()
    if now - _state["probe_t"] >= PROBE_INTERVAL and _state["emerg_target"] < _state["ceiling"]:
      _state["emerg_target"] += 1
      _state["probe_t"] = now
    target = min(_state["emerg_target"], _state["ceiling"], TARGET_HARD_MAX)
    _state["curve_target"] = _clamp_run(target)  # standard mode ramps down from here afterwards
    return 1, target

  if mode == "silent":
    if temp >= SILENT_MAX_TEMP:
      _state["silent_forced"] = True
    elif temp <= SILENT_RESUME:
      _state["silent_forced"] = False
    return 1, (TARGET_RUN_MIN if _state["silent_forced"] else 0)

  if mode == "standard":
    return 1, _standard_target(temp)

  return 1, _clamp_run(_state["target"])


def _healthy_check(want_target):
  """If the RPM collapsed at a high target (fan stalled), lower the ceiling and return a safe target."""
  if want_target is None or want_target < HEALTHY_MIN_TARGET:
    return want_target
  if time.monotonic() - _state["changed_t"] < SETTLE_SECONDS:
    return want_target
  if _read(OFF_TARGET)[0] != want_target:
    return want_target
  rpm = int.from_bytes(_read(OFF_RPM, 2), "big")
  if rpm >= STALL_RPM:
    return want_target
  ceiling = max(TARGET_CEILING_FLOOR, want_target - 2)
  decky_plugin.logger.error(f"oxp3_fan: RPM {rpm} at target {want_target} -> ceiling {ceiling}")
  _state["ceiling"] = ceiling
  _state["emerg_target"] = min(_state["emerg_target"], ceiling)
  return min(want_target, ceiling)


def _tdp_step(temp):
  """Optional: lower TDP step by step while overheating, restore it slowly once cool."""
  if not _state["tdp_limiter"] or temp is None or _state["tdp_requested"] is None:
    return
  import cpu_utils
  now = time.monotonic()
  req = _state["tdp_requested"]
  cap = _state["tdp_cap"]
  cur = cap if cap is not None else req
  floor = _state["tdp_floor"]
  # Reaching 80°C starts lowering TDP, and it keeps going until the CPU is
  # back at 75°C. Going down to 70°C would cost too much in demanding games,
  # while staying at 85-100°C makes the device misbehave (a USB-C wireless
  # audio dongle kept disconnecting at those temperatures, not when cool).
  if temp >= THROTTLE_ON:
    _state["throttling"] = True
  elif temp <= THROTTLE_TARGET:
    _state["throttling"] = False
  if _state["throttling"] and cur > floor:
    interval, step = (2, 2) if temp >= THROTTLE_CRITICAL else (TDP_STEP_SECONDS, 1)
    if now - _state["tdp_step_t"] >= interval:
      _state["tdp_cap"] = max(floor, cur - step)
      _state["tdp_step_t"] = now
      decky_plugin.logger.info(f"oxp3_fan: CPU {temp}C -> TDP cap {_state['tdp_cap']}W")
      cpu_utils.set_tdp(req)
  elif temp <= THROTTLE_RESUME and cap is not None:
    if now - _state["tdp_step_t"] >= TDP_RESTORE_SECONDS:
      _state["tdp_cap"] = None if cap + 1 >= req else cap + 1
      _state["tdp_step_t"] = now
      cpu_utils.set_tdp(req)


def limit_tdp(requested):
  """Called by cpu_utils.set_tdp: remember the requested TDP and apply the overheat cap.
  The cap is never saved to settings or profiles."""
  _state["tdp_requested"] = requested
  cap = _state["tdp_cap"]
  if cap is not None and requested > cap:
    return cap
  return requested


def apply_once():
  """Bring the EC to the desired state (also reverts values changed by something else)."""
  temp = _cpu_temp()
  _tdp_step(temp)
  want_mode, want_target = _desired(temp)
  want_target = _healthy_check(want_target)
  if want_target is not None:
    assert want_target == 0 or TARGET_RUN_MIN <= want_target <= TARGET_HARD_MAX
    if _read(OFF_TARGET)[0] != want_target:
      _write(OFF_TARGET, want_target)
      _state["changed_t"] = time.monotonic()
  if want_mode == 1:
    _take_turbo()
  if _read(OFF_MODE)[0] != want_mode:
    _write(OFF_MODE, want_mode)


def _take_turbo():
  """Manual fan control only sticks while the OS owns the turbo button."""
  cur = _read(OFF_TURBO)[0]
  if _state["turbo_orig"] is None:
    _state["turbo_orig"] = cur
  if not cur & TURBO_TAKE:
    _write(OFF_TURBO, cur | TURBO_TAKE)
    decky_plugin.logger.info(f"oxp3_fan: turbo takeover {cur:#x} -> {cur | TURBO_TAKE:#x}")


def _save():
  try:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
      json.dump({"mode": _state["mode"], "target": _state["target"],
                 "tdp_limiter": _state["tdp_limiter"], "tdp_floor": _state["tdp_floor"]}, f)
  except OSError as e:
    decky_plugin.logger.error(f"oxp3_fan save {e}")


def _load():
  try:
    with open(SETTINGS_PATH) as f:
      d = json.load(f)
    if d.get("mode") in MODES:
      _state["mode"] = d["mode"]
    _state["target"] = _clamp_run(d.get("target", 90))
    if _state["mode"] == "manual" and _state["target"] < HEALTHY_MIN_TARGET:
      _state["mode"] = "standard"  # older builds used a fixed target 90 for standard
    _state["tdp_limiter"] = bool(d.get("tdp_limiter", False))
    _state["tdp_floor"] = max(5, min(30, int(d.get("tdp_floor", 20))))
  except (OSError, ValueError):
    pass


def set_mode(mode, target=None):
  if mode not in MODES:
    return read_status()
  _state["mode"] = mode
  if target is not None:
    _state["target"] = _clamp_run(target)
  _state["emergency"] = False
  _state["silent_forced"] = False
  _state["smooth_temp"] = None
  _state["curve_target"] = None
  _state["temp_history"] = []
  _save()
  try:
    if ensure_ec_access():
      apply_once()
  except Exception as e:
    decky_plugin.logger.error(f"oxp3_fan set_mode {e}")
  return read_status()


def set_options(tdp_limiter=None, tdp_floor=None):
  if tdp_limiter is not None:
    _state["tdp_limiter"] = bool(tdp_limiter)
    if not _state["tdp_limiter"]:
      _release_tdp_cap()
  if tdp_floor is not None:
    _state["tdp_floor"] = max(5, min(30, int(tdp_floor)))
  _save()
  return read_status()


def on_resume():
  """After suspend: drop the overheat cap right away so profile / resume TDP is not blocked."""
  _state["tdp_step_t"] = time.monotonic()
  _state["throttling"] = False
  _release_tdp_cap()


def _release_tdp_cap():
  """Remove the TDP cap and re-apply the requested TDP."""
  if _state["tdp_cap"] is None:
    return
  _state["tdp_cap"] = None
  try:
    import cpu_utils
    if _state["tdp_requested"] is not None:
      cpu_utils.set_tdp(_state["tdp_requested"])
  except Exception as e:
    decky_plugin.logger.error(f"oxp3_fan release tdp cap {e}")


def restore_auto():
  """Hand the fan back to the EC (unload, shutdown, errors)."""
  try:
    if os.access(EC_IO, os.W_OK) and _read(OFF_MODE)[0] != 0:
      _write(OFF_MODE, 0)
    orig = _state["turbo_orig"]
    if orig is not None and os.access(EC_IO, os.W_OK) and _read(OFF_TURBO)[0] != orig:
      _write(OFF_TURBO, orig)
    _state["turbo_orig"] = None
  except Exception as e:
    decky_plugin.logger.error(f"oxp3_fan restore_auto {e}")


async def _loop():
  while True:
    interval = LOOP_INTERVAL
    try:
      if _state["mode"] != "auto":
        apply_once()
        try:
          fast = _state["emergency"] or _read(OFF_TARGET)[0] >= HEALTHY_MIN_TARGET
        except OSError:
          fast = False
        interval = FAST_LOOP_INTERVAL if fast else LOOP_INTERVAL
      else:
        _tdp_step(_cpu_temp())  # the TDP limiter also works in auto mode
    except Exception as e:
      decky_plugin.logger.error(f"oxp3_fan loop {e}")
      restore_auto()  # fall back to EC auto if control fails
    await asyncio.sleep(interval)


def start():
  global _task
  if not is_supported():
    decky_plugin.logger.info("oxp3_fan: unsupported device, fan control disabled")
    return
  _load()
  if not ensure_ec_access():
    decky_plugin.logger.error("oxp3_fan: ec_sys write access unavailable")
    return
  try:
    apply_once()
  except Exception as e:
    decky_plugin.logger.error(f"oxp3_fan start {e}")
  _task = asyncio.get_event_loop().create_task(_loop())


def stop():
  global _task
  if _task:
    _task.cancel()
    _task = None
  restore_auto()
  _release_tdp_cap()
