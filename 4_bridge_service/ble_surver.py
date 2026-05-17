"""
EyeCatch BLE Setup Server (라즈베리파이 전용)

흐름:
1. 라즈베리파이 부팅 시 실행
2. BLE 광고 시작 → 앱에서 "EyeCatch-XXXX" 기기 검색됨
3. 앱이 BLE로 연결 → {ssid, password, camera_name} 전송
4. 집 와이파이 연결
5. 브릿지 서비스(main.py) 실행

설치:
    pip install dbus-python PyGObject
    sudo apt-get install python3-dbus python3-gi bluez
"""

import subprocess
import json
import sys
import os
import time
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

# BLE 서비스/특성 UUID
EYECATCH_SERVICE_UUID  = "12345678-1234-5678-1234-56789abcdef0"
WIFI_CHAR_UUID         = "12345678-1234-5678-1234-56789abcdef1"  # 앱 → 라즈베리파이

BLUEZ_SERVICE          = "org.bluez"
DBUS_OM_IFACE          = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE        = "org.freedesktop.DBus.Properties"
GATT_SERVICE_IFACE     = "org.bluez.GattService1"
GATT_CHRC_IFACE        = "org.bluez.GattCharacteristic1"
LE_ADVERTISING_MANAGER = "org.bluez.LEAdvertisingManager1"
LE_ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"

mainloop = None
received_data = None


# ──────────────────────────────────────────
# BLE Advertisement
# ──────────────────────────────────────────

class Advertisement(dbus.service.Object):
    PATH_BASE = "/org/bluez/eyecatch/advertisement"

    def __init__(self, bus, index):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = "peripheral"
        self.local_name = f"EyeCatch-{str(uuid.uuid4())[:4].upper()}"
        self.service_uuids = [EYECATCH_SERVICE_UUID]
        dbus.service.Object.__init__(self, bus, self.path)
        print(f"📡 BLE 광고 이름: {self.local_name}")

    def get_properties(self):
        return {
            LE_ADVERTISEMENT_IFACE: {
                "Type": self.ad_type,
                "LocalName": dbus.String(self.local_name),
                "ServiceUUIDs": dbus.Array(self.service_uuids, signature="s"),
                "IncludeTxPower": dbus.Boolean(True),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        return self.get_properties()[interface][prop]

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return self.get_properties()[interface]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE)
    def Release(self):
        print("BLE 광고 해제됨")


# ──────────────────────────────────────────
# GATT 특성 (앱 → 라즈베리파이 데이터 수신)
# ──────────────────────────────────────────

class WifiCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, service):
        self.path = service.path + "/char" + str(index)
        self.bus = bus
        self.service = service
        self.uuid = WIFI_CHAR_UUID
        self.flags = ["write"]
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        return self.get_properties()[interface][prop]

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return self.get_properties()[interface]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        global received_data
        raw = bytes(value).decode("utf-8")
        print(f"📥 데이터 수신: {raw}")
        try:
            received_data = json.loads(raw)
            print(f"✅ 파싱 완료: {received_data}")
            # 데이터 받으면 메인루프 종료
            GLib.idle_add(mainloop.quit)
        except json.JSONDecodeError:
            print("❌ JSON 파싱 실패")


# ──────────────────────────────────────────
# GATT 서비스
# ──────────────────────────────────────────

class EyeCatchService(dbus.service.Object):
    PATH = "/org/bluez/eyecatch/service0"

    def __init__(self, bus):
        self.path = self.PATH
        self.bus = bus
        self.uuid = EYECATCH_SERVICE_UUID
        self.primary = True
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

        # 특성 등록
        self.characteristics.append(WifiCharacteristic(bus, 0, self))

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                "UUID": self.uuid,
                "Primary": self.primary,
                "Characteristics": dbus.Array(
                    [c.get_path() for c in self.characteristics],
                    signature="o"
                ),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        return self.get_properties()[interface][prop]

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return self.get_properties()[interface]

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {self.get_path(): self.get_properties()}
        for chrc in self.characteristics:
            response[chrc.get_path()] = chrc.get_properties()
        return response


# ──────────────────────────────────────────
# 와이파이 연결
# ──────────────────────────────────────────

def connect_wifi(ssid: str, password: str) -> bool:
    print(f"\n📶 와이파이 연결 중: {ssid}")
    try:
        # wpa_supplicant 설정 업데이트
        config = f"""
country=KR
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as f:
            f.write(config)

        subprocess.run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"], check=True)
        print("⏳ 연결 대기 중...")
        time.sleep(10)

        # 연결 확인
        result = subprocess.run(
            ["wpa_cli", "-i", "wlan0", "status"],
            capture_output=True, text=True
        )
        if "COMPLETED" in result.stdout:
            print("✅ 와이파이 연결 성공!")
            return True
        else:
            print("❌ 와이파이 연결 실패")
            return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    global mainloop

    print("=" * 50)
    print("🔵 EyeCatch BLE Setup 시작")
    print("=" * 50)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # BlueZ 어댑터 가져오기
    adapter_path = None
    om = dbus.Interface(bus.get_object(BLUEZ_SERVICE, "/"), DBUS_OM_IFACE)
    objects = om.GetManagedObjects()
    for path, interfaces in objects.items():
        if "org.bluez.Adapter1" in interfaces:
            adapter_path = path
            break

    if not adapter_path:
        print("❌ 블루투스 어댑터를 찾을 수 없어요")
        sys.exit(1)

    adapter = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE, adapter_path),
        "org.bluez.Adapter1"
    )

    # 블루투스 켜기
    props = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE, adapter_path),
        DBUS_PROP_IFACE
    )
    props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))

    # GATT 서비스 등록
    service = EyeCatchService(bus)
    gatt_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE, adapter_path),
        "org.bluez.GattManager1"
    )
    gatt_manager.RegisterApplication(service.get_path(), {})

    # BLE 광고 시작
    advertisement = Advertisement(bus, 0)
    ad_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE, adapter_path),
        LE_ADVERTISING_MANAGER
    )
    ad_manager.RegisterAdvertisement(advertisement.get_path(), {})

    print("\n⏳ 앱에서 EyeCatch 기기를 검색하고 연결해주세요...\n")

    mainloop = GLib.MainLoop()
    mainloop.run()

    # 데이터 수신 완료
    if received_data:
        ssid = received_data.get("ssid")
        password = received_data.get("password")
        camera_name = received_data.get("camera_name", "내 카메라")

        # camera_name을 환경변수로 저장 (main.py에서 사용)
        with open(".ble_data", "w") as f:
            json.dump({"camera_name": camera_name}, f)

        # 와이파이 연결
        if connect_wifi(ssid, password):
            print("\n🚀 브릿지 서비스 시작...")
            os.execv(sys.executable, [sys.executable, "main.py"])
        else:
            print("❌ 와이파이 연결 실패. 다시 시도해주세요.")
            sys.exit(1)
    else:
        print("❌ 데이터를 받지 못했어요.")
        sys.exit(1)


if __name__ == "__main__":
    main()