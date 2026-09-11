import QtQuick
import Quickshell
import Quickshell.Io

// Only gameplay messages reach the verifier. Parent authentication stays in Screen Time.
Item {
  id: root
  property string clientPath: "/usr/bin/omarchy-kids-controls-grove-client"
  property var status: ({})
  property var current: null
  readonly property bool available: status.ok === true && status.active === true
  readonly property var receipts: status.receipts || []
  readonly property int seconds: Number(status.seconds_per_event) || 0
  readonly property string note: status.reason === "daily_cap_reached" ? "Today's reward allowance is used. Practice is always ready."
    : status.reason === "policy_blocked" ? "Rewards are paused by Screen Time. Practice is always ready."
    : "Optional rewards: set up Screen Time and enable this game in Connected games."
  signal reply(int token, var result)
  function cancel() {
    watchdog.stop()
    if (current) { var job = current; current = null; job.running = false; job.destroy() }
  }
  function refresh() { if (!current) request(-1, {cmd: "status"}) }
  function finish(job, result) {
    if (current !== job) return
    var token = job.token
    cancel()
    if (token === -1) status = result
    else { reply(token, result); refresh() }
  }
  function request(token, payload) {
    if (current && current.token === -1 && token !== -1) cancel()
    if (current) { reply(token, {ok: false, error: "busy"}); return }
    current = requestProcess.createObject(root, {token: token,
      command: [clientPath, "request", JSON.stringify(payload)]})
    watchdog.start(); current.running = true
  }
  function openParentSettings() {
    if (status.available) parentSettings.running = true
    else Qt.openUrlExternally("https://github.com/peterholko/omarchy-screen-time-platform#install-on-omarchy")
  }
  Timer { id: watchdog; interval: 10000; onTriggered: if (root.current) root.finish(root.current, {ok: false, error: "unavailable"}) }
  Timer { interval: 5000; repeat: true; running: true; onTriggered: root.refresh() }
  Component {
    id: requestProcess
    Process {
      id: job
      property int token: -1
      property bool launched: false
      stdout: StdioCollector { id: output; waitForEnd: true }
      onStarted: launched = true
      onRunningChanged: if (!running && !launched) root.finish(job, {ok: false, error: "unavailable"})
      onExited: {
        var result
        try { result = JSON.parse(output.text) } catch (error) { result = {ok: false, error: "unavailable"} }
        root.finish(job, result)
      }
    }
  }
  Process { id: parentSettings; command: ["/usr/bin/omarchy-peterholko-screen-time", "parent", "settings"] }
  Component.onCompleted: refresh()
  Component.onDestruction: cancel()
}
