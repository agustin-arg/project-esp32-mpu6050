import math
import utime

class PostureProcessor:
    def __init__(self, alpha=0.98):
        self.alpha = alpha
        self.last_time = utime.ticks_us()
        self.filtered_pitch = 0.0

    def reset(self, initial_angle=0.0):
        """Reinicia el filtro con un ángulo conocido"""
        self.last_time = utime.ticks_us()
        self.filtered_pitch = initial_angle

    def calculate_pitch(self, accel_data, gyro_data):
        """
        Calcula el ángulo de inclinación (pitch) usando un filtro complementario.
        Combina datos de acelerómetro y giroscopio.
        """
        # 1. Pitch del acelerómetro (Geometría básica)
        x, y, z = accel_data['x'], accel_data['y'], accel_data['z']
        # Evitar división por cero si y=0 y x=0 (caso raro pero posible)
        try:
            accel_pitch = math.degrees(math.atan2(z, math.sqrt(y**2 + x**2)))
        except ValueError:
            accel_pitch = 0.0

        # 2. Delta de tiempo
        current_time = utime.ticks_us()
        delta_t = utime.ticks_diff(current_time, self.last_time) / 1000000.0
        
        # Protección contra delta_t extraños (primera ejecución o overflow)
        if delta_t <= 0 or delta_t > 1.0: 
            delta_t = 0.001
            
        self.last_time = current_time

        # 3. Integración del Giroscopio
        gyro_rate = gyro_data.get('y', 0.0)
        gyro_change = gyro_rate * delta_t

        # 4. Filtro Complementario
        # Nuevo ángulo = (Confianza en Giroscopio + cambio) + (Confianza en Acelerómetro)
        self.filtered_pitch = (1.0 - self.alpha) * (self.filtered_pitch + gyro_change) + \
                              (self.alpha) * accel_pitch
                              
        return self.filtered_pitch