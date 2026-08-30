import serial
import time
from pymavlink import mavutil
import os
import base64
import sys

ESP_PORT = '/dev/ttyUSB0'
ESP_BAUD = 921600
CUBE_PORT = '/dev/ttyACM0'
CUBE_BAUD = 115200

print(f"Cube Orange'a bağlanılıyor ({CUBE_PORT})")
try:
    os.environ['MAVLINK20'] = '1'
    master = mavutil.mavlink_connection(CUBE_PORT, baud=CUBE_BAUD)
    master.wait_heartbeat()
    print(f" Cube Orange Heartbeat alındı!")
except Exception as e:
    print(f"Bağlantı hatası: {e}")
    exit()

print(f"ESP32'ye bağlanılıyor ({ESP_PORT})")
try:
    esp_serial = serial.Serial(ESP_PORT, ESP_BAUD, timeout=0.1)
    esp_serial.reset_input_buffer()
    print(" ESP bağlantısı başarılı. RTK akışı bekleniyor")
except Exception as e:
    print(f"ESP hatası: {e}")
    exit()

last_fix_type = -1
gps1_fix = 0
gps2_fix = 0
sequence_id = 0
last_status_print_time = time.time()  # 3 saniyelik periyodu tutacağımız zamanlayıcı

print("\n--- Sistem Dinlemede ---")

try:
    while True:
        # 1. ESP-NOW MESH AĞINDAN VERİ OKU VE UÇAĞA BAS
        if esp_serial.in_waiting > 0:
            try:
                line = esp_serial.readline().decode('ascii', errors='ignore').strip()
                
                if line.startswith("RTK:"):
                    b64_part = line.split("*")[0][4:]
                    raw_rtcm = base64.b64decode(b64_part)
                    data_len = len(raw_rtcm)
                    
                    sequence_id = (sequence_id + 1) % 32
                    
                    padded_data = bytearray(raw_rtcm)
                    if len(padded_data) < 180:
                        padded_data.extend([0] * (180 - data_len))
                    
                    master.mav.gps_rtcm_data_send(
                        (sequence_id << 3), 
                        data_len,           
                        list(padded_data)   
                    )
                    
                    # EKRANIN KAYMASINI ÖNLEYEN SABİT SATIR YAZISI (\r ile üzerine yazar)
                    sys.stdout.write(f"\r Mesh'ten {data_len:3} Byte veri drone'a gönderiliyor ")
                    sys.stdout.flush()
            except Exception as e:
                pass 

        # 2. CUBE ORANGE'IN DURUMUNU OKU (Sürekli okur ama her saniye ekrana basmaz)
        msg = master.recv_match(type=['GPS_RAW_INT', 'GPS2_RAW'], blocking=False)
        if msg:
            if msg.get_type() == 'GPS_RAW_INT':
                gps1_fix = msg.fix_type
            elif msg.get_type() == 'GPS2_RAW':
                gps2_fix = msg.fix_type
            last_fix_type = max(gps1_fix, gps2_fix)
        # 3. HER 3 SANİYEDE BİR DURUM RAPORU VER
        current_time = time.time()
        if current_time - last_status_print_time >= 3.0:
            print("\n" + "-" * 50) # Sabit satırın altına inmek için \n
            if last_fix_type == 6:
                print("[GÜVENLİ] CUBE ORANGE: RTK FIXED ")
            elif last_fix_type == 5:
                print("[BEKLE] CUBE ORANGE: RTK FLOAT")
            elif last_fix_type == 3:
                print("[DİKKAT] CUBE ORANGE: 3D FIX (Normal GPS)")
            elif last_fix_type == -1:
                print("[YÜKLENİYOR] CUBE ORANGE: GPS Verisi Bekleniyor...")
            else:
                print(f"[UYARI] CUBE ORANGE: GPS Sinyali Düşük/Yok (Kod: {last_fix_type})")
            print("-" * 50)
            
            # Zamanlayıcıyı sıfırla
            last_status_print_time = current_time

        time.sleep(0.005)

except KeyboardInterrupt:
    pass
finally:
    print("\n\nİşlem kullanıcı tarafından durduruldu.")
    esp_serial.close()
    master.close()