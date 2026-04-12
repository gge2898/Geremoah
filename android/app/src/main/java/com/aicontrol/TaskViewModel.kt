package com.aicontrol

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel

data class LogEntry(val type: String, val text: String)

class TaskViewModel : ViewModel() {

    private val _isConnected = MutableLiveData(false)
    val isConnected: LiveData<Boolean> = _isConnected

    private val _log = MutableLiveData<List<LogEntry>>(emptyList())
    val log: LiveData<List<LogEntry>> = _log

    private val _connectedDevice = MutableLiveData<String?>(null)
    val connectedDevice: LiveData<String?> = _connectedDevice

    fun setConnected(deviceName: String?) {
        _isConnected.postValue(deviceName != null)
        _connectedDevice.postValue(deviceName)
    }

    fun appendLog(entry: LogEntry) {
        val current = _log.value ?: emptyList()
        _log.postValue(current + entry)
    }

    fun clearLog() {
        _log.postValue(emptyList())
    }
}
