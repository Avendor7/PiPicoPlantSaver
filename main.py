from machine import Pin, I2C, ADC, SPI
import utime as time
import dht
import framebuf
import network
from umqtt.simple import MQTTClient
import json

# WiFi Settings
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# MQTT Settings
MQTT_BROKER = "YOUR_HOME_ASSISTANT_IP"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "pico_plant_saver"
MQTT_USER = "YOUR_MQTT_USERNAME"  # If you have MQTT authentication enabled
MQTT_PASSWORD = "YOUR_MQTT_PASSWORD"  # If you have MQTT authentication enabled
MQTT_TOPIC = "homeassistant/sensor/plant_saver"

# Soil Moisture Sensor Setup
adc = ADC(26)
conversion_factor = 100 / (65535)

# DHT11 Sensor Setup
dht_pin = Pin(28, Pin.OUT, Pin.PULL_DOWN)
dht_sensor = dht.DHT11(dht_pin)

# OLED Display Setup
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

class OLED_1inch3(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 128
        self.height = 64
        self.rotate = 180
        
        self.cs = Pin(CS,Pin.OUT)
        self.rst = Pin(RST,Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,2000_000)
        self.spi = SPI(1,20000_000,polarity=0, phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)
        self.init_display()
        
        self.white =   0xffff
        self.balck =   0x0000
        
    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)
        
        self.write_cmd(0xAE)
        self.write_cmd(0x00)
        self.write_cmd(0x10)
        self.write_cmd(0xB0)
        self.write_cmd(0xdc)
        self.write_cmd(0x00)
        self.write_cmd(0x81)
        self.write_cmd(0x6f)
        self.write_cmd(0x21)
        if self.rotate == 0:
            self.write_cmd(0xa0)
        elif self.rotate == 180:
            self.write_cmd(0xa1)
        self.write_cmd(0xc0)
        self.write_cmd(0xa4)
        self.write_cmd(0xa6)
        self.write_cmd(0xa8)
        self.write_cmd(0x3f)
        self.write_cmd(0xd3)
        self.write_cmd(0x60)
        self.write_cmd(0xd5)
        self.write_cmd(0x41)
        self.write_cmd(0xd9)
        self.write_cmd(0x22)
        self.write_cmd(0xdb)
        self.write_cmd(0x35)
        self.write_cmd(0xad)
        self.write_cmd(0x8a)
        self.write_cmd(0XAF)

    def show(self):
        self.write_cmd(0xb0)
        for page in range(0,64):
            if self.rotate == 0:
                self.column = 63 - page
            elif self.rotate == 180:
                self.column = page
            self.write_cmd(0x00 + (self.column & 0x0f))
            self.write_cmd(0x10 + (self.column >> 4))
            for num in range(0,16):
                self.write_data(self.buffer[page*16+num])

# Initialize OLED
oled = OLED_1inch3()
oled.fill(0x0000)
oled.show()

# Connect to WiFi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
    print('WiFi connected!')
    print('Network config:', wlan.ifconfig())

# Initialize MQTT Client
def connect_mqtt():
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER,
                       port=MQTT_PORT,
                       user=MQTT_USER,
                       password=MQTT_PASSWORD,
                       keepalive=30)
    client.connect()
    return client

# Connect to WiFi
connect_wifi()

# Connect to MQTT
try:
    mqtt_client = connect_mqtt()
    print("Connected to MQTT broker")
except Exception as e:
    print("Could not connect to MQTT broker:", e)
    mqtt_client = None

# Main loop
while True:
    try:
        # Read soil moisture
        moisture = 130 - (adc.read_u16() * conversion_factor)
        print("Moisture: ", round(moisture, 1), "%")
        
        # Read temperature and humidity
        dht_sensor.measure()
        t = dht_sensor.temperature()
        h = dht_sensor.humidity()
        print("Temperature: {}°C".format(t))
        print("Humidity: {}%".format(h))
        
        # Update OLED display
        oled.fill(0x0000)
        oled.text("Moisture: {}%".format(round(moisture, 1)), 0, 0, oled.white)
        oled.text("Temp: {}C".format(t), 0, 20, oled.white)
        oled.text("Humidity: {}%".format(h), 0, 40, oled.white)
        oled.show()
        
        # Send data to Home Assistant via MQTT
        if mqtt_client:
            sensor_data = {
                "moisture": round(moisture, 1),
                "temperature": t,
                "humidity": h
            }
            try:
                mqtt_client.publish(MQTT_TOPIC, json.dumps(sensor_data))
                print("Data sent to Home Assistant")
            except Exception as e:
                print("Failed to publish MQTT message:", e)
                # Try to reconnect
                try:
                    mqtt_client = connect_mqtt()
                except:
                    pass
        
        # Wait before next reading
        time.sleep(5)
        
    except Exception as e:
        print("Error:", e)
        time.sleep(5) 