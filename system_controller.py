from machine import Pin, PWM, I2C
from time import sleep
from mpu6050_sensor import accel

class SystemController:
    def __init__(self, sensores: dict, actuadores: dict):
        '''
        actuadores = {'a1': {'pin': 15, 'tag': 'led_rojo', 'type': 'Pin'}}
        '''
        self.sensores = sensores
        self.actuadores_config = actuadores 
        self.setup_actuadores()

    def setup_actuadores(self):
        for key, config in self.actuadores_config.items():
            pin = config['pin']
            tipo = config['tipo']
            clasificacion = config['clasificacion']
            nombre = f"{tipo}_{clasificacion}"

            if tipo == 'Pin':
                setattr(self, nombre, Pin(pin, Pin.OUT))
            elif tipo == 'PWM':
                setattr(self, nombre, PWM(Pin(pin)))
            # Podés agregar más tipos como 'motor', 'servo', etc.

    def test_actuadores(self):
        print("Probando actuadores...")

        for key, config in self.actuadores_config.items():
            tipo = config['tipo']
            clasificacion = config['clasificacion']
            nombre = f"{tipo}_{clasificacion}"
            dispositivo = getattr(self, nombre)

            print(f"Probando {nombre}...")

            if isinstance(dispositivo, PWM):
                dispositivo.freq(659)
                dispositivo.duty(500)
                sleep(0.15)
                dispositivo.duty(0)
            elif hasattr(dispositivo, 'value'):
                dispositivo.value(1)
                sleep(0.2)
                dispositivo.value(0)

        print("Prueba completa.")

    
    def temp(self):
        '''
        Devuelve la temperatura
        .get_valuesTmp() devuelve: {'Tmp': 24.00059}
        '''
        return round(self.mpu.get_valuesTmp()['Tmp'], 2)
    def gyz(self):
        '''
        Max: 32750(250°sec), Min: -32750(-250°sec)
        '''
        return round(self.mpu.get_values()['GyZ'] *250/32750, 2)
    def gyx(self):
        '''
        Max: 32750(250°sec), Min: -32750(-250°sec)
        '''
        return round(self.mpu.get_values()['GyX'] *250/32750, 2)
    def gyy(self):
        '''
        Max: 32750(250°sec), Min: -32750(-250°sec)
        '''
        return round(self.mpu.get_values()['GyY'] *250/32750, 2)
    def acz(self):
        '''
        Devuelve la aceleración en el eje Y en g.
        '''
        return round(self.mpu.get_values()['AcZ']*2/32767, 2)
    def acx(self):
        '''
        Devuelve la aceleración en el eje Y en g.
        '''
        return round(self.mpu.get_values()['AcX']*2/32767, 2)
    def acy(self):
        '''
        Devuelve la aceleración en el eje Y en g.
        '''
        return round(self.mpu.get_values()['AcY']*2/32767, 2)

    