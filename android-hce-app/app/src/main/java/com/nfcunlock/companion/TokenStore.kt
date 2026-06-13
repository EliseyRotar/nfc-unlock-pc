package com.nfcunlock.companion

import android.content.Context
import android.content.SharedPreferences
import java.security.SecureRandom

/**
 * Holds this device's unlock token: a 16-byte random value, hex-encoded.
 *
 * This token - not the phone's hardware identity - is what
 * src/nfc_unlock/reader.py reads via HCE and compares against the value
 * stored in config.json during enrollment. Android randomizes the HCE
 * "UID" for privacy reasons on every tap, so we can't rely on it; the
 * token is the actual shared secret.
 *
 * It is stored in plain SharedPreferences (not the Keystore) because it
 * needs to be readable/regenerable from the UI and is only useful to
 * someone who already has physical access to both this phone AND your
 * NFC reader - the same threat model as a physical access card.
 */
object TokenStore {
    private const val PREFS = "nfc_unlock_companion"
    private const val KEY_TOKEN = "token_hex"
    private const val TOKEN_BYTES = 16

    private fun prefs(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun getToken(context: Context): String {
        val p = prefs(context)
        val existing = p.getString(KEY_TOKEN, null)
        if (existing != null) return existing
        val fresh = generate()
        p.edit().putString(KEY_TOKEN, fresh).apply()
        return fresh
    }

    fun regenerate(context: Context): String {
        val fresh = generate()
        prefs(context).edit().putString(KEY_TOKEN, fresh).apply()
        return fresh
    }

    private fun generate(): String {
        val bytes = ByteArray(TOKEN_BYTES)
        SecureRandom().nextBytes(bytes)
        return bytes.joinToString("") { "%02X".format(it) }
    }
}
