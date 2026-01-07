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

const char* ssid = "Zala";
const char* password = "88888888";

/* ================= PINS ================= */
#define TRIG_PIN 5
#define ECHO_PIN 18

#define MOTOR_RELAY 23
#define MOTOR_LED   22

#define TANK_LED_COUNT 8
int tankLEDs[TANK_LED_COUNT] = {14, 16, 25, 26, 27, 32, 33, 21};

#define IRR_LED   13
#define SOLAR_LED 16
#define RO_LED    15

#define COLD_LED 12
#define HOT_LED  2

#define ONE_WIRE_BUS 4

/* ================= OBJECTS ================= */
WebServer server(80);
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);

/* ================= VARIABLES ================= */
float tankHeight = 100.0;
float tankArea   = 10000.0;
float waterPercent = 0;
float lastVolumeLiters = 0;
float monthlyLiters = 0;
float temperatureC = 0;

bool motorState = false;
bool motorManual = false;
bool irrState = false, solarState = false, roState = false;

unsigned long now;
unsigned long irrLast = 0, solarLast = 0, roLast = 0;

unsigned long irrInterval   = 86400000UL;
unsigned long solarInterval = 864000000UL;
unsigned long roInterval    = 43200000UL;

unsigned long irrRunTime = 10000;
unsigned long solarRunTime = 10000;
unsigned long roRunTime = 10000;

/* ================= ULTRASONIC ================= */
float getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return tankHeight;
  return duration * 0.034 / 2;
}

/* ================= TANK ================= */
void updateTank() {
  float d = getDistance();
  float h = constrain(tankHeight - d, 0, tankHeight);
  waterPercent = (h / tankHeight) * 100.0;

  float volumeLiters = (h * tankArea) / 1000.0;
  if (volumeLiters > lastVolumeLiters)
    monthlyLiters += volumeLiters - lastVolumeLiters;
  lastVolumeLiters = volumeLiters;

  int c = map(waterPercent, 0, 100, 0, TANK_LED_COUNT);
  for (int i = 0; i < TANK_LED_COUNT; i++)
    digitalWrite(tankLEDs[i], i < c);
}

/* ================= MOTOR ================= */
void motorAuto() {
  if (motorManual) return;

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
  digitalWrite(HOT_LED, temperatureC > 60);
}

/* ================= LOOP ================= */
void loop() {
  server.handleClient();
  updateTank();
  motorAuto();
  geyser();
  delay(100);
}
'''

# Display code with syntax highlighting
st.subheader("📜 ESP32 Firmware Code")
st.code(esp32_code, language="cpp")

st.markdown("---")
st.markdown(
    "✅ **Tip:** You can copy this code directly into the Arduino IDE or PlatformIO."
)
