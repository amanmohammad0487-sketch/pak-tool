package com.majlish.tool

import android.animation.ValueAnimator
import android.app.Activity
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Outline
import android.graphics.Paint
import android.graphics.RadialGradient
import android.graphics.RectF
import android.graphics.Shader
import android.graphics.Typeface
import android.graphics.drawable.Drawable
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.LayerDrawable
import android.os.Build
import android.util.TypedValue
import android.view.MotionEvent
import android.view.View
import android.view.ViewOutlineProvider
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

fun Context.dp(v: Int): Int = (v * resources.displayMetrics.density + 0.5f).toInt()
fun Context.dpf(v: Float): Float = v * resources.displayMetrics.density
fun withAlpha(color: Int, a: Int): Int = Color.argb(a, Color.red(color), Color.green(color), Color.blue(color))

/** Soft gradient page background with glowing colour blobs (what the glass sits on). */
class AuroraView(ctx: Context, private val t: GlassTheme) : View(ctx) {
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)

    override fun onDraw(canvas: Canvas) {
        val w = width.toFloat()
        val h = height.toFloat()
        p.shader = LinearGradient(
            0f, 0f, 0f, h,
            intArrayOf(t.bgTop, t.bgMid, t.bgBottom),
            floatArrayOf(0f, 0.55f, 1f),
            Shader.TileMode.CLAMP
        )
        canvas.drawRect(0f, 0f, w, h, p)
        blob(canvas, w * 0.98f, h * 0.40f, w * 0.80f, t.blobA, 170)
        blob(canvas, w * 0.02f, h * 0.82f, w * 0.85f, t.blobB, 150)
        blob(canvas, w * 0.20f, h * 0.04f, w * 0.70f, t.blobC, 210)
    }

    private fun blob(c: Canvas, cx: Float, cy: Float, r: Float, color: Int, alpha: Int) {
        p.shader = RadialGradient(
            cx, cy, r,
            withAlpha(color, alpha), withAlpha(color, 0),
            Shader.TileMode.CLAMP
        )
        c.drawCircle(cx, cy, r, p)
    }
}

class SlidersIcon(ctx: Context, private val color: Int) : View(ctx) {
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)

    override fun onDraw(c: Canvas) {
        val w = width.toFloat()
        val h = height.toFloat()
        p.color = color
        p.strokeCap = Paint.Cap.ROUND
        p.strokeWidth = h * 0.075f
        val knob = floatArrayOf(0.34f, 0.66f, 0.42f)
        for (i in 0..2) {
            val y = h * (0.30f + 0.20f * i)
            p.style = Paint.Style.STROKE
            c.drawLine(w * 0.18f, y, w * 0.82f, y, p)
            p.style = Paint.Style.FILL
            c.drawCircle(w * knob[i], y, h * 0.095f, p)
        }
    }
}

class GlassProgress(ctx: Context, private val t: GlassTheme) : View(ctx) {
    private var value = 0f
    private var indeterminate = true
    private var phase = 0f
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)
    private val rect = RectF()
    private val anim = ValueAnimator.ofFloat(0f, 1f).apply {
        duration = 1300
        repeatCount = ValueAnimator.INFINITE
        addUpdateListener {
            phase = it.animatedValue as Float
            invalidate()
        }
    }

    fun setIndeterminate() {
        indeterminate = true
        if (isAttachedToWindow && !anim.isStarted) anim.start()
        invalidate()
    }

    fun setFraction(f: Float) {
        indeterminate = false
        value = f.coerceIn(0f, 1f)
        anim.cancel()
        invalidate()
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        if (indeterminate) anim.start()
    }

    override fun onDetachedFromWindow() {
        anim.cancel()
        super.onDetachedFromWindow()
    }

    override fun onDraw(c: Canvas) {
        val w = width.toFloat()
        val h = height.toFloat()
        val r = h / 2f
        p.shader = null
        p.color = Color.argb(70, 255, 255, 255)
        rect.set(0f, 0f, w, h)
        c.drawRoundRect(rect, r, r, p)
        p.color = Color.argb(60, 80, 100, 150)
        p.style = Paint.Style.STROKE
        p.strokeWidth = 1f
        c.drawRoundRect(rect, r, r, p)
        p.style = Paint.Style.FILL
        if (indeterminate) {
            val segW = w * 0.32f
            val x = -segW + (w + segW) * phase
            rect.set(maxOf(0f, x), 0f, minOf(w, x + segW), h)
        } else {
            rect.set(0f, 0f, maxOf(h, w * value), h)
        }
        if (rect.width() > 0f) {
            p.shader = LinearGradient(rect.left, 0f, rect.right, 0f, t.dotA, t.dotB, Shader.TileMode.CLAMP)
            c.drawRoundRect(rect, r, r, p)
            p.shader = null
        }
    }
}

class MaxHeightScrollView(ctx: Context, private val maxPx: Int) : ScrollView(ctx) {
    override fun onMeasure(widthSpec: Int, heightSpec: Int) {
        super.onMeasure(widthSpec, MeasureSpec.makeMeasureSpec(maxPx, MeasureSpec.AT_MOST))
    }
}

object Glass {

