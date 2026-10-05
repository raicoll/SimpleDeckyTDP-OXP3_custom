# SimpleDeckyTDP for ONEXPLAYER 3 (CachyOS)

[English](README.md) | **한국어** | [日本語](README.ja.md) | [繁體中文](README.zh-Hant.md)

Aarron Lee의 [SimpleDeckyTDP](https://github.com/aarron-lee/SimpleDeckyTDP)를 포크한 개인 저장소입니다. TDP, GPU, CPU 관련 기능은 모두 원본 프로젝트의 것이고, 이 포크는 ONEXPLAYER 3에서 CachyOS를 쓰기 위해 필요한 부분만 추가했습니다. 원본 프로젝트와는 관계가 없으니, 이 빌드의 문제는 원본 저장소에 올리지 말아 주세요.

OneXPlayer3에서 CachyOS를 쓰기 위해 몇 가지 작업을 진행했고, 그 소스와 바이너리를 공유합니다.

데키로더까지 설치된 후에, 아래 스크립트를 실행하여 설치하시면 됩니다.

```bash
curl -L https://github.com/raicoll/SimpleDeckyTDP-OXP3_custom/raw/main/install.sh | bash
```

**기존 SimpleDeckyTDP 소스로부터 추가 작업한 내용**

- TDP 조절 연동
- FAN 속도 조절 연동

**기타 추가 작업**

- 밝기 조절 및 볼륨 조절 (퀵 패널에 이미 있는 기능이지만, 이쪽에 추가하였습니다.)
- 사운드 카드 변경 (여러 개의 USB 사운드 장치를 쓸 때 조금 더 편하게 변경이 가능합니다)

## 원본과 달라진 점

- **팬 제어 (ONEXPLAYER 3 전용).** TDP 슬라이더 아래에 저소음, 자동, 표준, 최대 4단 슬라이더가 있고, 현재 RPM과 대략적인 목표 RPM을 보여줍니다.
  - 저소음: 50°C 이하에서는 팬을 멈추고, 그보다 높으면 최저 속도로 돌립니다.
  - 자동: 팬 제어를 임베디드 컨트롤러(EC)에 맡깁니다.
  - 표준: CPU 온도에 따라 곡선으로 조절합니다(45°C 약 1100 RPM부터 82°C 약 4800 RPM까지). 속도는 서서히 바뀌고, 느려질 때는 최근 60초 동안의 최고 온도를 기준으로 합니다. 부하가 일정해도 센서 값이 3~4°C씩 오르내리기 때문입니다. 그래서 경계 온도 근처에서 시끄러웠다 조용했다를 반복하지 않습니다.
  - 최대: 약 4700 RPM입니다. 80°C 이상이면 더 올립니다(약 4800 RPM 이상).
  - 안전장치: 목표값은 180을 넘지 않고(이 기종은 185 이상에서 팬이 멈춥니다), 80°C 이상이면 팬을 최대로 올리며, 플러그인이 내려가면 EC 자동 모드로 되돌립니다.
- **과열 시 TDP 자동 감소 (선택).** 80°C가 되면 75°C로 돌아올 때까지 TDP를 조금씩 낮추고(지정한 최저 한도 아래로는 내리지 않음), 72°C까지 식으면 천천히 다시 올립니다. 85~100°C로 오래 쓰면 USB-C 무선 오디오 동글 연결이 반복해서 끊겼고, 70°C까지 내리면 고사양 게임에서 손해가 너무 커서 75°C를 목표로 했습니다. 저장된 프로필은 바뀌지 않고, 제한 중에는 TDP 슬라이더에 실제 적용값이 표시됩니다.
- **빠른 제어.** CPU 온도와 전력, 화면 밝기, 볼륨, 음소거, 출력 장치를 아이콘과 슬라이더를 한 줄에 두는 간결한 레이아웃으로 보여줍니다.
- **상세 보기.** CPU 요약, 밝기와 볼륨, 출력 장치, TDP 제어와 그 상세 항목을 각각 켜고 끌 수 있고, TDP 제어를 위에 두거나 이 플러그인 탭을 퀵 메뉴 맨 위로 옮길 수 있습니다.
- **전용 퀵 메뉴 탭**이 Decky 탭 바로 위에 생깁니다.
- **ONEXPLAYER 3 최대 TDP 40 W.** 펌웨어가 25 W로 알려주기 때문에 원본 플러그인에서는 슬라이더가 25 W에서 멈춥니다. 다른 한도를 쓰려면 `$HOME/homebrew/settings/SimpleDeckyTDP/settings.json`의 `INTEL_MAX_TDP_SETTING`을 바꾸세요.
- **번역**: 영어, 한국어, 일본어, 중국어 간체, 중국어 번체.
- **OTA 업데이트 비활성화.** 원본 프로젝트의 업데이트가 이 빌드를 실수로 덮어쓰지 않도록 했습니다.

팬 제어, 밝기, 오디오 기능은 별도 설정 없이 동작합니다. 팬 제어는 DMI 제품명이 정확히 `ONEXPLAYER 3`일 때만 켜지고, 다른 기기에서는 빠른 제어를 빼면 원본과 같이 동작합니다.

## ONEXPLAYER 3 참고 사항

- `oxpec` 커널 드라이버가 아직 이 기종을 지원하지 않아서, `ec_sys` 모듈로 ACPI EC에 직접 접근해 팬을 제어합니다. 플러그인이 `write_support=1`로 모듈을 직접 불러오므로 커널 파라미터는 필요 없습니다. 팬이 수동 모드일 때는 EC의 터보 버튼 인계 비트(레지스터 0xEB의 0x40, `oxpec` 드라이버가 OneXPlayer 2·X1에서 쓰는 것과 같음)도 켭니다. 이 비트가 꺼져 있으면 EC가 자기 곡선으로 팬 속도를 계속 덮어씁니다.
- PowerTools 등 다른 TDP 플러그인과 함께 쓰지 마세요. Decky에서 먼저 꺼 주세요. PowerTools가 설치되어 있으면 설치 스크립트가 알려줍니다.
- Handheld Daemon(HHD) 등 다른 도구도 팬을 제어한다면, 그쪽 팬 제어를 꺼서 EC를 두고 충돌하지 않게 해 주세요.
- 이 기기의 패널에서는 Steam 기본 밝기 슬라이더가 동작하지 않아서 밝기 슬라이더를 넣었습니다.
- Steam 성능 오버레이는 CPU 전력 센서 값을 읽기 때문에, 별도 패치 없이 이 플러그인이 설정한 TDP가 반영됩니다.
- 여기서 출력 장치를 바꾸면 Steam의 출력 장치도 함께 바뀌어서, 본체 볼륨 버튼이 고른 장치의 볼륨을 조절합니다.
- **알려진 문제:** 부팅 후 화면이 나오기까지 약 1분 정도 걸립니다. 2026년 10월 5일 현재 아직 해결 방법이 없는 것으로 보입니다.

## 이 포크 제거하기

원본 SimpleDeckyTDP가 ONEXPLAYER 3를 지원하게 되면, 이 빌드를 지우고 Decky 스토어에서 원본을 설치하세요.

```bash
sudo rm -rf $HOME/homebrew/plugins/SimpleDeckyTDP
sudo systemctl restart plugin_loader.service
```

설정은 `$HOME/homebrew/settings/SimpleDeckyTDP`에 남고, 원본 플러그인과 호환됩니다.

원본 SimpleDeckyTDP 설명서(영어)는 [README.md](README.md#simpledeckytdp-original-readme)에 있습니다.
