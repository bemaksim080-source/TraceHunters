import ctypes, os, subprocess, sys, time
from ctypes import wintypes
PROCESS_SUSPEND_RESUME = 0x0800
try:
    _ntdll = ctypes.WinDLL("ntdll.dll"); _kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)
    _NtSuspendProcess = _ntdll.NtSuspendProcess; _NtSuspendProcess.argtypes = [wintypes.HANDLE]; _NtSuspendProcess.restype = ctypes.c_long
    _NtResumeProcess = _ntdll.NtResumeProcess; _NtResumeProcess.argtypes = [wintypes.HANDLE]; _NtResumeProcess.restype = ctypes.c_long
    _OpenProcess = _kernel32.OpenProcess; _OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]; _OpenProcess.restype = wintypes.HANDLE
    _CloseHandle = _kernel32.CloseHandle; _CloseHandle.argtypes = [wintypes.HANDLE]; _CloseHandle.restype = wintypes.BOOL
    WINAPI_AVAILABLE = True
except: WINAPI_AVAILABLE = False
def suspend_process(pid):
    if not WINAPI_AVAILABLE: return False
    h = _OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
    if not h: return False
    try: return _NtSuspendProcess(h) == 0
    finally: _CloseHandle(h)
def resume_process(pid):
    if not WINAPI_AVAILABLE: return False
    h = _OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
    if not h: return False
    try: return _NtResumeProcess(h) == 0
    finally: _CloseHandle(h)
class AntiMiner:
    def __init__(self, config, print_func=None):
        self.config = config; self.print_slow = print_func or (lambda x, d=0: print(x))
        self.threshold = config.get("antiminer.cpu_threshold_percent", 80) if config else 80
        self.interval = config.get("antiminer.monitor_interval_sec", 3) if config else 3
        self.auto_suspend = config.get("antiminer.auto_suspend", False) if config else False
        self.suspend_duration = config.get("antiminer.suspend_duration_sec", 30) if config else 30
        self.whitelist = [w.lower() for w in (config.get("antiminer.whitelist", []) if config else [])]
        self.suspended = {}
    def get_cpu_per_process(self):
        processes = []
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-Counter '\\Process(*)\\% Processor Time' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty CounterSamples | Where-Object { $_.InstanceName -ne '_total' -and $_.InstanceName -ne 'idle' } | ForEach-Object { $name = $_.InstanceName; $cpu = [math]::Round($_.CookedValue / [Environment]::ProcessorCount, 1); $pid_val = (Get-Process -Name $name -ErrorAction SilentlyContinue | Select-Object -First 1).Id; if ($pid_val) { Write-Output ('{0}|{1}|{2}' -f $pid_val, $name, $cpu) } }"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, shell=True)
            for line in result.stdout.strip().split("\n"):
                parts = line.strip().split("|")
                if len(parts) == 3:
                    try: processes.append({"pid": int(parts[0]), "name": parts[1], "cpu": float(parts[2])})
                    except: pass
        except: pass
        return processes
    def is_whitelisted(self, name): return name.lower() in self.whitelist
    def scan_once(self):
        suspects = []
        for p in self.get_cpu_per_process():
            if p["cpu"] >= self.threshold and not self.is_whitelisted(p["name"]): suspects.append(p)
        return sorted(suspects, key=lambda x: x["cpu"], reverse=True)
    def monitor_loop(self, duration_sec=0):
        self.print_slow(f"🛡️ АНТИ-МАЙНЕР АКТИВИРОВАН (Порог: {self.threshold}%)")
        start_time = time.time()
        try:
            while True:
                if duration_sec > 0 and (time.time() - start_time) >= duration_sec: break
                suspects = self.scan_once()
                if suspects:
                    for s in suspects[:5]:
                        marker = "🔴" if s["cpu"] >= 90 else "🟡"
                        print(f"   {marker} PID:{s['pid']} | CPU:{s['cpu']:.1f}% | {s['name']}")
                        if self.auto_suspend and s["pid"] not in self.suspended:
                            if suspend_process(s["pid"]):
                                self.suspended[s["pid"]] = time.time()
                                self.print_slow(f"      ⏸️ ПРИОСТАНОВЛЕН на {self.suspend_duration}с")
                now = time.time()
                to_resume = [pid for pid, t in self.suspended.items() if now - t >= self.suspend_duration]
                for pid in to_resume:
                    if resume_process(pid): self.print_slow(f"   ▶️ PID:{pid} возобновлён"); del self.suspended[pid]
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.print_slow("🛑 Мониторинг остановлен")
            for pid in list(self.suspended.keys()): resume_process(pid); del self.suspended[pid]
    def quick_check(self):
        self.print_slow("🔍 Быстрая проверка CPU...")
        suspects = self.scan_once()
        if suspects:
            for s in suspects[:10]: print(f"   {'🔴' if s['cpu']>=90 else '🟡'} PID:{s['pid']} CPU:{s['cpu']:.1f}% {s['name']}")
        else: self.print_slow("✅ Чисто")
