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
                control_pwm = PWM(Pin(pin), freq= 500, duty= 0)
                self.actuators['PWM'][key] = {
                    'actuator': control_pwm,
                    'tag': tag,
                    'power': 1
                }
    def config_actuator_stability(self, *args, **kwargs):
        stabilities = [] 
        for stability in args:
            try:
                if stability not in self.actuators_config.keys():
                    print(f'No existe el actuador {stability}')  # Solo print, sin raise
                    continue 
                
                # Obtener tipo del actuador
                actuator_type = self.actuators_config[stability]['type']
                
                if actuator_type == 'Pin':
                    act = self.actuators['Pin'][stability]
                    if act['actuator'] not in self.act_stability:
                        self.act_stability.append(act['actuator'])
                        stabilities.append(act['tag'])
                    else:
                        print(f"Actuador {stability} ya está configurado")
                        
                elif actuator_type == 'PWM':
                    act = self.actuators['PWM'][stability]
                    if act['actuator'] not in self.act_stability:
                        self.act_stability.append(act['actuator'])
                        stabilities.append(act['tag'])
                    else:
                        print(f"Actuador {stability} ya está configurado")
                        
            except KeyError:
                print(f'No existe el actuador {stability}')
                continue
            except Exception as e:
                print(f'Error al configurar actuador {stability}: {e}')
                continue
        
        if stabilities:
            print(f'''Se añadieron los siguientes actuadores como actuadores de aviso de estabilidad:\n{stabilities}''')
        else:
            print("No se añadieron actuadores de estabilidad.")
    
    def config_actuator_alert(self, *args, **kwargs):
        alerts_actuators = [] 
        for alert in args:
            try:
                if alert not in self.actuators_config.keys():
                    print(f'No existe el actuador {alert}')
                    continue
                
                # Obtener tipo del actuador
                actuator_type = self.actuators_config[alert]['type']
                
                if actuator_type == 'Pin':
                    act = self.actuators['Pin'][alert]
                    if act['actuator'] not in self.act_alert:
                        self.act_alert.append(act['actuator'])
                        alerts_actuators.append(act['tag'])
                    else:
                        print(f"Actuador {alert} ya está configurado para alertas")
                        
                elif actuator_type == 'PWM':
                    act = self.actuators['PWM'][alert]
                    if act['actuator'] not in self.act_alert:
                        self.act_alert.append(act['actuator'])
                        alerts_actuators.append(act['tag'])
                    else:
                        print(f"Actuador {alert} ya está configurado para alertas")
                        
            except KeyError:
                print(f'No existe el actuador {alert}')
                continue
            except Exception as e:
                print(f'Error al configurar actuador {alert}: {e}')
                continue
            
        if alerts_actuators:
            print(f'''Se añadieron los siguientes actuadores como actuadores de aviso de alerta:\n{alerts_actuators}''')
        else:
            print("No se añadieron actuadores de alerta.")

    def test_actuators(self, rang=1):
        # Validación simple
        if rang < 0:
            print("Error: El número de pruebas no puede ser negativo.")
            return
        
        for i in range(rang):
            print(f"Prueba N° {i+1} actuadores...")
        
            for actuator_type, actuators_dict in self.actuators.items():
                if not actuators_dict:  # Si no hay actuadores, continuar
                    continue
                    
                print(f"→ Probando {actuator_type}:")
                
                for key, actuator_info in actuators_dict.items():
                    try:
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
                        
                        sleep(0.1)
                        
                    except Exception as e:
                        print(f"  Error probando {key}: {e}")
                        continue  # Continuar con el siguiente
            
            print("Prueba completa.")

    def stability_sequence(self, duration=1):
        """
        Activa todos los actuadores de estabilidad a la vez, luego los apaga.
        """
        # Validación simple
        if duration < 0:
            print("Error: La duración no puede ser negativa.")
            return
        
        if not self.act_stability:
            print("No hay actuadores de estabilidad configurados.")
            return
        
        print(f"Activando alerta de estabilidad por {duration}s...")
        
        # Activar con try/catch simple 
        # hasattr colabora si el obj tiene algun metodo
        for i, actuator in enumerate(self.act_stability):
            try:
                if hasattr(actuator, 'value'):  # Pin
                    actuator.value(1)
                elif hasattr(actuator, 'duty'):   # PWM
                    actuator.freq(659)
                    actuator.duty(500)
            except Exception as e:
                print(f"Error activando actuator {i}: {e}")
        
        sleep(duration)
        
        # Apagar con try/catch simple
        for i, actuator in enumerate(self.act_stability):
            try:
                if hasattr(actuator, 'value'):  # Pin
                    actuator.value(0)
                elif hasattr(actuator, 'duty'):   # PWM
                    actuator.duty(0)
            except Exception as e:
                print(f"Error apagando actuator {i}: {e}")
        
        print("Alerta de estabilidad completada.")

    def alert_sequence(self, duration = 1):
        """
        Activa todos los actuadores de alerta a la vez, luego los apaga.
        """
        # Validación simple
        if duration < 0:
            print("Error: La duración no puede ser negativa.")
            return
        
        if not self.act_alert:
            print("No hay actuadores de alerta configurados.")
            return
        
        print(f"Activando alerta de alerta por {duration}s...")
        
        # Activar con try/catch simple 
        # hasattr colabora si el obj tiene algun metodo
        for i, actuator in enumerate(self.act_alert):
            try:
                if hasattr(actuator, 'value'):  # Pin
                    actuator.value(1)
                elif hasattr(actuator, 'duty'):   # PWM
                    actuator.freq(659)
                    actuator.duty(500)
            except Exception as e:
                print(f"Error activando actuator {i}: {e}")
        
        sleep(duration)
        
        # Apagar con try/catch simple
        for i, actuator in enumerate(self.act_alert):
            try:
                if hasattr(actuator, 'value'):  # Pin
                    actuator.value(0)
                elif hasattr(actuator, 'duty'):   # PWM
                    actuator.duty(0)
            except Exception as e:
                print(f"Error apagando actuator {i}: {e}")
        
        print("Alerta de estabilidad completada.")