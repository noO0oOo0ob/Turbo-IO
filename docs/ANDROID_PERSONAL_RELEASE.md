# Android 个人完整版：GUARD-07 + TAP1-TEST-01

此包包括 Android 1.0.5（201）完整 Turbo IO 插件，以及指定眼镜实验固件。
APK 沿用已有 Unofficial-IO-Android 构建的包名、版本、名称和签名。
构建脚本拒绝签名不一致的输出；目标是保留应用数据覆盖安装、沿用绑定。
这是与本地旧 APK 的一致性校验，仍需在实际手机确认覆盖安装和重连。

## 文件与安装

- `TurboIO-RayNeo-1.0.5_201-GUARD07-personal.apk`：完整手机插件及官方 OTA 接入。
- `TurboIO-TAP1-TEST-01.zip`：固定眼镜 OTA 包，不要解压或重新压缩。
- `SHA256SUMS.txt`：执行 `shasum -a 256 -c SHA256SUMS.txt` 校验整个目录。
- `build-report.json`、`guarded-package-audit.json`、`build.log`：构建、签名及内容校验证据。

手机最低 Android 10、arm64。配套眼镜为雷鸟 iO / Strix OS 1.0.4.12。
若版本不同，停止，不能修改白名单或越过升级保护。

在手机覆盖安装此个人 APK，或用 ADB 执行：

```sh
adb install --no-incremental -r /absolute/path/TurboIO-RayNeo-1.0.5_201-GUARD07-personal.apk
```

不要先卸载、清除应用数据、解绑或重置眼镜。若签名冲突，停止并核对实际
已安装包的签名，不用卸载解决。安装后先确认官方登录、已有眼镜连接正常。

## 在 App 里升级眼镜

实验固件可能导致无法启动、失去 OTA 或设备损坏，不能保证回滚救砖。
眼镜电量至少 50%；手机保持前台亮屏、供电和稳定蓝牙。先结束录音、
全天智记、语音、导航、音乐、阅读和提词。升级期间不要退出、断连或重启。

1. 将配套 ZIP 原样传到手机。打开 **Turbo IO → 实验固件升级 · 默认锁定**，
   确认页面显示 **GUARD-07 · 预检有效期2分钟**。
2. 点 **开启 15 分钟官方只下载**，选择 ZIP；返回官方 App，进入
   **眼镜 → 设置 → 关于本机 → Strix OS / 眼镜软件版本**。
3. 检查更新，确认说明含 **TAP1-TEST-01**，完成下载和准备。出现
   **开始安装** 后先停下，不点击。
4. 回 Turbo IO 做 **只读预检**；官方目录须 **15/15** 校验通过，版本、
   电量和空闲通过，空间由官方最终检查，不能绕过。
5. 点 **校验目录并允许一次试刷**，输入 `TAP1-TEST-01`；确认
   **授权：1 / ARMED**，返回官方页，点 **开始安装一次**。
6. 等眼镜自然重启回首页，检查菜单 **显示TEST**。手机上的传输百分比
   不代表眼镜安装完成，版本号仍为 1.0.4.12 也不代表失败。
7. 回插件升级页底部，点 **已自然回首页：允许只读回查**，等待同一眼镜
   新的版本/空闲回执；检查镜片正常后点 **已检查显示TEST：解除结果保护**。
8. 最终应为 **LOCKED / 授权0 / 结果保护未开始**，再验官方功能和新应用。

第7步必须完成，否则官方语音、录音、字幕等可能继续被保护机制拦截。
更新中、黑屏或状态不明时，不解除保护、不重刷、不解绑或清数据。
详细异常处理见上游 `android-addon/docs/INSTALL_AND_FLASH.md`。

## 完整版范围与仍需自备的部分

已包含模型/Tools/TTS、导航、音乐、TXT阅读、番茄、仪表盘、四槽小应用、
20个离线模板、新闻、云端字幕、录音导出、后台任务和指定官方流程 OTA。
配套固件提供原生菜单/应用页、图形卡片与四槽运行时。

- 模型、TinyFish、地图、书架和字幕服务需要自己的配置或 Key；刷机本身
  不需要这些 Key。云端字幕默认地址为空，不能只填任意语音服务就认为协议兼容。
- 本机 TTS 需要已安装的中文离线音色和蓝牙媒体音频路由；没有离线翻译。
- 阅读正文支持 UTF-8 TXT，网页正文适配、Cookie入口和 EPUB 未包含。
- 模板是离线快照，真实 MCP 数据源自行在服务端接入；没有自动后台刷新。
- 滴滴菜单属于沙箱展示，Android 没有完整真实叫车功能。
- 当前 APK/固件不包含 Watch 遥控或 TLC1 全天智记共存修复；不能混刷其固件。
- 你原 Unofficial-IO-Android 的 MiniMax ASR、意图路由、Paseo/CatPaw会话桥接
  属于额外个人定制，尚未迁入此上游完整版。

## 从源码重建

先按上游要求安装 JDK、Node、Python 3.11+、apktool 和 Android SDK 36，
并在 `dashboard-service` 执行 `uv sync --locked`。从仓库根运行：

```sh
export ANDROID_SDK_ROOT=/absolute/path/to/Android/sdk
dashboard-service/.venv/bin/python android-addon/build-personal-release.py \
  --stock-apk /absolute/path/RayNeo_AI_1.0.5_201.apk \
  --firmware /absolute/path/TurboIO-TAP1-TEST-01.zip \
  --previous-apk /absolute/path/your-current-signed.apk \
  --output /absolute/path/new-bundle-directory
```

默认使用本机 `~/.android/debug.keystore` 与标准 Android debug alias/password，
也可通过 `ANDROID_DEBUG_KEYSTORE`、`TURBOIO_KEY_ALIAS`、
`TURBOIO_STORE_PASSWORD`、`TURBOIO_KEY_PASSWORD` 配置现有密钥。
Key、签名密钥、APK和个人配置不提交到 Git；构建脚本不安装或刷机。
