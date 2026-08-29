import serial
import time
from pymavlink import mavutil

ESP_PORT = '/dev/ttyUSB0'
ESP_BAUD = 921600 

CUBE_PORT = '/dev/ttyACM0'
CUBE_BAUD = 115200

print(f"Cube Orange'a bağlanılıyor ({CUBE_PORT})...")
try:
    # MAVLink 2 kullanılmalı (RTCM için zorunludur)
    import os
    os.environ['MAVLINK20'] = '1'
    
    master = mavutil.mavlink_connection(CUBE_PORT, baud=CUBE_BAUD)
    master.wait_heartbeat()
    print("-> Cube Orange Heartbeat alındı!")
    
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL, 
        2, 1
    )
except Exception as e:
    print(f"Cube Orange bağlantı hatası: {e}")
    exit()

print(f"ESP32'ye bağlanılıyor ({ESP_PORT})...")
try:
    esp_serial = serial.Serial(ESP_PORT, ESP_BAUD, timeout=0.1)
    print("-> ESP bağlantısı başarılı.")
except Exception as e:
    print(f"ESP bağlantı hatası: {e}")
    exit()

last_fix_type = -1
sequence_id = 0  # RTCM paket sırası (0-31 arası döner)

print("\n--- Sistem Dinlemede (Bekleyiniz) ---")

try:
    while True:
        # 1. ESP'den Gelen RTCM'i Oku ve Yönlendir
        if esp_serial.in_waiting > 0:
            raw_data = esp_serial.read(min(esp_serial.in_waiting, 180))
            
            # Veriyi 180 byte'lık MAVLink standardına uydur ama DOLDURMA! (Flags ile yönet)
            data_len = len(raw_data)
            print(f"Havadan {data_len} byte geldi ve MAVLink'e basılıyor...")
            flags = 0  # Parçalanma bayrağı (şimdilik 0, basit yollama)
            
            # Sequence ID 0-31 arası sürekli döner
            sequence_id = (sequence_id + 1) % 32
            
            # Verinin geri kalanını 0 ile doldurmak zorundayız (MAVLink yapısı gereği)
            padded_data = bytearray(raw_data)
            if len(padded_data) < 180:
                padded_data.extend([0] * (180 - len(padded_data)))

            # DOĞRU MESAJ FORMATI: flags, len, data
            master.mav.gps_rtcm_data_send(
                flags | (sequence_id << 3), # Flags ve Sequence ID birleşimi
                data_len,                   # Sadece GERÇEK verinin uzunluğu
                list(padded_data)           # 180 byte'lık dizi
            )

        # 2. Cube Orange'ın GPS Durumunu Oku
        msg = master.recv_match(type='GPS_RAW_INT', blocking=False)
        if msg:
            current_fix = msg.fix_type
            if current_fix != last_fix_type:
                last_fix_type = current_fix
                print("-" * 50)
                if current_fix == 6:
                    print("[GÜVENLİ] CUBE ORANGE: RTK FIXED (Santimetre Hassasiyeti)")
                elif current_fix == 5:
                    print("[BEKLE] CUBE ORANGE: RTK FLOAT")
                elif current_fix == 3:
                    print("[DİKKAT] CUBE ORANGE: 3D FIX (Normal GPS)")
                print("-" * 50)
                
        time.sleep(0.01)

except KeyboardInterrupt:
    pass
finally:
    esp_serial.close()
    master.close()