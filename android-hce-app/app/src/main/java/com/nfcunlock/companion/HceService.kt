package com.nfcunlock.companion

/**
 * Responds to the SELECT AID command sent by reader.get_hce_token() in
 * src/nfc_unlock/reader.py with this device's enrollment token (raw bytes,
 * not hex), followed by status word 90 00 (success).
 *
 * The AID itself (F0AC1DC0DE0001, declared in res/xml/apduservice.xml) is
 * what gets the SELECT routed here by Android's NFC stack - we don't need
 * to inspect the incoming APDU at all, just answer it.
 */
import android.nfc.cardemulation.HostApduService
import android.os.Bundle

class HceService : HostApduService() {

    override fun processCommandApdu(commandApdu: ByteArray?, extras: Bundle?): ByteArray {
        val token = TokenStore.getToken(applicationContext)
        val tokenBytes = hexToBytes(token)
        // SW_OK = 90 00
        return tokenBytes + byteArrayOf(0x90.toByte(), 0x00.toByte())
    }

    override fun onDeactivated(reason: Int) {
        // Nothing to clean up - the token is static and read-only here.
    }

    private fun hexToBytes(hex: String): ByteArray {
        val out = ByteArray(hex.length / 2)
        for (i in out.indices) {
            val byteStr = hex.substring(i * 2, i * 2 + 2)
            out[i] = byteStr.toInt(16).toByte()
        }
        return out
    }
}
