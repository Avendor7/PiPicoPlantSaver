import machine
import utime
import I2C_LCD_driver

led_onboard = machine.Pin(25, machine.Pin.OUT)
adc = machine.ADC(26)
lcd = I2C_LCD_driver.lcd()
conversion_factor = 100 / (65535)

while True:
    moisture = 130 - (adc.read_u16() * conversion_factor)
    print("Moisture: ", round(moisture, 1), "% - ", utime.localtime())
    lcd.lcd_display_string("Moisture: {:.1f}%  ".format(moisture,), 1)
    
    if moisture >= 70 :
        led_onboard.value(0)
        utime.sleep(30)
    elif moisture < 70 :
        led_onboard.toggle()
        utime.sleep_ms(500)