import serial
import time
from pymavlink import mavutil
import os

ESP_PORT = '/dev/ttyUSB0'
# espbaud921600 imiş, bu değere sadık kalıyoruz.
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
    print("-> ESP bağlantısı başarılı.")
except Exception as e:
    print(f"ESP hatası: {e}")
    exit()

last_fix_type = -1
sequence_id = 0

print("\n--- Sistem Dinlemede ---")

try:
    while True:
        # ESP'den gelenleri oku (Maksimum 180 byte alabiliriz)
        if esp_serial.in_waiting > 0:
            raw_data = esp_serial.read(min(esp_serial.in_waiting, 180))
            data_len = len(raw_data)
            
            sequence_id = (sequence_id + 1) % 32
            
            # PyMAVLink, list() dizisinin tam 180 eleman olmasını zorunlu kılar
            padded_data = bytearray(raw_data)
            if len(padded_data) < 180:
                padded_data.extend([0] * (180 - data_len))
            
            # Veriyi Cube Orange'a gönder (data_len ile sadece dolu kısmı işleme almasını sağlıyoruz)
            master.mav.gps_rtcm_data_send(
                (sequence_id << 3), # Flags: parçalanma yok, sequence ID ekli
                data_len,           # Uçağa bildirilen GERÇEK veri boyutu
                list(padded_data)   # 180 byte'lık dizi kalıbı
            )
            
            # Ekranda senin istediğin dinamik gösterim
            print(f"Havadan {data_len} Byte geldi ve MAVLink'e basıldı!")

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