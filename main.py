from system_controller import SystemController
from time import sleep
sensors = {'scl': 22, 'sda': 21}
actuators = {
            'a1': {'pin': 15, 'tag': 'led_rojo', 'type': 'Pin'},
            'a1': {'pin': 15, 'tag': 'led_rojo', 'type': 'Pin'},
            'a1': {'pin': 15, 'tag': 'led_rojo', 'type': 'Pin'},
            'a1': {'pin': 15, 'tag': 'led_rojo', 'type': 'Pin'},
             }
System = SystemController(sensors, actuators)
while True:
    data = {
        'GyX': System.gyx(), 'GyY': System.gyz(), 'GyX': System.gyy(),
        'AcZ': System.acz(), 'AcY': System.acy(), 'AcX': System.acx(),
        'Tmp': System.temp()
         }
    print(data)
    sleep(1)