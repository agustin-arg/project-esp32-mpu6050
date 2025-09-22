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
        self.act_stability = []
        self.act_alert = []
        self.setup_actuators()

    def setup_actuators(self):
        '''
        ejemplo:
        {'Pin': {
        'a1': {'actuator': Pin_obj, 'tag': 'led_rojo', 'power': 1},
        }}
        '''
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
    def actuator_stability(self, *args, **kwargs):
        stabilities = [] 
        for stability in args:
            try:
                if stability not in self.actuators_config.keys():
                    raise ValueError(f'No existe el actuador {stability}')
                
                # Obtener tipo del actuador
                actuator_type = self.actuators_config[stability]['type']
                
                if actuator_type == 'Pin':
                    act = self.actuators['Pin'][stability]
                    self.act_stability.append(act['actuator'])
                    stabilities.append(act['tag'])
                    
                elif actuator_type == 'PWM':
                    act = self.actuators['PWM'][stability]
                    self.act_stability.append(act['actuator'])
                    stabilities.append(act['tag'])
                    
            except KeyError:
                raise ValueError(f'No existe el actuador {stability}')
            except Exception as e:
                raise ValueError(f'Error al configurar actuador {stability}: {e}')
        
        if stabilities:
            print(f'''Se añadieron los siguientes actuadores como actuadores de aviso de estabilidad:\n{stabilities}''')
        else:
            print("No se añadieron actuadores de estabilidad.")
            
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

    def trigger_stability_alert(self, duration=1):
        """
        Activa todos los actuadores de estabilidad a la vez, luego los apaga.
        Args:
            duration (float): Duración en segundos que permanecen encendidos (default: 1)
        """
        if not self.act_stability:
            print("No hay actuadores de estabilidad configurados.")
            return
        for actuator in self.act_stability:
            if hasattr(actuator, 'value'):  # Pin (LED, relay, etc.)
                actuator.value(1)
            elif hasattr(actuator, 'duty'):   # PWM (buzzer, servo, etc.)
                actuator.freq(659)  # Frecuencia de alerta
                actuator.duty(500)  # 50% duty cycle
        sleep(duration)
        # APAGAR todos los actuadores a la vez
        for actuator in self.act_stability:
            if hasattr(actuator, 'value'):  # Pin
                actuator.value(0)
            elif hasattr(actuator, 'duty'):   # PWM
                actuator.duty(0)  # Apagar PWM
        
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