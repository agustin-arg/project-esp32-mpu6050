# posture_corrector.py
# (todo igual salvo las partes mostradas abajo; copialo entero si querés)

import ubluetooth
import struct
import time
import math
from machine import Pin, I2C, PWM

# --- CLASE MPU6050 (sin cambios) ---
class MPU6050:
    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr
        # Despertar el sensor MPU6050
        self.i2c.writeto(self.addr, b'\x6B\x00')

    def _read_word_2c(self, reg):
        val = self.i2c.readfrom_mem(self.addr, reg, 2)
        val = (val[0] << 8) | val[1]
        if val >= 0x8000:
            return -((65535 - val) + 1)
        else:
            return val

    def get_accel_data(self, g=False):
        x = self._read_word_2c(0x3B)
        y = self._read_word_2c(0x3D)
        z = self._read_word_2c(0x3F)
        if g:
            x /= 16384.0
            y /= 16384.0
            z /= 16384.0
        return {'x': x, 'y': y, 'z': z}

    def get_gyro_data(self):
        x = self._read_word_2c(0x43)
        y = self._read_word_2c(0x45)
        z = self._read_word_2c(0x47)
        x /= 131.0
        y /= 131.0
        z /= 131.0
        return {'x': x, 'y': y, 'z': z}

# --- PINES (Constantes de módulo) ---
PIN_SDA = 21
PIN_SCL = 22
PIN_LED_RED = 25      # Postura incorrecta
PIN_LED_GREEN = 33    # Postura correcta
PIN_LED_BLUE = 32     # Estado de BLE
PIN_BUZZER = 26
PIN_VIBRATOR = 18

# --- UUIDs (igual que antes) ---
_POSTURE_SERVICE_UUID = ubluetooth.UUID("0000180f-0000-1000-8000-00805f9b34fb")
_POSTURE_STATUS_CHAR_UUID = ubluetooth.UUID("00002a19-0000-1000-8000-00805f9b34fb")
_THRESHOLD_ANGLE_CHAR_UUID = ubluetooth.UUID("00002a1b-0000-1000-8000-00805f9b34fb")
_CALIBRATE_CHAR_UUID = ubluetooth.UUID("00002a1c-0000-1000-8000-00805f9b34fb")
_BUZZER_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a1e-0000-1000-8000-00805f9b34fb")
_VIBRATOR_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a1f-0000-1000-8000-00805f9b34fb")
_LEDS_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a20-0000-1000-8000-00805f9b34fb")
_NOTIFY_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a21-0000-1000-8000-00805f9b34fb")
# nuevo UUID para control de encendido/apagado del sistema
_SYSTEM_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a22-0000-1000-8000-00805f9b34fb")

