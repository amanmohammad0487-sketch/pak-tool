package com.majlish.tool

import android.graphics.Color

class GlassTheme(
    val key: String,
    val title: String,
    val bgTop: Int,
    val bgMid: Int,
    val bgBottom: Int,
    val blobA: Int,
    val blobB: Int,
    val blobC: Int,
    val accent: Int,
    val accentDark: Int,
    val dotA: Int,
    val dotB: Int,
    val text: Int,
    val subText: Int
)

private fun c(s: String): Int = Color.parseColor(s)

object Themes {
    val all: List<GlassTheme> = listOf(
        GlassTheme(
            "green", "Liquid Green",
            c("#E6FFF1"), c("#C4F7DD"), c("#9CEBC4"),
            c("#4ADE80"), c("#22D3EE"), c("#FFFFFF"),
            c("#12A150"), c("#0B7A3B"), c("#22C55E"), c("#06B6D4"),
            c("#0B2E1F"), c("#3F6B58")
        ),
        GlassTheme(
            "ice", "Ice Blue",
            c("#E3F2FF"), c("#C2E3FF"), c("#9ED3FF"),
            c("#3B82F6"), c("#22D3EE"), c("#FFFFFF"),
            c("#1673F0"), c("#0A4FB8"), c("#3B82F6"), c("#06B6D4"),
            c("#0B1F3F"), c("#4A5F85")
        ),
        GlassTheme(
            "violet", "Aurora Violet",
            c("#F0E9FF"), c("#DCCBFF"), c("#BFA6FF"),
            c("#8B5CF6"), c("#EC4899"), c("#FFFFFF"),
            c("#7C3AED"), c("#5B21B6"), c("#8B5CF6"), c("#EC4899"),
            c("#1E1038"), c("#5E4B85")
        ),
        GlassTheme(
            "amber", "Sunset Amber",
            c("#FFF2E2"), c("#FFDDB8"), c("#FFC08A"),
            c("#FB923C"), c("#F43F5E"), c("#FFFFFF"),
            c("#EA6A0A"), c("#B45309"), c("#F97316"), c("#EF4444"),
            c("#3A1A05"), c("#8A5A33")
        ),
        GlassTheme(
            "frost", "Frost Light",
            c("#E2ECFF"), c("#CBD7FF"), c("#BDE9FA"),
            c("#A78BFA"), c("#38BDF8"), c("#FFFFFF"),
            c("#1570EF"), c("#0B4BC4"), c("#3B82F6"), c("#A78BFA"),
            c("#0E1A3A"), c("#52607F")
        )
    )

    const val DEFAULT_KEY = "frost"

    fun byKey(key: String?): GlassTheme {
        for (t in all) {
            if (t.key == key) return t
        }
        return all.last()
    }
}
