package cn.labconnect.platform;

import android.os.Bundle;
import android.webkit.WebView;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            private boolean resolving;

            @Override
            public void handleOnBackPressed() {
                if (resolving) return;
                WebView webView = getBridge() == null ? null : getBridge().getWebView();
                if (webView == null) {
                    finish();
                    return;
                }
                resolving = true;
                // Existing React dialogs own cancellation, including the busy-write guard.
                webView.evaluateJavascript(
                    "(() => { const dialogs = document.querySelectorAll('dialog[open]');"
                    + "const dialog = dialogs[dialogs.length - 1]; if (!dialog) return false;"
                    + "if (dialog.dispatchEvent(new Event('cancel', {bubbles:true, cancelable:true}))) dialog.close();"
                    + "return true; })()",
                    handled -> {
                        resolving = false;
                        if (isFinishing() || isDestroyed() || "true".equals(handled)) return;
                        if (webView.canGoBack()) webView.goBack();
                        else finish();
                    }
                );
            }
        });
    }
}