class PostureCorrector:
    def __init__(self):
        # Hardware
        self.led_red = Pin(PIN_LED_RED, Pin.OUT, value=0)
        self.led_green = Pin(PIN_LED_GREEN, Pin.OUT, value=0)
        self.led_blue = Pin(PIN_LED_BLUE, Pin.OUT, value=0)
        self.buzzer = PWM(Pin(PIN_BUZZER), freq=220, duty=0)
        self.vibrator = Pin(PIN_VIBRATOR, Pin.OUT, value=0)
        
        i2c = I2C(0, sda=Pin(PIN_SDA), scl=Pin(PIN_SCL))
        self.mpu = MPU6050(i2c)
        
        # Estado
        self.calibrated_angle = 0.0
        self.threshold_angle = 20.0
        self.is_calibrated = False
        self.is_bad_posture = False
        self.buzzer_enabled = True
        self.vibrator_enabled = True
        self.leds_enabled = True
        self.notifications_enabled = True

        # nuevo: control de sistema (on/off). Cuando False no hace controles continuos pero acepta writes.
        self.system_enabled = True

        # Flag para pedir calibración desde el IRQ
        self._calibrate_request = False
        self._calibrating = False  # para evitar reentradas

        # BLE
        self.setup_ble()

    def setup_ble(self):
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self.ble_irq)
        
        status_char = (_POSTURE_STATUS_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_NOTIFY,)
        threshold_char = (_THRESHOLD_ANGLE_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        calibrate_char = (_CALIBRATE_CHAR_UUID, ubluetooth.FLAG_WRITE,)
        buzzer_char = (_BUZZER_CONTROL_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        vibrator_char = (_VIBRATOR_CONTROL_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        leds_char = (_LEDS_CONTROL_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        notify_char = (_NOTIFY_CONTROL_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        # nuevo: characteristic para encender/apagar sistema
        system_char = (_SYSTEM_CONTROL_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)

        posture_service = (_POSTURE_SERVICE_UUID, (status_char, threshold_char, calibrate_char, buzzer_char,
                                                   vibrator_char, leds_char, notify_char, system_char),)
        
        handles = self.ble.gatts_register_services((posture_service,))
        (self.status_handle, self.threshold_handle, self.calibrate_handle, self.buzzer_handle, 
         self.vibrator_handle, self.leds_handle, self.notify_handle, self.system_handle) = handles[0]
        
        # Valores iniciales
#         self.ble.gatts_write(self.threshold_handle, struct.pack('<B', int(self.threshold_angle)))
        self.ble.gatts_write(self.buzzer_handle, struct.pack('<B', 1))
        self.ble.gatts_write(self.vibrator_handle, struct.pack('<B', 1))
        self.ble.gatts_write(self.leds_handle, struct.pack('<B', 1))
        self.ble.gatts_write(self.notify_handle, struct.pack('<B', 1))
        # estado inicial del sistema (1 = encendido)
        self.ble.gatts_write(self.system_handle, struct.pack('<B', 1))

        self.adv_payload = self._adv_payload(name='Posture', services=[_POSTURE_SERVICE_UUID])
        self.start_advertising()
        self.conn_handle = None

    def start_advertising(self):
        self.ble.gap_advertise(100000, self.adv_payload)
        print("Iniciando advertising BLE...")

    def _adv_payload(self, name, services):
        payload = bytearray()
        def _append(data_type, value):
            nonlocal payload
            value_len = 16 if isinstance(value, ubluetooth.UUID) else len(value)
            payload += struct.pack('BB', value_len + 1, data_type) + value
        _append(0x01, b'\x06')
        _append(0x07, services[0])
        _append(0x09, name.encode())
        return payload

    def ble_irq(self, event, data):
        # Manejo mínimo de eventos BLE
        if event == 1: # _IRQ_CENTRAL_CONNECT
            # data == (conn_handle, addr_type, addr)
            conn_handle, addr_type, addr = data
            self.conn_handle = conn_handle
            if addr:
                mac = ':'.join('{:02X}'.format(b) for b in addr)
                print(f"Conectado: {mac}")
            else:
                print(f"Conectado: {self.conn_handle}")
            self.led_blue.on()
        elif event == 2: # _IRQ_CENTRAL_DISCONNECT
            print("Desconectado.")
            self.conn_handle = None
            self.led_blue.off()
            self.start_advertising()
        elif event == 3: # _IRQ_GATTS_WRITE
            _, value_handle = data
            value = self.ble.gatts_read(value_handle)
            # proteger unpack si recibe tamaño distinto
            if len(value) >= 1:
                state = struct.unpack('<B', value[:1])[0] == 1
            else:
                state = False

            if value_handle == self.threshold_handle:
                # aceptar cambio de umbral siempre
                self.threshold_angle = float(struct.unpack('<B', value[:1])[0])
                print(f"Nuevo umbral: {self.threshold_angle} grados")
            elif value_handle == self.calibrate_handle:
                # NO llamar calibrate() desde el IRQ: pedir calibración para que se ejecute en el loop
                print("Solicitud de calibración recibida (marcando flag).")
                self._calibrate_request = True
            elif value_handle == self.buzzer_handle:
                self.buzzer_enabled = state
                print(f"Buzzer: {'activado' if state else 'desactivado'}")
                # aplicar cambio inmediato si el sistema está encendido
                if not self.system_enabled:
                    # si el sistema está apagado queremos que las escrituras sigan pudiendo cambiar el flag,
                    # pero en estado apagado los actuadores deben permanecer apagados físicamente
                    self.buzzer.duty(0)
            elif value_handle == self.vibrator_handle:
                self.vibrator_enabled = state
                print(f"Vibrador: {'activado' if state else 'desactivado'}")
                if not self.system_enabled:
                    try:
                        self.vibrator.off()
                    except Exception:
                        try:
                            self.vibrator.value(0)
                        except Exception:
                            pass
            elif value_handle == self.leds_handle:
                self.leds_enabled = state
                print(f"LEDs de estado: {'activados' if state else 'desactivados'}")
                if not self.system_enabled:
                    self.led_red.off()
                    self.led_green.off()
                    self.led_blue.on()
            elif value_handle == self.notify_handle:
                self.notifications_enabled = state
                print(f"Notificaciones BLE: {'activadas' if state else 'desactivadas'}")
            elif value_handle == self.system_handle:
                # controlar encendido/apagado del monitoreo continuo
                self.system_enabled = state
                print(f"Sistema {'encendido' if state else 'apagado'}")
                if not state:
                    # apagar actuadores inmediatamente al apagar el sistema
                    try:
                        self.buzzer.duty(0)
                    except Exception:
                        pass
                    try:
                        self.vibrator.off()
                    except Exception:
                        try:
                            self.vibrator.value(0)
                        except Exception:
                            pass
                    self.led_red.off()
                    self.led_green.off()
                    # LED azul debe indicar estado BLE activo
                    self.led_blue.on()
                try:
                    self.ble.gatts_write(self.system_handle, struct.pack('<B', 1 if state else 0))
                except Exception:
                    pass

    def calculate_pitch(self, accel_data):
        x, y, z = accel_data['x'], accel_data['y'], accel_data['z']
        pitch = math.atan2(z, math.sqrt(y**2 + x**2))
        return math.degrees(pitch)
        
    def calibrate(self):
        # Esta función debe ejecutarse fuera del IRQ
        if self._calibrating:
            print("Ya se estaba calibrando, ignorando nueva petición.")
            return
        self._calibrating = True
        print("Calibrando...")
        for _ in range(3):
            self.led_blue.on(); time.sleep_ms(100)
            self.led_blue.off(); time.sleep_ms(100)
        
        accel_data = self.mpu.get_accel_data()
        self.calibrated_angle = self.calculate_pitch(accel_data)
        self.is_calibrated = True
        
        self.led_green.on(); time.sleep_ms(1000); self.led_green.off()
        print(f"Calibración completa. Ángulo: {self.calibrated_angle:.2f}")
        # restablecer flags
        self._calibrate_request = False
        self._calibrating = False
        if self.conn_handle is not None:
            self.led_blue.on()

    def run(self):
        print("Corrector de postura iniciado.")
        last_notified_state = None
        
        while True:
            # si hay una solicitud de calibración desde el IRQ, la ejecutamos acá
            if self._calibrate_request and not self._calibrating:
                time.sleep_ms(10)
                self.calibrate()
                time.sleep_ms(50)
                continue

            # si el sistema está apagado, NO hacer monitoreo continuo ni alertas,
            # pero seguir permitiendo escrituras a threshold/calibrate/actuadores.
            if not self.system_enabled:
                # comportamiento LED BLE para mantener responsividad
                if self.conn_handle is None:
                    self.led_blue.on(); time.sleep_ms(50)
                    self.led_blue.off(); time.sleep_ms(950)
                else:
                    self.led_blue.on()
                time.sleep_ms(100)
                continue

            # si no está calibrado, no hacer lecturas de postura pero ceder CPU
            if not self.is_calibrated:
                if self.conn_handle is None:
                    self.led_blue.on(); time.sleep_ms(50)
                    self.led_blue.off(); time.sleep_ms(950)
                else:
                    self.led_blue.on()
                time.sleep_ms(100)
                continue

            # Normal operation: leer sensor y evaluar postura
            accel_data = self.mpu.get_accel_data()
            current_angle = self.calculate_pitch(accel_data)
            deviation = abs(current_angle - self.calibrated_angle)
            
            self.is_bad_posture = deviation > self.threshold_angle

            # --- Control de Alertas Individuales ---
            if self.leds_enabled:
                self.led_red.value(self.is_bad_posture)
                self.led_green.value(not self.is_bad_posture)
            else:
                self.led_red.off()
                self.led_green.off()

            if self.buzzer_enabled:
                if self.is_bad_posture:
                    self.buzzer.duty(512)
                else:
                    self.buzzer.duty(0)
            else:
                self.buzzer.duty(0)

            if self.vibrator_enabled:
                self.vibrator.value(self.is_bad_posture)
            else:
                self.vibrator.off()

            if self.notifications_enabled and self.is_bad_posture != last_notified_state:
                if self.conn_handle is not None:
                    try:
                        data = struct.pack('<B', 1 if self.is_bad_posture else 0)
                        self.ble.gatts_notify(self.conn_handle, self.status_handle, data)
                        last_notified_state = self.is_bad_posture
                    except OSError as e:
                        print(f"Error al notificar: {e}")
            
            time.sleep_ms(100)

if __name__ == "__main__":
    corrector = PostureCorrector()
    corrector.run()
