package com.moviegenerator

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ProgressBar
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView

class MainActivity : AppCompatActivity() {

    private lateinit var vm: ChatViewModel
    private lateinit var adapter: ChatAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val toolbar = findViewById<Toolbar>(R.id.toolbar)
        setSupportActionBar(toolbar)

        val apiKey = intent.getStringExtra("api_key") ?: run { finish(); return }

        vm = ViewModelProvider(this)[ChatViewModel::class.java]
        vm.init(apiKey)

        adapter = ChatAdapter()
        val rv = findViewById<RecyclerView>(R.id.rvMessages)
        rv.layoutManager = LinearLayoutManager(this).also { it.stackFromEnd = true }
        rv.adapter = adapter

        val etInput  = findViewById<EditText>(R.id.etInput)
        val btnSend  = findViewById<ImageButton>(R.id.btnSend)
        val progress = findViewById<ProgressBar>(R.id.progressBar)

        btnSend.setOnClickListener {
            val text = etInput.text.toString().trim()
            if (text.isBlank()) return@setOnClickListener
            etInput.text.clear()
            vm.sendMessage(text)
        }

        vm.messages.observe(this) { msgs ->
            adapter.setMessages(msgs)
            rv.scrollToPosition(msgs.size - 1)
        }

        vm.chatState.observe(this) { state ->
            when (state) {
                is ChatState.Thinking -> {
                    progress.visibility = View.VISIBLE
                    btnSend.isEnabled = false
                }
                is ChatState.ScriptReady -> {
                    progress.visibility = View.GONE
                    btnSend.isEnabled = true
                    // Launch renderer
                    startActivity(
                        Intent(this, RendererActivity::class.java)
                            .putExtra("js_code", state.code)
                    )
                }
                is ChatState.Error -> {
                    progress.visibility = View.GONE
                    btnSend.isEnabled = true
                }
                else -> {
                    progress.visibility = View.GONE
                    btnSend.isEnabled = true
                }
            }
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_new -> { vm.reset(); true }
            R.id.action_change_key -> {
                getSharedPreferences("mg_prefs", MODE_PRIVATE).edit()
                    .remove("api_key").apply()
                startActivity(Intent(this, ApiKeyActivity::class.java))
                finish()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
}
