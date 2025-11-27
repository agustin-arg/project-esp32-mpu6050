import utime
from machine import I2C, Pin
import config
from mpu6050 import MPU6050
from actuators import PostureActuators
from ble_service import PostureBLE
from posture_logic import PostureProcessor
from battery_monitor import BatteryMonitor

class PostureApp:
    def __init__(self):
        # 1. Inicializar Hardware I2C y Sensor
        try:
            i2c = I2C(0, sda=Pin(config.PIN_SDA), scl=Pin(config.PIN_SCL))
            self.mpu = MPU6050(i2c)
        except Exception as e:
            print(f"Error I2C: {e}")
            self.mpu = None

        # 2. Inicializar Actuadores
        self.actuators = PostureActuators()

        # 3. Inicializar BLE
        self.ble = PostureBLE()

        # 4. Lógica de Procesamiento
        self.processor = PostureProcessor(alpha=0.98)
        
        # 5. Monitor de Batería
        self.battery = BatteryMonitor()
        self.last_battery_check = 0
        # Usamos el valor desde la configuración (ahora 5 minutos)
        self.battery_check_interval = config.BAT_CHECK_INTERVAL_MS

        # 6. Estado de la Aplicación
        self.calibrated_angle = 0.0
        self.is_calibrated = False
        self.is_bad_posture = False

    def calibrate(self):
        print("Calibrando...")
        self.actuators.feedback_calibration() 
        
        if self.mpu:
            accel = self.mpu.get_accel_data()
            gyro = self.mpu.get_gyro_data()
            
            self.processor.reset() 
            current_angle = self.processor.calculate_pitch(accel, gyro)
            
            self.calibrated_angle = current_angle
            self.processor.reset(initial_angle=self.calibrated_angle)
            
            self.is_calibrated = True
            self.actuators.confirm_calibration()
            print(f"Calibrado a: {self.calibrated_angle:.2f}")
        else:
            print("Error: No hay sensor para calibrar")
        
        self.ble.calibrate_request = False

    def run(self):
        print(f"Sistema iniciado. Chequeo de batería cada {self.battery_check_interval/1000}s")
        last_notified_state = None

        #Notifica la batería una vez
        volts_inicial = self.battery.read_voltage()
        self.ble.notify_battery(volts_inicial)
        
        while True:
            now = utime.ticks_ms()

           # --- GESTIÓN DE BATERÍA ---
            if utime.ticks_diff(now, self.last_battery_check) > self.battery_check_interval:
                # 1. Revisar hardware y obtener voltaje
                volts = self.battery.check_and_handle_low_battery(self.actuators)
                print("Voltaje es de ", volts)
                
                # 2. Notificar al servicio BLE
                self.ble.notify_battery(volts)
                
                self.last_battery_check = now

            # 1. Chequear petición de calibración
            if self.ble.calibrate_request:
                self.calibrate()
                utime.sleep_ms(50)
                continue

            # 2. Manejo de estado: Sistema Apagado
            if not self.ble.system_enabled:
                self.actuators.stop_all(keep_ble_led=True)
                if self.ble.conn_handle is None:
                    self.actuators.blink_ble_led()
                else:
                    self.actuators.set_ble_led(True)
                    utime.sleep_ms(100)
                continue

            # 3. Manejo de estado: No Calibrado
            if not self.is_calibrated:
                if self.ble.conn_handle is None:
                    self.actuators.blink_ble_led()
                else:
                    self.actuators.set_ble_led(True)
                    utime.sleep_ms(100)
                continue
            
            # --- OPERACIÓN NORMAL ---
            if self.mpu:
                accel = self.mpu.get_accel_data()
                gyro = self.mpu.get_gyro_data()
                current_angle = self.processor.calculate_pitch(accel, gyro)
                
                deviation = abs(current_angle - self.calibrated_angle)
                self.is_bad_posture = deviation > self.ble.threshold_angle

                self.actuators.update(self.is_bad_posture, settings=self.ble)
                
                if self.ble.conn_handle:
                    self.actuators.set_ble_led(True)

                if self.is_bad_posture != last_notified_state:
                    if self.ble.notify_status(self.is_bad_posture):
                        last_notified_state = self.is_bad_posture

            utime.sleep_ms(100)

if __name__ == "__main__":
    app = PostureApp()
    app.run()