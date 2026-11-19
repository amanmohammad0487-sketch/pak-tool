package com.majlish.tool

import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors

/** Receives live output from the Python engine. Methods are called from the Python thread. */
class Sink(
    private val onLog: (String) -> Unit,
    private val onProgress: (Int, Int, String) -> Unit
) {
    fun log(s: String) {
        onLog(s)
    }

    fun progress(done: Int, total: Int, label: String) {
        onProgress(done, total, label)
    }
}

class Item(val name: String, val path: String, val detail: String)

object Engine {
    private val worker = Executors.newSingleThreadExecutor()

    private fun py(ctx: Context): Python {
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(ctx.applicationContext))
        }
        return Python.getInstance()
    }

    /** Runs work on the engine thread (one job at a time, in order). */
    fun async(work: () -> Unit) {
        worker.execute(work)
    }

    fun init(ctx: Context, base: String) {
        py(ctx).getModule("bridge").callAttr("init", base)
    }

    fun list(ctx: Context, kind: String): List<Item> {
        val raw = py(ctx).getModule("bridge").callAttr("list_items", kind).toString()
        val arr = JSONArray(raw)
        val out = ArrayList<Item>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            out.add(Item(o.getString("name"), o.getString("path"), o.optString("detail", "")))
        }
        return out
    }

    fun run(ctx: Context, task: String, args: JSONObject, sink: Sink): JSONObject {
        val raw = py(ctx).getModule("bridge").callAttr("run", task, args.toString(), sink).toString()
        return JSONObject(raw)
    }

    /** License check (called from a normal background thread). */
    fun verify(ctx: Context, key: String): JSONObject {
        val raw = py(ctx).getModule("majlish_auth")
            .callAttr("verify_key", key, Store.deviceId(ctx), Store.deviceName()).toString()
        return JSONObject(raw)
    }
}
