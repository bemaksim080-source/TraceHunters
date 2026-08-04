import math, os, struct
from pathlib import Path
class PEDetector:
    def __init__(self, config):
        self.config = config
        self.entropy_threshold = config.get("ai_detector.entropy_threshold", 7.2) if config else 7.2
        self.risk_threshold = config.get("ai_detector.risk_threshold", 60) if config else 60
        self.suspicious_sections = [".packed", ".upx", ".themida", ".vmp", ".enigma"]
        self.suspicious_imports = ["VirtualAllocEx", "WriteProcessMemory", "CreateRemoteThread", "URLDownloadToFile", "WinExec", "ShellExecute"]
    @staticmethod
    def calculate_entropy(data):
        if not data: return 0.0
        freq = {}
        for byte in data: freq[byte] = freq.get(byte, 0) + 1
        entropy = 0.0; length = len(data)
        for count in freq.values():
            p = count / length
            if p > 0: entropy -= p * math.log2(p)
        return entropy
    def parse_pe(self, filepath):
        result = {"is_pe": False, "filepath": filepath, "size": 0, "entropy_overall": 0.0, "sections": [], "high_entropy_sections": [], "suspicious_section_names": [], "imports": [], "suspicious_imports_found": [], "risk_score": 0, "risk_factors": []}
        try:
            with open(filepath, "rb") as f: data = f.read()
        except: return None
        result["size"] = len(data); result["entropy_overall"] = self.calculate_entropy(data)
        if len(data) < 64 or data[:2] != b"MZ": return result
        e_lfanew = struct.unpack("<I", data[60:64])[0]
        if e_lfanew + 24 > len(data) or data[e_lfanew:e_lfanew+4] != b"PE\x00\x00": return result
        result["is_pe"] = True
        coff_offset = e_lfanew + 4
        if coff_offset + 20 > len(data): return result
        machine, num_sections, timestamp, _, _, size_opt, characteristics = struct.unpack("<HHIIIHH", data[coff_offset:coff_offset+20])
        opt_offset = coff_offset + 20
        section_offset = opt_offset + size_opt
        for i in range(num_sections):
            sec_start = section_offset + i * 40
            if sec_start + 40 > len(data): break
            name = data[sec_start:sec_start+8].rstrip(b"\x00").decode("ascii", errors="ignore").lower()
            vsize, vaddr, raw_size, raw_ptr = struct.unpack("<IIII", data[sec_start+8:sec_start+24])
            sec_data = data[raw_ptr:raw_ptr+raw_size] if raw_ptr > 0 and raw_size > 0 and raw_ptr + raw_size <= len(data) else b""
            sec_entropy = self.calculate_entropy(sec_data)
            result["sections"].append({"name": name, "entropy": round(sec_entropy, 2)})
            if sec_entropy >= self.entropy_threshold: result["high_entropy_sections"].append(name)
            if name in self.suspicious_sections: result["suspicious_section_names"].append(name)
        data_lower = data.lower()
        for imp in self.suspicious_imports:
            if imp.encode().lower() in data_lower: result["suspicious_imports_found"].append(imp)
        score = 0; factors = []
        if result["entropy_overall"] >= self.entropy_threshold: score += 25; factors.append(f"Высокая энтропия: {result['entropy_overall']:.2f}")
        if result["suspicious_section_names"]: score += min(len(result["suspicious_section_names"]) * 20, 40); factors.append(f"Подозрительные секции: {', '.join(result['suspicious_section_names'])}")
        if result["high_entropy_sections"]: score += min(len(result["high_entropy_sections"]) * 15, 30); factors.append(f"High Entropy секции: {', '.join(result['high_entropy_sections'])}")
        if result["suspicious_imports_found"]: score += min(len(result["suspicious_imports_found"]) * 15, 45); factors.append(f"Подозрительные API: {', '.join(result['suspicious_imports_found'])}")
        if result["size"] < 10240 or result["size"] > 50_000_000: score += 10; factors.append(f"Аномальный размер: {result['size']} байт")
        result["risk_score"] = min(score, 100); result["risk_factors"] = factors
        return result
    def analyze_file(self, filepath):
        pe_data = self.parse_pe(filepath)
        if not pe_data or not pe_data["is_pe"]: return {"filepath": filepath, "is_pe": False, "risk_score": 0, "verdict": "Не PE-файл"}
        score = pe_data["risk_score"]
        verdict = "🔴 ВЫСОКИЙ РИСК" if score >= self.risk_threshold else ("🟡 СРЕДНИЙ РИСК" if score >= 30 else "🟢 НИЗКИЙ РИСК")
        return {"filepath": filepath, "is_pe": True, "risk_score": score, "verdict": verdict, "entropy": pe_data["entropy_overall"], "sections": len(pe_data["sections"]), "high_entropy_sections": pe_data["high_entropy_sections"], "suspicious_sections": pe_data["suspicious_section_names"], "suspicious_imports": pe_data["suspicious_imports_found"], "risk_factors": pe_data["risk_factors"]}
    def scan_directory(self, dirpath, callback=None):
        results = []; path = Path(dirpath)
        pe_files = [f for f in path.rglob("*") if f.is_file() and f.suffix.lower() in (".exe", ".dll", ".sys", ".ocx")]
        for i, f in enumerate(pe_files, 1):
            res = self.analyze_file(str(f)); results.append(res)
            if callback: callback(i, len(pe_files), res)
        return results
