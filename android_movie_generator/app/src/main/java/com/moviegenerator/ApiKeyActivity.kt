package com.moviegenerator

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class ApiKeyActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // If we already have a saved key, go straight to chat
        val prefs = getSharedPreferences("mg_prefs", MODE_PRIVATE)
        val saved = prefs.getString("api_key", null)
        if (!saved.isNullOrBlank()) {
            openMain(saved)
            return
        }

        setContentView(R.layout.activity_api_key)

        val etKey    = findViewById<EditText>(R.id.etApiKey)
        val btnStart = findViewById<Button>(R.id.btnStart)
        val btnClear = findViewById<Button>(R.id.btnClearKey)

        btnStart.setOnClickListener {
            val key = etKey.text.toString().trim()
            if (!key.startsWith("sk-") || key.length < 20) {
                Toast.makeText(this, "That doesn't look like a valid OpenAI key", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            prefs.edit().putString("api_key", key).apply()
            openMain(key)
        }

        btnClear.setOnClickListener {
            prefs.edit().remove("api_key").apply()
            etKey.text.clear()
            Toast.makeText(this, "Key cleared", Toast.LENGTH_SHORT).show()
        }
    }

    private fun openMain(key: String) {
        startActivity(Intent(this, MainActivity::class.java)
            .putExtra("api_key", key))
        finish()
    }
}
