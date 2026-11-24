"""
Simulasi perangkat ESP32 dengan Python + MQTT (paho-mqtt)

- Kirim suhu (simulasi DHT22) tiap 3 detik -> iot/<NIM>/sensor/suhu
- Terima perintah relay "ON"/"OFF"        <- iot/<NIM>/aktuator/relay  (GPIO 26)
- Terima nilai PWM 0-255                  <- iot/<NIM>/aktuator/pwm    (GPIO 2)

Install : pip install paho-mqtt
Jalankan: python esp32_sim.py
"""

import random
import time

import paho.mqtt.client as mqtt

# ====== KONFIGURASI (sesuaikan) ======
NIM = "2410020023"          # <-- pastikan ini NIM kamu
BROKER = "localhost"        # Mosquitto di laptop yang sama
PORT = 1883
INTERVAL = 3                # detik

TOPIC_SUHU = f"iot/{NIM}/sensor/suhu"
TOPIC_RELAY = f"iot/{NIM}/aktuator/relay"
TOPIC_PWM = f"iot/{NIM}/aktuator/pwm"
# Topik tambahan: umpan balik status ke dashboard
TOPIC_STATUS_RELAY = f"iot/{NIM}/status/relay"
TOPIC_STATUS_LED = f"iot/{NIM}/status/led"

PIN_RELAY = 26
PIN_LED = 2

# ====== STATE PERANGKAT ======
relay_state = "OFF"
pwm_value = 0
suhu = 28.0
client = None


def baca_dht22():
    """Simulasi pembacaan DHT22: suhu naik-turun pelan di sekitar 24-36 C."""
    global suhu
    suhu += random.uniform(-0.5, 0.5)
    suhu = max(24.0, min(36.0, suhu))
    return round(suhu, 1)


def set_relay(state):
    global relay_state
    relay_state = state
    # Kalau pakai Raspberry Pi asli: GPIO.output(PIN_RELAY, state == "ON")
    print(f"[RELAY] GPIO {PIN_RELAY} -> {state}")
    kirim_status()


def set_pwm(value):
    global pwm_value
    pwm_value = value
    persen = round(value / 255 * 100)
    # Kalau pakai Raspberry Pi asli: pwm.ChangeDutyCycle(persen)
    print(f"[PWM]   GPIO {PIN_LED} -> {value}/255 (~{persen}% kecerahan LED)")
    if value == 0:
        print("[LED]   MATI")
    else:
        print(f"[LED]   NYALA ({persen}%)")
    kirim_status()


def kirim_status():
    """Kirim status relay & LED ke dashboard (retain supaya langsung tampil)."""
    if client is None or not client.is_connected():
        return
    client.publish(TOPIC_STATUS_RELAY, f"Relay: {relay_state}", retain=True)
    if pwm_value == 0:
        teks_led = "LED: MATI"
    else:
        teks_led = f"LED: NYALA ({round(pwm_value / 255 * 100)}%)"
    client.publish(TOPIC_STATUS_LED, teks_led, retain=True)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Terhubung ke broker {BROKER}:{PORT}")
        client.subscribe([(TOPIC_RELAY, 0), (TOPIC_PWM, 0)])
        print(f"Subscribe: {TOPIC_RELAY}, {TOPIC_PWM}")
        kirim_status()
    else:
        print(f"Gagal konek, kode: {reason_code}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8").strip()

    if msg.topic == TOPIC_RELAY:
        perintah = payload.upper()
        if perintah in ("ON", "OFF"):
            set_relay(perintah)
        else:
            print(f"[RELAY] perintah tidak dikenal: {payload!r}")

    elif msg.topic == TOPIC_PWM:
        try:
            nilai = int(float(payload))
        except ValueError:
            print(f"[PWM]   nilai tidak valid: {payload!r}")
            return
        set_pwm(max(0, min(255, nilai)))  # batasi 0-255


def main():
    global client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()  # thread terpisah untuk menerima pesan

    set_relay("OFF")
    set_pwm(0)

    try:
        while True:
            t = baca_dht22()
            client.publish(TOPIC_SUHU, str(t))
            print(f"[SUHU]  publish {t} C -> {TOPIC_SUHU}")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\nBerhenti.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
