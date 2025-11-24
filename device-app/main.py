import utime
from machine import I2C, Pin
import config
from mpu6050 import MPU6050
from actuators import PostureActuators
from ble_service import PostureBLE
from posture_logic import PostureProcessor

class PostureApp:
    def __init__(self):
        # 1. Inicializar Hardware I2C y Sensor
        i2c = I2C(0, sda=Pin(config.PIN_SDA), scl=Pin(config.PIN_SCL))
        self.mpu = MPU6050(i2c)

        # 2. Inicializar Actuadores
        self.actuators = PostureActuators()

        # 3. Inicializar BLE
        self.ble = PostureBLE()

        # 4. Lógica de Procesamiento (Matemática)
        self.processor = PostureProcessor(alpha=0.98)

        # 5. Estado de la Aplicación
        self.calibrated_angle = 0.0
        self.is_calibrated = False
        self.is_bad_posture = False

    def calibrate(self):
        """
        Orquesta el proceso de calibración:
        1. Feedback Visual -> 2. Lectura Datos -> 3. Cálculo -> 4. Guardado -> 5. Confirmación
        """
        print("Calibrando...")
        self.actuators.feedback_calibration() 
        
        accel = self.mpu.get_accel_data()
        gyro = self.mpu.get_gyro_data()
        
        # Usamos el procesador para calcular el ángulo actual
        # Reiniciamos el procesador primero para evitar deltas de tiempo viejos
        self.processor.reset() 
        current_angle = self.processor.calculate_pitch(accel, gyro)
        
        # Establecemos este ángulo como nuestro "Cero" relativo
        self.calibrated_angle = current_angle
        # Reiniciamos el filtro con el valor ya calibrado para que arranque suave
        self.processor.reset(initial_angle=self.calibrated_angle)
        
        self.is_calibrated = True
        self.actuators.confirm_calibration()
        
        self.ble.calibrate_request = False
        print(f"Calibrado a: {self.calibrated_angle:.2f}")

    def run(self):
        print("Sistema iniciado (Modo modular completo)")
        last_notified_state = None

        while True:
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
            
            # A. Leer sensores
            accel = self.mpu.get_accel_data()
            gyro = self.mpu.get_gyro_data()
            
            # B. Calcular ángulo usando la lógica extraída
            current_angle = self.processor.calculate_pitch(accel, gyro)
            
            # C. Determinar postura (Lógica de negocio simple)
            deviation = abs(current_angle - self.calibrated_angle)
            self.is_bad_posture = deviation > self.ble.threshold_angle

            # D. Actualizar actuadores
            self.actuators.update(self.is_bad_posture, settings=self.ble)
            
            # E. Estado BLE
            if self.ble.conn_handle:
                self.actuators.set_ble_led(True)

            # F. Notificaciones
            if self.is_bad_posture != last_notified_state:
                if self.ble.notify_status(self.is_bad_posture):
                    last_notified_state = self.is_bad_posture

            utime.sleep_ms(100)

if __name__ == "__main__":
    app = PostureApp()
    app.run()