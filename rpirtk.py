import serial
import time
from pymavlink import mavutil

# ==========================================
# 1. AYARLAR (RASPBERRY PI PORTLARI)
# ==========================================
# Pi'ye bağlı ESP'nin portu (USB üzerinden bağlı olduğunu varsayarak)
ESP_PORT = '/dev/ttyUSB0'
ESP_BAUD = 921600 

# Cube Orange'ın Type-C kablo ile Pi'ye bağlı olduğu port
CUBE_PORT = '/dev/ttyACM0'
CUBE_BAUD = 115200

# ==========================================
# 2. BAĞLANTILARI KUR
# ==========================================
print(f"Cube Orange'a bağlanılıyor ({CUBE_PORT})...")
try:
    master = mavutil.mavlink_connection(CUBE_PORT, baud=CUBE_BAUD)
    master.wait_heartbeat()
    print("-> Cube Orange ile MAVLink bağlantısı kuruldu!")
except Exception as e:
    print(f"Cube Orange bağlantı hatası: {e}")
    exit()

print(f"ESP32'ye bağlanılıyor ({ESP_PORT})...")
try:
    esp_serial = serial.Serial(ESP_PORT, ESP_BAUD, timeout=0.1)
    print(" ESP bağlantısı başarılı. Veri akışı ve dinleme başlıyor...")
except Exception as e:
    print(f"ESP bağlantı hatası: {e}")
    exit()

# ==========================================
# 3. AKTARIM VE DİNLEME DÖNGÜSÜ
# ==========================================
last_fix_type = -1

try:
    while True:
        # 1. ESP'den gelen RTCM verisini al ve Cube Orange'a yönlendir
        raw_rtcm_data = esp_serial.read(180)
        
        if raw_rtcm_data:
            chunk_size = 180
            padded_chunk = bytearray(raw_rtcm_data)
            
            if len(padded_chunk) < chunk_size:
                padded_chunk.extend([0] * (chunk_size - len(padded_chunk)))
            
            master.mav.gps_rtcm_data_send(
                0, len(raw_rtcm_data), list(padded_chunk)
            )

        # 2. Cube Orange'ın RTK durumunu Pi üzerinden yerel olarak dinle
        msg = master.recv_match(type='GPS_RAW_INT', blocking=False)
        
        if msg:
            current_fix = msg.fix_type
            
            if current_fix != last_fix_type:
                last_fix_type = current_fix
                print("-" * 50)
                if current_fix == 6:
                    print("[GÜVENLİ] CUBE ORANGE: RTK FIXED (Santimetre Hassasiyeti)")
                elif current_fix == 5:
                    print("[BEKLE] CUBE ORANGE: RTK FLOAT (Düzeltme alınıyor...)")
                elif current_fix == 3:
                    print("[DİKKAT] CUBE ORANGE: 3D FIX (Normal GPS)")
                elif current_fix <= 2:
                    print("[UYARI] CUBE ORANGE: GPS Sinyali Yok/Yetersiz!")
                print("-" * 50)
                
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nİşlem durduruldu.")
finally:
    esp_serial.close()
    master.close()