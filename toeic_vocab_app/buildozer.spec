name: TOEIC背单词
version: 1.0.0

# Buildozer 打包配置
# 用法: buildozer android debug

[app]
title = TOEIC背单词
package.name = toeicvocab
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf,txt
source.exclude_exts = spec
version.filename = %(source.dir)s/main.py
version.regex = __version__ = ['\"'](.*)['\"']
requirements = python3,kivy==2.2.1,kivymd==1.1.1,plyer,pyjnius,android,pillow
orientation = portrait
fullscreen = 0
android.presplash_color = #2E7D32

# API 级别
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.archs = arm64-v8a, armeabi-v7a

# 权限
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# 启动画面
android.presplash_lottie = 

[buildozer]
log_level = 2
warn_on_root = 1
