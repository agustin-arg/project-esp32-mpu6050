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
        """
        Configura actuadores para alertas de estabilidad con manejo robusto de errores.
        """
        stabilities = []
        errors = []  # Coleccionar errores sin detener
        
        for stability in args:
            try:
                if stability not in self.actuators_config.keys():
                    errors.append(f"'{stability}' no existe en configuración")
                    continue  # Continuar con el siguiente
                
                # Obtener tipo del actuador
                actuator_type = self.actuators_config[stability]['type']
                
                if actuator_type == 'Pin':
                    act = self.actuators['Pin'][stability]
                    # Evitar duplicados
                    if act['actuator'] not in self.act_stability:
                        self.act_stability.append(act['actuator'])
                        stabilities.append(act['tag'])
                    else:
                        errors.append(f"'{stability}' ({act['tag']}) ya está configurado")
                        
                elif actuator_type == 'PWM':
                    act = self.actuators['PWM'][stability]
                    # Evitar duplicados
                    if act['actuator'] not in self.act_stability:
                        self.act_stability.append(act['actuator'])
                        stabilities.append(act['tag'])
                    else:
                        errors.append(f"'{stability}' ({act['tag']}) ya está configurado")
                        
            except KeyError as e:
                errors.append(f"'{stability}': clave no encontrada - {str(e)}")
                continue  # Continuar procesando
            except Exception as e:
                errors.append(f"'{stability}': error inesperado - {str(e)}")
                continue  # Continuar procesando
        
        # Reportar resultados al final
        if stabilities:
            print(f"Se añadieron los siguientes actuadores como actuadores de aviso de estabilidad:\n{stabilities}")
        
        if errors:
            print(f"Errores encontrados: {errors}")
        
        if not stabilities and not errors:
            print("No se especificaron actuadores válidos.")
        
        return len(stabilities), len(errors)

    def test_actuators(self, rang=1):
        """
        Prueba todos los actuadores con manejo robusto de errores.
        
        Args:
            rang (int): Número de veces que se repite la prueba (debe ser >= 0)
        """
        # Validar que rang no sea negativo
        if rang < 0:
            print("Error: El número de pruebas no puede ser negativo.")
            return
        
        if rang == 0:
            print("No se realizarán pruebas (rang = 0).")
            return
        
        total_rounds = 0
        total_tested = 0
        total_failed = 0
        
        for i in range(rang):
            print(f"Prueba N° {i+1} de {rang}...")
            round_tested = 0
            round_failed = 0
            failed_actuators = []  # Coleccionar fallos por ronda

            for actuator_type, actuators_dict in self.actuators.items():
                if not actuators_dict:  # Si no hay actuadores de este tipo
                    continue
                    
                print(f"-> Probando {actuator_type}:")
                
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
                        
                        round_tested += 1
                        print(f"    {key} OK")
                        
                    except Exception as e:
                        failed_actuators.append(f"{key}({tag}): {str(e)}")
                        round_failed += 1
                        print(f"    {key} FALLO: {str(e)}")
                        continue  # Continuar con el siguiente actuador
                    
                    sleep(0.1)  # Pausa entre actuadores
            
            # Reporte de la ronda
            print(f"  Ronda {i+1}: {round_tested} OK, {round_failed} fallaron")
            if failed_actuators:
                print(f"  Problemas: {failed_actuators}")
            
            total_tested += round_tested
            total_failed += round_failed
            total_rounds += 1
            
            if i < rang - 1:  # No pausar después de la última prueba
                sleep(0.5)
        
        # Reporte final
        print(f"\nResumen final:")
        print(f"   Rondas completadas: {total_rounds}")
        print(f"   Total probados: {total_tested}")
        print(f"   Total fallaron: {total_failed}")
        if total_tested > 0:
            success_rate = (total_tested / (total_tested + total_failed)) * 100
            print(f"   Tasa de éxito: {success_rate:.1f}%")

    def trigger_stability_alert(self, duration=1):
        """
        Activa todos los actuadores de estabilidad con manejo robusto de errores.
        
        Args:
            duration (float): Duración en segundos (debe ser >= 0)
        """
        # Validar que duration no sea negativo
        if duration < 0:
            print("Error: La duración no puede ser negativa.")
            return
        
        if duration == 0:
            print("Duración es 0, no se activarán actuadores.")
            return
        
        if not self.act_stability:
            print("No hay actuadores de estabilidad configurados.")
            return
        
        print(f"Activando alerta de estabilidad por {duration}s...")
        
        activated = []
        activation_errors = []  # Errores de activación
        
        # Intentar activar cada actuador individualmente
        for i, actuator in enumerate(self.act_stability):
            try:
                if hasattr(actuator, 'value'):  # Pin
                    actuator.value(1)
                    activated.append(f"Pin_{i}")
                elif hasattr(actuator, 'duty'):   # PWM
                    actuator.freq(659)
                    actuator.duty(500)
                    activated.append(f"PWM_{i}")
                else:
                    activation_errors.append(f"Actuator_{i}: tipo desconocido")
                    
            except Exception as e:
                activation_errors.append(f"Actuator_{i}: {str(e)}")
                continue  # Continuar con los demás
        
        # Reportar activación
        if activated:
            print(f"Activados: {len(activated)} actuadores")
        if activation_errors:
            print(f"Fallos de activación: {activation_errors}")
        
        # Solo esperar si hay actuadores funcionando
        if activated:
            sleep(duration)
            
            # Intentar apagar cada actuador individualmente
            deactivated = 0
            deactivation_errors = []  # Errores de desactivación
            
            for i, actuator in enumerate(self.act_stability):
                try:
                    if hasattr(actuator, 'value'):  # Pin
                        actuator.value(0)
                        deactivated += 1
                    elif hasattr(actuator, 'duty'):   # PWM
                        actuator.duty(0)
                        deactivated += 1
                except Exception as e:
                    deactivation_errors.append(f"Actuator_{i}: {str(e)}")
                    continue  # Continuar apagando otros
            
            # Reportar desactivación
            print(f"Desactivados: {deactivated} actuadores")
            if deactivation_errors:
                print(f"Fallos de desactivación: {deactivation_errors}")
        
        print("Alerta de estabilidad completada.")
        
        # Retornar estadísticas
        return {
            'activated': len(activated),
            'activation_errors': len(activation_errors),
            'deactivation_errors': len(deactivation_errors) if activated else 0
        }

    # También mejora los métodos de sensores para mayor robustez
    def temp(self):
        """
        Devuelve la temperatura con manejo de errores
        """
        try:
            return round(self.mpu.get_valuesTmp()['Tmp'], 2)
        except Exception as e:
            print(f"Error leyendo temperatura: {e}")
            return None

    def gyz(self):
        """
        Max: 32750(250°sec), Min: -32750(-250°sec)
        """
        try:
            return round(self.mpu.get_values()['GyZ'] * 250/32750, 2)
        except Exception as e:
            print(f"Error leyendo giroscopio Z: {e}")
            return 0.0

    def gyx(self):
        """
        Max: 32750(250°sec), Min: -32750(-250°sec)
        """
        try:
            return round(self.mpu.get_values()['GyX'] * 250/32750, 2)
        except Exception as e:
            print(f"Error leyendo giroscopio X: {e}")
            return 0.0

    def gyy(self):
        """
        Max: 32750(250°sec), Min: -32750(-250°sec)
        """
        try:
            return round(self.mpu.get_values()['GyY'] * 250/32750, 2)
        except Exception as e:
            print(f"Error leyendo giroscopio Y: {e}")
            return 0.0

    def acz(self):
        """
        Devuelve la aceleración en el eje Z en g.
        """
        try:
            return round(self.mpu.get_values()['AcZ'] * 2/32767, 2)
        except Exception as e:
            print(f"Error leyendo acelerómetro Z: {e}")
            return 0.0

    def acx(self):
        """
        Devuelve la aceleración en el eje X en g.
        """
        try:
            return round(self.mpu.get_values()['AcX'] * 2/32767, 2)
        except Exception as e:
            print(f"Error leyendo acelerómetro X: {e}")
            return 0.0

    def acy(self):
        """
        Devuelve la aceleración en el eje Y en g.
        """
        try:
            return round(self.mpu.get_values()['AcY'] * 2/32767, 2)
        except Exception as e:
            print(f"Error leyendo acelerómetro Y: {e}")
            return 0.0