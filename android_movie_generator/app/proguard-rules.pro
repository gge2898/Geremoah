# Default ProGuard rules for AI Movie Generator
# Keep OkHttp and JSON classes used at runtime
-dontwarn okhttp3.**
-keep class okhttp3.** { *; }
-keep class org.json.** { *; }

# Keep WebView JavaScript interface methods
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
