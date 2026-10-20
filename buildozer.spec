[app]

# (str) Title of your application
title = Smart Finance

# (str) Package name
package.name = smartfinance

# (str) Package domain (needed for android packaging)
package.domain = org.smartfinance

# (str) Source files where the include files are located
source.dir = .

# (list) Source files to include (let empty to include all files)
source.include_exts = py,png,jpg,kv,atlas

# (str) Application versioning
version = 0.1

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy

# (str) Supported orientations
orientation = portrait

# (list) List of permissions
android.permissions = INTERNET

# (int) Target Android API, should be as high as possible.
android.api = 31

# (int) Minimum API your APK will support.
android.minapi = 21

# (bool) Skip / Do not update Android SDK
android.skip_update = False

# (str) Android NDK version to use
android.ndk = 25b

# (bool) Automatically accept SDK license
android.sdk_accept_licenses = True

# (list) Supported architectures
android.archs = armeabi-v7a

# (bool) Indicate whether the screen should stay on
# fullscreen = 0
