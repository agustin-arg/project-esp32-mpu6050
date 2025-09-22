from machine import Pin, PWM, I2C
from time import sleep
from mpu6050_sensor import accel

class SystemController:
    def __init__(self, sensors: dict, actuators: dict):
        '''
        sensor = {'scl': Pin, 'sda': Pin}
        actuadores = {'a1': {'pin': 15, 'tag': 'led_red', 'type': 'Pin'}}
        '''
        self.sensors = I2C(scl= Pin(sensors['scl']), sda = Pin(sensors['sda']))
        self.mpu = accel(self.sensors)
        self.actuators_config = actuators
        self.actuators = {'Pin': {}, 'PWM': {}}
        self.setup_actuators()

    def setup_actuators(self):
        for key, config in self.actuators_config.items():
            pin = config['pin']
            type = config['type']
            tag = config['tag']
            
            if type == 'Pin':
                control_pin = Pin(pin, Pin.OUT)
                self.actuators['Pin'][key] = {
                    'actuator': control_pin,
                    'tag': tag,
                    'power': 1
                }
            elif type == 'PWM':
                control_pwm = PWM(Pin(pin), freq= 500, duty_u16= 0)
                self.actuators['PWM'][key] = {
                    'actuator': control_pwm,
                    'tag': tag,
                    'power': 1
                }

    def test_actuators(self, rang = 1):
        for i in range(1, rang):
            print(f"Prueba N° {i} actuadores...")
        
            for actuator_type, actuators_dict in self.actuators.items():
                print(f"→ Probando {actuator_type}:")
                
                for key, actuator_info in actuators_dict.items():
                    actuator_obj = actuator_info['actuator']
                    tag = actuator_info['tag']
                    
                    print(f"  Probando {key} ({tag})...")
                    
                    if actuator_type == 'PWM':
                        actuator_obj.freq(659)
                        actuator_obj.duty(500)
                        sleep(0.15)
                        actuator_obj.duty(0)
                    elif actuator_type == 'Pin':
                        actuator_obj.value(1)
                        sleep(0.5)
                        actuator_obj.value(0)
                        sleep(0.5)
                    
                    sleep(0.1)
            
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