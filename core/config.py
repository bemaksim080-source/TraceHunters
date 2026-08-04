import json, os
class ConfigManager:
    DEFAULT_CONFIG = {
        "scanner": {"auto_scan_on_start": False, "show_clean_processes": False, "progress_interval": 15},
        "cleaner": {"auto_clean_temp": False, "warn_threshold_mb": 100, "include_prefetch": False, "include_recycle_bin": True},
        "quarantine": {"auto_isolate_threats": False, "use_encryption": True, "confirm_before_action": True},
        "antiminer": {"enabled": True, "cpu_threshold_percent": 80, "monitor_interval_sec": 3, "auto_suspend": False, "whitelist": ["system", "svchost.exe", "explorer.exe", "python.exe"]},
        "ai_detector": {"enabled": True, "entropy_threshold": 7.2, "risk_threshold": 60},
        "ui": {"print_speed": 0.015, "theme": "cowboy"},
        "updates": {"auto_check": True, "update_url": "https://raw.githubusercontent.com/bemaksim080-source/TraceHunters/main/update.json"},
        "version": "0.7"
    }
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.config_path = os.path.join(self.config_dir, "config.json")
        self.config = {}
        self._load()
    def _load(self):
        os.makedirs(self.config_dir, exist_ok=True)
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f: self.config = self._deep_merge(self.DEFAULT_CONFIG, json.load(f))
            except: self.config = self.DEFAULT_CONFIG.copy()
        else:
            self.config = self.DEFAULT_CONFIG.copy(); self._save()
    def _deep_merge(self, base, override):
        res = base.copy()
        for k, v in override.items():
            if k in res and isinstance(res[k], dict) and isinstance(v, dict): res[k] = self._deep_merge(res[k], v)
            else: res[k] = v
        return res
    def _save(self):
        with open(self.config_path, "w", encoding="utf-8") as f: json.dump(self.config, f, indent=2)
    def get(self, key, default=None):
        keys = key.split("."); val = self.config
        for k in keys:
            if isinstance(val, dict) and k in val: val = val[k]
            else: return default
        return val
    def set(self, key, value):
        keys = key.split("."); target = self.config
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict): target[k] = {}
            target = target[k]
        target[keys[-1]] = value; self._save()
    def reset(self): self.config = self.DEFAULT_CONFIG.copy(); self._save()
