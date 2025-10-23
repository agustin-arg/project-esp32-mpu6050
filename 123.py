import network
import socket
from machine import Pin, ADC
import time

# Configurar ESP32 como Access Point
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='ESP32_AP', password='12345678')

print('Access Point activo')
print('SSID: ESP32_AP')
print('Contraseña: 12345678')
print('IP del AP:', ap.ifconfig()[0])

# Página HTML
html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ESP32 Control</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            background-color: #f0f0f0;
            padding: 20px;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .button-group {
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .btn-on {
            background-color: #4CAF50;
            color: white;
        }
        .btn-on:hover {
            background-color: #45a049;
        }
        .btn-off {
            background-color: #f44336;
            color: white;
        }
        .btn-off:hover {
            background-color: #da190b;
        }
        .status {
            text-align: center;
            margin-top: 20px;
            font-size: 18px;
            padding: 10px;
            border-radius: 5px;
            background-color: #e8f5e9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Control ESP32</h1>
        <div class="button-group">
            <button class="btn-on" onclick="location.href='/led/on'">LED ON</button>
            <button class="btn-off" onclick="location.href='/led/off'">LED OFF</button>
        </div>
        <div class="status">
            <p>Estado: <strong>{status}</strong></p>
            <p>IP: 192.168.4.1</p>
        </div>
    </div>
</body>
</html>
"""

# Configurar GPIO para LED (opcional, usar GPIO 2 o ajustar según tu ESP32)
led = Pin(2, Pin.OUT)

estado_led = False

# Crear socket servidor
def crear_servidor():
    global estado_led
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(1)
    print('Servidor web escuchando en puerto 80...')
    
    while True:
        try:
            conn, addr = s.accept()
            print(f'Conexión desde: {addr}')
            
            request = conn.recv(1024).decode()
            print(f'Request:\n{request}\n')
            
            # Procesar solicitudes
            if '/led/on' in request:
                led.on()
                estado_led = True
                print('LED encendido')
            elif '/led/off' in request:
                led.off()
                estado_led = False
                print('LED apagado')
            
            # Preparar respuesta
            estado_texto = "ENCENDIDO" if estado_led else "APAGADO"
            html_respuesta = html.format(status=estado_texto)
            
            # Enviar respuesta HTTP
            response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Connection: close

{html_respuesta}"""
            
            conn.sendall(response.encode())
            conn.close()
            
        except Exception as e:
            print(f'Error: {e}')
            conn.close()

# Iniciar servidor
crear_servidor()