    /** Frosted glass surface: translucent white fill, bright rim, top specular highlight. */
    fun surface(ctx: Context, radiusDp: Float, strong: Boolean = false): Drawable {
        val r = ctx.dpf(radiusDp)
        val a1 = if (strong) 238 else 150
        val a2 = if (strong) 214 else 64
        val a3 = if (strong) 228 else 104
        val fill = GradientDrawable(
            GradientDrawable.Orientation.TL_BR,
            intArrayOf(
                Color.argb(a1, 255, 255, 255),
                Color.argb(a2, 244, 248, 255),
                Color.argb(a3, 228, 240, 255)
            )
        )
        fill.cornerRadius = r
        fill.setStroke(maxOf(1, ctx.dp(1)), Color.argb(if (strong) 255 else 210, 255, 255, 255))
        val hi = GradientDrawable(
            GradientDrawable.Orientation.TOP_BOTTOM,
            intArrayOf(
                Color.argb(if (strong) 90 else 110, 255, 255, 255),
                Color.argb(0, 255, 255, 255),
                Color.argb(0, 255, 255, 255)
            )
        )
        hi.cornerRadius = r
        return LayerDrawable(arrayOf<Drawable>(fill, hi))
    }

    fun accentFill(ctx: Context, t: GlassTheme, radiusDp: Float): Drawable {
        val r = ctx.dpf(radiusDp)
        val g = GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT, intArrayOf(t.accent, t.accentDark))
        g.cornerRadius = r
        val hi = GradientDrawable(
            GradientDrawable.Orientation.TOP_BOTTOM,
            intArrayOf(Color.argb(120, 255, 255, 255), Color.argb(0, 255, 255, 255), Color.argb(0, 255, 255, 255))
        )
        hi.cornerRadius = r
        return LayerDrawable(arrayOf<Drawable>(g, hi))
    }

    fun dangerFill(ctx: Context, radiusDp: Float): Drawable {
        val g = GradientDrawable(
            GradientDrawable.Orientation.LEFT_RIGHT,
            intArrayOf(Color.parseColor("#F04438"), Color.parseColor("#B42318"))
        )
        g.cornerRadius = ctx.dpf(radiusDp)
        return g
    }

    fun circle(a: Int, b: Int): Drawable {
        val g = GradientDrawable(GradientDrawable.Orientation.TL_BR, intArrayOf(a, b))
        g.shape = GradientDrawable.OVAL
        return g
    }

    fun label(
        ctx: Context, text: String, sp: Float, color: Int,
        bold: Boolean = false, spacing: Float = 0f
    ): TextView {
        val tv = TextView(ctx)
        tv.text = text
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp)
        tv.setTextColor(color)
        tv.typeface = if (bold) Typeface.create("sans-serif-medium", Typeface.BOLD)
        else Typeface.create("sans-serif", Typeface.NORMAL)
        tv.letterSpacing = spacing
        tv.includeFontPadding = false
        return tv
    }

    fun roundedImage(ctx: Context, resId: Int, sizeDp: Int, radiusDp: Float): ImageView {
        val iv = ImageView(ctx)
        iv.setImageResource(resId)
        iv.scaleType = ImageView.ScaleType.CENTER_CROP
        val r = ctx.dpf(radiusDp)
        iv.outlineProvider = object : ViewOutlineProvider() {
            override fun getOutline(view: View, outline: Outline) {
                outline.setRoundRect(0, 0, view.width, view.height, r)
            }
        }
        iv.clipToOutline = true
        iv.layoutParams = LinearLayout.LayoutParams(ctx.dp(sizeDp), ctx.dp(sizeDp))
        return iv
    }

    /** Pill / glass button with centred text. */
    fun button(ctx: Context, t: GlassTheme, text: String, accent: Boolean, danger: Boolean = false): TextView {
        val tv = label(
            ctx, text, 16f,
            if (accent || danger) Color.WHITE else t.accent,
            bold = true, spacing = 0.06f
        )
        tv.gravity = android.view.Gravity.CENTER
        tv.setPadding(ctx.dp(18), ctx.dp(15), ctx.dp(18), ctx.dp(15))
        tv.background = when {
            danger -> dangerFill(ctx, 40f)
            accent -> accentFill(ctx, t, 40f)
            else -> surface(ctx, 40f)
        }
        tv.pressable()
        return tv
    }
}

fun View.pressable() {
    setOnTouchListener { v, e ->
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN ->
                v.animate().scaleX(0.97f).scaleY(0.97f).alpha(0.92f).setDuration(90).start()
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL ->
                v.animate().scaleX(1f).scaleY(1f).alpha(1f).setDuration(140).start()
        }
        false
    }
}

/** Draw behind the system bars and pad [target] by the bar sizes. */
@Suppress("DEPRECATION")
fun Activity.edgeToEdge(target: View) {
    window.statusBarColor = Color.TRANSPARENT
    window.navigationBarColor = Color.TRANSPARENT
    var flags = View.SYSTEM_UI_FLAG_LAYOUT_STABLE or
        View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
        View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
    if (Build.VERSION.SDK_INT >= 23) flags = flags or View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
    if (Build.VERSION.SDK_INT >= 26) flags = flags or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
    window.decorView.systemUiVisibility = flags
    target.setOnApplyWindowInsetsListener { v, insets ->
        v.setPadding(0, insets.systemWindowInsetTop, 0, insets.systemWindowInsetBottom)
        insets
    }
    target.requestApplyInsets()
}
