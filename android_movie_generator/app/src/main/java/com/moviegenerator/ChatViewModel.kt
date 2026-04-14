package com.moviegenerator

import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

sealed class ChatState {
    object Idle : ChatState()
    object Thinking : ChatState()
    data class ScriptReady(val code: String, val description: String) : ChatState()
    data class Error(val message: String) : ChatState()
}

class ChatViewModel : ViewModel() {

    val messages   = MutableLiveData<List<Message>>(emptyList())
    val chatState  = MutableLiveData<ChatState>(ChatState.Idle)

    private var gpt: GptClient? = null
    private var lastCode: String? = null

    fun init(apiKey: String) {
        gpt = GptClient(apiKey)
    }

    fun sendMessage(text: String) {
        addMessage(Message(text, isUser = true))
        chatState.value = ChatState.Thinking

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val (code, desc) = gpt!!.generateAnimation(text)
                lastCode = code
                addMessage(Message(desc, isUser = false))
                chatState.postValue(ChatState.ScriptReady(code, desc))
            } catch (e: Exception) {
                val err = e.message ?: "Unknown error"
                addMessage(Message("Error: $err", isUser = false))
                chatState.postValue(ChatState.Error(err))
            }
        }
    }

    fun fixLastCode(errorMsg: String) {
        val broken = lastCode ?: return
        addMessage(Message("Fixing error — please wait…", isUser = false))
        chatState.value = ChatState.Thinking

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val (code, desc) = gpt!!.fixAnimation(broken, errorMsg)
                lastCode = code
                addMessage(Message("Fixed: $desc", isUser = false))
                chatState.postValue(ChatState.ScriptReady(code, desc))
            } catch (e: Exception) {
                chatState.postValue(ChatState.Error(e.message ?: "Fix failed"))
            }
        }
    }

    fun reset() {
        gpt?.reset()
        messages.value = emptyList()
        chatState.value = ChatState.Idle
        lastCode = null
    }

    private fun addMessage(msg: Message) {
        val current = messages.value ?: emptyList()
        messages.postValue(current + msg)
    }
}
