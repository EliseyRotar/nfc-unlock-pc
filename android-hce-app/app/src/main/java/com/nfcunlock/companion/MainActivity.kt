package com.nfcunlock.companion

import android.content.ClipData
import android.content.ClipboardManager
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

/**
 * Shows this device's current unlock token and lets the user regenerate it.
 *
 * There is intentionally no "pairing"/network step: the user copies (or just
 * reads, since it's short) the token shown here and it gets written into
 * config.json by `python src/main.py enroll` on the PC when the phone is
 * tapped on the reader - the enrollment wizard reads it straight off the NFC
 * exchange, so usually nothing needs to be typed at all.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var textToken: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        textToken = findViewById(R.id.textToken)
        val buttonRegenerate = findViewById<Button>(R.id.buttonRegenerate)

        refreshToken()

        textToken.setOnClickListener {
            val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(ClipData.newPlainText("token", textToken.text))
            Toast.makeText(this, getString(R.string.copied_toast), Toast.LENGTH_SHORT).show()
        }

        buttonRegenerate.setOnClickListener {
            Toast.makeText(this, getString(R.string.regenerate_warning), Toast.LENGTH_LONG).show()
            TokenStore.regenerate(applicationContext)
            refreshToken()
        }
    }

    private fun refreshToken() {
        textToken.text = TokenStore.getToken(applicationContext)
    }
}
