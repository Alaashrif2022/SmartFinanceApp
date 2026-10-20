[app]
title = Smart Finance
package.name = smartfinance
package.domain = org.smartfinance
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy
orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.9.1
fullscreen = 0

# Android specific configurations
android.api = 31
android.minapi = 21
android.sdk_accept_licenses = True
android.ndk = 25b
android.skip_update = False
android.permissions = INTERNET
