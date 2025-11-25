import ubluetooth

# --- Configuración de Pines ---
PIN_SDA = 21
PIN_SCL = 22

# Pines de Feedback Visual (Postura y BLE)
PIN_LED_RED = 25      # Mala Postura
PIN_LED_GREEN = 33    # Buena Postura
PIN_LED_BLUE = 32     # Estado Bluetooth

# Pin Exclusivo Batería (LED Integrado)
PIN_LED_BAT_LOW = 2   # Solo se enciende al hibernar

PIN_BUZZER = 26
PIN_VIBRATOR = 18
PIN_SERVO = 19
PIN_BAT = 27          # Entrada ADC Batería

# --- Constantes del Servo ---
SERVO_FREQ = 50
SERVO_ALERT_ANGLE = 90
SERVO_IDLE_ANGLE = 0
SERVO_DEBOUNCE_MS = 300
SERVO_HOLD_MS = 200

# --- Gestión de Energía ---
BAT_DIVIDER_FACTOR = 2.0  
BAT_MIN_VOLTAGE = 4.7  # Voltaje mínimo para hibernar. Recomendado: 4.7V     
BAT_CHECK_INTERVAL_MS = 300000 # 5 minutos

# --- UUIDs de Bluetooth BLE ---
POSTURE_SERVICE_UUID = ubluetooth.UUID("0000180f-0000-1000-8000-00805f9b34fb")
POSTURE_STATUS_CHAR_UUID = ubluetooth.UUID("00002a19-0000-1000-8000-00805f9b34fb")
THRESHOLD_ANGLE_CHAR_UUID = ubluetooth.UUID("00002a1b-0000-1000-8000-00805f9b34fb")
CALIBRATE_CHAR_UUID = ubluetooth.UUID("00002a1c-0000-1000-8000-00805f9b34fb")
BUZZER_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a1e-0000-1000-8000-00805f9b34fb")
VIBRATOR_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a1f-0000-1000-8000-00805f9b34fb")
LEDS_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a20-0000-1000-8000-00805f9b34fb")
NOTIFY_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a21-0000-1000-8000-00805f9b34fb")
SYSTEM_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a22-0000-1000-8000-00805f9b34fb")