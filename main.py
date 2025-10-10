from system_controller import SystemController
import utime


#mpu = MPU6050(bus = 0, sda = 21, scl= 22, ofs = (1794, -3335, 1252, 92, -18, 12))

#if mpu.passed_self_test:
    #while True:
        #ax, ay, az, gx, gy, gz = mpu.data
        #print(ax, ay, az, gx, gy, gz)

sensors = {'scl': 22, 'sda': 21}
actuators = {
            'a1': {'pin': 32, 'tag': 'led_red', 'type': 'Pin'},
            'a2': {'pin': 33, 'tag': 'led_green', 'type': 'Pin'},
            'a3': {'pin': 25, 'tag': 'led_blue', 'type': 'Pin'},
            'a4': {'pin': 27, 'tag': 'buzzer_1', 'type': 'PWM'},
             }
system = SystemController(sensors, actuators)
system.test_actuators()
system.config_actuator_stability('a2')
system.config_actuator_alert('a1', 'a4')

while True:
    system.alert_upright_position(75)