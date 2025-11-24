# **Posture**

Un dispositivo *wearable* que detecta malas posturas en tiempo real y ofrece retroalimentación háptica (vibración), acción mecánica (servomotor), visual (LEDs) y auditiva (buzzer). Incluye conectividad **Bluetooth Low Energy (BLE)** para configuración y monitoreo remoto.

## **Características**

* **Feedback Multimodal:**  
  * **LED Rojo:** Mala postura.  
  * **LED Verde:** Postura correcta.  
  * **Buzzer:** Alerta sonora.  
  * **Vibrador:** Alerta táctil.  
  * **Servomotor:** Acción mecánica correctiva (opcional).  
* **Conectividad BLE:** Permite ver el estado, calibrar y configurar umbrales desde la App móvil.  

## **🛠️ Hardware Requerido y Conexiones**

| Componente | Pin ESP32 (GPIO) | Descripción |
| :---- | :---- | :---- |
| **MPU6050 SDA** | GPIO 21 | Datos I2C |
| **MPU6050 SCL** | GPIO 22 | Reloj I2C |
| **LED Rojo** | GPIO 25 | Indicador de mala postura |
| **LED Verde** | GPIO 33 | Indicador de postura correcta |
| **LED Azul** | GPIO 32 | Estado Bluetooth / Calibración |
| **Buzzer** | GPIO 26 | Alarma sonora (PWM) |
| **Vibrador** | GPIO 18 | Motor de vibración |
| **Servomotor** | GPIO 19 | Servo para corrección física |

## **📂 Estructura del Proyecto**

El código está organizado en 6 archivos para facilitar el mantenimiento:

1. main.py: **Punto de entrada**. Orquesta la inicialización y el bucle principal.  
2. config.py: **Configuración**. Almacena pines, constantes y UUIDs de Bluetooth.  
3. mpu6050.py: **Driver**. Manejo de bajo nivel del sensor I2C.  
4. actuators.py: **Hardware**. Controla LEDs, buzzer, motor y servo.
5. ble\_service.py: **Comunicaciones**. Gestiona la publicidad BLE, conexión y características GATT.  
6. posture\_logic.py: **Matemáticas**. Contiene la física pura y el filtro complementario para calcular el ángulo.

## **🚀 Instalación y Uso**

1. **Flashear MicroPython:** Asegúrate de que tu ESP32 tenga instalado el firmware de MicroPython más reciente.  
2. **Subir Archivos:** Sube los 6 archivos .py a la raíz del dispositivo (usando Thonny IDE, ampy o rshell).  
3. **Encendido:** Reinicia el ESP32.  
4. **Calibración (Importante):**  
   * Colócate el dispositivo en la espalda en una **postura correcta**.  
   * Envía el comando de calibración vía BLE o espera la secuencia inicial.  
   * El **LED Azul** parpadeará 3 veces (tomando datos).  
   * El **LED Verde** se encenderá por 1 segundo confirmando el éxito.  
5. **Funcionamiento:** Si te inclinas más allá del umbral (por defecto 20°), el dispositivo te alertará.

## **📱 Especificaciones Bluetooth (BLE)**

Para desarrollar o conectar Posture App (link), utiliza los siguientes UUIDs definidos en config.py:

**Service UUID:** 0000180f-0000-1000-8000-00805f9b34fb

| Característica | UUID (Prefijo 0000...) | Permisos | Función |
| :---- | :---- | :---- | :---- |
| **Status** | ...2a19... | Read, Notify | Notifica 1 si hay mala postura, 0 si es buena. |
| **Threshold** | ...2a1b... | Read, Write | Lee o establece el ángulo límite (ej. 20°). |
| **Calibrate** | ...2a1c... | Write | Escribe cualquier valor para iniciar calibración. |
| **System** | ...2a22... | Read, Write | 1 \= Encendido, 0 \= Apagado (Standby). |
| **Buzzer** | ...2a1e... | Read, Write | 1 \= Enable, 0 \= Disable. |
| **Vibrator** | ...2a1f... | Read, Write | 1 \= Enable, 0 \= Disable. |
| **LEDs** | ...2a20... | Read, Write | 1 \= Enable, 0 \= Disable. |

## **⚙️ App de Android**

Se incluye una app de Android para poder enciende o apaga actuadores vía Bluetooth y muestra imágenes a modo de monitoreo

