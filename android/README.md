# Android

Capacitor8.5.3 原生工程位于 native，三项 Capacitor 包同版本。F 接管并扩展设备权限、录音/文件选择、返回键和安全凭据。

复用本机 JDK21/Android SDK，Gradle8.14.3、AGP8.13.0、compile/target36，minSdk24（Android7+，只是构建下限，尚不代表所有版本实测）。运行 `others/scripts/Build-Android.ps1` 自动从本地配置设置当前进程环境；SDK路径保存在忽略的 native/local.properties，Gradle缓存位于本端 .gradle-user-home。

根目录首次运行 `pnpm --filter @safelab/android run init:native`；已存在 native 时跳过。运行 `pnpm run build:android` 同步共享调试网页并构建 native/app/build/outputs/apk/debug/app-debug.apk。

模拟器访问电脑服务使用 http://10.0.2.2:8000；调试网络仅允许 10.0.2.2、127.0.0.1、localhost。实体机可使用受信任 HTTPS 或 ADB 反向端口；实体机尚未验收。release 禁止 HTTP 与混合内容，签名和正式发布由 F 完成。

运行时连接统一后端；其他用户只安装发布包，不需要开发目录。

## A1 本机模拟器复验

本机手动体验：双击本目录 `Open-Emulator.cmd`。它会打开可见的 SafeLab_API36 窗口，等待开机、安装已有调试 APK 并启动安研通；电脑后端需保持运行。登录学校代码 demo-a，账号 teacher/student/admin，密码从忽略的 others/runtime/demo-accounts.json 取得。模拟器服务地址填写 http://10.0.2.2:8000。

也可在项目根目录执行 `./android/scripts/Start-Emulator.ps1`。脚本不会重新下载镜像或构建 APK；缺失时会提示先准备。下方 `-no-window` 命令专供无窗口自动化测试；如已有无窗口实例，先按文末命令停止，再双击启动文件显示窗口。

已安装并验证 Google 官方 Android16/API36 Google APIs x86_64 **r07**，SHA1 `c6bf44bdcd885bb902b4ba752d111a073ad7a817`。原始来源：https://dl.google.com/android/repository/sys-img/google_apis/x86_64-36_r07.zip 。镜像位于 D:/AndroidSDK/system-images/android-36/google_apis/x86_64，AVD 数据留本端忽略区；均不进入源码包。

在仓库根目录另开 PowerShell，设置仅对当前进程生效的路径。若 AVD 尚不存在，先使用已装 SDK 的 avdmanager 创建；不覆盖现有 AVD：

~~~powershell
. ./others/scripts/Use-ProjectEnvironment.ps1
$env:ANDROID_USER_HOME=Join-Path (Get-Location) 'android/.android-home'
$env:ANDROID_AVD_HOME=Join-Path (Get-Location) 'android/.avd'
# 仅首次且镜像已安装时：
# 'no' | & "$env:ANDROID_SDK_ROOT/cmdline-tools/22.0/bin/avdmanager.bat" create avd --name SafeLab_API36 --package 'system-images;android-36;google_apis;x86_64' --device pixel_6 --path (Join-Path $env:ANDROID_AVD_HOME 'SafeLab_API36.avd')
Start-Process -FilePath "$env:ANDROID_SDK_ROOT/emulator/emulator.exe" -WindowStyle Hidden -ArgumentList '-avd SafeLab_API36 -port 5556 -no-window -no-audio -no-snapshot -gpu swiftshader -memory 1536 -cores 2 -no-boot-anim'
adb -s emulator-5556 shell getprop sys.boot_completed
~~~

确认返回1后测试。首次开机可能需要等待系统与网络完成初始化。后端8000及网页5173须已运行，先执行 Windows 测试生成 windows-test.json，再执行 `pnpm --filter @safelab/android run test`。该测试实际安装 APK、操作原生 WebView、验证 Windows课程读取、网页双向同步、原生触摸退出和学生权限，检查原生无弹窗遮挡并截图。结果位于 others/reports/a1。

停止自己启动的模拟器可运行 `adb -s emulator-5556 emu kill`，AVD 数据保留。物理设备可以设置 ANDROID_SERIAL 选择，但本轮只报告上述模拟器通过。

`./others/scripts/Build-Android.ps1 -Release` 会重新构建并同步生产网页。A1 额外构建了未签名 release 并核对包内 cleartext/mixedContent 及合并 Manifest 的 debuggable 均关闭；签名和正式发布仍由 F 完成。
