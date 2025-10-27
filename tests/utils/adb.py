import subprocess
import time
from typing import List, Optional


def run_adb(args: List[str], serial: Optional[str] = None) -> subprocess.CompletedProcess:
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += args
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def list_connected_devices() -> List[str]:
    proc = run_adb(["devices"])
    lines = proc.stdout.strip().splitlines()
    out: List[str] = []
    for line in lines[1:]:
        parts = line.strip().split("\t")
        if len(parts) == 2 and parts[1] == "device":
            out.append(parts[0])
    return out


def pick_udid_from_devices() -> Optional[str]:
    devices = list_connected_devices()
    return devices[0] if len(devices) == 1 else None


def wait_for_boot(serial: Optional[str], timeout_sec: int = 180) -> None:
    start = time.time()
    run_adb(["wait-for-device"], serial)
    while time.time() - start < timeout_sec:
        sys_boot = run_adb(["shell", "getprop", "sys.boot_completed"], serial).stdout.strip()
        dev_boot = run_adb(["shell", "getprop", "dev.bootcomplete"], serial).stdout.strip()
        bootanim = run_adb(["shell", "getprop", "init.svc.bootanim"], serial).stdout.strip()
        if sys_boot == "1" and (dev_boot in ("1", "true")) and bootanim == "stopped":
            run_adb(["shell", "input", "keyevent", "82"], serial)
            return
        time.sleep(2)
    raise TimeoutError("Android device did not finish booting in time")
