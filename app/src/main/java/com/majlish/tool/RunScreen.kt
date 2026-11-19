package com.majlish.tool

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.os.Handler
import android.os.Looper
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import org.json.JSONObject

/** Full-screen glass panel that streams the engine log, shows progress and the final result. */
class RunScreen(
    private val act: MainActivity,
    private val t: GlassTheme,
    title: String
) {
    val view: LinearLayout = LinearLayout(act)
    private val statusView: TextView
    private val bar: GlassProgress
    private val logView: TextView
    private val scroll: ScrollView
    private val resultView: TextView
    private val button: TextView
    private val copyChip: TextView
    private val buf = StringBuilder()
    private val lock = Any()
    private var dirty = false
    private val ui = Handler(Looper.getMainLooper())

    @Volatile
    var running = true
        private set

    private val flusher = object : Runnable {
        override fun run() {
            if (dirty) {
                dirty = false
                render()
            }
            if (running) ui.postDelayed(this, 220)
        }
    }

    init {
        view.orientation = LinearLayout.VERTICAL
        view.background = Glass.surface(act, 38f, strong = true)
        view.setPadding(act.dp(20), act.dp(22), act.dp(20), act.dp(18))

        val head = LinearLayout(act)
        head.orientation = LinearLayout.HORIZONTAL
        head.gravity = Gravity.CENTER_VERTICAL
        head.addView(
            Glass.label(act, title.uppercase(), 23f, t.accent, bold = true, spacing = 0.02f),
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        )
        copyChip = Glass.label(act, "COPY LOG", 12f, t.accent, bold = true, spacing = 0.08f)
        copyChip.background = Glass.surface(act, 20f)
        copyChip.setPadding(act.dp(12), act.dp(8), act.dp(12), act.dp(8))
        copyChip.pressable()
        copyChip.setOnClickListener { copyLog() }
        head.addView(copyChip)
        view.addView(head)

        statusView = Glass.label(act, "Working... keep the app open", 14f, t.subText)
        statusView.setPadding(0, act.dp(8), 0, act.dp(10))
        view.addView(statusView)

        bar = GlassProgress(act, t)
        bar.setIndeterminate()
        view.addView(bar, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, act.dp(9)))

        val logCard = LinearLayout(act)
        logCard.background = Glass.surface(act, 24f)
        logCard.setPadding(act.dp(10), act.dp(10), act.dp(10), act.dp(10))
        scroll = ScrollView(act)
        scroll.isVerticalScrollBarEnabled = false
        logView = TextView(act)
        logView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 8f)
        logView.typeface = Typeface.MONOSPACE
        logView.setTextColor(t.text)
        scroll.addView(logView)
        logCard.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f)
        lp.topMargin = act.dp(14)
        view.addView(logCard, lp)

        resultView = Glass.label(act, "", 15f, t.text, bold = true)
        resultView.visibility = View.GONE
        resultView.setPadding(0, act.dp(12), 0, 0)
        view.addView(resultView)

        button = Glass.button(act, t, "PLEASE WAIT...", accent = true)
        button.alpha = 0.55f
        button.isEnabled = false
        val blp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        blp.topMargin = act.dp(14)
        view.addView(button, blp)
        button.setOnClickListener { act.closeRun() }
    }

    fun begin() {
        ui.postDelayed(flusher, 220)
    }

    fun append(s: String) {
        synchronized(lock) {
            buf.append(s).append('\n')
            if (buf.length > 40000) buf.delete(0, buf.length - 30000)
            dirty = true
        }
    }

    fun progress(done: Int, total: Int, label: String) {
        ui.post {
            if (total > 0) {
                bar.setFraction(done.toFloat() / total.toFloat())
                statusView.text = "$label   $done / $total"
            } else {
                statusView.text = label
            }
        }
    }

    private fun render() {
        val text = synchronized(lock) { buf.toString() }
        logView.text = text
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
    }

    private fun copyLog() {
        val text = synchronized(lock) { buf.toString() }
        val cm = act.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("MAJLISH log", text))
        Toast.makeText(act, "Log copied", Toast.LENGTH_SHORT).show()
    }

    fun finish(res: JSONObject) {
        running = false
        ui.removeCallbacks(flusher)
        render()
        val ok = res.optBoolean("ok", false)
        val msg = res.optString("message", "")
        val secs = res.optInt("seconds", 0)
        bar.setFraction(if (ok) 1f else 0f)
        statusView.text = if (ok) "Completed in ${secs}s" else "Stopped after ${secs}s"
        resultView.visibility = View.VISIBLE
        resultView.setTextColor(if (ok) Color.parseColor("#0F9D58") else Color.parseColor("#D92D20"))
        resultView.text = (if (ok) "✓  " else "✕  ") + msg
        button.text = "DONE"
        button.alpha = 1f
        button.isEnabled = true
    }
}
