# Android

Capacitor8.5.3 原生工程位于 native，三项 Capacitor 包同版本。F 接管并扩展设备权限、录音/文件选择、返回键和安全凭据。

复用本机 JDK21/Android SDK，Gradle8.14.3、AGP8.13.0、compile/target36，minSdk24（Android7+，只是构建下限，尚不代表所有版本实测）。运行 `others/scripts/Build-Android.ps1` 自动从本地配置设置当前进程环境；SDK路径保存在忽略的 native/local.properties，Gradle缓存位于本端 .gradle-user-home。

根目录首次运行 `pnpm --filter @safelab/android run init:native`；已存在 native 时跳过。运行 `pnpm run build:android` 同步共享调试网页并构建 native/app/build/outputs/apk/debug/app-debug.apk。

模拟器访问电脑服务使用 http://10.0.2.2:8000；调试网络仅允许 10.0.2.2、127.0.0.1、localhost。实体机可使用受信任 HTTPS 或 ADB 反向端口；实体机尚未验收。release 禁止 HTTP 与混合内容，签名和正式发布由 F 完成。

运行时连接统一后端；其他用户只安装发布包，不需要开发目录。
