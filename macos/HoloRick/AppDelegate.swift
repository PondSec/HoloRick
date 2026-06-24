import AppKit
import WebKit

private enum AppConfig {
    static let appName = "Holo Rick"
    static let allowedHost = "chat.pondsec.com"
    static let homeURL = URL(string: "https://chat.pondsec.com")!
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow!
    private var webController: WebViewController!

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)

        webController = WebViewController()
        configureMainMenu()

        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1280, height: 820),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.isReleasedWhenClosed = false
        window.title = AppConfig.appName
        window.minSize = NSSize(width: 980, height: 640)
        window.collectionBehavior = [.fullScreenPrimary]
        window.contentViewController = webController
        window.center()
        window.makeKeyAndOrderFront(nil)
        window.orderFrontRegardless()

        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag {
            window?.makeKeyAndOrderFront(nil)
            window?.orderFrontRegardless()
        }
        return true
    }

    @objc private func showAboutPanel() {
        NSApp.orderFrontStandardAboutPanel(options: [
            .applicationName: AppConfig.appName,
            .applicationVersion: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0",
            .credits: NSAttributedString(string: "Native macOS wrapper for https://chat.pondsec.com")
        ])
    }

    private func configureMainMenu() {
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(NSMenuItem(title: "Über Holo Rick", action: #selector(showAboutPanel), keyEquivalent: ""))
        appMenu.addItem(.separator())
        appMenu.addItem(NSMenuItem(title: "Holo Rick beenden", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)

        let editMenuItem = NSMenuItem()
        let editMenu = NSMenu(title: "Bearbeiten")
        editMenu.addItem(NSMenuItem(title: "Widerrufen", action: Selector(("undo:")), keyEquivalent: "z"))
        let redo = NSMenuItem(title: "Wiederholen", action: Selector(("redo:")), keyEquivalent: "Z")
        redo.keyEquivalentModifierMask = [.command, .shift]
        editMenu.addItem(redo)
        editMenu.addItem(.separator())
        editMenu.addItem(NSMenuItem(title: "Ausschneiden", action: #selector(NSText.cut(_:)), keyEquivalent: "x"))
        editMenu.addItem(NSMenuItem(title: "Kopieren", action: #selector(NSText.copy(_:)), keyEquivalent: "c"))
        editMenu.addItem(NSMenuItem(title: "Einfügen", action: #selector(NSText.paste(_:)), keyEquivalent: "v"))
        editMenu.addItem(NSMenuItem(title: "Alles auswählen", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a"))
        editMenuItem.submenu = editMenu
        mainMenu.addItem(editMenuItem)

        let viewMenuItem = NSMenuItem()
        let viewMenu = NSMenu(title: "Darstellung")
        let back = NSMenuItem(title: "Zurück", action: #selector(WebViewController.goBack), keyEquivalent: "[")
        back.target = webController
        viewMenu.addItem(back)
        let forward = NSMenuItem(title: "Vorwärts", action: #selector(WebViewController.goForward), keyEquivalent: "]")
        forward.target = webController
        viewMenu.addItem(forward)
        let reload = NSMenuItem(title: "Neu laden", action: #selector(WebViewController.reloadPage), keyEquivalent: "r")
        reload.target = webController
        viewMenu.addItem(reload)
        viewMenuItem.submenu = viewMenu
        mainMenu.addItem(viewMenuItem)

        NSApp.mainMenu = mainMenu
    }
}

final class WebViewController: NSViewController, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    private lazy var webView: WKWebView = {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = true
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        configuration.applicationNameForUserAgent = "HoloRickMac/1.0"

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        webView.allowsMagnification = false
        webView.translatesAutoresizingMaskIntoConstraints = false
        return webView
    }()

    private lazy var errorView: NSView = {
        let container = NSView()
        container.translatesAutoresizingMaskIntoConstraints = false

        let title = NSTextField(labelWithString: "Holo Rick ist gerade nicht erreichbar.")
        title.font = .systemFont(ofSize: 20, weight: .semibold)
        title.alignment = .center

        let detail = NSTextField(labelWithString: "Prüfe die Verbindung zu https://chat.pondsec.com und lade die App neu.")
        detail.font = .systemFont(ofSize: 13)
        detail.textColor = .secondaryLabelColor
        detail.alignment = .center
        detail.lineBreakMode = .byWordWrapping
        detail.maximumNumberOfLines = 3

        let retry = NSButton(title: "Neu laden", target: self, action: #selector(reloadPage))
        retry.bezelStyle = .rounded
        retry.controlSize = .large

        let stack = NSStackView(views: [title, detail, retry])
        stack.orientation = .vertical
        stack.alignment = .centerX
        stack.spacing = 14
        stack.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(stack)

        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: container.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: container.centerYAnchor),
            stack.widthAnchor.constraint(lessThanOrEqualToConstant: 460)
        ])

        container.isHidden = true
        return container
    }()

    override func loadView() {
        view = NSView()
    }

    override func viewDidLoad() {
        super.viewDidLoad()

        view.addSubview(webView)
        view.addSubview(errorView)

        NSLayoutConstraint.activate([
            webView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            webView.topAnchor.constraint(equalTo: view.topAnchor),
            webView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            errorView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            errorView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            errorView.topAnchor.constraint(equalTo: view.topAnchor),
            errorView.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])

        loadHome()
    }

    @objc func reloadPage() {
        errorView.isHidden = true

        if webView.url == nil {
            loadHome()
        } else {
            webView.reload()
        }
    }

    @objc func goBack() {
        if webView.canGoBack {
            webView.goBack()
        }
    }

    @objc func goForward() {
        if webView.canGoForward {
            webView.goForward()
        }
    }

    private func loadHome() {
        var request = URLRequest(url: AppConfig.homeURL)
        request.cachePolicy = .useProtocolCachePolicy
        request.timeoutInterval = 30
        webView.load(request)
    }

    private func isAllowedInternalURL(_ url: URL) -> Bool {
        if url.scheme == "about" {
            return true
        }

        guard
            url.scheme?.lowercased() == "https",
            let host = url.host?.lowercased()
        else {
            return false
        }

        return host == AppConfig.allowedHost
    }

    private func openExternally(_ url: URL) {
        let allowedExternalSchemes = ["https", "http", "mailto"]
        guard let scheme = url.scheme?.lowercased(), allowedExternalSchemes.contains(scheme) else {
            NSSound.beep()
            return
        }

        NSWorkspace.shared.open(url)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.cancel)
            return
        }

        if navigationAction.shouldPerformDownload {
            decisionHandler(.download)
            return
        }

        if isAllowedInternalURL(url) {
            errorView.isHidden = true
            decisionHandler(.allow)
            return
        }

        openExternally(url)
        decisionHandler(.cancel)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationResponse: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        if navigationResponse.canShowMIMEType {
            decisionHandler(.allow)
        } else {
            decisionHandler(.download)
        }
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        errorView.isHidden = false
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        errorView.isHidden = false
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        webView.reload()
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        guard let url = navigationAction.request.url else {
            return nil
        }

        if isAllowedInternalURL(url) {
            webView.load(navigationAction.request)
        } else {
            openExternally(url)
        }

        return nil
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
        download.delegate = self
    }

    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
        download.delegate = self
    }

    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        let downloads = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask).first
        let filename = suggestedFilename.isEmpty ? "HoloRick-Download" : suggestedFilename
        completionHandler(downloads?.appendingPathComponent(filename))
    }
}
