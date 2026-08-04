"""Built-in bloatware package (cannot be uninstalled in Android itself) configuration for Android filters."""

BLOATWARE_XIAOMI = (
    "com.android.browser", # Xiaomi Browser / 小米浏览器（国内版）
    "com.mi.globalbrowser", # Xiaomi Browser / 小米浏览器（国际版）
    "com.miui.analytics", # Xiaomi Analytics (cannot uninstall without root) / 小米分析（无法彻底删除）
    "com.miui.hybrid*", # Xiaomi Hybrid Framework / 小米快应用框架
    "com.miui.nextpay", # Xiaomi NextPay / 小米支付
    "com.miui.player", # Xiaomi Music / 小米音乐
    "com.miui.systemAdSolution", # Xiaomi System Ad Solution / 小米系统广告解决方案
    "com.miui.video", # Xiaomi Video / 小米视频
    "com.xiaomi.gamecenter", # Xiaomi Game Center / 小米游戏中心
    "com.xiaomi.glgm", # Xiaomi Game Center / 小米游戏中心
    "com.xiaomi.joyose", # Xiaomi Joyose / 小米游戏服务
    "com.xiaomi.shop", # Xiaomi Store / 小米商城
    "com.xiaomi.youpin", # Xiaomi Youpin / 小米有品
)

BLOATWARE_PACKAGE_PATTERNS: tuple[str, ...] = (
    "com.baidu.input_mi",
    "com.facebook.appmanager",
    "com.facebook.katana",
    "com.facebook.services",
    "com.facebook.system",
    "com.google.android.apps.magazines",
    "com.google.android.apps.tachyon",
    "com.google.android.videos",
    "com.heytap.browser",
    "com.heytap.cloud",
    "com.heytap.market",
    "com.huawei.appmarket",
    "com.huawei.fastapp*",
    "com.oppo.market",
    "com.samsung.android.game.gamehome",
    "com.tencent.soter.soterserver",
    "com.vivo.browser",
    "com.vivo.hybrid*",
    *BLOATWARE_XIAOMI
)
