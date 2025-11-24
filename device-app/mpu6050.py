import machine

class MPU6050:
    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr
        # Despertar el sensor MPU6050
        self.i2c.writeto(self.addr, b'\x6B\x00')

    def _read_word_2c(self, reg):
        val = self.i2c.readfrom_mem(self.addr, reg, 2)
        val = (val[0] << 8) | val[1]
        if val >= 0x8000:
            return -((65535 - val) + 1)
        else:
            return val

    def get_accel_data(self, g=False):
        x = self._read_word_2c(0x3B)
        y = self._read_word_2c(0x3D)
        z = self._read_word_2c(0x3F)
        if g:
            x /= 16384.0
            y /= 16384.0
            z /= 16384.0
        return {'x': x, 'y': y, 'z': z}

    def get_gyro_data(self):
        x = self._read_word_2c(0x43)
        y = self._read_word_2c(0x45)
        z = self._read_word_2c(0x47)
        x /= 131.0
        y /= 131.0
        z /= 131.0
        return {'x': x, 'y': y, 'z': z}