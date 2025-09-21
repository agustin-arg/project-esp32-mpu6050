from system_controller import mpu6050
from time import sleep

mpu = SystemController(pin_red = 17, pin_green = 16, pin_blue = 4, 
        pin_buzzer = 25, pin_scl = 22, pin_sda = 21)
while True:
    data = {
        'GyX': mpu.gyx(), 'GyY': mpu.gyz(), 'GyX': mpu.gyy(), 'Tmp': mpu.temp(),
         'AcZ': mpu.acz(), 'AcY': mpu.acy(), 'AcX': mpu.acx()
         }
    print(data)
    sleep(1)