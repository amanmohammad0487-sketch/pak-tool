package com.majlish.tool

import android.app.Activity
import android.graphics.Color
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView

class Row(
    val title: String,
    val sub: String? = null,
    val dotA: Int? = null,
    val dotB: Int? = null,
    val checked: Boolean = false,
    val danger: Boolean = false
)

/** Shows liquid-glass dialogs on top of the activity and blurs the content underneath (Android 12+). */
class OverlayHost(
    private val act: Activity,
    private val root: FrameLayout,
    private val blurTarget: View,
    private val t: GlassTheme
) {
    private var current: View? = null
    private var onDismissed: (() -> Unit)? = null

    fun isShowing(): Boolean = current != null

    fun dismiss() {
        val v = current ?: return
        current = null
        root.removeView(v)
        unblur()
        val cb = onDismissed
        onDismissed = null
        cb?.invoke()
    }

    private fun blur() {
        if (Build.VERSION.SDK_INT >= 31) {
            blurTarget.setRenderEffect(RenderEffect.createBlurEffect(26f, 26f, Shader.TileMode.CLAMP))
        }
    }

    private fun unblur() {
        if (Build.VERSION.SDK_INT >= 31) {
            blurTarget.setRenderEffect(null)
        }
    }

    @Suppress("DEPRECATION")
    /** Puts [panel] in a dim scrim. [full] = stretch to the whole screen (log screen). */
    fun show(panel: View, cancelable: Boolean = true, full: Boolean = false, closed: (() -> Unit)? = null) {
        if (current != null) {
            root.removeView(current)
            current = null
            onDismissed = null
        }
        val scrim = FrameLayout(act)
        scrim.setBackgroundColor(Color.argb(95, 14, 22, 44))
        scrim.isClickable = true
        if (cancelable) scrim.setOnClickListener { dismiss() }
        panel.isClickable = true
        val lp = FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            if (full) ViewGroup.LayoutParams.MATCH_PARENT else ViewGroup.LayoutParams.WRAP_CONTENT,
            Gravity.CENTER
        )
        val m = act.dp(if (full) 12 else 18)
        lp.setMargins(m, act.dp(14), m, act.dp(14))
        scrim.addView(panel, lp)
        scrim.setOnApplyWindowInsetsListener { v, insets ->
            v.setPadding(0, insets.systemWindowInsetTop, 0, insets.systemWindowInsetBottom)
            insets
        }
        root.addView(scrim, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        scrim.requestApplyInsets()
        current = scrim
        onDismissed = closed
        blur()
        panel.alpha = 0f
        panel.scaleX = 0.93f
        panel.scaleY = 0.93f
        panel.animate().alpha(1f).scaleX(1f).scaleY(1f).setDuration(180).start()
    }

    private fun card(): LinearLayout {
        val c = LinearLayout(act)
        c.orientation = LinearLayout.VERTICAL
        c.background = Glass.surface(act, 38f, strong = true)
        c.setPadding(act.dp(22), act.dp(24), act.dp(22), act.dp(22))
        return c
    }

    private fun heading(c: LinearLayout, title: String, sub: String?) {
        c.addView(Glass.label(act, title.uppercase(), 25f, t.accent, bold = true, spacing = 0.02f))
        if (!sub.isNullOrEmpty()) {
            val s = Glass.label(act, sub, 16f, t.subText)
            s.setPadding(0, act.dp(6), 0, 0)
            c.addView(s)
        }
        val gap = View(act)
        c.addView(gap, LinearLayout.LayoutParams(1, act.dp(16)))
    }

    private fun rowView(r: Row, onClick: () -> Unit): View {
        val box = LinearLayout(act)
        box.orientation = LinearLayout.HORIZONTAL
        box.gravity = Gravity.CENTER_VERTICAL
        box.background = Glass.surface(act, 34f)
        box.setPadding(act.dp(18), act.dp(14), act.dp(18), act.dp(14))
        if (r.dotA != null && r.dotB != null) {
            val dot = View(act)
            dot.background = Glass.circle(r.dotA, r.dotB)
            box.addView(dot, LinearLayout.LayoutParams(act.dp(38), act.dp(38)).also { it.rightMargin = act.dp(16) })
        }
        val col = LinearLayout(act)
        col.orientation = LinearLayout.VERTICAL
        val titleColor = if (r.danger) Color.parseColor("#D92D20") else t.text
        col.addView(Glass.label(act, r.title, 18f, titleColor, bold = true))
        if (!r.sub.isNullOrEmpty()) {
            val s = Glass.label(act, r.sub, 13.5f, t.subText)
            s.setPadding(0, act.dp(3), 0, 0)
            col.addView(s)
        }
        box.addView(col, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        if (r.checked) {
            box.addView(Glass.label(act, "✓", 26f, t.accent, bold = true))
        }
        box.pressable()
        box.setOnClickListener { onClick() }
        return box
    }

    private fun gap(h: Int): View {
        val v = View(act)
        v.layoutParams = LinearLayout.LayoutParams(1, act.dp(h))
        return v
    }

    /** List of options. Picking one closes the dialog and calls [onPick] with its index. */
    fun choices(
        title: String, sub: String?, rows: List<Row>,
        cancelLabel: String = "CANCEL", onPick: (Int) -> Unit
    ) {
        val c = card()
        heading(c, title, sub)
        val maxH = (act.resources.displayMetrics.heightPixels * 0.52f).toInt()
        val sv = MaxHeightScrollView(act, maxH)
        sv.isVerticalScrollBarEnabled = false
        val list = LinearLayout(act)
        list.orientation = LinearLayout.VERTICAL
        rows.forEachIndexed { i, r ->
            list.addView(rowView(r) {
                dismiss()
                onPick(i)
            })
            list.addView(gap(10))
        }
        sv.addView(list)
        c.addView(sv)
        val cancel = Glass.button(act, t, cancelLabel, accent = false)
        cancel.setOnClickListener { dismiss() }
        c.addView(cancel)
        show(c)
    }

    fun message(title: String, message: String, buttonLabel: String = "OK") {
        val c = card()
        heading(c, title, null)
        c.addView(Glass.label(act, message, 16f, t.text))
        c.addView(gap(18))
        val b = Glass.button(act, t, buttonLabel, accent = true)
        b.setOnClickListener { dismiss() }
        c.addView(b)
        show(c)
    }

    fun confirm(
        title: String, message: String, okLabel: String, cancelLabel: String = "CANCEL",
        danger: Boolean = false, onOk: () -> Unit
    ) {
        val c = card()
        heading(c, title, null)
        c.addView(Glass.label(act, message, 16f, t.text))
        c.addView(gap(18))
        val ok = Glass.button(act, t, okLabel, accent = !danger, danger = danger)
        ok.setOnClickListener {
            dismiss()
            onOk()
        }
        c.addView(ok)
        c.addView(gap(10))
        val cancel = Glass.button(act, t, cancelLabel, accent = false)
        cancel.setOnClickListener { dismiss() }
        c.addView(cancel)
        show(c)
    }

    fun input(
        title: String, sub: String?, hint: String, okLabel: String,
        onOk: (String) -> Unit
    ) {
        val c = card()
        heading(c, title, sub)
        val field = LinearLayout(act)
        field.background = Glass.surface(act, 30f)
        field.setPadding(act.dp(18), act.dp(4), act.dp(18), act.dp(4))
        val et = EditText(act)
        et.background = null
        et.hint = hint
        et.setHintTextColor(withAlpha(t.text, 110))
        et.setTextColor(t.text)
        et.textSize = 16f
        et.isSingleLine = true
        et.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS or
            InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
        field.addView(et, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, act.dp(52)))
        c.addView(field)
        c.addView(gap(18))
        val ok = Glass.button(act, t, okLabel, accent = true)
        ok.setOnClickListener {
            val v = et.text.toString().trim()
            dismiss()
            onOk(v)
        }
        c.addView(ok)
        c.addView(gap(10))
        val cancel = Glass.button(act, t, "CANCEL", accent = false)
        cancel.setOnClickListener { dismiss() }
        c.addView(cancel)
        show(c)
    }

    fun loading(text: String) {
        val c = card()
        val tv: TextView = Glass.label(act, text, 18f, t.accent, bold = true, spacing = 0.04f)
        tv.gravity = Gravity.CENTER
        c.addView(tv)
        c.addView(gap(14))
        val pb = GlassProgress(act, t)
        pb.setIndeterminate()
        c.addView(pb, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, act.dp(8)))
        show(c, cancelable = false)
    }
}
