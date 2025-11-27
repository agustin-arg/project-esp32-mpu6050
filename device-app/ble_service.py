import ubluetooth
import struct
import config

class PostureBLE:
    def __init__(self):
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)
        
        # Estado configurable remoto
        self.threshold_angle = 20.0
        self.buzzer_enabled = True
        self.vibrator_enabled = True
        self.leds_enabled = True
        self.notifications_enabled = True
        self.system_enabled = True
        self.servo_enabled = True
        
        # Flags de eventos
        self.calibrate_request = False
        self.conn_handle = None

        self._setup_services()
        self._start_advertising()
        # Estado de batería actual
        self.last_battery_level = None

    def _setup_services(self):
        # Definición de características
        status_char = (config.POSTURE_STATUS_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_NOTIFY,)
        threshold_char = (config.THRESHOLD_ANGLE_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        calibrate_char = (config.CALIBRATE_CHAR_UUID, ubluetooth.FLAG_WRITE,)
        buzzer_char = (config.BUZZER_CONTROL_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        vibrator_char = (config.VIBRATOR_CONTROL_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        leds_char = (config.LEDS_CONTROL_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        notify_char = (config.NOTIFY_CONTROL_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        system_char = (config.SYSTEM_CONTROL_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE,)
        battery_char = (config.BATTERY_NOTIFY_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_NOTIFY,)

        posture_service = (config.POSTURE_SERVICE_UUID, (status_char, threshold_char, calibrate_char, buzzer_char,
                                                         vibrator_char, leds_char, notify_char, system_char, battery_char),)
        
        handles = self.ble.gatts_register_services((posture_service,))
        (self.status_handle, self.threshold_handle, self.calibrate_handle, self.buzzer_handle, 
         self.vibrator_handle, self.leds_handle, self.notify_handle, self.system_handle, self.battery_handle) = handles[0]
         
        # Escribir valores iniciales
        self.ble.gatts_write(self.buzzer_handle, struct.pack('<B', 1))
        self.ble.gatts_write(self.vibrator_handle, struct.pack('<B', 1))
        self.ble.gatts_write(self.leds_handle, struct.pack('<B', 1))
        self.ble.gatts_write(self.notify_handle, struct.pack('<B', 1))
        self.ble.gatts_write(self.system_handle, struct.pack('<B', 1))
        self.ble.gatts_write(self.battery_handle, struct.pack('<B', 2))

    def _start_advertising(self):
        payload = bytearray()
        def _append(data_type, value):
            nonlocal payload
            value_len = 16 if isinstance(value, ubluetooth.UUID) else len(value)
            payload += struct.pack('BB', value_len + 1, data_type) + value
        _append(0x01, b'\x06')
        _append(0x07, config.POSTURE_SERVICE_UUID)
        _append(0x09, b'Posture')
        self.ble.gap_advertise(100000, payload)

    def notify_status(self, is_bad_posture):
        """Envía notificación si hay conexión y está habilitado"""
        if self.conn_handle is not None and self.notifications_enabled:
            try:
                data = struct.pack('<B', 1 if is_bad_posture else 0)
                self.ble.gatts_notify(self.conn_handle, self.status_handle, data)
                return True
            except:
                pass
        return False

    def update_system_state_on_characteristic(self, state):
        """Sincroniza el valor de la característica con la variable interna"""
        try:
            self.ble.gatts_write(self.system_handle, struct.pack('<B', 1 if state else 0))
        except: pass

    def notify_battery(self, voltage):
        # 1. Calcular nivel
        if voltage >= config.BATTERY_VOLTAGE_MAX:
            battery_level = 2
        elif voltage >= config.BATTERY_VOLTAGE_MID:
            battery_level = 1
        else:
            battery_level = 0
            
        # 2. Guardar en memoria SIEMPRE (GATTS Write)
        try:
            self.ble.gatts_write(self.battery_handle, struct.pack('<B', battery_level))
        except:
            pass

        # 3. Chequeo de conexión CORRECTO
        if self.conn_handle is None:
            return False
        
        # 4. Filtro de repetidos
        if battery_level == self.last_battery_level:
            return battery_level
            
        self.last_battery_level = battery_level
        
        # 5. Notificar
        try:
            self.ble.gatts_notify(
                self.conn_handle, 
                self.battery_handle, 
                struct.pack('<B', battery_level)
            )
        except:
            pass
        
        return battery_level
    
    def _irq(self, event, data):
        if event == 1: # CONNECT
            self.conn_handle, _, _ = data
            self.last_battery_level = None
            print("BLE Conectado")
        elif event == 2: # DISCONNECT
            self.conn_handle = None
            print("BLE Desconectado")
            self._start_advertising()
        elif event == 3: # WRITE
            _, value_handle = data
            value = self.ble.gatts_read(value_handle)
            
            # Decodificar booleano simple
            state = False
            if len(value) >= 1:
                state = struct.unpack('<B', value[:1])[0] == 1

            if value_handle == self.threshold_handle:
                self.threshold_angle = float(struct.unpack('<B', value[:1])[0])
                print(f"Nuevo umbral: {self.threshold_angle}")
                
            elif value_handle == self.calibrate_handle:
                self.calibrate_request = True
                
            elif value_handle == self.buzzer_handle:
                self.buzzer_enabled = state
                
            elif value_handle == self.vibrator_handle:
                self.vibrator_enabled = state
                
            elif value_handle == self.leds_handle:
                self.leds_enabled = state
                
            elif value_handle == self.notify_handle:
                self.notifications_enabled = state
                
            elif value_handle == self.system_handle:
                self.system_enabled = state
                print(f"Sistema: {state}")