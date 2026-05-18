"""
EyeCatch BLE Setup Server (라즈베리파이 전용)
dbus-next 기반 구현

UUID:
  서비스:        0000ebec-0000-1000-8000-00805f9b34fb
  와이파이 수신: 0000ec01-0000-1000-8000-00805f9b34fb  (Write)
  상태 알림:     0000ec02-0000-1000-8000-00805f9b34fb  (Notify)
  페어링 코드:   0000ec03-0000-1000-8000-00805f9b34fb  (Notify)
"""

import sys

if sys.platform != "linux":
    print("❌ ble_server.py는 라즈베리파이(Linux)에서만 실행 가능해요.")
    sys.exit(1)

import asyncio
import subprocess
import json
import os
import time
import uuid
import requests
from dotenv import load_dotenv
from dbus_next.aio import MessageBus
from dbus_next import BusType, Variant
from dbus_next.service import ServiceInterface, method, dbus_property
from dbus_next.constants import PropertyAccess

load_dotenv()

SERVER_URL        = os.getenv("SERVER_URL", "http://localhost:8000")
BRIDGE_STATE_FILE = "bridge_state.json"

SERVICE_UUID        = "0000ebec-0000-1000-8000-00805f9b34fb"
PROVISION_CHAR_UUID = "0000ec01-0000-1000-8000-00805f9b34fb"
STATUS_CHAR_UUID    = "0000ec02-0000-1000-8000-00805f9b34fb"
CODE_CHAR_UUID      = "0000ec03-0000-1000-8000-00805f9b34fb"

SERVICE_PATH   = "/org/eyecatch/service0"
CHAR_PATH_BASE = "/org/eyecatch/service0/char"
AD_PATH        = "/org/eyecatch/advertisement0"

received_wifi_data  = None
status_char_obj     = None
code_char_obj       = None
wifi_received_event = None


# ──────────────────────────────────────────
# GATT 특성
# ──────────────────────────────────────────

class ProvisioningCharacteristic(ServiceInterface):
    def __init__(self, service_path):
        super().__init__("org.bluez.GattCharacteristic1")
        self._service = service_path
        self._value   = []

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> 's':
        return PROVISION_CHAR_UUID

    @dbus_property(access=PropertyAccess.READ)
    def Service(self) -> 'o':
        return self._service

    @dbus_property(access=PropertyAccess.READ)
    def Flags(self) -> 'as':
        return ["write"]

    @dbus_property(access=PropertyAccess.READ)
    def Value(self) -> 'ay':
        return self._value

    @method()
    def WriteValue(self, value: 'ay', options: 'a{sv}'):
        global received_wifi_data
        raw = bytes(value).decode("utf-8")
        print(f"📥 와이파이 정보 수신: {raw}")
        try:
            received_wifi_data = json.loads(raw)
            print(f"✅ ssid={received_wifi_data.get('ssid')}")
            if wifi_received_event:
                wifi_received_event.set()
        except json.JSONDecodeError:
            print("❌ JSON 파싱 실패")


class NotifyCharacteristic(ServiceInterface):
    def __init__(self, service_path, char_uuid):
        super().__init__("org.bluez.GattCharacteristic1")
        self._service   = service_path
        self._uuid      = char_uuid
        self._value     = []
        self._notifying = False

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> 's':
        return self._uuid

    @dbus_property(access=PropertyAccess.READ)
    def Service(self) -> 'o':
        return self._service

    @dbus_property(access=PropertyAccess.READ)
    def Flags(self) -> 'as':
        return ["notify"]

    @dbus_property(access=PropertyAccess.READ)
    def Value(self) -> 'ay':
        return self._value

    @method()
    def StartNotify(self):
        self._notifying = True

    @method()
    def StopNotify(self):
        self._notifying = False

    def send(self, message: str):
        self._value = list(message.encode("utf-8"))
        self.emit_properties_changed({"Value": Variant('ay', self._value)})


