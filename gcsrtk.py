import serial
import time

# ==========================================
# 1. AYARLAR (BİLGİSAYAR PORTLARI)
# ==========================================
BASE_STATION_PORT = 'COM8'  
BASE_BAUD_RATE = 115200     

ESP_PORT = 'COM5' 
ESP_BAUD_RATE = 921600      

# ==========================================
# 2. BAĞLANTILARI KUR
# ==========================================
print("Portlar açiliyor")
try:
    base_serial = serial.Serial(BASE_STATION_PORT, BASE_BAUD_RATE, timeout=0.1)
    esp_serial = serial.Serial(ESP_PORT, ESP_BAUD_RATE, timeout=0.1)
    print("Sistem hazir. Tripod verisi ESP üzerinden gönderiliyor")
except Exception as e:
    print(f"Bağlanti hatasi: {e}")
    exit()

# ==========================================
# 3. HAM VERİ AKTARIM DÖNGÜSÜ
# ==========================================
try:
    while True:
        # Tripoddan RTCM verisi geldikçe oku
        if base_serial.in_waiting > 0:
            raw_rtcm_data = base_serial.read(base_serial.in_waiting)
            
            # Veriyi hiçbir şeye (MAVLink'e vb.) sarmadan, ham haliyle ESP'ye yaz
            esp_serial.write(raw_rtcm_data)
            
        time.sleep(0.01) 
        
except KeyboardInterrupt:
    print("\nİşlem durduruldu.")
finally:
    base_serial.close()
    esp_serial.close()
    print("Portlar kapatildi.")