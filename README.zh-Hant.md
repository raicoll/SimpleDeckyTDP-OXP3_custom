# SimpleDeckyTDP for ONEXPLAYER 3 (CachyOS)

[English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md) | **繁體中文**

這是 Aarron Lee 的 [SimpleDeckyTDP](https://github.com/aarron-lee/SimpleDeckyTDP) 的個人分支。TDP、GPU 和 CPU 相關功能全部來自原專案，這個分支只加入了在 ONEXPLAYER 3 上使用 CachyOS 所需的部分。本分支與原專案無關，請不要把這個版本的問題回報到原專案。

為了在 OneXPlayer 3 上使用 CachyOS，我做了一些改動，現在分享原始碼和執行檔。

安裝好 Decky Loader 之後，執行以下指令即可安裝：

```bash
curl -L https://github.com/raicoll/SimpleDeckyTDP-OXP3_custom/raw/main/install.sh | bash
```

**在原版 SimpleDeckyTDP 之上加入的功能**

- TDP 調整整合
- 風扇轉速調整整合

**其他新增功能**

- 亮度和音量調整（快速設定面板已有這些功能，這裡也一併加入）
- 切換音效卡（同時使用多個 USB 音效裝置時切換更方便）

## 與原版的分別

- **風扇控制（僅限 ONEXPLAYER 3）。** TDP 滑桿下方有 靜音、自動、標準、最大 四段滑桿，並顯示目前轉速和大約的目標轉速。
  - 靜音：50°C 或以下時停止風扇，高於此溫度時以最低轉速運轉。
  - 自動：交由嵌入式控制器（EC）控制風扇。
  - 標準：依 CPU 溫度沿曲線調整（45°C 約 1100 RPM 到 82°C 約 4800 RPM）。轉速會逐步變化，減速時以最近 60 秒內的最高溫度為準，因為即使負載穩定，感測器數值也會上下跳動 3-4°C。所以在臨界溫度附近不會一直忽大聲忽小聲。
  - 最大：約 4700 RPM；80°C 以上會再提高（約 4800 RPM 或以上）。
  - 安全措施：目標值不會超過 180（此機型在 185 或以上會令風扇停轉），80°C 以上會把風扇調到最大，插件卸載時會把 EC 恢復為自動模式。
- **過熱時自動降低 TDP（可選）。** 溫度達到 80°C 時，會逐步降低 TDP 直到回到 75°C（不會低於你設定的下限），降到 72°C 後再慢慢恢復。長時間在 85-100°C 下使用時，USB-C 無線音訊接收器會反覆斷線；而降到 70°C 在高負載遊戲中犧牲太大，所以以 75°C 為目標。已儲存的設定檔不會改變，限制期間 TDP 滑桿會顯示實際套用的數值。
- **快速控制。** CPU 溫度和功耗、螢幕亮度、音量、靜音和輸出裝置，以圖示加滑桿同一行的精簡版面顯示。
- **顯示選項。** 可以分別顯示或隱藏 CPU 概要、亮度和音量、輸出裝置、TDP 控制及其詳情，也可以把 TDP 控制放在最上方，或把此插件的分頁移到快速存取選單頂部。
- **專用快速存取分頁**，位於 Decky 分頁正上方。
- **ONEXPLAYER 3 最高 TDP 40 W。** 韌體回報的是 25 W，所以原版插件的滑桿會停在 25 W。如要使用其他上限，請修改 `$HOME/homebrew/settings/SimpleDeckyTDP/settings.json` 中的 `INTEL_MAX_TDP_SETTING`。
- **翻譯**：英文、韓文、日文、簡體中文、繁體中文。
- **停用 OTA 更新**，避免原專案的更新意外覆蓋這個版本。

風扇控制、亮度和音訊功能不需要額外設定。風扇控制只會在 DMI 產品名稱完全等於 `ONEXPLAYER 3` 時啟用；在其他裝置上，除了快速控制之外，插件的行為與原版相同。

## ONEXPLAYER 3 注意事項

- `oxpec` 核心驅動程式暫時未支援此機型，所以透過 `ec_sys` 模組直接存取 ACPI EC 來控制風扇。插件會自行以 `write_support=1` 載入模組，不需要核心參數。風扇處於手動模式時，插件也會開啟 EC 的渦輪按鍵接管位元（暫存器 0xEB 的 0x40，與 `oxpec` 驅動程式在 OneXPlayer 2 和 X1 上使用的相同）；如果這個位元關閉，EC 會不斷以自己的曲線覆寫風扇轉速。
- 請不要同時使用 PowerTools 或其他 TDP 插件，請先在 Decky 中停用。如果已安裝 PowerTools，安裝指令碼會提示你。
- 如果 Handheld Daemon（HHD）或其他工具也在控制風扇，請關閉它們的風扇控制，避免同時操作 EC。
- 此機器的面板無法使用 Steam 內建的亮度滑桿，所以這裡加入了亮度滑桿。
- Steam 效能疊加層讀取的是 CPU 功耗感測器，所以不需要額外修補，就會反映此插件設定的 TDP。
- 在這裡切換輸出裝置時，Steam 的輸出裝置也會一併切換，所以機身音量鍵會調整你選擇的裝置。
- **已知問題：** 開機後約需 1 分鐘畫面才會出現。截至 2026 年 10 月 5 日，似乎仍沒有解決方法。

## 移除此分支

當原版 SimpleDeckyTDP 支援 ONEXPLAYER 3 之後，請刪除此版本，再從 Decky 商店安裝原版：

```bash
sudo rm -rf $HOME/homebrew/plugins/SimpleDeckyTDP
sudo systemctl restart plugin_loader.service
```

設定會保留在 `$HOME/homebrew/settings/SimpleDeckyTDP`，並與原版插件相容。

原版 SimpleDeckyTDP 的說明（英文）請見 [README.md](README.md#simpledeckytdp-original-readme)。
