import { useEffect, useState } from "react";
import { setSetting } from "../backend/utils";

// What the panel shows, kept per device in localStorage.
export type UiPrefs = {
  tabOnTop: boolean;
  showSummary: boolean;
  showBrightnessVolume: boolean;
  showAudioOutput: boolean;
  showTdp: boolean;
  showTdpDetails: boolean;
  tdpOnTop: boolean;
};

const STORAGE_KEY = "simpleDeckyTDP.uiPrefs";

const DEFAULTS: UiPrefs = {
  tabOnTop: true,
  showSummary: true,
  showBrightnessVolume: true,
  showAudioOutput: true,
  showTdp: true,
  showTdpDetails: false,
  tdpOnTop: false,
};

const SETTINGS_KEY = "uiPrefs";

const listeners = new Set<(p: UiPrefs) => void>();
let cached: UiPrefs | null = null;

const readLocal = (): Partial<UiPrefs> => {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
};

export const getUiPrefs = (): UiPrefs => {
  if (!cached) cached = { ...DEFAULTS, ...readLocal() };
  return cached;
};

// The plugin settings file is the durable copy (localStorage can be lost
// when Steam restarts); call this with the settings loaded at startup.
export const loadUiPrefs = (saved: unknown) => {
  if (!saved || typeof saved !== "object") return;
  cached = { ...DEFAULTS, ...(saved as Partial<UiPrefs>) };
  listeners.forEach((fn) => fn(cached as UiPrefs));
};

export const setUiPref = <K extends keyof UiPrefs>(key: K, value: UiPrefs[K]) => {
  const next = { ...getUiPrefs(), [key]: value };
  cached = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch (e) {
    console.error(e);
  }
  setSetting({ name: SETTINGS_KEY, value: next });
  listeners.forEach((fn) => fn(next));
};

export const useUiPrefs = () => {
  const [prefs, setPrefs] = useState<UiPrefs>(getUiPrefs);

  useEffect(() => {
    listeners.add(setPrefs);
    return () => {
      listeners.delete(setPrefs);
    };
  }, []);

  return prefs;
};
