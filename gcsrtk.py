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
            # MAX 180 byte'lık paketler halinde oku ki ESP boğulmasın
            raw_rtcm_data = base_serial.read(min(base_serial.in_waiting, 180))
            esp_serial.write(raw_rtcm_data)
            
            print(f"Tripoddan {len(raw_rtcm_data)} byte okundu ve ESP'ye basıldı.")
            
            # KRİTİK: ESP'ye bu veriyi havaya atması için 5 milisaniye nefes aldır!
            time.sleep(0.005) 
            
except KeyboardInterrupt:
    print("\nİşlem durduruldu.")
finally:
    base_serial.close()
    esp_serial.close()
    print("Portlar kapatıldı.")