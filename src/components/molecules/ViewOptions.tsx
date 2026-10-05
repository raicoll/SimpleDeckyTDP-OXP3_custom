import { FC } from "react";
import { UiPrefs, setUiPref } from "../../hooks/useUiPrefs";
import ArrowToggleButton from "../atoms/ArrowToggleButton";
import ErrorBoundary from "../ErrorBoundary";
import { DeckyRow, DeckySection, DeckyToggle } from "../atoms/DeckyFrontendLib";
import t from "../../i18n/i18n";

// [pref, translation key, English fallback, ends a group]
const OPTIONS: [keyof UiPrefs, string, string, boolean][] = [
  ["tabOnTop", "VIEW_TAB_ON_TOP", "Show my tab at the top", false],
  ["showSummary", "VIEW_SHOW_SUMMARY", "Show CPU and TDP", true],
  ["showBrightnessVolume", "VIEW_SHOW_BRIGHTNESS_VOLUME", "Show brightness and volume", false],
  ["showAudioOutput", "VIEW_SHOW_AUDIO_OUTPUT", "Show output device", true],
  ["showTdp", "VIEW_SHOW_TDP", "Show TDP controls", false],
  ["showTdpDetails", "VIEW_SHOW_TDP_DETAILS", "Show TDP control details", false],
  ["tdpOnTop", "VIEW_TDP_ON_TOP", "Show TDP controls at the top", false],
];

const ViewOptions: FC<{ prefs: UiPrefs }> = ({ prefs }) => (
  <DeckySection title={t("VIEW_OPTIONS_TITLE", "View Options")}>
    <ErrorBoundary title="View Options">
      <ArrowToggleButton cacheKey="simpleDeckyTDP.viewOptionsButton">
        {OPTIONS.map(([key, tKey, fallback, endsGroup]) => (
          <DeckyRow key={key}>
            <DeckyToggle
              label={t(tKey, fallback)}
              checked={prefs[key]}
              disabled={
                (key === "showTdpDetails" || key === "tdpOnTop") && !prefs.showTdp
              }
              bottomSeparator={endsGroup ? "thick" : "none"}
              onChange={(v: boolean) => setUiPref(key, v)}
            />
          </DeckyRow>
        ))}
      </ArrowToggleButton>
    </ErrorBoundary>
  </DeckySection>
);

export default ViewOptions;
