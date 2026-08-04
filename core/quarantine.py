import hashlib, json, os, time, subprocess
from pathlib import Path
class QuarantineManager:
    def __init__(self):
        self.base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.quarantine_dir = os.path.join(self.base_dir, "quarantine")
        self.log_path = os.path.join(self.base_dir, "quarantine_log.json")
        self.key = b"TraceHuntersSecretKey2026!"
        os.makedirs(self.quarantine_dir, exist_ok=True)
    def _xor_crypt(self, data): return bytes([b ^ self.key[i % len(self.key)] for i, b in enumerate(data)])
    def _load_log(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f: return json.load(f)
            except: return []
        return []
    def _save_log(self, log):
        with open(self.log_path, "w", encoding="utf-8") as f: json.dump(log, f, indent=2)
    def isolate_file(self, filepath, threat_name, pid=None):
        if not os.path.isfile(filepath): return {"success": False, "message": "Файл не найден"}
        qid = f"{int(time.time())}_{hashlib.sha256(filepath.encode()).hexdigest()[:12]}"
        q_path = os.path.join(self.quarantine_dir, f"{qid}_{Path(filepath).name}.quarantined")
        try:
            with open(filepath, "rb") as f: data = f.read()
            with open(q_path, "wb") as f: f.write(self._xor_crypt(data))
            os.remove(filepath)
            log = self._load_log()
            log.append({"id": qid, "original_path": filepath, "threat": threat_name, "timestamp": int(time.time()), "status": "quarantined"})
            self._save_log(log)
            return {"success": True, "message": f"Изолирован: {qid}"}
        except Exception as e: return {"success": False, "message": str(e)}
    def kill_and_isolate(self, pid, filepath, threat_name):
        try: subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=10); time.sleep(0.5)
        except: pass
        return self.isolate_file(filepath, threat_name, pid)
    def list_quarantined(self): return self._load_log()
    def restore(self, qid):
        log = self._load_log(); entry = next((e for e in log if e["id"] == qid), None)
        if not entry: return {"success": False, "message": "Не найден"}
        candidates = [f for f in os.listdir(self.quarantine_dir) if f.startswith(qid)]
        if not candidates: return {"success": False, "message": "Файл удален"}
        try:
            with open(os.path.join(self.quarantine_dir, candidates[0]), "rb") as f: enc = f.read()
            with open(entry["original_path"], "wb") as f: f.write(self._xor_crypt(enc))
            os.remove(os.path.join(self.quarantine_dir, candidates[0]))
            entry["status"] = "restored"; self._save_log(log)
            return {"success": True, "message": "Восстановлен"}
        except Exception as e: return {"success": False, "message": str(e)}
    def delete_permanently(self, qid):
        log = self._load_log(); entry = next((e for e in log if e["id"] == qid), None)
        if not entry: return {"success": False, "message": "Не найден"}
        candidates = [f for f in os.listdir(self.quarantine_dir) if f.startswith(qid)]
        if not candidates: return {"success": False, "message": "Уже удален"}
        try:
            os.remove(os.path.join(self.quarantine_dir, candidates[0]))
            entry["status"] = "deleted"; self._save_log(log)
            return {"success": True, "message": "Удален навсегда"}
        except Exception as e: return {"success": False, "message": str(e)}
