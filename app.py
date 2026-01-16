import streamlit as st

# Page configuration
st.set_page_config(
    page_title="ESP32 Smart Water Automation Code",
    layout="wide"
)

st.title("💧 Smart Water Automation – ESP32 Source Code")
st.markdown(
    "This page displays the complete **ESP32 Smart Water Automation** firmware code "
    "using Streamlit with syntax highlighting."
)

# Your ESP32 / Arduino code as a string
esp32_code = r'''
#include <WiFi.h>
#include <WebServer.h>
#include <OneWire.h>
#include <DallasTemperature.h>

/* ================= WIFI ================= */
const char* ssid     = "POCO";
const char* password = "20242025";

/* ================= PINS ================= */
#define TRIG_PIN 5
#define ECHO_PIN 18
#define MOTOR_RELAY 23
#define MOTOR_LED   22
#define IRR_LED     25
#define SOLAR_LED   27
#define RO_LED      33
#define COLD_LED    12
#define HOT_LED     2
#define ONE_WIRE_BUS 4
#define TANK_LED_COUNT 3
int tankLEDs[TANK_LED_COUNT] = { 14 , 21, 26};
  
/* ================= OBJECTS ================= */
WebServer server(80);
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);

/* ================= VARIABLES ================= */
float tankHeight = 100.0;      // cm
float tankArea   = 10000.0;    // cm²
float waterPercent = 0;
float lastVolumeLiters = 0;
float monthlyLiters = 0;
float temperatureC = 0;
float MANUAL_STOP_LEVEL = 95.0;   // % water level to stop manual motor
float MANUAL_START_LIMIT = 20.0;  // optional safety (not mandatory)

bool motorState = false;
bool motorManual = false;
bool irrState = false;
bool solarState = false;
bool roState = false;
unsigned long now;
unsigned long irrLast = 0, solarLast = 0, roLast = 0;
unsigned long irrInterval   = 86400000UL;   // 1 day
unsigned long solarInterval = 864000000UL;  // 10 days
unsigned long roInterval    = 43200000UL;   // 12 hours
unsigned long irrRunTime   = 10000;
unsigned long solarRunTime = 10000;
unsigned long roRunTime    = 10000;
/* ================= ULTRASONIC ================= */
float getDistance() {
  float sum = 0;

  for (int i = 0; i < 5; i++) {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    long duration = pulseIn(ECHO_PIN, HIGH, 30000);
    if (duration == 0) duration = tankHeight * 58;

    sum += (duration * 0.0343) / 2.0;
    delay(10);
  }

  return sum / 5;
}


/* ================= TANK ================= */
void updateTank() {
  float d = getDistance();
  float h = constrain(tankHeight - d, 0, tankHeight);

  waterPercent = (h / tankHeight) * 100.0;

  float volumeLiters = (h * tankArea) / 1000.0;
 if (motorState && volumeLiters > lastVolumeLiters) {
  monthlyLiters += volumeLiters - lastVolumeLiters;
}

  lastVolumeLiters = volumeLiters;
}

/* ================= MOTOR AUTO ================= */void motorAuto() {
  if (motorManual) {
    // Stop manual motor if water reaches stop level
    if (waterPercent >= MANUAL_STOP_LEVEL && motorState) {
      motorState = false;
      motorManual = false; // return to auto mode
      digitalWrite(MOTOR_RELAY, HIGH);
      digitalWrite(MOTOR_LED, LOW);
    }
    return; // skip auto logic while manual motor is active
  }

  // Automatic motor control
  if (waterPercent < 30 && !motorState) {
    motorState = true;
    digitalWrite(MOTOR_RELAY, LOW);
    digitalWrite(MOTOR_LED, HIGH);
  }

  if (waterPercent > 90 && motorState) {
    motorState = false;
    digitalWrite(MOTOR_RELAY, HIGH);
    digitalWrite(MOTOR_LED, LOW);
  }
}


/* ================= GEYSER ================= */
void geyser() {
  tempSensor.requestTemperatures();
  temperatureC = tempSensor.getTempCByIndex(0);

  digitalWrite(COLD_LED, temperatureC < 40);
  digitalWrite(HOT_LED, temperatureC >=40);
}

/* ================= AUTO SYSTEMS ================= */
void autoSystems() {
  now = millis();

  if (irrState && now - irrLast >= irrRunTime) {
    irrState = false;
    digitalWrite(IRR_LED, LOW);
  }

  if (solarState && now - solarLast >= solarRunTime) {
    solarState = false;
    digitalWrite(SOLAR_LED, LOW);
  }

  if (roState && now - roLast >= roRunTime) {
    roState = false;
    digitalWrite(RO_LED, LOW);
  }
}

/* ================= STATUS API ================= */
void handleStatus() {
  now = millis();
  long irrRemaining = irrState ? max(0UL, (irrRunTime - (now - irrLast)) / 1000) : 0;
long solarRemaining = solarState ? max(0UL, (solarRunTime - (now - solarLast)) / 1000) : 0;
long roRemaining = roState ? max(0UL, (roRunTime - (now - roLast)) / 1000) : 0;

long irrNext  = !irrState ? max(0UL, (irrInterval - (now - irrLast)) / 1000) : 0;
long solarNext= !solarState ? max(0UL, (solarInterval - (now - solarLast)) / 1000) : 0;
long roNext   = !roState ? max(0UL, (roInterval - (now - roLast)) / 1000) : 0;

  String json = "{";
  json += "\"level\":" + String(waterPercent, 1) + ",";
  json += "\"month\":" + String(monthlyLiters, 1) + ",";
  json += "\"temp\":" + String(temperatureC, 1) + ",";
  json += "\"motor\":" + String(motorState ? "true" : "false") + ",";
  json += "\"irr\":" + String(irrRemaining) + ",";
  json += "\"sol\":" + String(solarRemaining) + ",";
  json += "\"ro\":" + String(roRemaining) + ",";
  json += "\"irrNext\":" + String(irrNext) + ",";
  json += "\"solNext\":" + String(solarNext) + ",";
  json += "\"roNext\":" + String(roNext);
  json += "}";
  server.send(200, "application/json", json);
}



/* ================= ROOT ================= */
void handleRoot() {
  server.send(
    200,
    "text/html",
    R"rawliteral(
<!DOCTYPE html>
<html lang="en" class=""><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smart Water Automation</title>

<style>
:root {
  --bg:#0a0a0f;
  --glass:rgba(255,255,255,.08);
  --accent:#3b82f6;
  --accent-glow:#60a5fa;
  --success:#10b981;
  --success-glow:#34d399;
  --running:#f59e0b;
  --running-glow:#fbbf24;
  --text-primary:#f8fafc;
  --text-secondary:#cbd5e1;
  --shadow-medium:0 10px 15px -3px rgba(0,0,0,.1);
  --shadow-heavy:0 20px 25px -5px rgba(0,0,0,.2);
}

* { box-sizing:border-box; }

body {
  margin:0;
  font-family:system-ui,sans-serif;
  background:linear-gradient(135deg,#0a0a0f,#1a1a2e);
  color:var(--text-primary);
}

.container {
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(320px,1fr));
  gap:20px;
  padding:20px;
  max-width:1400px;
  margin:auto;
}

.card {
  background:linear-gradient(145deg,var(--glass),rgba(255,255,255,.02));
  border-radius:24px;
  padding:24px;
  box-shadow:var(--shadow-medium);
  position:relative;
}

.card.running {
  box-shadow:0 0 30px var(--running-glow);
}

h2,h3 { margin:0 0 16px; }
.tank-wrapper {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 14px;
  height: 340px;
}

.tank-section {
  display:flex;
  gap:40px;
  flex-wrap:wrap;
  justify-content:center;
}
.level-bar {
  width: 42px;
  height: 320px;
  background: linear-gradient(
    to top,
    #ef4444 0%,
    #f59e0b 50%,
    #10b981 100%
  );
  border-radius: 24px;
}

.pointer {
  position:absolute;
  left:52px;
  width:32px;
  height:5px;
  background:white;
  border-radius:4px;
}.tank {
  width: 160px;
  height: 320px;
  border-radius: 24px;
  border: 2px solid #64748b;
  position: relative;
  overflow: hidden;
}
.water {
  position: absolute;
  bottom: 0;
  width: 100%;
  height: 0%;
  background: linear-gradient(180deg, #0ea5e9, #7dd3fc);
  transition: height 0.8s ease;
}
.pointer {
  position: absolute;
  left: 46px;               /* between bar & tank */
  width: 26px;
  height: 6px;
  background: #e5e7eb;
  border-radius: 6px;
  box-shadow: 0 0 10px #60a5fa;
  transform: translateY(50%);
}
.status {
  margin-bottom: 12px;
  padding: 10px;
  border-radius: 12px;
  font-weight: bold;
  text-align: center;
  font-size: 18px;
}

.status.on {
  background: #16a34a;
  color: white;
  box-shadow: 0 0 15px #22c55e;
}

.status.off {
  background: #dc2626;
  color: white;
  box-shadow: 0 0 15px #ef4444;
}



.data-list p {
  margin:6px 0;
  color:var(--text-secondary);
}

button {
  width:100%;
  padding:14px;
  border:none;
  border-radius:16px;
  background:var(--accent);
  color:white;
  font-size:16px;
  cursor:pointer;
}
    .progress {
  width: 100%;
  height: 4px;
  background: rgba(255,255,255,0.12);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  width: 0%;
  background: #22c55e; /* neon green */
  box-shadow: 0 0 6px #22c55e, 0 0 12px rgba(34,197,94,0.6);
  transition: width 0.5s linear;
}



button.running {
  background:var(--running);
}
</style>
</head>

<body>
<div class="container">

<div class="card" style="grid-column:1/-1">
<h2>Water Tank Monitoring</h2>
<div class="tank-section">

<div><div class="tank-wrapper">
  <div class="level-bar"></div>
  <div id="pointer" class="pointer"></div>
  <div class="tank">
    <div id="water" class="water"></div>
  </div>
</div>

</div>

<div class="data-list">
  <p>Level: <span id="level">0</span>%</p>
  <p>Temperature: <span id="temp">0</span> °C</p>
  <p>Monthly Usage: <span id="month">0</span> L</p>
</div>

</div>
</div>

<div class="card" id="motorCard">
<h3>Motor Pump</h3>

<div id="motorStatus" class="status off">
  ● OFF
</div>

<button id="motorBtn" onclick="fetch('/motor')">Turn On</button>

</div>

<div class="card" id="irrCard">
<h3>Irrigation</h3>

<div id="irrStatus" class="status off">
  ● IDLE
</div>

<p>Next in: <span id="irr">--</span></p>
    <div class="progress">
  <div id="irrBar" class="progress-fill"></div>
</div>

<button id="irrBtn" onclick="fetch('/irr')">Run Now</button>

</div>

<div class="card" id="solCard">
<h3>Solar Wash</h3>

<div id="solStatus" class="status off">
  ● IDLE
</div>

<p>Next in: <span id="sol">--</span></p>
    <div class="progress">
  <div id="solBar" class="progress-fill"></div>
</div>

<button id="solBtn" onclick="fetch('/solar')">Run Now</button>
</div>

<div class="card" id="roCard">
<h3>RO System</h3>

<div id="roStatus" class="status off">
  ● IDLE
</div>

<p>Next in: <span id="ro">--</span></p>
    <div class="progress">
  <div id="roBar" class="progress-fill"></div>
</div>

<button id="roBtn" onclick="fetch('/ro')">Run Now</button>
</div>

</div>
<script>
function formatTime(sec){
  sec = Math.max(0, sec);
  let d = Math.floor(sec / 86400);
  sec %= 86400;
  let h = Math.floor(sec / 3600);
  sec %= 3600;
  let m = Math.floor(sec / 60);
  let s = sec % 60;
  return d + ":" + String(h).padStart(2,'0') + ":" +
         String(m).padStart(2,'0') + ":" +
         String(s).padStart(2,'0');
}

function updateRunCard(id, sec){
  const card = document.getElementById(id + "Card");
  const btn  = document.getElementById(id + "Btn");
  if (sec > 0 && sec <= 10) {
    card.classList.add("running");
    btn.classList.add("running");
    btn.innerText = "Running...";
  } else {
    card.classList.remove("running");
    btn.classList.remove("running");
    btn.innerText = "Run Now";
  }

}const irrRunTime   = 10;  // must match ESP32 irrRunTime /1000
const solarRunTime = 10;
const roRunTime    = 10;

setInterval(() => {
  fetch("/status")
    .then(r => r.json())
    .then(d => {
      // ===== MOTOR STATUS =====
motorStatus.innerText = d.motor === "true" ? "● ON" : "● OFF";
motorStatus.className = "status " + (d.motor === "true" ? "on" : "off");

// Optional: update the button text too
motorBtn.innerText = d.motor === "true" ? "Turn Off" : "Turn On";

      // ===== BASIC DATA =====
      level.innerText = d.level;
      temp.innerText  = d.temp;
      month.innerText = d.month;
      water.style.height = d.level + "%";
      pointer.style.bottom = d.level + "%";

      // ===== NEXT RUN =====
      irr.innerText = formatTime(d.irrNext);
      sol.innerText = formatTime(d.solNext);
      ro.innerText  = formatTime(d.roNext);

      // ===== IRRIGATION BAR =====
      if (d.irr > 0) {
        irrStatus.innerText = "● IRRIGATION RUNNING";
        irrStatus.className = "status on";
        let percent = (d.irr / irrRunTime) * 100;   // decreasing
        irrBar.style.width = percent + "%";
        irrBar.style.opacity = "1";
      } else {
        irrStatus.innerText = "● IDLE";
        irrStatus.className = "status off";
        irrBar.style.width = "0%";
        irrBar.style.opacity = "0.3";
      }

      // ===== SOLAR BAR =====
      if (d.sol > 0) {
        solStatus.innerText = "● SOLAR RUNNING";
        solStatus.className = "status on";
        let percent = (d.sol / solarRunTime) * 100;
        solBar.style.width = percent + "%";
        solBar.style.opacity = "1";
      } else {
        solStatus.innerText = "● IDLE";
        solStatus.className = "status off";
        solBar.style.width = "0%";
        solBar.style.opacity = "0.3";
      }

      // ===== RO BAR =====
      if (d.ro > 0) {
        roStatus.innerText = "● RO RUNNING";
        roStatus.className = "status on";
        let percent = (d.ro / roRunTime) * 100;
        roBar.style.width = percent + "%";
        roBar.style.opacity = "1";
      } else {
        roStatus.innerText = "● IDLE";
        roStatus.className = "status off";
        roBar.style.width = "0%";
        roBar.style.opacity = "0.3";
      }

      // ===== UPDATE CARD =====
      updateRunCard("irr", d.irr);
      updateRunCard("sol", d.sol);
      updateRunCard("ro",  d.ro);
    });
}, 1000);

</script>



</body></html>
)rawliteral"
  );
}
void updateTankLEDs() {
  if (waterPercent < 30) {
    digitalWrite(tankLEDs[0], HIGH);
    digitalWrite(tankLEDs[1], LOW);
    digitalWrite(tankLEDs[2], LOW);
  } else if (waterPercent < 70) {
    digitalWrite(tankLEDs[0], HIGH);
    digitalWrite(tankLEDs[1], HIGH);
    digitalWrite(tankLEDs[2], LOW);
  } else {
    digitalWrite(tankLEDs[0], HIGH);
    digitalWrite(tankLEDs[1], HIGH);
    digitalWrite(tankLEDs[2], HIGH);
  }
}



/* ================= SETUP ================= */
void setup() {
  for (int i = 0; i < TANK_LED_COUNT; i++) {
  pinMode(tankLEDs[i], OUTPUT);
  digitalWrite(tankLEDs[i], LOW);
}

  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  pinMode(MOTOR_RELAY, OUTPUT);
  pinMode(MOTOR_LED, OUTPUT);

  pinMode(IRR_LED, OUTPUT);
  pinMode(SOLAR_LED, OUTPUT);
  pinMode(RO_LED, OUTPUT);

  pinMode(COLD_LED, OUTPUT);
  pinMode(HOT_LED, OUTPUT);

  digitalWrite(MOTOR_RELAY, HIGH);

  tempSensor.begin();

  WiFi.begin(ssid, password);
  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected");
  Serial.println(WiFi.localIP());
server.on("/", handleRoot);

  server.on("/status", handleStatus);

 server.on("/motor", [] {
  // If motor is OFF and tank is full, do NOT allow turning ON
  if (!motorState && waterPercent >= MANUAL_STOP_LEVEL) {
    server.send(403, "text/plain", "Tank Full, cannot start motor");
    return;
  }

  // Toggle motor manually
  motorManual = true;          // mark as manual mode
  motorState = !motorState;    // switch motor ON/OFF

  // Update relay and LED immediately
  if (motorState) {
    digitalWrite(MOTOR_RELAY, LOW);  // ON
    digitalWrite(MOTOR_LED, HIGH);
  } else {
    digitalWrite(MOTOR_RELAY, HIGH); // OFF
    digitalWrite(MOTOR_LED, LOW);
    motorManual = false;              // stop manual mode if motor is off
  }

  // Send response to client
  server.send(200, "text/plain", motorState ? "Motor ON" : "Motor OFF");
});




  server.on("/irr", [] {
    irrState = true;
    irrLast = millis();
    digitalWrite(IRR_LED, HIGH);
    server.send(200, "text/plain", "OK");
  });

  server.on("/solar", [] {
    solarState = true;
    solarLast = millis();
    digitalWrite(SOLAR_LED, HIGH);
    server.send(200, "text/plain", "OK");
  });

  server.on("/ro", [] {
    roState = true;
    roLast = millis();
    digitalWrite(RO_LED, HIGH);
    server.send(200, "text/plain", "OK");
  });
  digitalWrite(MOTOR_RELAY, HIGH); // OFF
digitalWrite(MOTOR_LED, LOW);

  server.begin();
}

/* ================= LOOP ================= */
void loop() {
  server.handleClient();

  static unsigned long lastLoop = 0;
  if (millis() - lastLoop >= 200) {
    lastLoop = millis();

    updateTank();
    updateTankLEDs();
    motorAuto();
    geyser();
    autoSystems();
  }
}
'''

# Display code with syntax highlighting
st.subheader("📜 ESP32 Firmware Code")
st.code(esp32_code, language="cpp")

st.markdown("---")
