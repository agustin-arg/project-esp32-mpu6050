# posture_corrector.py

import ubluetooth
import struct
import utime
import math
from machine import Pin, I2C, PWM

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

PIN_SDA = 21
PIN_SCL = 22
PIN_LED_RED = 25      # Postura incorrecta
PIN_LED_GREEN = 33    # Postura correcta
PIN_LED_BLUE = 32     # Estado de BLE
PIN_BUZZER = 26
PIN_VIBRATOR = 18
PIN_SERVO = 19

_POSTURE_SERVICE_UUID = ubluetooth.UUID("0000180f-0000-1000-8000-00805f9b34fb")
_POSTURE_STATUS_CHAR_UUID = ubluetooth.UUID("00002a19-0000-1000-8000-00805f9b34fb")
_THRESHOLD_ANGLE_CHAR_UUID = ubluetooth.UUID("00002a1b-0000-1000-8000-00805f9b34fb")
_CALIBRATE_CHAR_UUID = ubluetooth.UUID("00002a1c-0000-1000-8000-00805f9b34fb")
_BUZZER_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a1e-0000-1000-8000-00805f9b34fb")
_VIBRATOR_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a1f-0000-1000-8000-00805f9b34fb")
_LEDS_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a20-0000-1000-8000-00805f9b34fb")
_NOTIFY_CONTROL_CHAR_UUID = ubluetooth.UUID("00002a21-0000-1000-8000-00805f9b34fb")
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

        # nuevo: servomotor
        try:
            self.servo = PWM(Pin(PIN_SERVO), freq=50, duty=0)
        except Exception:
            self.servo = None
        self.servo_enabled = True
        self.servo_alert_angle = 180   # ángulo cuando hay mala postura
        self.servo_idle_angle = 0     # ángulo en reposo

        # Servomotor
        try:
            self.servo = PWM(Pin(PIN_SERVO), freq=50, duty=0)
        except Exception:
            self.servo = None
        self.servo_enabled = True
        self.servo_alert_angle = 90    # reducido de 180° a 90° para ajustarse al rango real
        self.servo_idle_angle = 0      # ángulo en reposo

        # Debounce y gestión de señal para evitar oscilaciones rápidas
        self._servo_last_applied_state = False          # estado aplicado al servo (False=buena, True=mala)
        self._servo_candidate_state = None              # estado observado actualmente candidato a aplicar
        self._servo_candidate_since = 0                 # ticks_ms cuando comenzó el candidato
        self.servo_debounce_ms = 300                    # tiempo mínimo estable antes de mover servo
        self.servo_hold_ms = 200                        # tiempo en ms para mantener la señal PWM luego de mover
        self._servo_hold_until = 0                      # ticks_ms hasta cuando mantener señal activa

        # Control de sistema (on/off). Cuando False no hace controles continuos pero acepta writes.
        self.system_enabled = True

        # Flag para pedir calibración desde el IRQ
        self._calibrate_request = False
        self._calibrating = False  # para evitar reentradas

        # BLE
        self.setup_ble()

        # Parámetros y estado del filtro complementario (Sensor Fusion)
        self.filtered_pitch = 0.0                  # Ángulo filtrado
        self.last_time = utime.ticks_us()         # Marca de tiempo inicial (microsegundos)
        self.alpha = 0.98                          # Factor de ponderación (alpha para acelerómetro)

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
                    # apagar servo al apagar sistema
                    try:
                        if self.servo is not None:
                            self.servo.duty(0)
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

    def calculate_accel_pitch(self, accel_data):
        x, y, z = accel_data['x'], accel_data['y'], accel_data['z']
        pitch = math.atan2(z, math.sqrt(y**2 + x**2))
        return math.degrees(pitch)

    def calculate_fused_pitch(self, accel_data, gyro_data):
        current_time = utime.ticks_us()
        delta_t = utime.ticks_diff(current_time, self.last_time) / 1000000.0
        
        if delta_t <= 0:
            delta_t = 0.001
        self.last_time = current_time
        accel_pitch = self.calculate_accel_pitch(accel_data)
        gyro_rate = gyro_data.get('y', 0.0)  # °/s
        gyro_change = gyro_rate * delta_t  # en grados
        self.filtered_pitch = (1.0 - self.alpha) * (self.filtered_pitch + gyro_change) + \
                              (self.alpha) * accel_pitch

        return self.filtered_pitch
        
    def calibrate(self):
        # Esta función debe ejecutarse fuera del IRQ
        if self._calibrating:
            print("Ya se estaba calibrando, ignorando nueva petición.")
            return
        self._calibrating = True
        print("Calibrando...")
        for _ in range(3):
            self.led_blue.on(); utime.sleep_ms(100)
            self.led_blue.off(); utime.sleep_ms(100)
        
        accel_data = self.mpu.get_accel_data()
        gyro_data = self.mpu.get_gyro_data()
        # Resetear la marca de tiempo del filtro para evitar un Δt grande en la primera fusión
        self.last_time = utime.ticks_us()
        self.calibrated_angle = self.calculate_fused_pitch(accel_data, gyro_data)
        self.is_calibrated = True

        # Inicializar estado del filtro con el ángulo calibrado
        self.filtered_pitch = self.calibrated_angle
        
        self.led_green.on(); utime.sleep_ms(1000); self.led_green.off()
        print(f"Calibración completa. Ángulo: {self.calibrated_angle:.2f}")
        # restablecer flags
        self._calibrate_request = False
        self._calibrating = False
        if self.conn_handle is not None:
            self.led_blue.on()

    # --- Métodos para controlar servo ---
    def _angle_to_duty(self, angle):
        # mapea 0-90º a rango de duty ajustado para el servo real
        min_duty = 25
        max_duty = 75
        if angle is None:
            return 0
        a = max(0, min(90, int(angle)))  # limitado a 90° en lugar de 180°
        return int(min_duty + (a / 90.0) * (max_duty - min_duty))

    def set_servo_angle(self, angle):
        # Aplica señal PWM y programa un periodo de hold tras el movimiento
        if self.servo is None:
            return
        try:
            # convertir ángulo a duty (misma función previa)
            duty = self._angle_to_duty(angle)
            # aplicar señal
            self.servo.duty(duty)
            # programar hasta cuando mantener la señal
            self._servo_hold_until = utime.ticks_add(utime.ticks_ms(), self.servo_hold_ms)
        except Exception:
            pass

    def run(self):
        print("Corrector de postura iniciado.")
        last_notified_state = None
        
        while True:
            # si hay una solicitud de calibración desde el IRQ, la ejecutamos acá
            if self._calibrate_request and not self._calibrating:
                utime.sleep_ms(10)
                self.calibrate()
                utime.sleep_ms(50)
                continue

            # si el sistema está apagado, NO hacer monitoreo continuo ni alertas,
            # pero seguir permitiendo escrituras a threshold/calibrate/actuadores.
            if not self.system_enabled:
                # comportamiento LED BLE para mantener responsividad
                if self.conn_handle is None:
                    self.led_blue.on(); utime.sleep_ms(50)
                    self.led_blue.off(); utime.sleep_ms(950)
                else:
                    self.led_blue.on()
                utime.sleep_ms(100)
                continue

            # si no está calibrado, no hacer lecturas de postura pero ceder CPU
            if not self.is_calibrated:
                if self.conn_handle is None:
                    self.led_blue.on(); utime.sleep_ms(50)
                    self.led_blue.off(); utime.sleep_ms(950)
                else:
                    self.led_blue.on()
                utime.sleep_ms(100)
                continue

            # Normal operation: leer sensor y evaluar postura usando filtro complementario
            accel_data = self.mpu.get_accel_data()
            gyro_data = self.mpu.get_gyro_data()
            current_angle = self.calculate_fused_pitch(accel_data, gyro_data)
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

            # control del servomotor según postura con debounce y señal temporal
            if self.servo_enabled and self.servo is not None and self.system_enabled:
                now = utime.ticks_ms()
                observed = bool(self.is_bad_posture)

                # Si el candidato es distinto del observado, iniciar periodo de candidato
                if self._servo_candidate_state is None or self._servo_candidate_state != observed:
                    self._servo_candidate_state = observed
                    self._servo_candidate_since = now

                # Si el candidato lleva tiempo suficiente estable, aplicarlo
                if utime.ticks_diff(now, self._servo_candidate_since) >= self.servo_debounce_ms:
                    if self._servo_last_applied_state != self._servo_candidate_state:
                        # aplicar movimiento (solo cuando haya cambio estable)
                        angle = self.servo_alert_angle if self._servo_candidate_state else self.servo_idle_angle
                        self.set_servo_angle(angle)
                        self._servo_last_applied_state = self._servo_candidate_state

                # Si ya pasó el hold, desconectar la señal PWM para ahorrar corriente
                if utime.ticks_diff(now, self._servo_hold_until) >= 0 and self._servo_hold_until != 0:
                    try:
                        # quitar señal (duty 0)
                        self.servo.duty(0)
                        self._servo_hold_until = 0
                    except Exception:
                        pass
            else:
                # si servo deshabilitado o sistema apagado, asegurarse de quitar señal y resetear candidatos
                try:
                    if self.servo is not None:
                        self.servo.duty(0)
                except Exception:
                    pass
                self._servo_candidate_state = None
                self._servo_candidate_since = 0

            if self.notifications_enabled and self.is_bad_posture != last_notified_state:
                if self.conn_handle is not None:
                    try:
                        data = struct.pack('<B', 1 if self.is_bad_posture else 0)
                        self.ble.gatts_notify(self.conn_handle, self.status_handle, data)
                        last_notified_state = self.is_bad_posture
                    except OSError as e:
                        print(f"Error al notificar: {e}")
            
            utime.sleep_ms(100)

if __name__ == "__main__":
    corrector = PostureCorrector()
    corrector.run()
