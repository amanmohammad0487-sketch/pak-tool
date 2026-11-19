package com.majlish.tool

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import org.json.JSONObject

class MainActivity : Activity() {
    private lateinit var t: GlassTheme
    private lateinit var rootFrame: FrameLayout
    private lateinit var content: FrameLayout
    private lateinit var overlay: OverlayHost
    private lateinit var statusTitle: TextView
    private lateinit var statusSub: TextView

    private var runScreen: RunScreen? = null
    private var askedPermission = false
    private var engineBase: String? = null
    private var engineError: String? = null
    private var engineReady = false

    private class Entry(val num: String, val title: String, val sub: String, val action: () -> Unit)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Store.key(this).isEmpty()) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }
        t = Store.theme(this)
        buildUi()
        ensureEngine()
    }

    override fun onResume() {
        super.onResume()
        if (!::t.isInitialized) return
        ensureEngine()
        refreshStatus()
        if (!askedPermission && !Store.hasAllFiles(this)) {
            askedPermission = true
            overlay.confirm(
                "ALLOW FILE ACCESS",
                "MAJLISH keeps its folders (PAK, UNPACK, REPACK, RESULT...) in:\n\n" +
                    "Internal storage / MAJLISH\n\n" +
                    "Allow file access so you can drop .pak files there and export results.",
                "ALLOW", "LATER"
            ) { requestStorage() }
        }
    }

    // ------------------------------------------------------------------ UI
    private fun buildUi() {
        rootFrame = FrameLayout(this)
        content = FrameLayout(this)
        content.addView(AuroraView(this, t), ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)

        val scroll = ScrollView(this)
        scroll.isVerticalScrollBarEnabled = false
        scroll.clipToPadding = false
        val col = LinearLayout(this)
        col.orientation = LinearLayout.VERTICAL
        col.setPadding(dp(16), dp(14), dp(16), dp(30))
        scroll.addView(col, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        content.addView(scroll, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        rootFrame.addView(content, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        setContentView(rootFrame)
        edgeToEdge(scroll)
        overlay = OverlayHost(this, rootFrame, content, t)

        // header
        val header = LinearLayout(this)
        header.orientation = LinearLayout.HORIZONTAL
        header.gravity = Gravity.CENTER_VERTICAL
        header.background = Glass.surface(this, 44f)
        header.setPadding(dp(14), dp(14), dp(16), dp(14))
        header.addView(Glass.roundedImage(this, R.drawable.logo, 72, 22f))
        val titles = LinearLayout(this)
        titles.orientation = LinearLayout.VERTICAL
        titles.setPadding(dp(16), 0, 0, 0)
        titles.addView(Glass.label(this, "MAJLISH", 34f, t.accent, bold = true))
        val tag = Glass.label(this, "GAMING TOOL CONTROL PANEL", 12.5f, t.subText, bold = true, spacing = 0.02f)
        tag.setPadding(0, dp(4), 0, 0)
        titles.addView(tag)
        header.addView(titles, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        val settings = FrameLayout(this)
        settings.background = Glass.surface(this, 40f)
        settings.addView(SlidersIcon(this, t.text), FrameLayout.LayoutParams(dp(30), dp(30), Gravity.CENTER))
        settings.pressable()
        settings.setOnClickListener { showSettings() }
        header.addView(settings, LinearLayout.LayoutParams(dp(54), dp(54)))
        col.addView(header)

        // status card
        val status = LinearLayout(this)
        status.orientation = LinearLayout.VERTICAL
        status.background = Glass.surface(this, 38f)
        status.setPadding(dp(26), dp(20), dp(26), dp(20))
        statusTitle = Glass.label(this, "●  SYSTEM READY", 17f, t.accent, bold = true, spacing = 0.02f)
        statusSub = Glass.label(this, "License panel connected  •  Android edition", 15f, t.subText)
        statusSub.setPadding(0, dp(8), 0, 0)
        status.addView(statusTitle)
        status.addView(statusSub)
        status.pressable()
        status.setOnClickListener { onStatusTap() }
        val slp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        slp.topMargin = dp(14)
        col.addView(status, slp)

        section(col, "PAK OPERATIONS")
        val pak = listOf(
            Entry("01", "UNPACK PAK", "Extract files from a selected .pak") { doUnpack() },
            Entry("02", "REPACK PAK", "Rebuild an unpacked PAK from its edited folder") { doRepack() },
            Entry("03", "REPACK TO PATH", "Repack edited files into a chosen PAK path") { doRepackToPath() },
            Entry("04", "CUSTOM FILE / INJECT", "Add or replace files using a selected folder") { doInject() },
            Entry("05", "PROTECT PAK", "Run the existing PAK protection workflow") { doProtect() },
            Entry("06", "DELETE FOLDER", "Remove a workspace folder") { doDelete() },
            Entry("07", "EXPORT RESULT", "Save a generated PAK to phone storage") { doExport() }
        )
        for (e in pak) col.addView(menuCard(e))

        section(col, "LUA BYTECODE CONVERSION")
        col.addView(menuCard(Entry("08", "LUA UTILITIES", "Convert game Lua bytecode both ways") { doLua() }))

    }

    private fun section(col: LinearLayout, text: String) {
        val tv = Glass.label(this, text, 16f, t.accent, bold = true, spacing = 0.03f)
        tv.setPadding(dp(8), dp(24), 0, dp(10))
        col.addView(tv)
    }

    private fun menuCard(e: Entry): LinearLayout {
        val card = LinearLayout(this)
        card.orientation = LinearLayout.HORIZONTAL
        card.gravity = Gravity.CENTER_VERTICAL
        card.background = Glass.surface(this, 38f)
        card.setPadding(dp(16), dp(16), dp(20), dp(16))

        val tile = TextView(this)
        tile.text = e.num
        tile.gravity = Gravity.CENTER
        tile.setTextColor(t.accent)
        tile.setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, 21f)
        tile.typeface = android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.BOLD)
        tile.background = Glass.surface(this, 22f)
        card.addView(tile, LinearLayout.LayoutParams(dp(58), dp(58)))

        val col = LinearLayout(this)
        col.orientation = LinearLayout.VERTICAL
        col.setPadding(dp(18), 0, dp(8), 0)
        col.addView(Glass.label(this, e.title, 20f, t.text, bold = true))
        val sub = Glass.label(this, e.sub, 14.5f, t.subText)
        sub.setPadding(0, dp(5), 0, 0)
        col.addView(sub)
        card.addView(col, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))

        card.addView(Glass.label(this, "❯", 26f, t.accent, bold = true))
        card.pressable()
        card.setOnClickListener { e.action() }
        val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        lp.bottomMargin = dp(14)
        card.layoutParams = lp
        return card
    }

    private fun refreshStatus() {
        if (!::statusTitle.isInitialized) return
        val err = engineError
        when {
            err != null -> {
                statusTitle.text = "●  ENGINE ERROR"
                statusSub.text = err.take(90)
            }
            !Store.hasAllFiles(this) -> {
                statusTitle.text = "●  FILE ACCESS NEEDED"
                statusSub.text = "Tap here to allow storage access"
            }
            else -> {
                statusTitle.text = "●  SYSTEM READY"
                statusSub.text = "License panel connected  •  Android edition"
            }
        }
    }

    private fun onStatusTap() {
        if (!Store.hasAllFiles(this)) requestStorage()
        else Toast.makeText(this, "Workspace: " + Store.baseDir(this).absolutePath, Toast.LENGTH_LONG).show()
    }

    // ------------------------------------------------------------------ permissions / engine
    private fun requestStorage() {
        if (Build.VERSION.SDK_INT >= 30) {
            try {
                startActivity(
                    Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$packageName"))
                )
            } catch (e: Exception) {
                startActivity(Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION))
            }
        } else if (Build.VERSION.SDK_INT >= 23) {
            requestPermissions(
                arrayOf(
                    android.Manifest.permission.READ_EXTERNAL_STORAGE,
                    android.Manifest.permission.WRITE_EXTERNAL_STORAGE
                ), 7
            )
        }
    }

    private fun ensureEngine() {
        val base = Store.baseDir(this).absolutePath
        if (engineBase == base) return
        engineBase = base
        engineReady = false
        Engine.async {
            try {
                Engine.init(this, base)
                engineError = null
                engineReady = true
            } catch (e: Throwable) {
                engineError = e.message ?: e.toString()
                engineBase = null
            }
            runOnUiThread { refreshStatus() }
        }
    }

    private fun basePath(): String = Store.baseDir(this).absolutePath

    // ------------------------------------------------------------------ settings
    private fun showSettings() {
        overlay.choices(
            "SETTINGS", "MAJLISH control panel",
            listOf(
                Row("CHANGE UI", "Current: " + t.title),
                Row("LOG OUT", "Remove the saved key"),
                Row("EXIT TOOL", "Close MAJLISH", danger = true)
            ), "CANCEL"
        ) { i ->
            when (i) {
                0 -> showThemes()
                1 -> overlay.confirm("LOG OUT", "You will need to paste your key again.", "LOG OUT", danger = true) {
                    Store.clearKey(this)
                    val login = Intent(this, LoginActivity::class.java)
                    login.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK)
                    startActivity(login)
                    finish()
                }
                2 -> finishAffinity()
            }
        }
    }

    private fun showThemes() {
        val rows = Themes.all.map { Row(it.title, null, it.dotA, it.dotB, checked = it.key == t.key) }
        overlay.choices("CHANGE UI", "Choose a liquid glass style", rows, "CANCEL") { i ->
            Store.setTheme(this, Themes.all[i].key)
            recreate()
        }
    }

    // ------------------------------------------------------------------ list helper
    private fun withList(kind: String, onResult: (List<Item>) -> Unit) {
        overlay.loading("SCANNING FOLDERS...")
        Engine.async {
            val items: List<Item> = try {
                Engine.list(this, kind)
            } catch (e: Throwable) {
                emptyList()
            }
            runOnUiThread {
                overlay.dismiss()
                onResult(items)
            }
        }
    }

    private fun pickItem(
        kind: String, title: String, sub: String, emptyHint: String,
        onPick: (Item) -> Unit
    ) {
        withList(kind) { items ->
            if (items.isEmpty()) {
                overlay.message("NOTHING FOUND", emptyHint)
            } else {
                overlay.choices(title, sub, items.map { Row(it.name, it.detail) }) { i -> onPick(items[i]) }
            }
        }
    }

    // ------------------------------------------------------------------ operations
    private fun doUnpack() {
        pickItem(
            "pak", "UNPACK PAK", "Select a .pak from your PAK folder",
            "No .pak files found.\n\nPut your .pak files in:\n${basePath()}/PAK\n\nthen open this option again."
        ) { item ->
            runTask("UNPACK PAK", "unpack", JSONObject().put("pak_path", item.path))
        }
    }

    private fun doRepack() {
        pickItem(
            "unpack", "REPACK PAK", "Select an unpacked PAK",
            "No unpacked folders found.\n\nUse UNPACK PAK first, then place your edited files in UNPACK/<pak>/edited/."
        ) { item ->
            overlay.choices(
                "PATH MODE", "How should edited files be matched?",
                listOf(
                    Row("FOLDER-WISE", "edited/ keeps the full in-pak folder path"),
                    Row("INDEX.CSV AUTO", "Drop files only - path found from EXE/index.csv")
                ), "CANCEL"
            ) { m ->
                runTask(
                    "REPACK PAK", "repack",
                    JSONObject().put("unpack_name", item.name).put("mode", if (m == 0) "1" else "2")
                )
            }
        }
    }

    private fun doRepackToPath() {
        pickItem(
            "unpack", "REPACK TO PATH", "Select an unpacked PAK",
            "No unpacked folders found.\n\nUse UNPACK PAK first."
        ) { item ->
            overlay.input(
                "TARGET PATH", "Folder inside the PAK where the files go",
                "Content/Lua/GameLua/...", "START"
            ) { path ->
                runTask(
                    "REPACK TO PATH", "repack_to_path",
                    JSONObject().put("unpack_name", item.name).put("target", path)
                )
            }
        }
    }

    private fun doInject() {
        pickItem(
            "toolpak", "CUSTOM FILE / INJECT", "Select the .pak to inject into",
            "No .pak files found.\n\nPut the .pak in:\n${basePath()}/PAK TOOL/PAK\n\nand your files (with their in-pak paths) in:\n${basePath()}/PAK TOOL/EDIT"
        ) { item ->
            overlay.choices(
                "ENCRYPT FILES?", "Encrypt injected files with SM4",
                listOf(
                    Row("YES - ENCRYPT", "Game-native encryption (recommended)"),
                    Row("NO - PRESERVE ORIGINAL", "Keep existing files’ encryption settings; new files stay plain")
                ), "CANCEL"
            ) { e ->
                runTask(
                    "CUSTOM FILE / INJECT", "inject",
                    JSONObject().put("pak_path", item.path).put("encrypt", e == 0)
                )
            }
        }
    }

    private fun doProtect() {
        pickItem(
            "toolpak", "PROTECT PAK", "Select the .pak to protect",
            "No .pak files found.\n\nPut the .pak in:\n${basePath()}/PAK TOOL/PAK"
        ) { item ->
            overlay.confirm(
                "START PROTECT?",
                "Re-encrypts every file with game-native SM4. The output keeps the same file name and is saved in PAK TOOL/RESULT. " +
                    "Large paks can take a long time - keep the app open.",
                "START"
            ) {
                runTask("PROTECT PAK", "protect", JSONObject().put("pak_path", item.path))
            }
        }
    }

    private fun doDelete() {
        pickItem(
            "folders", "DELETE FOLDER", "Select a workspace folder to remove",
            "No removable folders found in UNPACK or REPACK."
        ) { item ->
            overlay.confirm("DELETE FOLDER", "Delete ${item.name} (${item.detail})? This cannot be undone.", "DELETE", danger = true) {
                runTask("DELETE FOLDER", "delete", JSONObject().put("folder_path", item.path))
            }
        }
    }

    private fun doExport() {
        if (!Store.hasAllFiles(this)) {
            overlay.confirm(
                "FILE ACCESS NEEDED",
                "Allow file access to save results into Downloads/MAJLISH.", "ALLOW", "LATER"
            ) { requestStorage() }
            return
        }
        pickItem(
            "result", "EXPORT RESULT", "Select a generated PAK to save",
            "No generated PAKs yet.\n\nRun REPACK, INJECT or PROTECT first."
        ) { item ->
            runTask(
                "EXPORT RESULT", "export",
                JSONObject().put("src_path", item.path).put("dest_dir", Store.exportDir().absolutePath)
            )
        }
    }

    private fun doLua() {
        overlay.choices(
            "LUA UTILITIES", "Lua bytecode conversion",
            listOf(
                Row("GAME LUA → STANDARD", "Lua_org  →  Lua_Decript (.luac)"),
                Row("STANDARD → GAME LUA", "EDIT_LUA (.luac)  →  Lua_Rueslt (.lua)")
            ), "CANCEL"
        ) { which ->
            val kind = if (which == 0) "lua_org" else "lua_edit"
            val folder = if (which == 0) "Lua_org" else "EDIT_LUA"
            withList(kind) { items ->
                if (items.isEmpty()) {
                    overlay.message("NOTHING FOUND", "No .lua / .luac files found.\n\nPut them in:\n${basePath()}/LUA TOOL/$folder")
                } else {
                    val rows = ArrayList<Row>()
                    rows.add(Row("ALL FILES", "${items.size} file(s)"))
                    for (entry in items) rows.add(Row(entry.name, entry.detail))
                    overlay.choices("SELECT FILES", "From $folder", rows) { i ->
                        val paths = org.json.JSONArray()
                        if (i == 0) items.forEach { paths.put(it.path) } else paths.put(items[i - 1].path)
                        runTask(
                            "LUA UTILITIES", if (which == 0) "lua_to_standard" else "lua_to_game",
                            JSONObject().put("paths", paths)
                        )
                    }
                }
            }
        }
    }

    // ------------------------------------------------------------------ run a task with the log screen
    private fun runTask(title: String, task: String, args: JSONObject) {
        val rs = RunScreen(this, t, title)
        runScreen = rs
        overlay.show(rs.view, cancelable = false, full = true)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        rs.begin()
        val sink = Sink({ s -> rs.append(s) }, { d, tt, l -> rs.progress(d, tt, l) })
        Engine.async {
            val res: JSONObject = try {
                Engine.run(this, task, args, sink)
            } catch (e: Throwable) {
                JSONObject().put("ok", false).put("message", e.message ?: e.toString()).put("seconds", 0)
            }
            runOnUiThread {
                rs.finish(res)
                window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            }
        }
    }

    fun closeRun() {
        runScreen = null
        overlay.dismiss()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        val rs = runScreen
        when {
            rs != null && rs.running ->
                Toast.makeText(this, "Task is running - please wait until it finishes", Toast.LENGTH_SHORT).show()
            rs != null -> closeRun()
            ::overlay.isInitialized && overlay.isShowing() -> overlay.dismiss()
            else -> super.onBackPressed()
        }
    }
}
