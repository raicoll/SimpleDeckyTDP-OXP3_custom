import { useEffect, useState } from "react";
import { useQuickAccessVisible } from "@decky/ui";
import {
  Oxp3FanStatus,
  getFanStatus,
  setFanMode,
  setFanOptions,
} from "../backend/utils";

// One poller shared by every component that shows fan / TDP status,
// running only while the Quick Access menu is open.
const POLL_MS = 2000;
let latest: Oxp3FanStatus | null = null;
const listeners = new Set<(s: Oxp3FanStatus) => void>();
let timer: ReturnType<typeof setInterval> | undefined;

const publish = (s: Oxp3FanStatus | null) => {
  if (!s) return;
  latest = s;
  listeners.forEach((fn) => fn(s));
};

const refresh = () => getFanStatus().then(publish).catch(() => {});

const subscribe = (fn: (s: Oxp3FanStatus) => void) => {
  listeners.add(fn);
  if (!timer) {
    refresh();
    timer = setInterval(refresh, POLL_MS);
  }
  return () => {
    listeners.delete(fn);
    if (listeners.size === 0 && timer) {
      clearInterval(timer);
      timer = undefined;
    }
  };
};

export const useOxp3Fan = () => {
  const visible = useQuickAccessVisible();
  const [status, setStatus] = useState<Oxp3FanStatus | null>(latest);

  useEffect(() => {
    if (!visible) return;
    return subscribe(setStatus);
  }, [visible]);

  return {
    status,
    setMode: (mode: string, target: number | null) =>
      setFanMode(mode, target).then(publish).catch(() => {}),
    setOptions: (tdpLimiter: boolean | null, tdpFloor: number | null) =>
      setFanOptions(tdpLimiter, tdpFloor).then(publish).catch(() => {}),
  };
};

// measured on the ONEXPLAYER 3: EC target value -> RPM
const RPM_TABLE: [number, number][] = [
  [0, 0],
  [15, 520],
  [20, 730],
  [30, 1120],
  [40, 1500],
  [70, 2430],
  [110, 3450],
  [160, 4460],
  [180, 4810],
  [184, 4900],
];

export const approxRpm = (target: number) => {
  if (target <= 10) return 0;
  for (let i = 1; i < RPM_TABLE.length; i++) {
    const [t1, r1] = RPM_TABLE[i];
    if (target <= t1) {
      const [t0, r0] = RPM_TABLE[i - 1];
      const rpm = r0 + ((r1 - r0) * (target - t0)) / (t1 - t0);
      return Math.round(rpm / 100) * 100;
    }
  }
  return RPM_TABLE[RPM_TABLE.length - 1][1];
};
