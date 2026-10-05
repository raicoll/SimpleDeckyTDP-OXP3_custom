import { definePlugin } from "@decky/api";
import { BsCpuFill } from "react-icons/bs";
import { getSettings, setValuesForGameId } from "./backend/utils";
import { store } from "./redux-modules/store";
import {
  acPowerEventListener,
  currentGameInfoListener,
  resumeFromSuspendEventListener,
  suspendEventListener,
} from "./steamListeners";
import { updateInitialLoad } from "./redux-modules/settingsSlice";

import { cleanupAction } from "./redux-modules/extraActions";

import { fetchPowerControlInfo } from "./redux-modules/thunks";
import AppContainer from "./App";
import { initializePollingStore } from "./redux-modules/pollingMiddleware";
import { getUiPrefs, loadUiPrefs } from "./hooks/useUiPrefs";

// Own Quick Access tab (instead of only an entry in Decky's list), placed
// right above Decky's tab or at the very top ("Show my tab at the top").
const TAB_ID = "sdtdp-qam-tab";
const DECKY_TAB_KEY = 999;

const addQuickAccessTab = () => {
  const hook = (window as any).DeckyPluginLoader?.tabsHook;
  if (!hook) return () => {};
  const origRender = hook.render.bind(hook);
  try {
    hook.removeById(TAB_ID);
    hook.add({
      id: TAB_ID,
      title: <div>SimpleDeckyTDP</div>,
      icon: <BsCpuFill />,
      content: <AppContainer />,
    });
    hook.render = (tabs: any[], visible: boolean) => {
      // Decky re-adds all of its tabs whenever the number of decky tabs in
      // Steam's array differs from its own list, so tabs left behind by an
      // unloaded plugin make every render append another copy. Drop stale
      // and duplicate decky tabs first.
      const ids = new Set(hook.tabs.map((t: any) => t.id));
      const seen = new Set();
      for (let i = 0; i < tabs.length; i++) {
        const t = tabs[i];
        if (!t?.decky) continue;
        if (!ids.has(t.key) || seen.has(t.key)) {
          tabs.splice(i--, 1);
        } else {
          seen.add(t.key);
        }
      }
      origRender(tabs, visible);
      const mine = tabs.findIndex((x) => x && x.key === TAB_ID);
      if (mine < 0) return;
      const [tab] = tabs.splice(mine, 1);
      const deck = tabs.findIndex((x) => x && x.key === DECKY_TAB_KEY);
      const at = getUiPrefs().tabOnTop ? 0 : deck >= 0 ? deck : tabs.length;
      tabs.splice(at, 0, tab);
    };
  } catch (e) {
    console.error("[SimpleDeckyTDP] could not add the Quick Access tab", e);
  }
  return () => {
    try {
      hook.removeById(TAB_ID);
      hook.render = origRender;
    } catch (e) {
      console.error(e);
    }
  };
};

export default definePlugin(() => {
  initializePollingStore(store);

  // fetch settings from backend, send into redux state
  getSettings().then((result) => {
    const results = (result || {}) as Record<string, unknown>;
    loadUiPrefs(results.uiPrefs);

    store.dispatch(
      updateInitialLoad({
        ...results,
      }),
    );
    store.dispatch(fetchPowerControlInfo());

    setTimeout(() => {
      setValuesForGameId({ gameId: "default" });
    }, 0);
  });

  const removeQuickAccessTab = addQuickAccessTab();
  const unregisterCurrentGameListener = currentGameInfoListener();
  const unregisterResumeListener = resumeFromSuspendEventListener();
  const unregisterSuspendListener = suspendEventListener();

  let unregisterAcPowerListener: (() => void) | undefined;

  acPowerEventListener().then((unregister) => {
    unregisterAcPowerListener = unregister;
  });

  return {
    name: "SimpleDeckyTDP",
    content: <AppContainer />,
    icon: <BsCpuFill />,
    onDismount: () => {
      try {
        removeQuickAccessTab();
        store.dispatch(cleanupAction());
        // if (unpatch) unpatch();
        if (unregisterCurrentGameListener) unregisterCurrentGameListener();
        if (
          unregisterAcPowerListener &&
          typeof unregisterAcPowerListener === "function"
        )
          unregisterAcPowerListener();
        if (
          unregisterSuspendListener &&
          typeof unregisterSuspendListener === "function"
        )
          unregisterSuspendListener();
        if (
          unregisterResumeListener &&
          typeof unregisterResumeListener === "function"
        )
          unregisterResumeListener();
      } catch (e) {
        console.error(e);
      }
    },
  };
});