class GattService(ServiceInterface):
    def __init__(self):
        super().__init__("org.bluez.GattService1")

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> 's':
        return SERVICE_UUID

    @dbus_property(access=PropertyAccess.READ)
    def Primary(self) -> 'b':
        return True


class LEAdvertisement(ServiceInterface):
    def __init__(self):
        super().__init__("org.bluez.LEAdvertisement1")
        self._name = f"EyeCatch-{str(uuid.uuid4())[:4].upper()}"
        print(f"📡 BLE 광고 이름: {self._name}")

    @dbus_property(access=PropertyAccess.READ)
    def Type(self) -> 's':
        return "peripheral"

    @dbus_property(access=PropertyAccess.READ)
    def LocalName(self) -> 's':
        return self._name

    @dbus_property(access=PropertyAccess.READ)
    def ServiceUUIDs(self) -> 'as':
        return [SERVICE_UUID]

    @dbus_property(access=PropertyAccess.READ)
    def IncludeTxPower(self) -> 'b':
        return True

    @method()
    def Release(self):
        print("BLE 광고 해제됨")


class ObjectManager(ServiceInterface):
    def __init__(self, objects):
        super().__init__("org.freedesktop.DBus.ObjectManager")
        self._objects = objects

    @method()
    def GetManagedObjects(self) -> 'a{oa{sa{sv}}}':
        return self._objects


# ──────────────────────────────────────────
# 와이파이 연결
# ──────────────────────────────────────────

