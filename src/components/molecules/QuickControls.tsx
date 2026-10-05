import { FC, ReactNode, useEffect, useRef, useState } from "react";
import { useQuickAccessVisible } from "@decky/ui";
import { MdBrightnessMedium, MdVolumeOff, MdVolumeUp } from "react-icons/md";
import {
  QuickState,
  getQuickState,
  setAudioOutput,
  setBrightness,
  setMute,
  setVolume,
  syncSteamAudioOutput,
} from "../../backend/utils";
import { UiPrefs } from "../../hooks/useUiPrefs";
import ErrorBoundary from "../ErrorBoundary";
import {
  DeckyDropdown,
  DeckyField,
  DeckyRow,
  DeckySection,
  DeckySlider,
  DeckyToggle,
} from "../atoms/DeckyFrontendLib";
import t from "../../i18n/i18n";

const POLL_MS = 2000;
// ignore polled values for a moment after the user touched a control
const TOUCH_GRACE_MS = 1500;

const EMPTY: QuickState = {
  temp: null,
  power: null,
  brightness: null,
  volume: 0,
  muted: false,
  sink: "",
  sinks: [],
};

// Steam quick settings style: icon, slider, value on one line.
// The QAM gives slider rows a 270px min-width, which would push the slider
// under the value, so let everything inside the slider column shrink.
const INLINE_SLIDER_CSS = ".sdtdp-inline-slider * { min-width: 0 !important; }";

const InlineSlider: FC<{
  icon: JSX.Element;
  value: number;
  min: number;
  onChange: (v: number) => void;
}> = ({ icon, value, min, onChange }) => (
  <DeckyRow>
    <div style={{ display: "flex", alignItems: "center" }}>
      <div className="sdtdp-inline-slider" style={{ flex: 1, minWidth: 0 }}>
        <DeckySlider
          icon={icon}
          value={value}
          min={min}
          max={100}
          step={1}
          showValue={false}
          bottomSeparator="none"
          onChange={onChange}
        />
      </div>
      <div style={{ width: "3em", textAlign: "right", flexShrink: 0 }}>
        {value}
      </div>
    </div>
  </DeckyRow>
);

export const cpuSummaryText = (st: QuickState) => {
  if (st.temp == null) return "-";
  return st.power == null ? `${st.temp}°C` : `${st.temp}°C (${st.power}W)`;
};

// The CPU summary always comes first; the TDP controls go right under it
// or after the brightness / audio rows ("Show TDP controls at the top").
const QuickControls: FC<{ prefs: UiPrefs; tdpControls: ReactNode }> = ({
  prefs,
  tdpControls,
}) => {
  const visible = useQuickAccessVisible();
  const [st, setSt] = useState<QuickState>(EMPTY);
  const touched = useRef(0);

  useEffect(() => {
    if (!visible) return;
    const refresh = () =>
      getQuickState()
        .then((s) => {
          if (!s) return;
          setSt((old) =>
            Date.now() - touched.current > TOUCH_GRACE_MS
              ? s
              : { ...old, temp: s.temp, power: s.power }
          );
        })
        .catch(() => {});
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [visible]);

  const touch = (patch: Partial<QuickState>) => {
    touched.current = Date.now();
    setSt((s) => ({ ...s, ...patch }));
  };

  const { showSummary, showBrightnessVolume, showAudioOutput, tdpOnTop } =
    prefs;

  return (
    <ErrorBoundary title="Quick Controls">
      <style>{INLINE_SLIDER_CSS}</style>
      {showSummary && (
        <DeckySection title={t("QUICK_SUMMARY_TITLE", "Summary")}>
          <DeckyRow>
            <DeckyField label="CPU" bottomSeparator="none">
              {cpuSummaryText(st)}
            </DeckyField>
          </DeckyRow>
        </DeckySection>
      )}
      {tdpOnTop && tdpControls}
      {(showBrightnessVolume || showAudioOutput) && (
        <DeckySection>
          {showBrightnessVolume && (
            <>
              {st.brightness != null && (
                <InlineSlider
                  icon={<MdBrightnessMedium />}
                  value={st.brightness}
                  min={1}
                  onChange={(v: number) => {
                    touch({ brightness: v });
                    setBrightness(v);
                  }}
                />
              )}
              <InlineSlider
                icon={st.muted ? <MdVolumeOff /> : <MdVolumeUp />}
                value={st.volume}
                min={0}
                onChange={(v: number) => {
                  touch(v > 0 ? { volume: v, muted: false } : { volume: v });
                  setVolume(v);
                }}
              />
              <DeckyRow>
                <DeckyToggle
                  label={t("QUICK_MUTE", "Mute")}
                  checked={st.muted}
                  bottomSeparator={showAudioOutput ? "standard" : "none"}
                  onChange={(v: boolean) => {
                    touch({ muted: v });
                    setMute(v);
                  }}
                />
              </DeckyRow>
            </>
          )}
          {showAudioOutput && st.sinks.length > 0 && (
            <DeckyRow>
              <DeckyDropdown
                label={t("QUICK_AUDIO_OUTPUT", "Output device")}
                rgOptions={st.sinks.map((s) => ({ data: s.name, label: s.label }))}
                selectedOption={st.sink}
                bottomSeparator="none"
                onChange={(o: { data: string }) => {
                  touch({ sink: o.data });
                  const sink = st.sinks.find((s) => s.name === o.data);
                  setAudioOutput(o.data)
                    .then((ok) => (ok && sink ? syncSteamAudioOutput(sink) : undefined))
                    .catch((e) => console.error("[SimpleDeckyTDP] audio output", e));
                }}
              />
            </DeckyRow>
          )}
        </DeckySection>
      )}
      {!tdpOnTop && tdpControls}
    </ErrorBoundary>
  );
};

export default QuickControls;
