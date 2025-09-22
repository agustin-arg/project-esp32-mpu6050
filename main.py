from system_controller import SystemController
from time import sleep
sensors = {'scl': 22, 'sda': 21}
actuators = {
            'a1': {'pin': 17, 'tag': 'led_red', 'type': 'Pin'},
            'a2': {'pin': 16, 'tag': 'led_green', 'type': 'Pin'},
            'a3': {'pin': 4, 'tag': 'led_blue', 'type': 'Pin'},
            'a4': {'pin': 25, 'tag': 'buzzer_1', 'type': 'PWM'},
             }
#los nombres de los controladores (a1, a2, a3...) no se deben repetir
system = SystemController(sensors, actuators)
system.test_actuators()
system.trigger_stability_alert()
system.actuator_stability('a3', 'a2', 'a1')
while True:
    data = {
        'GyX': system.gyx(), 'GyY': system.gyz(), 'GyX': system.gyy(),
        'AcZ': system.acz(), 'AcY': system.acy(), 'AcX': system.acx(),
        'Tmp': system.temp()
         }
    print(data)
    system.trigger_stability_alert()
    sleep(1)