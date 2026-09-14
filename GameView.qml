import QtQuick
import QtQuick.Controls
import "Facts.js" as Facts
import "GameEngine.js" as Engine

// A reusable Qt Quick game with local questions and scoring.
FocusScope {
  id: root
  objectName: "numberGroveGame"
  focus: true
  implicitWidth: 1040
  implicitHeight: 760
  property bool windowActive: true
  property int grade: 5
  property bool calm: false
  property bool paused: false
  property string screen: "start"
  property var session: Engine.create(5, 10, 1)
  signal quitRequested()

  // Focusing a scope preserves its last button. Give gameplay its own target.
  Item {
    id: gameInput
    objectName: "gameInput"
    focus: true
  }
  function focusGame() { gameInput.forceActiveFocus() }

  function reset() {
    screen = "start"
    paused = false
    focusGame()
  }
  function start() {
    session = Engine.create(Facts.level(grade), 10, Date.now())
    screen = "game"
    paused = false
    nextQuestion()
  }
  function nextQuestion() {
    session = Engine.board(session, Facts.question(session.grade))
    focusGame()
  }
  function move(dx, dy) {
    if (screen !== "game" || paused) return
    session = Engine.move(session, dx, dy)
  }
  function collect() {
    if (screen !== "game" || paused) return
    session = Engine.collect(session)
    if (session.phase !== "checking") return
    var value = session.tiles[session.player]
    session = Engine.verdict(session, {ok: true, correct: value === session.question.answer,
                                      answer: session.question.answer})
  }
  function togglePause() {
    if (screen !== "game") return
    paused = !paused
    focusGame()
  }
  onWindowActiveChanged: if (!windowActive && screen === "game") paused = true
  Keys.onPressed: function(event) {
    if (event.key === Qt.Key_Escape || event.key === Qt.Key_P) {
      if (screen === "start") quitRequested()
      else togglePause()
    } else if (screen === "start" && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter)) start()
    else if (!paused && screen === "game") {
      if (event.key === Qt.Key_Left || event.key === Qt.Key_A) move(-1, 0)
      else if (event.key === Qt.Key_Right || event.key === Qt.Key_D) move(1, 0)
      else if (event.key === Qt.Key_Up || event.key === Qt.Key_W) move(0, -1)
      else if (event.key === Qt.Key_Down || event.key === Qt.Key_S) move(0, 1)
      else if (event.key === Qt.Key_Space || event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
        if (event.isAutoRepeat) { event.accepted = true; return }
        if (session.phase === "feedback") nextQuestion()
        else if (session.phase === "results" || session.phase === "error") reset()
        else collect()
      } else { event.accepted = false; return }
    } else { event.accepted = false; return }
    event.accepted = true
  }
  Timer {
    interval: Engine.interval(root.session)
    repeat: true
    running: root.screen === "game" && root.session.phase === "play" && !root.paused && root.windowActive && !root.calm
    onTriggered: root.session = Engine.tick(root.session)
  }
  Rectangle { anchors.fill: parent; color: "#F4F1E6" }
  Item {
    id: page
    width: 1040; height: 760
    anchors.centerIn: parent
    scale: Math.min(root.width / width, root.height / height)
    readonly property bool playing: root.screen === "game"
    readonly property var preview: Engine.board(Engine.create(5, 10, 173),
      {text: "7 × 8", choices: [42, 48, 54, 56, 63, 72]})
    readonly property var game: playing ? root.session : preview

    SeedSprite { x: 38; y: 24; width: 38; height: 42; animate: root.windowActive }
    Text { x: 88; y: 28; text: "Number Grove"; color: "#244B36"; font.pixelSize: 23; font.weight: Font.Bold }
    Text { x: 88; y: 56; text: "A LITTLE PRACTICE. A LOT OF GROWTH."; color: "#6E7D68"; font.pixelSize: 10; font.letterSpacing: 1.6 }
    GroveButton {
      objectName: "pauseButton"
      x: 844; y: 28; width: 156; height: 42
      text: page.playing ? (root.paused ? "Resume" : "Pause  ·  P") : "Close"
      onClicked: page.playing ? root.togglePause() : root.quitRequested()
    }
    Rectangle { x: 40; y: 94; width: 960; height: 1; color: "#DCE0CE" }

    Column {
      x: 40; y: 132; width: 306; spacing: 19
      visible: !page.playing
      Text { text: "Small facts.\nBig adventures."; font.pixelSize: 43; font.weight: Font.Bold; lineHeight: 1.03; color: "#244B36" }
      Text { width: parent.width; text: "Guide your seed courier to the right answer. Collect seeds. Watch out for the drift bugs."; font.pixelSize: 17; lineHeight: 1.3; wrapMode: Text.WordWrap; color: "#61715D" }
      Column {
        spacing: 11
        Text { text: "CHOOSE YOUR GRADE"; font.pixelSize: 11; font.letterSpacing: 1.4; font.weight: Font.Bold; color: "#61715D" }
        Row {
          spacing: 7
          Repeater {
            model: 6
            GroveButton {
              required property int index
              objectName: "grade" + (index + 1)
              width: 45; height: 44; text: String(index + 1); selected: root.grade === index + 1
              onClicked: { root.grade = index + 1; root.focusGame() }
            }
          }
        }
        Text { width: 300; height: 38; text: Facts.hint(root.grade); font.pixelSize: 14; wrapMode: Text.WordWrap; color: "#61715D" }
      }
      GroveButton {
        objectName: "calmMode"; width: 306; height: 38
        text: root.calm ? "Calm garden  ·  bugs rest" : "Adventure  ·  bugs wander"
        font.pixelSize: 14
        onClicked: { root.calm = !root.calm; root.focusGame() }
      }
      GroveButton { objectName: "practiceButton"; width: 306; primary: true; text: "Play  →"; onClicked: root.start() }
    }
    Column {
      x: 40; y: 136; width: 300; spacing: 22
      visible: page.playing
      Text { text: "PRACTICE GARDEN"; font.pixelSize: 12; font.letterSpacing: 2; color: "#698063"; font.weight: Font.Bold }
      Text { text: "Grow at your\nown pace."; font.pixelSize: 39; font.weight: Font.Bold; color: "#244B36" }
      Text { text: "Grade " + root.session.grade + "  ·  " + (root.calm ? "Calm garden" : "Trail " + Engine.difficulty(root.session)); font.pixelSize: 17; color: "#61715D" }
      Rectangle {
        width: 300; height: 144; radius: 18; color: "#E8EBD9"
        Column {
          x: 20; y: 18; spacing: 10
          Text { text: root.session.correct + " seeds collected"; font.pixelSize: 24; font.weight: Font.Bold; color: "#244B36" }
          Text { text: root.session.answered + " / " + root.session.total + " facts  ·  " + root.session.score + " points"; font.pixelSize: 15; color: "#61715D" }
          Text { text: "♥ ".repeat(Math.max(0, root.session.hearts)) + "♡ ".repeat(Math.max(0, 3 - root.session.hearts)); font.pixelSize: 26; color: "#AD6849" }
        }
      }
      Text {
        width: 292; text: "Each correct fact plants a seed.\nA wrong answer costs one heart."
        font.pixelSize: 16; lineHeight: 1.3; wrapMode: Text.WordWrap; color: "#61715D"
      }
      Text { width: 292; text: "ARROWS / WASD  ·  move\nSPACE / ENTER  ·  collect\nP / ESC  ·  pause"; font.pixelSize: 13; lineHeight: 1.6; color: "#698063"; font.weight: Font.Medium }
      GroveButton { objectName: "newRoundButton"; width: 176; height: 42; text: "New round"; onClicked: root.reset() }
    }

    Rectangle {
      x: 384; y: 128; width: 616; height: 66; radius: 16; color: "#E6EBD9"
      Text { x: 22; anchors.verticalCenter: parent.verticalCenter; text: "FIND THE\nANSWER"; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1.2; lineHeight: 1.2; color: "#698063" }
      Text {
        objectName: "questionText"
        anchors.centerIn: parent
        text: page.game.question ? page.game.question.text + " = ?" : "One moment…"
        font.pixelSize: 32; font.weight: Font.Bold; color: "#244B36"
      }
      Text { anchors.right: parent.right; anchors.rightMargin: 20; anchors.verticalCenter: parent.verticalCenter; text: "✦"; font.pixelSize: 25; color: "#B4822E" }
    }
    Rectangle {
      id: garden
      x: 384; y: 208; width: 616; height: 440; radius: 20; color: "#254D39"
      clip: true
      Repeater {
        model: 35
        Rectangle {
          required property int index
          x: (index % 7) * 88 + 4; y: Math.floor(index / 7) * 88 + 4
          width: 80; height: 80; radius: 15
          color: index % 2 === 0 ? "#305B42" : "#2D573F"
          border.color: "#39654A"
          Rectangle {
            visible: page.game.stones.indexOf(index) >= 0
            anchors.centerIn: parent; width: 52; height: 43; radius: 16; rotation: -8
            color: "#708378"; border.color: "#96A397"; border.width: 2
            Rectangle { x: 10; y: 9; width: 19; height: 5; radius: 3; color: "#A5B1A0"; rotation: -12 }
          }
          Rectangle {
            visible: page.game.tiles.length > index && page.game.tiles[index] !== null
            anchors.centerIn: parent; width: 55; height: 53; radius: 19
            color: "#E9DCB2"; border.color: "#FFF0C8"; border.width: 2
            Text {
              anchors.centerIn: parent; text: page.game.tiles[index] === null || page.game.tiles[index] === undefined ? "" : String(page.game.tiles[index])
              font.pixelSize: 24; font.weight: Font.Bold; color: "#354A32"
            }
            Rectangle { x: 39; y: -5; width: 15; height: 8; radius: 5; rotation: -32; color: "#B9D584" }
          }
        }
      }
      Repeater {
        model: page.game.bugs.length
        SeedSprite {
          required property int index
          bug: true; width: 56; height: 60
          x: (page.game.bugs[index] % 7) * 88 + 16
          y: Math.floor(page.game.bugs[index] / 7) * 88 + 12
          animate: root.windowActive && !root.paused && (!page.playing || root.session.phase === "play") && !root.calm
          Behavior on x { NumberAnimation { duration: 130 } }
          Behavior on y { NumberAnimation { duration: 130 } }
        }
      }
      SeedSprite {
        objectName: "seedCourier"
        width: 60; height: 64
        x: (page.game.player % 7) * 88 + 14
        y: Math.floor(page.game.player / 7) * 88 + 10
        shielded: page.playing && root.session.shield > 0 && !root.calm
        animate: root.windowActive && !root.paused && (!page.playing || root.session.phase === "play")
        Behavior on x { NumberAnimation { duration: 85 } }
        Behavior on y { NumberAnimation { duration: 85 } }
      }
      Rectangle {
        anchors.fill: parent; radius: 20; color: "#D9254D39"
        visible: page.playing && (root.paused || ["feedback", "results", "error", "waiting", "checking"].indexOf(root.session.phase) >= 0)
        Rectangle {
          width: 532; height: messageColumn.implicitHeight + 56
          anchors.centerIn: parent; radius: 22; color: "#FAF6E9"
          Column {
            id: messageColumn
            x: 28; y: 28; width: 476; spacing: 18
            Text {
              width: parent.width; horizontalAlignment: Text.AlignHCenter
              text: root.paused ? "Take a breather."
                : root.session.phase === "results" ? (root.session.hearts > 0 ? "Look at your grove!" : "Every seed is progress.")
                : root.session.phase === "feedback" ? (root.session.good ? "A little more growth!" : "Keep growing.")
                : root.session.phase === "error" ? "Let's take a fresh path."
                : root.session.phase === "checking" ? "Checking your answer…" : "Finding a fresh seed…"
              font.pixelSize: 28; font.weight: Font.Bold; color: "#244B36"; wrapMode: Text.WordWrap
            }
            Text {
              width: parent.width; horizontalAlignment: Text.AlignHCenter
              text: root.paused ? "Your garden will be here when you're ready."
                : root.session.phase === "results" ? root.session.correct + " seeds  ·  " + root.session.score + " points\n" + root.session.message
                : root.session.message
              font.pixelSize: 17; color: "#61715D"; wrapMode: Text.WordWrap; lineHeight: 1.3
            }
            GroveButton {
              objectName: "continueButton"
              anchors.horizontalCenter: parent.horizontalCenter; width: 236; primary: true
              visible: root.paused || ["feedback", "results", "error"].indexOf(root.session.phase) >= 0
              text: root.paused ? "Back to the garden" : root.session.phase === "feedback" ? "Next seed  →" : "Choose a new round"
              onClicked: {
                if (root.paused) root.togglePause()
                else if (root.session.phase === "feedback") root.nextQuestion()
                else root.reset()
              }
            }
          }
        }
      }
    }
    Text {
      x: 384; y: 668; width: 616
      text: page.playing ? (root.session.phase === "play" ? (root.session.tiles[root.session.player] !== null
          ? "On seed " + root.session.tiles[root.session.player] + "  ·  Press Space to collect" : root.session.message) : "Little by little, facts become second nature.")
        : "01  Solve the fact     02  Find the seed     03  Press Space"
      color: "#65765F"; font.pixelSize: 14; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
    }
    Text { x: 40; y: 726; text: "OMARCHY KIDS  /  NUMBER GROVE"; font.pixelSize: 10; font.letterSpacing: 1.5; color: "#86917D" }
    Text { anchors.right: parent.right; anchors.rightMargin: 40; y: 724; text: "Built for recall. Made for play."; font.pixelSize: 12; color: "#86917D" }
  }
}
