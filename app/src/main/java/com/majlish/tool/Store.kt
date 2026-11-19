package com.majlish.tool

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Environment
import android.provider.Settings
import java.io.File

object Store {
    private fun prefs(c: Context) = c.getSharedPreferences("majlish", Context.MODE_PRIVATE)

    fun theme(c: Context): GlassTheme =
        Themes.byKey(prefs(c).getString("theme", Themes.DEFAULT_KEY))

    fun setTheme(c: Context, key: String) {
        prefs(c).edit().putString("theme", key).apply()
    }

    fun key(c: Context): String = prefs(c).getString("license_key", "") ?: ""

    fun expiry(c: Context): String = prefs(c).getString("license_expiry", "") ?: ""

    fun saveKey(c: Context, key: String, expiry: String) {
        prefs(c).edit().putString("license_key", key).putString("license_expiry", expiry).apply()
    }

    fun clearKey(c: Context) {
        prefs(c).edit().remove("license_key").remove("license_expiry").apply()
    }

    fun deviceId(c: Context): String {
        val id = try {
            Settings.Secure.getString(c.contentResolver, Settings.Secure.ANDROID_ID)
        } catch (e: Exception) {
            null
        }
        return "DEV-" + (id ?: "UNKNOWN")
    }

    fun deviceName(): String = (Build.MANUFACTURER + " " + Build.MODEL).trim()

    fun hasAllFiles(c: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= 30) {
            Environment.isExternalStorageManager()
        } else if (Build.VERSION.SDK_INT >= 23) {
            c.checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED
        } else {
            true
        }
    }

    /** Workspace folder (PAK, UNPACK, REPACK, RESULT ...). */
    fun baseDir(c: Context): File {
        return if (hasAllFiles(c)) {
            File(Environment.getExternalStorageDirectory(), "MAJLISH")
        } else {
            File(c.getExternalFilesDir(null) ?: c.filesDir, "MAJLISH")
        }
    }

    fun exportDir(): File =
        File(File(Environment.getExternalStorageDirectory(), "Download"), "MAJLISH")
}
