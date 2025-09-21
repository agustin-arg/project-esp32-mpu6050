from machine import Pin, PWM, I2C
from time import sleep
from mpu6050_sensor import accel

class SystemController:
    def __init__(self, sensors: dict, actuators: dict):
        '''
        sensor = {'scl': Pin, 'sda': Pin}
        actuadores = {'a1': {'pin': 15, 'tag': 'led_rojo', 'type': 'Pin'}}
        '''
        self.sensors = I2C(sensors['scl'], sensors['sda'])
        self.mpu = accel(self.sensors)
        self.actuators_config = actuators 
        self.setup_actuators()

    def setup_actuators(self):
        for key, config in self.actuators_config.items():
            pin = config['pin']
            type = config['type']
            nombre = f"{type}_{clasificacion}"

            # Crear los objetos actuadores
            if type == 'Pin':
                setattr(self, nombre, Pin(pin, Pin.OUT))
            elif type == 'PWM':
                setattr(self, nombre, PWM(Pin(pin)))
            # Se puede agregar más tipos como 'servo', 'motor', etc.

    def test_actuators(self):
        print("Probando actuadores...")

        for key, config in self.actuators_config.items():
            type = config['type']
            clasificacion = config['clasificacion']
            nombre = f"{type}_{clasificacion}"
            actuator = getattr(self, nombre)

            print(f"Probando {nombre}...")

            if isinstance(actuator, PWM):
                actuator.freq(659)
                actuator.duty(500)
                sleep(0.15)
                actuator.duty(0)
            elif hasattr(actuator, 'value'):
                actuator.value(1)
                sleep(0.2)
                actuator.value(0)

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

    