import hashlib
import json
import os
import shutil
import tempfile
import time
import urllib.request
import zipfile

class AutoUpdater:
    def __init__(self, config=None):
        self.config = config
        self.current_version = "0.7"
        # ⚠️ ВАЖНО: Используем raw.githubusercontent.com для прямого доступа к файлу
        self.update_url = "https://bemaksim080-source.github.io/TraceHunters/update.json"
        self.install_dir = os.path.dirname(os.path.dirname(__file__))
        # Обход прокси (на случай если он всё ещё мешает)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def check_for_updates(self):
        result = {"has_update": False, "latest_version": self.current_version, "message": "", "changelog": [], "download_url": "", "sha256": "", "file_size_mb": 0}
        try:
            req = urllib.request.Request(self.update_url, headers={"User-Agent": "TraceHunters/0.7"})
            with self.opener.open(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latest = data.get("latest_version", "0.0")
                result.update({
                    "latest_version": latest,
                    "changelog": data.get("changelog", []),
                    "download_url": data.get("download_url", ""),
                    "sha256": data.get("sha256", ""),
                    "file_size_mb": data.get("file_size_mb", 0)
                })
                if self._ver(latest) > self._ver(self.current_version):
                    result["has_update"] = True
                    result["message"] = f"Доступна новая версия: v{latest}"
                else:
                    result["message"] = "У вас последняя версия, шериф!"
        except Exception as e:
            result["message"] = f"Ошибка проверки: {e}"
        return result

    @staticmethod
    def _ver(v):
        try: return tuple(int(x) for x in v.split("."))
        except: return (0,)

    def download_update(self, url, expected_hash="", progress_callback=None):
        tmp = os.path.join(tempfile.gettempdir(), f"th_update_{int(time.time())}.zip")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TraceHunters/0.7"})
            with self.opener.open(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                done = 0
                with open(tmp, "wb") as f:
                    while chunk := resp.read(8192):
                        f.write(chunk); done += len(chunk)
                        if progress_callback and total > 0: progress_callback(done, total)
            if expected_hash and expected_hash != "PLACEHOLDER_HASH_WILL_BE_SET_AFTER_BUILD":
                h = hashlib.sha256()
                with open(tmp, "rb") as f:
                    while c := f.read(65536): h.update(c)
                if h.hexdigest().lower() != expected_hash.lower():
                    os.remove(tmp); raise ValueError("Хеш не совпадает!")
            return tmp
        except Exception:
            if os.path.exists(tmp): os.remove(tmp)
            raise

    def apply_update(self, zip_path, backup=True):
        result = {"success": False, "message": ""}
        backup_dir = None
        try:
            if backup:
                backup_dir = self.install_dir + f"_backup_{int(time.time())}"
                shutil.copytree(self.install_dir, backup_dir, ignore=shutil.ignore_patterns("data", "__pycache__", ".idea", "website", ".git"))
            with zipfile.ZipFile(zip_path, "r") as zf: zf.extractall(self.install_dir)
            os.remove(zip_path)
            result.update({"success": True, "message": "Обновление установлено! Перезапусти приложение.", "backup_dir": backup_dir})
        except PermissionError:
            result["message"] = "Нет прав. Запусти от администратора."
        except Exception as e:
            result["message"] = f"Ошибка: {e}"
        finally:
            if not result["success"] and backup_dir and os.path.exists(backup_dir):
                try: shutil.rmtree(self.install_dir); shutil.move(backup_dir, self.install_dir)
                except: pass
        return result

    def create_update_package(self, output_path):
        exclude = {"data", "__pycache__", ".idea", "website", "tracehunters_backup_*", ".git"}
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.install_dir):
                dirs[:] = [d for d in dirs if d not in exclude and not d.startswith(".")]
                for f in files:
                    if f.endswith((".pyc", ".pyo")): continue
                    fp = os.path.join(root, f)
                    zf.write(fp, os.path.relpath(fp, self.install_dir))
        h = hashlib.sha256()
        with open(output_path, "rb") as f:
            while c := f.read(65536): h.update(c)
        return h.hexdigest()
