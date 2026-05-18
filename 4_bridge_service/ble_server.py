"""
EyeCatch BLE Setup Server (라즈베리파이 전용)

Flutter bridge_ble_service.dart 컨트랙트에 맞춰 구현.

UUID:
  서비스:        0000ebec-0000-1000-8000-00805f9b34fb
  와이파이 수신: 0000ec01-0000-1000-8000-00805f9b34fb  (Write)
  상태 알림:     0000ec02-0000-1000-8000-00805f9b34fb  (Notify)
  페어링 코드:   0000ec03-0000-1000-8000-00805f9b34fb  (Notify)

흐름:
  1. BLE 광고 시작 (EyeCatch-XXXX)
  2. 앱이 연결 → 와이파이 정보 수신 (ec01)
  3. 상태 알림: "wifi_connecting" (ec02)
  4. 와이파이 연결 시도
  5. 성공: "wifi_ok" / 실패: "wifi_failed"
  6. 서버에 브릿지 등록 → 페어링 코드 수신
  7. 페어링 코드 전송 (ec03)
  8. BLE 종료 → main.py 실행

설치:
  sudo apt-get install python3-dbus python3-gi bluez
  pip3 install dbus-python PyGObject --break-system-packages
"""

import sys

if sys.platform != "linux":
    print("❌ ble_server.py는 라즈베리파이(Linux)에서만 실행 가능해요.")
    sys.exit(1)

import subprocess
import json
import os
import time
import uuid
import requests
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
BRIDGE_STATE_FILE = "bridge_state.json"

# ── UUID ──
SERVICE_UUID        = "0000ebec-0000-1000-8000-00805f9b34fb"
PROVISION_CHAR_UUID = "0000ec01-0000-1000-8000-00805f9b34fb"  # 앱→브릿지 (Write)
STATUS_CHAR_UUID    = "0000ec02-0000-1000-8000-00805f9b34fb"  # 브릿지→앱 (Notify)
CODE_CHAR_UUID      = "0000ec03-0000-1000-8000-00805f9b34fb"  # 브릿지→앱 (Notify)

BLUEZ_SERVICE       = "org.bluez"
DBUS_OM_IFACE       = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE     = "org.freedesktop.DBus.Properties"
GATT_SERVICE_IFACE  = "org.bluez.GattService1"
GATT_CHRC_IFACE     = "org.bluez.GattCharacteristic1"
LE_AD_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
LE_AD_IFACE         = "org.bluez.LEAdvertisement1"

mainloop = None
received_wifi_data = None
status_characteristic = None
code_characteristic = None


# ──────────────────────────────────────────
# Notify 헬퍼
# ──────────────────────────────────────────

def notify_status(message: str):
    global status_characteristic
    if status_characteristic:
        status_characteristic.send_notify(message)
        print(f"📤 상태 전송: {message}")


def notify_pairing_code(code: str):
    global code_characteristic
    if code_characteristic:
        code_characteristic.send_notify(code)
        print(f"📤 페어링 코드 전송: {code}")


# ──────────────────────────────────────────
# BLE 광고
# ──────────────────────────────────────────

