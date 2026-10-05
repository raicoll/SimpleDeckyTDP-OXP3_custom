import { useTdpRange } from "../../hooks/useTdpRange";
import { useSetTdp } from "../../hooks/useTdpProfiles";
import { useSelector } from "react-redux";
import { getCurrentTdpInfoSelector } from "../../redux-modules/settingsSlice";
import ErrorBoundary from "../ErrorBoundary";
import { DeckyRow, DeckySlider } from "../atoms/DeckyFrontendLib";
import t from '../../i18n/i18n';
import { useOxp3Fan } from "../../hooks/useOxp3Fan";

export const TdpSlider = ({ disabled = false }: { disabled?: boolean }) => {
  const [minTdp, maxTdp] = useTdpRange();
  const setTdp = useSetTdp();
  const { tdp } = useSelector(getCurrentTdpInfoSelector);
  // ONEXPLAYER 3: show the TDP actually applied while the overheat limiter caps it
  const { status: fan } = useOxp3Fan();
  const actualTdp =
    fan?.supported && fan.tdpCap != null ? fan.tdpActual : null;
  const actualText =
    actualTdp != null && actualTdp !== tdp
      ? ` (${t("TDP_ACTUAL", "now {tdp}W").replace("{tdp}", `${actualTdp}`)})`
      : "";

  return (
    <DeckyRow>
      <ErrorBoundary title="TDP Slider">
        <DeckySlider
          value={tdp}
          label={t('TDP_SLIDER_LABEL', 'TDP (Watts)') + actualText}
          min={minTdp}
          max={maxTdp}
          step={1}
          disabled={disabled}
          onChange={(newTdp) => setTdp(newTdp)}
          notchTicksVisible
          showValue
        />
      </ErrorBoundary>
    </DeckyRow>
  );
};
