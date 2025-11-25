from machine import Pin, PWM
import utime
import config

class PostureActuators:
    def __init__(self):
        # Inicializar LEDs de Postura y BLE
        self.led_red = Pin(config.PIN_LED_RED, Pin.OUT, value=0)
        self.led_green = Pin(config.PIN_LED_GREEN, Pin.OUT, value=0)
        self.led_blue = Pin(config.PIN_LED_BLUE, Pin.OUT, value=0)
        
        # Inicializar LED de Batería (Pin 2)
        self.led_bat = Pin(config.PIN_LED_BAT_LOW, Pin.OUT, value=0)
        
        # Inicializar Buzzer y Vibrador
        self.buzzer = PWM(Pin(config.PIN_BUZZER), freq=220, duty=0)
        self.vibrator = Pin(config.PIN_VIBRATOR, Pin.OUT, value=0)
        
        # Inicializar Servo
        try:
            self.servo = PWM(Pin(config.PIN_SERVO), freq=config.SERVO_FREQ, duty=0)
        except Exception:
            self.servo = None
            
        # Variables de estado interno del Servo
        self._servo_last_applied_state = False
        self._servo_candidate_state = None
        self._servo_candidate_since = 0
        self._servo_hold_until = 0

    def set_ble_led(self, state):
        """Controla el LED Azul para estado de conexión"""
        self.led_blue.value(1 if state else 0)
        
    def blink_ble_led(self):
        """Parpadeo del LED Azul para indicar espera"""
        self.led_blue.on()
        utime.sleep_ms(50)
        self.led_blue.off()
        utime.sleep_ms(950)
        
    def signal_battery_low(self):
        """
        Señal única en el PIN 2 (LED Integrado) antes de morir.
        Se enciende fijo por 2 segundos.
        """
        self.led_bat.on()
        utime.sleep(2)
        self.led_bat.off()

    def feedback_calibration(self):
        """Secuencia visual: Parpadeo LED Azul"""
        for _ in range(3):
            self.led_blue.on(); utime.sleep_ms(100)
            self.led_blue.off(); utime.sleep_ms(100)

    def confirm_calibration(self):
        """Confirmación visual: LED Verde"""
        self.led_green.on(); utime.sleep_ms(1000); self.led_green.off()

    def stop_all(self, keep_ble_led=True):
        """Apaga actuadores principales (Rojo, Verde, Motores)"""
        self.led_red.off()
        self.led_green.off()
        if not keep_ble_led:
            self.led_blue.off()
        
        # El LED de batería (Pin 2) no se apaga aquí porque 
        # normalmente stop_all se llama antes de hibernar
        
        try: self.buzzer.duty(0)
        except: pass
        
        try: self.vibrator.off()
        except: 
            try: self.vibrator.value(0)
            except: pass
            
        try:
            if self.servo: self.servo.duty(0)
        except: pass

    def update(self, is_bad_posture, settings):
        """Actualiza LEDs Rojo/Verde y Motores"""
        # 1. LEDs Postura
        if settings.leds_enabled:
            self.led_red.value(is_bad_posture)
            self.led_green.value(not is_bad_posture)
        else:
            self.led_red.off()
            self.led_green.off()

        # 2. Buzzer
        if settings.buzzer_enabled:
            if is_bad_posture:
                self.buzzer.duty(512)
            else:
                self.buzzer.duty(0)
        else:
            self.buzzer.duty(0)

        # 3. Vibrador
        if settings.vibrator_enabled:
            self.vibrator.value(is_bad_posture)
        else:
            self.vibrator.off()

        # 4. Servo
        self._update_servo(is_bad_posture, settings.servo_enabled)

    def _angle_to_duty(self, angle):
        min_duty = 25
        max_duty = 75
        if angle is None: return 0
        a = max(0, min(90, int(angle)))
        return int(min_duty + (a / 90.0) * (max_duty - min_duty))

    def _update_servo(self, is_bad_posture, enabled):
        if self.servo is None: return
        
        now = utime.ticks_ms()
        if not enabled:
            try: self.servo.duty(0)
            except: pass
            self._servo_candidate_state = None
            self._servo_candidate_since = 0
            return

        observed = bool(is_bad_posture)
        if self._servo_candidate_state is None or self._servo_candidate_state != observed:
            self._servo_candidate_state = observed
            self._servo_candidate_since = now

        if utime.ticks_diff(now, self._servo_candidate_since) >= config.SERVO_DEBOUNCE_MS:
            if self._servo_last_applied_state != self._servo_candidate_state:
                target_angle = config.SERVO_ALERT_ANGLE if self._servo_candidate_state else config.SERVO_IDLE_ANGLE
                try:
                    self.servo.duty(self._angle_to_duty(target_angle))
                    self._servo_hold_until = utime.ticks_add(now, config.SERVO_HOLD_MS)
                except: pass
                self._servo_last_applied_state = self._servo_candidate_state

        if utime.ticks_diff(now, self._servo_hold_until) >= 0 and self._servo_hold_until != 0:
            try:
                self.servo.duty(0)
                self._servo_hold_until = 0
            except: pass