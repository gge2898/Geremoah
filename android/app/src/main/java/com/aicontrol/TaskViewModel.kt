package com.aicontrol

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel

enum class ConnectionState { DISCONNECTED, CONNECTED }

class TaskViewModel : ViewModel() {

    private val _connectionState = MutableLiveData(ConnectionState.DISCONNECTED)
    val connectionState: LiveData<ConnectionState> = _connectionState

    private val _connectedDevice = MutableLiveData<String?>(null)
    val connectedDevice: LiveData<String?> = _connectedDevice

    private val _log = MutableLiveData<List<String>>(emptyList())
    val log: LiveData<List<String>> = _log

    private val _isRunning = MutableLiveData(false)
    val isRunning: LiveData<Boolean> = _isRunning

    fun setConnected(deviceName: String?) {
        _connectionState.postValue(
            if (deviceName != null) ConnectionState.CONNECTED else ConnectionState.DISCONNECTED
        )
        _connectedDevice.postValue(deviceName)
    }

    fun setRunning(running: Boolean) {
        _isRunning.postValue(running)
    }

    fun addLog(message: String) {
        val current = _log.value ?: emptyList()
        _log.postValue(current + message)
    }

    fun clearLog() {
        _log.postValue(emptyList())
    }
}
