from system_controller import SystemController
from time import sleep
sensors = {'scl': 22, 'sda': 21}
actuators = {
            'a1': {'pin': 17, 'tag': 'led_red', 'type': 'Pin'},
            'a2': {'pin': 16, 'tag': 'led_green', 'type': 'Pin'},
            'a3': {'pin': 4, 'tag': 'led_blue', 'type': 'Pin'},
            'a4': {'pin': 25, 'tag': 'buzzer_1', 'type': 'pwm'},
             }
system = SystemController(sensors, actuators)

system.setup_actuators()
system.test_actuators()
while True:
    data = {
        'GyX': System.gyx(), 'GyY': System.gyz(), 'GyX': System.gyy(),
        'AcZ': System.acz(), 'AcY': System.acy(), 'AcX': System.acx(),
        'Tmp': System.temp()
         }
    print(data)
    sleep(1)