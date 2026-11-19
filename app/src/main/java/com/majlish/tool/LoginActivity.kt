package com.majlish.tool

import android.app.Activity
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject

class LoginActivity : Activity() {
    private lateinit var t: GlassTheme
    private lateinit var keyField: EditText
    private lateinit var statusView: TextView
    private lateinit var loginButton: TextView
    private lateinit var pasteChip: TextView
    private val progress by lazy { GlassProgress(this, t) }
    private var busy = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        t = Store.theme(this)
        buildUi()
        val saved = Store.key(this)
        if (saved.isNotEmpty()) {
            keyField.setText(saved)
            verify(saved, silent = true)
        }
    }

    private fun buildUi() {
        val root = FrameLayout(this)
        root.addView(AuroraView(this, t), ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)

        val scroll = ScrollView(this)
        scroll.isFillViewport = true
        scroll.isVerticalScrollBarEnabled = false
        val col = LinearLayout(this)
        col.orientation = LinearLayout.VERTICAL
        col.gravity = Gravity.CENTER_HORIZONTAL
        col.setPadding(dp(22), dp(40), dp(22), dp(32))
        scroll.addView(col, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        val spacerTop = View(this)
        col.addView(spacerTop, LinearLayout.LayoutParams(1, 0, 1f))

        // logo with glass ring
        val ring = FrameLayout(this)
        ring.background = Glass.surface(this, 38f, strong = true)
        ring.setPadding(dp(8), dp(8), dp(8), dp(8))
        val logo = Glass.roundedImage(this, R.drawable.logo, 104, 30f)
        ring.addView(logo, FrameLayout.LayoutParams(dp(104), dp(104)))
        col.addView(ring, LinearLayout.LayoutParams(dp(120), dp(120)))

        val title = Glass.label(this, "MAJLISH", 38f, t.accent, bold = true, spacing = 0.06f)
        title.setPadding(0, dp(20), 0, dp(6))
        col.addView(title)
        col.addView(Glass.label(this, "GAMING TOOL CONTROL PANEL", 13.5f, t.subText, bold = true, spacing = 0.08f))

        // glass login card
        val card = LinearLayout(this)
        card.orientation = LinearLayout.VERTICAL
        card.background = Glass.surface(this, 40f, strong = true)
        card.setPadding(dp(22), dp(24), dp(22), dp(22))
        val clp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        clp.topMargin = dp(34)
        col.addView(card, clp)

        card.addView(Glass.label(this, "LICENSE LOGIN", 20f, t.accent, bold = true, spacing = 0.03f))
        val hint = Glass.label(this, "Paste your key to unlock the tool", 15f, t.subText)
        hint.setPadding(0, dp(6), 0, dp(16))
        card.addView(hint)

        val field = LinearLayout(this)
        field.orientation = LinearLayout.HORIZONTAL
        field.gravity = Gravity.CENTER_VERTICAL
        field.background = Glass.surface(this, 32f)
        field.setPadding(dp(18), dp(4), dp(8), dp(4))
        keyField = EditText(this)
        keyField.background = null
        keyField.hint = "Enter license key"
        keyField.setHintTextColor(withAlpha(t.text, 110))
        keyField.setTextColor(t.text)
        keyField.textSize = 16f
        keyField.isSingleLine = true
        keyField.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS or
            InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
        field.addView(keyField, LinearLayout.LayoutParams(0, dp(54), 1f))
        pasteChip = Glass.label(this, "PASTE", 12.5f, t.accent, bold = true, spacing = 0.08f)
        pasteChip.background = Glass.surface(this, 22f)
        pasteChip.setPadding(dp(14), dp(10), dp(14), dp(10))
        pasteChip.pressable()
        pasteChip.setOnClickListener { pasteFromClipboard() }
        field.addView(pasteChip)
        card.addView(field)

        loginButton = Glass.button(this, t, "LOGIN", accent = true)
        loginButton.setOnClickListener { doLogin() }
        val blp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        blp.topMargin = dp(18)
        card.addView(loginButton, blp)

        card.addView(progress, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(6)).also { it.topMargin = dp(16) })
        progress.visibility = View.INVISIBLE

        statusView = Glass.label(this, "", 14f, t.subText, bold = true)
        statusView.gravity = Gravity.CENTER
        statusView.setPadding(0, dp(12), 0, 0)
        card.addView(statusView)

        val spacerBottom = View(this)
        col.addView(spacerBottom, LinearLayout.LayoutParams(1, 0, 1f))

        root.addView(scroll, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        setContentView(root)
        edgeToEdge(scroll)
    }

    private fun pasteFromClipboard() {
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = cm.primaryClip
        if (clip != null && clip.itemCount > 0) {
            val txt = clip.getItemAt(0).coerceToText(this)?.toString()?.trim() ?: ""
            if (txt.isNotEmpty()) {
                keyField.setText(txt)
                keyField.setSelection(txt.length)
                return
            }
        }
        setStatus("Clipboard is empty", error = true)
    }

    private fun doLogin() {
        if (busy) return
        val key = keyField.text.toString().trim().trim('`', '"', '\'')
        if (key.isEmpty()) {
            setStatus("ACCESS DENIED - NO KEY ENTERED", error = true)
            return
        }
        val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
        imm.hideSoftInputFromWindow(keyField.windowToken, 0)
        verify(key, silent = false)
    }

    private fun setBusy(on: Boolean) {
        busy = on
        loginButton.alpha = if (on) 0.6f else 1f
        loginButton.text = if (on) "CHECKING..." else "LOGIN"
        keyField.isEnabled = !on
        progress.visibility = if (on) View.VISIBLE else View.INVISIBLE
        if (on) progress.setIndeterminate()
    }

    private fun setStatus(msg: String, error: Boolean) {
        statusView.text = msg
        statusView.setTextColor(if (error) Color.parseColor("#D92D20") else t.subText)
    }

    private fun verify(key: String, silent: Boolean) {
        setBusy(true)
        setStatus(if (silent) "Verifying license..." else "Connecting to license panel...", error = false)
        Thread {
            val res: JSONObject = try {
                Engine.verify(this, key)
            } catch (e: Throwable) {
                JSONObject().put("ok", false).put("reason", (e.message ?: e.toString()).take(120).uppercase())
            }
            runOnUiThread {
                setBusy(false)
                if (res.optBoolean("ok", false)) {
                    Store.saveKey(this, res.optString("key", key), res.optString("expiry", ""))
                    setStatus("ACCESS GRANTED", error = false)
                    startActivity(Intent(this, MainActivity::class.java))
                    finish()
                } else {
                    val reason = res.optString("reason", "ACCESS DENIED")
                    if (!res.optBoolean("network", false)) Store.clearKey(this)
                    setStatus("ACCESS DENIED - $reason", error = true)
                }
            }
        }.start()
    }
}
