"""
EyeCatch BLE Setup Server - gi/GLib/dbus 기반
"""
import sys
if sys.platform != "linux":
    print("Linux only"); sys.exit(1)

import os, json, time, uuid, subprocess, requests, threading
from dotenv import load_dotenv
import dbus, dbus.service, dbus.mainloop.glib
from gi.repository import GLib

load_dotenv()

SERVER_URL        = os.getenv("SERVER_URL", "http://localhost:8000")
BRIDGE_STATE_FILE = "bridge_state.json"

SERVICE_UUID        = "0000ebec-0000-1000-8000-00805f9b34fb"
PROVISION_CHAR_UUID = "0000ec01-0000-1000-8000-00805f9b34fb"
STATUS_CHAR_UUID    = "0000ec02-0000-1000-8000-00805f9b34fb"
CODE_CHAR_UUID      = "0000ec03-0000-1000-8000-00805f9b34fb"

BLUEZ     = "org.bluez"
DBUS_OM   = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP = "org.freedesktop.DBus.Properties"
GATT_SVC  = "org.bluez.GattService1"
GATT_CHR  = "org.bluez.GattCharacteristic1"
LE_AD_MGR = "org.bluez.LEAdvertisingManager1"
LE_AD     = "org.bluez.LEAdvertisement1"

mainloop           = None
received_wifi_data = None
_status_chr        = None
_code_chr          = None


def _to_dbus_bytes(s):
    return dbus.Array([dbus.Byte(b) for b in s.encode("utf-8")], signature="y")


def _send_status(message):
    """GLib 메인루프에서 안전하게 상태 전송"""
    if _status_chr:
        GLib.idle_add(_status_chr.send, message)


def _send_code(code):
    """GLib 메인루프에서 안전하게 코드 전송"""
    if _code_chr:
        GLib.idle_add(_code_chr.send, code)


# ── Advertisement ────────────────────────────────────────────────────
class Advertisement(dbus.service.Object):
    def __init__(self, bus, index):
        self.path     = f"/org/eyecatch/ad{index}"
        self._ad_name = f"EyeCatch-{str(uuid.uuid4())[:4].upper()}"
        dbus.service.Object.__init__(self, bus, self.path)
        print(f"📡 BLE 광고 이름: {self._ad_name}")

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return {
            "Type":           dbus.String("peripheral"),
            "LocalName":      dbus.String(self._ad_name),
            "ServiceUUIDs":   dbus.Array([SERVICE_UUID], signature="s"),
            "IncludeTxPower": dbus.Boolean(True),
        }

    @dbus.service.method(LE_AD)
    def Release(self):
        pass


