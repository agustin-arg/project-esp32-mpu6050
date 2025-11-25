from machine import ADC, Pin, deepsleep
import utime
import config

class BatteryMonitor:
    def __init__(self):
        # Configuración del ADC
        self.adc = ADC(Pin(config.PIN_BAT))
        self.adc.atten(ADC.ATTN_11DB)   
        self.adc.width(ADC.WIDTH_12BIT) 
        
        self.divider_factor = config.BAT_DIVIDER_FACTOR
        self.min_voltage = config.BAT_MIN_VOLTAGE

    def read_voltage(self):
        suma = 0
        samples = 20
        for _ in range(samples):
            suma += self.adc.read()
            utime.sleep_ms(2)
        
        voltage = (suma / samples / 4095) * 3.3 * self.divider_factor
        return voltage

    def check_and_handle_low_battery(self, actuators):
        """
        Verifica el voltaje. Si es crítico:
        1. Apaga todo.
        2. Enciende Pin 2 (signal_battery_low) una sola vez.
        3. Entra en DeepSleep.
        """
        voltage = self.read_voltage()
        
        if voltage < self.min_voltage:
            print(f"⚠️ BATERÍA CRÍTICA ({voltage:.2f}V). Hibernando...")
            
            # 1. Apagar actuadores normales
            actuators.stop_all(keep_ble_led=False)
            
            # 2. Señal única en Pin 2 (LED Integrado)
            actuators.signal_battery_low()
            
            # 3. Hibernar
            print("Entrando en DeepSleep...")
            deepsleep()
            
        return voltage