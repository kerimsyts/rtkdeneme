import serial
import time
import base64
import zlib

BASE_STATION_PORT = 'COM8'
BASE_BAUD_RATE = 115200
ESP_PORT = 'COM5'
ESP_BAUD_RATE = 921600

def package_for_mesh(raw_chunk):
    # 1. Ham veriyi metne çevir (Base64)
    b64_data = base64.b64encode(raw_chunk).decode('ascii')
    # 2. Sürü paketlerinden ayırmak için "RTK:" başlığı ekle
    payload = f"RTK:{b64_data}"
    # 3. ESP32 C++ kodunun istediği CRC32 şifresini hesapla
    crc = zlib.crc32(payload.encode('ascii')) & 0xFFFFFFFF
    crc_hex = f"{crc:08x}"
    # 4. Şifreyi ve satır sonunu ekleyip ESP'ye yolla
    return f"{payload}*{crc_hex}\n".encode('ascii')

print("Portlar açılıyor...")
try:
    base_serial = serial.Serial(BASE_STATION_PORT, BASE_BAUD_RATE, timeout=0.1)
    esp_serial = serial.Serial(ESP_PORT, ESP_BAUD_RATE, timeout=0.1)
    base_serial.reset_input_buffer()
    esp_serial.reset_output_buffer()
    print("Sistem hazır. ESP-Mesh uyumlu yayın başlıyor...")
except Exception as e:
    print(f"Bağlantı hatası: {e}")
    exit()

try:
    while True:
        if base_serial.in_waiting > 0:
            # Sizin C++ kodunun MAX_LINE_BYTES=240 sınırı var. Güvenlik için 150 okuyoruz.
            raw_rtcm_data = base_serial.read(min(base_serial.in_waiting, 150))
            
            # Veriyi C++ kodunun kılığına sok ve gönder
            mesh_packet = package_for_mesh(raw_rtcm_data)
            esp_serial.write(mesh_packet)
            
            print(f"Tripoddan {len(raw_rtcm_data)} byte okundu, Mesh şifresiyle ESP'ye basıldı.")
            time.sleep(0.02) 
            
except KeyboardInterrupt:
    print("\nİşlem durduruldu.")
finally:
    base_serial.close()
    esp_serial.close()
    print("Portlar kapatıldı.")