# ── Base Characteristic ──────────────────────────────────────────────
class BaseChar(dbus.service.Object):
    def __init__(self, bus, index, char_uuid, flags, svc_path):
        self.path     = f"/org/eyecatch/svc0/chr{index}"
        self.uuid     = char_uuid
        self.flags    = flags
        self.svc_path = svc_path
        self._value   = dbus.Array([], signature="y")
        self._notify  = False
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def props(self):
        return {
            GATT_CHR: {
                "UUID":    dbus.String(self.uuid),
                "Service": dbus.ObjectPath(self.svc_path),
                "Flags":   dbus.Array(self.flags, signature="s"),
                "Value":   self._value,
            }
        }

    @dbus.service.method(DBUS_PROP, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return self.props().get(iface, {})

    @dbus.service.signal(DBUS_PROP, signature="sa{sv}as")
    def PropertiesChanged(self, iface, changed, invalid):
        pass

    @dbus.service.method(GATT_CHR)
    def StartNotify(self):
        self._notify = True

    @dbus.service.method(GATT_CHR)
    def StopNotify(self):
        self._notify = False

    def send(self, message):
        self._value = _to_dbus_bytes(message)
        self.PropertiesChanged(GATT_CHR, {"Value": self._value}, [])
        return False  # GLib.idle_add 콜백은 False 반환해야 1회 실행


# ── Provisioning Characteristic ──────────────────────────────────────
class ProvisionChar(BaseChar):
    def __init__(self, bus, svc_path):
        super().__init__(bus, 0, PROVISION_CHAR_UUID, ["write", "write-without-response"], svc_path)
        self.buffer = ""  # 💡 데이터를 모을 바구니 추가

    @dbus.service.method(GATT_CHR, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        global received_wifi_data
        chunk = bytes(value).decode("utf-8")
        self.buffer += chunk
        print(f"📥 수신된 조각: {chunk}")

        try:
            # 💡 바구니에 모인 데이터가 완벽한 JSON인지 확인
            received_wifi_data = json.loads(self.buffer)
            print(f"✅ 완전한 JSON 조립 성공: ssid={received_wifi_data.get('ssid')}")
            
            # 성공했으니 바구니 비우기
            self.buffer = ""
            
            # 메인루프 유지한 채로 별도 스레드에서 처리
            threading.Thread(target=after_wifi, daemon=False).start()
        except json.JSONDecodeError:
            # 💡 아직 덜 왔으면 에러를 내지 않고 다음 조각을 기다림
            pass
        except Exception as e:
            print(f"❌ JSON 파싱 실패: {e}")
            self.buffer = "" # 예기치 않은 오류 시 버퍼 초기화


# ── GATT Service ─────────────────────────────────────────────────────
class GattService(dbus.service.Object):
    PATH = "/org/eyecatch/svc0"

    def __init__(self, bus):
        dbus.service.Object.__init__(self, bus, self.PATH)
        self.chars = [
            ProvisionChar(bus, self.PATH),
            BaseChar(bus, 1, STATUS_CHAR_UUID, ["notify"], self.PATH),
            BaseChar(bus, 2, CODE_CHAR_UUID,   ["notify"], self.PATH),
        ]

    def get_path(self):
        return dbus.ObjectPath(self.PATH)

    def svc_props(self):
        return {
            GATT_SVC: {
                "UUID":            dbus.String(SERVICE_UUID),
                "Primary":         dbus.Boolean(True),
                "Characteristics": dbus.Array(
                    [c.get_path() for c in self.chars], signature="o"
                ),
            }
        }

    @dbus.service.method(DBUS_PROP, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return self.svc_props().get(iface, {})

    @dbus.service.method(DBUS_OM, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        result = {self.get_path(): self.svc_props()}
        for c in self.chars:
            result[c.get_path()] = c.props()
        return result


# ── Wi-Fi 연결 ───────────────────────────────────────────────────────
def connect_wifi(ssid, password):
    print(f"📶 와이파이 연결: {ssid}")
    _send_status("wifi_connecting")
    try:
        subprocess.run(
            ["sudo", "nmcli", "connection", "delete", ssid],
            capture_output=True
        )
        r = subprocess.run(
            ["sudo", "nmcli", "device", "wifi", "connect", ssid, "password", password],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            print("✅ 와이파이 성공")
            _send_status("wifi_ok")
            return True
        print(f"❌ 실패: {r.stderr}")
        _send_status("wifi_failed")
        return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        _send_status(f"error:{str(e)[:50]}")
        return False


def load_bridge_id():
    if os.path.exists(BRIDGE_STATE_FILE):
        with open(BRIDGE_STATE_FILE) as f:
            bid = json.load(f).get("bridge_id")
            if bid: return bid
    bid = str(uuid.uuid4())
    with open(BRIDGE_STATE_FILE, "w") as f:
        json.dump({"bridge_id": bid}, f)
    return bid


def register_code(bridge_id):
    _send_status("registering")
    for _ in range(5):
        try:
            r = requests.post(
                f"{SERVER_URL}/bridges/register",
                json={"bridge_id": bridge_id},
                timeout=10
            )
            if r.status_code in (200, 201):
                return r.json().get("pairing_code")
        except Exception as e:
            print(f"⚠️ {e}")
        time.sleep(3)
    _send_status("error:server_failed")
    return None


def after_wifi():
    ssid     = received_wifi_data["ssid"]
    password = received_wifi_data["password"]
    time.sleep(1)
    if not connect_wifi(ssid, password):
        GLib.idle_add(mainloop.quit)
        return
    bid  = load_bridge_id()
    code = register_code(bid)
    if not code:
        GLib.idle_add(mainloop.quit)
        return
    _send_code(code)
    print(f"✅ 코드 전송: {code}")
    time.sleep(3)
    GLib.idle_add(mainloop.quit)


# ── Main ─────────────────────────────────────────────────────────────
def main():
    global mainloop, _status_chr, _code_chr

    subprocess.run(["hciconfig", "hci0", "noscan"], capture_output=True)
    # Pairing/bonding 비활성화 — 앱에서 OS 페어링 팝업이 뜨지 않도록
    subprocess.run(["hciconfig", "hci0", "noauth", "noencrypt"], capture_output=True)
    subprocess.run(["btmgmt", "bondable", "off"], capture_output=True)

    print("=" * 50)
    print("🔵 EyeCatch BLE Setup 시작")
    print("=" * 50)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    register_agent(bus)

    om      = dbus.Interface(bus.get_object(BLUEZ, "/"), DBUS_OM)
    objects = om.GetManagedObjects()
    adapter_path = next(
        (p for p, i in objects.items() if "org.bluez.Adapter1" in i), None
    )
    if not adapter_path:
        print("❌ 블루투스 어댑터 없음")
        return

    props = dbus.Interface(bus.get_object(BLUEZ, adapter_path), DBUS_PROP)
    props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))

    svc = GattService(bus)
    _status_chr = svc.chars[1]
    _code_chr   = svc.chars[2]

    gatt_mgr = dbus.Interface(
        bus.get_object(BLUEZ, adapter_path), "org.bluez.GattManager1"
    )
    gatt_mgr.RegisterApplication(
        svc.get_path(), {},
        reply_handler=lambda: print("✅ GATT 등록 완료"),
        error_handler=lambda e: print(f"❌ GATT 오류: {e}")
    )

    ad     = Advertisement(bus, 0)
    ad_mgr = dbus.Interface(
        bus.get_object(BLUEZ, adapter_path), LE_AD_MGR
    )
    ad_mgr.RegisterAdvertisement(
        ad.get_path(), {},
        reply_handler=lambda: print("✅ BLE 광고 시작\n⏳ 앱에서 EyeCatch 기기를 검색해주세요\n"),
        error_handler=lambda e: print(f"❌ 광고 오류: {e}")
    )

    mainloop = GLib.MainLoop()
    mainloop.run()

    print("브릿지 서비스 시작...")
    os.execv(sys.executable, [sys.executable, "main.py"])


if __name__ == "__main__":
    main()