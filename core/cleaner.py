import os, subprocess
from pathlib import Path
class SystemCleaner:
    def __init__(self):
        self.user_profile = os.environ.get("USERPROFILE", "")
        self.targets = {
            "Windows Temp": {"path": os.environ.get("TEMP", ""), "safe": True, "desc": "Временные файлы"},
            "Chrome Cache": {"path": os.path.join(self.user_profile, r"AppData\Local\Google\Chrome\User Data\Default\Cache"), "safe": True, "desc": "Кеш Chrome"},
            "Recycle Bin": {"path": "shell:RecycleBinFolder", "safe": True, "desc": "Корзина", "is_recycle": True}
        }
    def scan(self):
        results = {}
        for name, info in self.targets.items():
            size_bytes = 0; file_count = 0; path = info["path"]
            if info.get("is_recycle"):
                try:
                    res = subprocess.run(["powershell", "-Command", "(New-Object -ComObject Shell.Application).NameSpace(0xA).Items() | Measure-Object -Property Size -Sum | Select-Object -ExpandProperty Sum"], capture_output=True, text=True, timeout=10)
                    size_bytes = int(res.stdout.strip() or 0)
                except: pass
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for f in files:
                        try: size_bytes += os.path.getsize(os.path.join(root, f)); file_count += 1
                        except: pass
            results[name] = {"size_mb": round(size_bytes / 1024 / 1024, 2), "files": file_count, "safe": info["safe"], "desc": info["desc"]}
        return results
    def clean(self, targets_list):
        report = {}
        for name in targets_list:
            if name not in self.targets: continue
            info = self.targets[name]; path = info["path"]; freed = 0; deleted = 0
            if info.get("is_recycle"):
                try: subprocess.run(["powershell", "-Command", "Clear-RecycleBin -Force"], capture_output=True, timeout=15); freed = -1
                except: pass
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path, topdown=False):
                    for f in files:
                        fp = os.path.join(root, f)
                        try: freed += os.path.getsize(fp); os.remove(fp); deleted += 1
                        except: pass
            report[name] = {"freed_mb": round(freed / 1024 / 1024, 2) if freed > 0 else freed, "deleted": deleted}
        return report