class Advertisement(dbus.service.Object):
    PATH_BASE = "/org/bluez/eyecatch/advertisement"

    def __init__(self, bus, index):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = "peripheral"
        self.local_name = f"EyeCatch-{str(uuid.uuid4())[:4].upper()}"
        self.service_uuids = [SERVICE_UUID]
        dbus.service.Object.__init__(self, bus, self.path)
        print(f"📡 BLE 광고 이름: {self.local_name}")

    def get_properties(self):
        return {
            LE_AD_IFACE: {
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

    @dbus.service.method(LE_AD_IFACE)
    def Release(self):
        print("BLE 광고 해제됨")


# ──────────────────────────────────────────
# GATT 특성 베이스
# ──────────────────────────────────────────

class BaseCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, char_uuid, flags, service):
        self.path = service.path + "/char" + str(index)
        self.bus = bus
        self.uuid = char_uuid
        self.flags = flags
        self.service = service
        self.notifying = False
        self._value = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
                "Value": dbus.Array(self._value, signature="y"),
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

    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    def send_notify(self, message: str):
        if not self.notifying:
            return
        value = [dbus.Byte(b) for b in message.encode("utf-8")]
        self._value = value
        self.PropertiesChanged(
            GATT_CHRC_IFACE,
            {"Value": dbus.Array(value, signature="y")},
            [],
        )

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        self.notifying = True

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        self.notifying = False


# ──────────────────────────────────────────
# GATT 특성 구현
# ──────────────────────────────────────────

class ProvisioningCharacteristic(BaseCharacteristic):
    """ec01 — 앱에서 와이파이 정보 수신 (Write)"""

    def __init__(self, bus, index, service):
        super().__init__(bus, index, PROVISION_CHAR_UUID, ["write"], service)

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        global received_wifi_data
        raw = bytes(value).decode("utf-8")
        print(f"📥 와이파이 정보 수신: {raw}")
        try:
            received_wifi_data = json.loads(raw)
            print(f"✅ 파싱 완료: ssid={received_wifi_data.get('ssid')}, camera_name={received_wifi_data.get('camera_name')}")
            GLib.idle_add(mainloop.quit)
        except json.JSONDecodeError:
            print("❌ JSON 파싱 실패")
            notify_status("error:invalid_json")


class StatusCharacteristic(BaseCharacteristic):
    """ec02 — 상태 알림 (Notify)"""

    def __init__(self, bus, index, service):
        super().__init__(bus, index, STATUS_CHAR_UUID, ["notify"], service)


class PairingCodeCharacteristic(BaseCharacteristic):
    """ec03 — 페어링 코드 전송 (Notify)"""

    def __init__(self, bus, index, service):
        super().__init__(bus, index, CODE_CHAR_UUID, ["notify"], service)


# ──────────────────────────────────────────
# GATT 서비스
# ──────────────────────────────────────────

class EyeCatchService(dbus.service.Object):
    PATH = "/org/bluez/eyecatch/service0"

    def __init__(self, bus):
        self.path = self.PATH
        self.bus = bus
        self.uuid = SERVICE_UUID
        self.primary = True
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

        global status_characteristic, code_characteristic
        provision_char = ProvisioningCharacteristic(bus, 0, self)
        status_characteristic = StatusCharacteristic(bus, 1, self)
        code_characteristic = PairingCodeCharacteristic(bus, 2, self)

        self.characteristics = [
            provision_char,
            status_characteristic,
            code_characteristic,
        ]

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
    notify_status("wifi_connecting")

    try:
        subprocess.run(
            ["sudo", "nmcli", "connection", "delete", ssid],
            capture_output=True
        )
        result = subprocess.run(
            ["sudo", "nmcli", "device", "wifi", "connect", ssid, "password", password],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print("✅ 와이파이 연결 성공!")
            notify_status("wifi_ok")
            return True
        else:
            print(f"❌ 와이파이 연결 실패: {result.stderr}")
            notify_status("wifi_failed")
            return False
    except subprocess.TimeoutExpired:
        print("❌ 와이파이 연결 타임아웃")
        notify_status("wifi_failed")
        return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        notify_status(f"error:{str(e)[:50]}")
        return False


# ──────────────────────────────────────────
# 브릿지 등록
# ──────────────────────────────────────────

def load_bridge_id() -> str:
    if os.path.exists(BRIDGE_STATE_FILE):
        with open(BRIDGE_STATE_FILE, "r") as f:
            state = json.load(f)
            bridge_id = state.get("bridge_id")
            if bridge_id:
                return bridge_id
    bridge_id = str(uuid.uuid4())
    with open(BRIDGE_STATE_FILE, "w") as f:
        json.dump({"bridge_id": bridge_id}, f)
    return bridge_id


def register_and_get_code(bridge_id: str) -> str | None:
    notify_status("registering")
    print("\n📡 서버에 브릿지 등록 중...")

    for _ in range(5):
        try:
            resp = requests.post(
                f"{SERVER_URL}/bridges/register",
                json={"bridge_id": bridge_id},
                timeout=10,
            )
            if resp.status_code in (200, 201):
                code = resp.json().get("pairing_code")
                print(f"✅ 페어링 코드 발급: {code}")
                return code
            else:
                print(f"⚠️  등록 실패 (status: {resp.status_code}), 재시도...")
        except Exception as e:
            print(f"⚠️  서버 연결 실패: {e}, 재시도...")
        time.sleep(3)

    notify_status("error:server_registration_failed")
    return None


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

    # BlueZ 어댑터 찾기
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

    # 블루투스 켜기
    props = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE, adapter_path), DBUS_PROP_IFACE
    )
    props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))

    # GATT 서비스 등록
    service = EyeCatchService(bus)
    gatt_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE, adapter_path), "org.bluez.GattManager1"
    )
    gatt_manager.RegisterApplication(service.get_path(), {})

    # BLE 광고 시작
    advertisement = Advertisement(bus, 0)
    ad_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE, adapter_path), LE_AD_MANAGER_IFACE
    )
    ad_manager.RegisterAdvertisement(advertisement.get_path(), {})

    print("\n⏳ 앱에서 EyeCatch 기기를 검색하고 연결해주세요...\n")

    mainloop = GLib.MainLoop()
    mainloop.run()

    if not received_wifi_data:
        print("❌ 데이터를 받지 못했어요.")
        sys.exit(1)

    ssid = received_wifi_data.get("ssid")
    password = received_wifi_data.get("password")

    time.sleep(1)

    if not connect_wifi(ssid, password):
        print("❌ 와이파이 연결 실패")
        sys.exit(1)

    bridge_id = load_bridge_id()
    pairing_code = register_and_get_code(bridge_id)

    if not pairing_code:
        print("❌ 페어링 코드 발급 실패")
        sys.exit(1)

    notify_pairing_code(pairing_code)
    print(f"✅ 앱에 페어링 코드 전송 완료: {pairing_code}")

    time.sleep(3)

    print("\n🚀 브릿지 서비스 시작...")
    os.execv(sys.executable, [sys.executable, "main.py"])


if __name__ == "__main__":
    main()