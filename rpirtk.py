import serial
import time
from pymavlink import mavutil
import os
import base64

ESP_PORT = '/dev/ttyUSB0'
ESP_BAUD = 921600
CUBE_PORT = '/dev/ttyACM0'
CUBE_BAUD = 115200

print(f"Cube Orange'a bağlanılıyor ({CUBE_PORT})...")
try:
    os.environ['MAVLINK20'] = '1'
    master = mavutil.mavlink_connection(CUBE_PORT, baud=CUBE_BAUD)
    master.wait_heartbeat()
    print("-> Cube Orange Heartbeat alındı!")
except Exception as e:
    print(f"Bağlantı hatası: {e}")
    exit()

print(f"ESP32'ye bağlanılıyor ({ESP_PORT})...")
try:
    esp_serial = serial.Serial(ESP_PORT, ESP_BAUD, timeout=0.1)
    esp_serial.reset_input_buffer()
    print("-> ESP bağlantısı başarılı. Temiz RTK akışı bekleniyor...")
except Exception as e:
    print(f"ESP hatası: {e}")
    exit()

last_fix_type = -1
sequence_id = 0

print("\n--- Sistem Dinlemede ---")

try:
    while True:
        # C++ kodu veriyi satır satır (\n) yolladığı için readline kullanıyoruz
        if esp_serial.in_waiting > 0:
            try:
                line = esp_serial.readline().decode('ascii', errors='ignore').strip()
                
                # GELEN VERİ BİZİM RTK VERİMİZ Mİ YOKSA DRONE TELEMETRİSİ Mİ?
                if line.startswith("RTK:"):
                    # "RTK:" başlığını ve "*xxxxxxxx" şifresini at, ortadaki veriyi al
                    b64_part = line.split("*")[0][4:]
                    
                    # Metni tekrar orjinal RAW RTCM bytelarına çevir
                    raw_rtcm = base64.b64decode(b64_part)
                    data_len = len(raw_rtcm)
                    
                    sequence_id = (sequence_id + 1) % 32
                    
                    padded_data = bytearray(raw_rtcm)
                    if len(padded_data) < 180:
                        padded_data.extend([0] * (180 - data_len))
                    
                    # Şifresi çözülmüş tertemiz RTCM paketini uçağa yolla
                    master.mav.gps_rtcm_data_send(
                        (sequence_id << 3), 
                        data_len,           
                        list(padded_data)   
                    )
                    
                    print(f"Havadaki Mesh'ten {data_len} Byte GERÇEK RTK alındı ve Uçağa basıldı!")
            except Exception as e:
                pass # Bozuk veya alakasız paketleri sessizce yut

        # Cube Orange Durumunu Oku
        msg = master.recv_match(type='GPS_RAW_INT', blocking=False)
        if msg:
            current_fix = msg.fix_type
            if current_fix != last_fix_type:
                last_fix_type = current_fix
                print("-" * 50)
                if current_fix == 6:
                    print("[GÜVENLİ] CUBE ORANGE: RTK FIXED")
                elif current_fix == 5:
                    print("[BEKLE] CUBE ORANGE: RTK FLOAT")
                elif current_fix == 3:
                    print("[DİKKAT] CUBE ORANGE: 3D FIX")
                print("-" * 50)
                
        time.sleep(0.005)

except KeyboardInterrupt:
    pass
finally:
    esp_serial.close()
    master.close()