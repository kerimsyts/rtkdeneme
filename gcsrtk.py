import serial
import time

BASE_STATION_PORT = 'COM8'  
BASE_BAUD_RATE = 115200     
ESP_PORT = 'COM5' 
ESP_BAUD_RATE = 921600      

print("Portlar açılıyor...")
try:
    base_serial = serial.Serial(BASE_STATION_PORT, BASE_BAUD_RATE, timeout=0.1)
    esp_serial = serial.Serial(ESP_PORT, ESP_BAUD_RATE, timeout=0.1)
    print("Sistem hazır. Tripod bekleniyor...")
except Exception as e:
    print(f"Bağlantı hatası: {e}")
    exit()

try:
    while True:
        if base_serial.in_waiting > 0:
            raw_rtcm_data = base_serial.read(base_serial.in_waiting)
            esp_serial.write(raw_rtcm_data)
            
            # Bize veri aktığını göstersin
            print(f"Tripoddan {len(raw_rtcm_data)} byte veri alındı ve ESP'ye basıldı!")
            
        time.sleep(0.01) 

except KeyboardInterrupt:
    print("\nİşlem kullanıcı tarafından durduruldu.")
finally:
    base_serial.close()
    esp_serial.close()
    print("Portlar güvenli bir şekilde kapatıldı.")