MAJLISH - Android (AndroidIDE) project
======================================
Open this folder in AndroidIDE -> Gradle sync -> Build APK.

Versions: AGP 7.3.1 | Gradle 7.4.2 | Kotlin 1.7.10 | Chaquopy 14.0.2
          compileSdk 33 | targetSdk 33 | minSdk 21 | Java 11 | Python 3.11

Python code  : app/src/main/python
  majlish_core.py  your APP.py engine (PAK / repack / inject / protect / Lua) - terminal screens removed
  bridge.py        glue between the app UI and the engine
  majlish_auth.py  key login (panel URL is at the top of this file)

Workspace folders (created automatically):
  <Internal storage>/MAJLISH/PAK            -> .pak files for UNPACK
  <Internal storage>/MAJLISH/UNPACK/<pak>/edited  -> your edited files for REPACK
  <Internal storage>/MAJLISH/PAK TOOL/PAK   -> .pak files for INJECT / PROTECT
  <Internal storage>/MAJLISH/PAK TOOL/EDIT  -> files to inject
  <Internal storage>/MAJLISH/RESULT, PAK TOOL/RESULT -> outputs
  <Internal storage>/MAJLISH/LUA TOOL/...   -> Lua_org, Lua_Decript, EDIT_LUA, Lua_Rueslt


BUILD FIX
---------
The Gradle plugins are now loaded using the legacy buildscript/apply syntax,
which is more compatible with older AndroidIDE versions. The Chaquopy Python
configuration was also corrected: Chaquopy 14.0.2 uses the python { } block
inside android.defaultConfig, not the newer chaquopy { } block. The Android
Gradle Plugin, Kotlin plugin, Chaquopy plugin, Gradle wrapper, SDK levels,
Java and Python versions remain at the versions listed above.

IMPORTANT:
1. Extract the ZIP.
2. In AndroidIDE, open/import the MAJLISH folder (the folder containing
   settings.gradle and the root build.gradle), not the ZIP preview and not
   the inner app folder.
3. Allow Gradle sync to finish, then build the APK.
