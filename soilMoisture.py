import machine
import utime

adc = machine.ADC(26)
conversion_factor = 100 / (65535)

while True:
    moisture = 130 - (adc.read_u16() * conversion_factor)
    print("Moisture: ", round(moisture, 1), "% - ", utime.localtime())
    
    if moisture >= 70 :
        utime.sleep_ms(500)
    elif moisture < 70 :
        utime.sleep_ms(500)