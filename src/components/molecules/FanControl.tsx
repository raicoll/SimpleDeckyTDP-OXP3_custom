import { FC, useEffect, useRef, useState } from "react";
import { approxRpm, useOxp3Fan } from "../../hooks/useOxp3Fan";
import { Oxp3FanStatus } from "../../backend/utils";
import ErrorBoundary from "../ErrorBoundary";
import {
  DeckyRow,
  DeckySlider,
  DeckyToggle,
  NotchLabel,
} from "../atoms/DeckyFrontendLib";
import t from "../../i18n/i18n";

// slider notches, left to right: [backend mode, manual target]
const NOTCHES: [Oxp3FanStatus["mode"], number | null][] = [
  ["silent", null],
  ["auto", null],
  ["standard", null],
  ["manual", 175],
];

const notchIndex = (st: Oxp3FanStatus) => {
  if (st.mode === "silent") return 0;
  if (st.mode === "auto") return 1;
  if (st.mode === "standard") return 2;
  return st.target >= 150 ? 3 : 2;
};

// Moving the slider passes through other modes (e.g. Quiet -> Auto -> Max).
// Send only the position it settles on, so the EC is not toggled between
// auto and manual on every notch.
const SEND_DELAY_MS = 700;

const rpmText = (target: number) => `${approxRpm(target)} RPM (${target})`;

const targetText = (st: Oxp3FanStatus) => {
  if (st.emergency) {
    const target = Math.min(180, st.ceiling);
    return `~${rpmText(target)} · ${t("FAN_EMERGENCY", "high temperature protection")}`;
  }
  if (st.mode === "auto") return t("FAN_TARGET_AUTO", "set by the EC");
  if (st.mode === "silent") {
    return st.silentForced
      ? `~${rpmText(20)} · ${t("FAN_SILENT_WARM", "warm, lowest speed")}`
      : `${rpmText(0)} · ${t("FAN_SILENT_COOL", "silent at 50°C or below")}`;
  }
  if (st.mode === "standard") {
    const curve = t("FAN_STANDARD_CURVE", "follows CPU temperature");
    return st.ecTarget == null ? curve : `~${rpmText(st.ecTarget)} · ${curve}`;
  }
  return `~${rpmText(st.target)}`;
};

const statusNote = (st: Oxp3FanStatus) => {
  if (!st.available)
    return t("FAN_UNAVAILABLE", "Fan control unavailable (check ec_sys)");
  if (st.tdpCap != null)
    return t("FAN_TDP_CAPPED", "Overheating: TDP limited to {cap}W").replace(
      "{cap}",
      `${st.tdpCap}`
    );
  return null;
};

export const FanControl: FC<{ showOptions?: boolean }> = ({
  showOptions = true,
}) => {
  const { status: st, setMode, setOptions } = useOxp3Fan();
  const [pending, setPending] = useState<number | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => () => clearTimeout(timer.current), []);

  if (!st || !st.supported) return null;

  const notchLabels: NotchLabel[] = [
    t("FAN_MODE_SILENT", "Quiet"),
    t("FAN_MODE_AUTO", "Auto"),
    t("FAN_MODE_STANDARD", "Standard"),
    t("FAN_MODE_MAX", "Max"),
  ].map((label, i) => ({ notchIndex: i, value: i, label }));

  const label =
    `${t("FAN_SPEED_LABEL", "Fan")}` + (st.rpm == null ? "" : ` · ${st.rpm} RPM`);
  const note = statusNote(st);

  return (
    <ErrorBoundary title="Fan Control">
      <DeckyRow>
        <DeckySlider
          label={label}
          description={
            <>
              <div>
                {t("FAN_TARGET", "Target")}: {targetText(st)}
              </div>
              {note && <div>{note}</div>}
            </>
          }
          value={pending ?? notchIndex(st)}
          min={0}
          max={NOTCHES.length - 1}
          step={1}
          notchCount={NOTCHES.length}
          notchLabels={notchLabels}
          notchTicksVisible
          showValue={false}
          disabled={!st.available}
          bottomSeparator="none"
          onChange={(v: number) => {
            setPending(v);
            clearTimeout(timer.current);
            timer.current = setTimeout(() => {
              const [mode, target] = NOTCHES[v];
              setMode(mode, target).then(() => setPending(null));
            }, SEND_DELAY_MS);
          }}
        />
      </DeckyRow>
      {showOptions && (
        <>
          <DeckyRow>
            <DeckyToggle
              label={t("FAN_TDP_LIMITER", "Lower TDP when overheating")}
              description={t(
                "FAN_TDP_LIMITER_DESC",
                "Above 85°C, lower TDP step by step and restore it once cool"
              )}
              checked={st.tdpLimiter}
              onChange={(v: boolean) => setOptions(v, null)}
              bottomSeparator="none"
            />
          </DeckyRow>
          {st.tdpLimiter && (
            <DeckyRow>
              <DeckySlider
                label={t("FAN_TDP_FLOOR", "Lowest TDP")}
                value={st.tdpFloor}
                min={5}
                max={30}
                step={1}
                showValue
                valueSuffix="W"
                bottomSeparator="none"
                onChange={(v: number) => setOptions(null, v)}
              />
            </DeckyRow>
          )}
        </>
      )}
    </ErrorBoundary>
  );
};

export default FanControl;