def connect_wifi(ssid: str, password: str) -> bool:
    print(f"\n📶 와이파이 연결 중: {ssid}")
    if status_char_obj:
        status_char_obj.send("wifi_connecting")
    try:
        subprocess.run(["sudo", "nmcli", "connection", "delete", ssid], capture_output=True)
        result = subprocess.run(
            ["sudo", "nmcli", "device", "wifi", "connect", ssid, "password", password],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print("✅ 와이파이 연결 성공!")
            if status_char_obj:
                status_char_obj.send("wifi_ok")
            return True
        else:
            print(f"❌ 실패: {result.stderr}")
            if status_char_obj:
                status_char_obj.send("wifi_failed")
            return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        if status_char_obj:
            status_char_obj.send(f"error:{str(e)[:50]}")
        return False


# ──────────────────────────────────────────
# 브릿지 등록
# ──────────────────────────────────────────

def load_bridge_id() -> str:
    if os.path.exists(BRIDGE_STATE_FILE):
        with open(BRIDGE_STATE_FILE, "r") as f:
            state = json.load(f)
            bid = state.get("bridge_id")
            if bid:
                return bid
    bid = str(uuid.uuid4())
    with open(BRIDGE_STATE_FILE, "w") as f:
        json.dump({"bridge_id": bid}, f)
    return bid


def register_and_get_code(bridge_id: str):
    if status_char_obj:
        status_char_obj.send("registering")
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
                print(f"✅ 페어링 코드: {code}")
                return code
        except Exception as e:
            print(f"⚠️  재시도... ({e})")
        time.sleep(3)
    if status_char_obj:
        status_char_obj.send("error:server_failed")
    return None


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

async def main_async():
    global status_char_obj, code_char_obj, wifi_received_event

    wifi_received_event = asyncio.Event()

    print("=" * 50)
    print("🔵 EyeCatch BLE Setup 시작")
    print("=" * 50)

    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    # 객체 생성
    gatt_service  = GattService()
    provision_char = ProvisioningCharacteristic(SERVICE_PATH)
    status_char   = NotifyCharacteristic(SERVICE_PATH, STATUS_CHAR_UUID)
    code_char     = NotifyCharacteristic(SERVICE_PATH, CODE_CHAR_UUID)
    advertisement = LEAdvertisement()

    status_char_obj = status_char
    code_char_obj   = code_char

    # ObjectManager에 등록할 객체 딕셔너리
    objects = {
        SERVICE_PATH: {
            "org.bluez.GattService1": {
                "UUID":    Variant('s', SERVICE_UUID),
                "Primary": Variant('b', True),
            }
        },
        CHAR_PATH_BASE + "0": {
            "org.bluez.GattCharacteristic1": {
                "UUID":    Variant('s', PROVISION_CHAR_UUID),
                "Service": Variant('o', SERVICE_PATH),
                "Flags":   Variant('as', ["write"]),
                "Value":   Variant('ay', []),
            }
        },
        CHAR_PATH_BASE + "1": {
            "org.bluez.GattCharacteristic1": {
                "UUID":    Variant('s', STATUS_CHAR_UUID),
                "Service": Variant('o', SERVICE_PATH),
                "Flags":   Variant('as', ["notify"]),
                "Value":   Variant('ay', []),
            }
        },
        CHAR_PATH_BASE + "2": {
            "org.bluez.GattCharacteristic1": {
                "UUID":    Variant('s', CODE_CHAR_UUID),
                "Service": Variant('o', SERVICE_PATH),
                "Flags":   Variant('as', ["notify"]),
                "Value":   Variant('ay', []),
            }
        },
    }

    obj_manager = ObjectManager(objects)

    # DBus 경로 등록
    bus.export("/", obj_manager)
    bus.export(SERVICE_PATH, gatt_service)
    bus.export(CHAR_PATH_BASE + "0", provision_char)
    bus.export(CHAR_PATH_BASE + "1", status_char)
    bus.export(CHAR_PATH_BASE + "2", code_char)
    bus.export(AD_PATH, advertisement)

    # BlueZ 어댑터 찾기
    intro  = await bus.introspect("org.bluez", "/")
    bluez  = bus.get_proxy_object("org.bluez", "/", intro)
    om     = bluez.get_interface("org.freedesktop.DBus.ObjectManager")
    managed = await om.call_get_managed_objects()

    adapter_path = None
    for path, ifaces in managed.items():
        if "org.bluez.Adapter1" in ifaces:
            adapter_path = path
            break

    if not adapter_path:
        print("❌ 블루투스 어댑터를 찾을 수 없어요")
        return

    print(f"✅ 어댑터: {adapter_path}")

    adapter_intro = await bus.introspect("org.bluez", adapter_path)
    adapter_obj   = bus.get_proxy_object("org.bluez", adapter_path, adapter_intro)
    adapter_props = adapter_obj.get_interface("org.freedesktop.DBus.Properties")
    await adapter_props.call_set("org.bluez.Adapter1", "Powered", Variant('b', True))

    # GATT 등록
    gatt_mgr = adapter_obj.get_interface("org.bluez.GattManager1")
    await gatt_mgr.call_register_application("/", {})
    print("✅ GATT 등록 완료")

    # BLE 광고
    ad_mgr = adapter_obj.get_interface("org.bluez.LEAdvertisingManager1")
    await ad_mgr.call_register_advertisement(AD_PATH, {})
    print("✅ BLE 광고 시작")
    print("\n⏳ 앱에서 EyeCatch 기기를 검색하고 연결해주세요...\n")

    # 와이파이 정보 수신 대기
    await wifi_received_event.wait()

    ssid     = received_wifi_data.get("ssid")
    password = received_wifi_data.get("password")

    await asyncio.sleep(1)

    # 와이파이 연결 (블로킹 작업 → executor)
    connected = await asyncio.get_event_loop().run_in_executor(
        None, connect_wifi, ssid, password
    )
    if not connected:
        print("❌ 와이파이 연결 실패")
        return

    # 서버 등록
    bridge_id    = load_bridge_id()
    pairing_code = await asyncio.get_event_loop().run_in_executor(
        None, register_and_get_code, bridge_id
    )
    if not pairing_code:
        print("❌ 페어링 코드 발급 실패")
        return

    if code_char_obj:
        code_char_obj.send(pairing_code)
    print(f"✅ 페어링 코드 전송: {pairing_code}")

    await asyncio.sleep(3)

    print("\n🚀 브릿지 서비스 시작...")
    os.execv(sys.executable, [sys.executable, "main.py"])


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()