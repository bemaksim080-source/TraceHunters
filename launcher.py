import hashlib, json, os, subprocess, sys, threading, time, tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(__file__), "core"))
try: from cleaner import SystemCleaner
except: SystemCleaner = None
try: from quarantine import QuarantineManager
except: QuarantineManager = None
try: from config import ConfigManager
except: ConfigManager = None
try: from antiminer import AntiMiner, suspend_process, resume_process, WINAPI_AVAILABLE
except: AntiMiner = None; WINAPI_AVAILABLE = False
try: from ai_detector import PEDetector
except: PEDetector = None
try: from updater import AutoUpdater
except: AutoUpdater = None
class T:
    BG="#3E2723"; BM="#5D4037"; GOLD="#D4A017"; GL="#F4C430"; PARCH="#F5E6C8"
    F=("Courier New",10); FW=("Courier New",12,"bold")
class SignatureDB:
    def __init__(self):
        self.db_path=os.path.join(os.path.dirname(__file__),"data","signatures.json"); self.signatures={}; self._load()
    def _load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path,"r",encoding="utf-8") as f: self.signatures={k.lower():v for k,v in json.load(f).items()}
            except: self.signatures={}
        else:
            os.makedirs(os.path.dirname(self.db_path),exist_ok=True)
            self.signatures={"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":"EICAR","275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f":"EICAR"}
            self._save()
    def _save(self):
        with open(self.db_path,"w",encoding="utf-8") as f: json.dump(self.signatures,f,indent=2)
    def check(self,h): return self.signatures.get(h.lower())
class ProcessHunter:
    @staticmethod
    def get_hash(fp):
        s=hashlib.sha256()
        try:
            with open(fp,"rb") as f:
                while c:=f.read(65536): s.update(c)
            return s.hexdigest()
        except: return ""
    @staticmethod
    def get_procs():
        procs=[]
        try:
            r=subprocess.run(["wmic","process","get","Name,ProcessId,ExecutablePath","/format:csv"],capture_output=True,text=True,shell=True,timeout=15)
            for line in r.stdout.strip().split("\n")[1:]:
                p=line.strip().split(",")
                if len(p)>=4 and p[2].strip().isdigit(): procs.append({"pid":int(p[2]),"name":p[1].strip(),"exe":p[3].strip() or "N/A"})
        except:
            try:
                r=subprocess.run(["tasklist","/fo","csv","/nh"],capture_output=True,text=True,shell=True,timeout=15)
                for line in r.stdout.strip().split("\n"):
                    p=line.strip().split(",")
                    if len(p)>=2 and p[1].strip('"').isdigit(): procs.append({"pid":int(p[1].strip('"')),"name":p[0].strip('"'),"exe":"N/A"})
            except: pass
        return procs
    def hunt(self,db,cb=None):
        res=[]; procs=self.get_procs(); tot=len(procs)
        for i,pr in enumerate(procs,1):
            h=self.get_hash(pr["exe"]) if pr["exe"]!="N/A" and os.path.isfile(pr["exe"]) else ""
            d=db.check(h) if h else None; pr.update({"hash":h,"detection":d}); res.append(pr)
            if cb: cb(i,tot,pr)
        return res
class App:
    def __init__(self,root):
        self.root=root; root.title("🤠 TraceHunters v0.7"); root.geometry("950x700"); root.configure(bg=T.BG)
        self.config=ConfigManager() if ConfigManager else None; self.db=SignatureDB(); self.hunter=ProcessHunter()
        self.cleaner=SystemCleaner() if SystemCleaner else None; self.qm=QuarantineManager() if QuarantineManager else None
        self.antiminer=AntiMiner(self.config,print_func=lambda x,d=0:None) if AntiMiner and self.config else None
        self.detector=PEDetector(self.config) if PEDetector and self.config else None
        self.updater=AutoUpdater(self.config) if AutoUpdater else None
        self._style(); self._ui()
        self._log("🤠 Добро пожаловать в офис шерифа!"); self._log(f"📜 В базе: {len(self.db.signatures)} записей")
    def _style(self):
        s=ttk.Style(); s.theme_use("clam")
        s.configure("TFrame",background=T.BG); s.configure("TLabel",background=T.BG,foreground=T.PARCH,font=T.F)
        s.configure("TButton",font=("Courier New",10,"bold"),padding=8); s.configure("Treeview",background=T.BM,foreground=T.PARCH,fieldbackground=T.BM,font=("Courier New",9))
        s.configure("Treeview.Heading",background=T.GOLD,foreground=T.BG,font=("Courier New",10,"bold"))
        s.map("Treeview",background=[("selected",T.GOLD)],foreground=[("selected",T.BG)])
        s.configure("Horizontal.TProgressbar",troughcolor=T.BM,background=T.GOLD,thickness=22)
        s.configure("TLabelframe",background=T.BG,foreground=T.GOLD,font=T.FW); s.configure("TLabelframe.Label",background=T.BG,foreground=T.GL,font=T.FW)
        s.configure("TCheckbutton",background=T.BG,foreground=T.PARCH,font=T.F)
        s.configure("TNotebook",background=T.BG); s.configure("TNotebook.Tab",background=T.BM,foreground=T.PARCH,font=("Courier New",10,"bold"),padding=[12,6])
        s.map("TNotebook.Tab",background=[("selected",T.GOLD)],foreground=[("selected",T.BG)])
    def _ui(self):
        tk.Frame(self.root,bg=T.GOLD,height=3).pack(fill=tk.X)
        hdr=tk.Frame(self.root,bg=T.BG); hdr.pack(fill=tk.X,padx=15,pady=10)
        tk.Label(hdr,text="🤠 TRACEHUNTERS",bg=T.BG,fg=T.GOLD,font=("Courier New",22,"bold")).pack(side=tk.LEFT)
        tk.Label(hdr,text="SHERIFF'S OFFICE • v0.7",bg=T.BG,fg=T.PARCH,font=("Courier New",9)).pack(side=tk.LEFT,padx=20)
        lf=tk.LabelFrame(self.root,text=" 📜 ЖУРНАЛ ",bg=T.BG,fg=T.GOLD,font=T.FW,padx=8,pady=5); lf.pack(fill=tk.X,padx=15,pady=5)
        self.log=scrolledtext.ScrolledText(lf,height=5,bg="#2C1A14",fg=T.GL,font=("Courier New",9),state=tk.DISABLED); self.log.pack(fill=tk.X)
        self.nb=ttk.Notebook(self.root); self.nb.pack(fill=tk.BOTH,expand=True,padx=15,pady=5)
        self._t_scan(); self._t_clean(); self._t_jail(); self._t_miner(); self._t_ai(); self._t_set(); self._t_upd()
    def _log(self,m):
        self.log.configure(state=tk.NORMAL); self.log.insert(tk.END,f"[{time.strftime('%H:%M:%S')}] {m}\n"); self.log.see(tk.END); self.log.configure(state=tk.DISABLED)
    def _t_scan(self):
        f=ttk.Frame(self.nb); self.nb.add(f,text=" 🔍 РОЗЫСК ")
        b=tk.Frame(f,bg=T.BG); b.pack(fill=tk.X,padx=10,pady=8)
        self.sbtn=ttk.Button(b,text="🔫 Облава",command=self._scan_start); self.sbtn.pack(side=tk.LEFT,padx=5)
        self.stbtn=ttk.Button(b,text="✋ Стоп",command=self._scan_stop,state=tk.DISABLED); self.stbtn.pack(side=tk.LEFT,padx=5)
        self.sprog=ttk.Progressbar(f); self.sprog.pack(fill=tk.X,padx=10,pady=5)
        self.sstat=tk.Label(f,text="🏜️ Готов...",bg=T.BG,fg=T.PARCH,font=T.F); self.sstat.pack(padx=10,anchor=tk.W)
        self.stree=ttk.Treeview(f,columns=("pid","name","exe","hash","st"),show="headings",height=13)
        for c,t,w in [("pid","PID",60),("name","Имя",180),("exe","Путь",280),("hash","Хеш",140),("st","Статус",120)]:
            self.stree.heading(c,text=t); self.stree.column(c,width=w)
        self.stree.pack(fill=tk.BOTH,expand=True,padx=10,pady=5); self._scanning=False
    def _scan_start(self):
        if self._scanning: return
        self._scanning=True; self.sbtn.configure(state=tk.DISABLED); self.stbtn.configure(state=tk.NORMAL); self.stree.delete(*self.stree.get_children()); self._log("🔫 Облава началась!")
        def w():
            def cb(i,tot,pr): self.root.after(0,self._s_upd,i,tot,int(i/tot*100),pr)
            r=self.hunter.hunt(self.db,cb); self.root.after(0,self._s_done,len(r),sum(1 for x in r if x["detection"]))
        threading.Thread(target=w,daemon=True).start()
    def _s_upd(self,i,tot,pct,pr):
        self.sprog["value"]=pct; self.sstat.config(text=f"🐎 {i}/{tot}")
        self.stree.insert("",tk.END,values=(pr["pid"],pr["name"],pr["exe"][:45],pr["hash"][:16]+"..." if pr["hash"] else "N/A",f"💀 {pr['detection']}" if pr["detection"] else "✅"))
    def _s_done(self,tot,thr):
        self._scanning=False; self.sbtn.configure(state=tk.NORMAL); self.stbtn.configure(state=tk.DISABLED); self.sprog["value"]=100
        self._log(f"🏆 Проверено {tot}, найдено {thr}"); self.sstat.config(text=f"🏆 Готово: {thr} угроз")
        if thr>0: messagebox.showinfo("⚠️",f"Найдено {thr} угроз. Для ареста используй main.py")
    def _scan_stop(self): self._scanning=False; self._log("✋ Остановлено")
    def _t_clean(self):
        f=ttk.Frame(self.nb); self.nb.add(f,text=" 🧹 САЛУН ")
        b=tk.Frame(f,bg=T.BG); b.pack(fill=tk.X,padx=10,pady=8)
        ttk.Button(b,text="🔍 Осмотр",command=self._junk_scan).pack(side=tk.LEFT,padx=5)
        ttk.Button(b,text="🧹 Убрать",command=self._junk_clean).pack(side=tk.LEFT,padx=5)
        self.ctree=ttk.Treeview(f,columns=("n","s","f","sf","d"),show="headings",height=12)
        for c,t,w in [("n","Место",150),("s","Размер",100),("f","Файлов",80),("sf","Безоп.",80),("d","Описание",350)]:
            self.ctree.heading(c,text=t); self.ctree.column(c,width=w)
        self.ctree.pack(fill=tk.BOTH,expand=True,padx=10,pady=5); self.cres={}
    def _junk_scan(self):
        if not self.cleaner: return
        self.ctree.delete(*self.ctree.get_children()); self.cres=self.cleaner.scan(); tot=0
        for n,inf in self.cres.items(): self.ctree.insert("",tk.END,values=(n,f"{inf['size_mb']:.1f}MB",inf["files"],"✅" if inf["safe"] else "⚠️",inf["desc"])); tot+=inf["size_mb"]
        self._log(f"🗑️ Мусора: {tot:.1f} MB")
    def _junk_clean(self):
        if not self.cres: return
        if not messagebox.askyesno("🤠","Вынести весь мусор?"): return
        rep=self.cleaner.clean(list(self.cres.keys())); fr=sum(r["freed_mb"] for r in rep.values() if r["freed_mb"]>0)
        self._log(f"✅ Убрано: {fr:.1f} MB"); messagebox.showinfo("🏆",f"Убрано {fr:.1f} MB")
    def _t_jail(self):
        f=ttk.Frame(self.nb); self.nb.add(f,text=" 🔒 ТЮРЬМА ")
        b=tk.Frame(f,bg=T.BG); b.pack(fill=tk.X,padx=10,pady=8)
        ttk.Button(b,text="🔄 Обновить",command=self._jail_ref).pack(side=tk.LEFT,padx=5)
        ttk.Button(b,text="🔓 Амнистия",command=self._jail_res).pack(side=tk.LEFT,padx=5)
        ttk.Button(b,text="⚰️ Удалить",command=self._jail_del).pack(side=tk.LEFT,padx=5)
        self.jtree=ttk.Treeview(f,columns=("id","th","p","sz","st"),show="headings",height=14)
        for c,t,w in [("id","ID",120),("th","Угроза",150),("p","Путь",300),("sz","Размер",80),("st","Статус",100)]:
            self.jtree.heading(c,text=t); self.jtree.column(c,width=w)
        self.jtree.pack(fill=tk.BOTH,expand=True,padx=10,pady=5); self._jail_ref()
    def _jail_ref(self):
        if not self.qm: return
        self.jtree.delete(*self.jtree.get_children())
        for it in self.qm.list_quarantined(): self.jtree.insert("",tk.END,values=(it["id"],it["threat"],it["original_path"],f"{it['size']}B",it["status"]))
        self._log(f"🔒 В тюрьме: {len(self.jtree.get_children())}")
    def _jail_res(self):
        if not self.qm: return
        s=self.jtree.selection()
        if not s: return
        qid=self.jtree.item(s[0])["values"][0]
        if messagebox.askyesno("🔓",f"Выпустить {qid}?"):
            r=self.qm.restore(qid); self._log(r["message"]); self._jail_ref()
    def _jail_del(self):
        if not self.qm: return
        s=self.jtree.selection()
        if not s: return
        qid=self.jtree.item(s[0])["values"][0]
        if messagebox.askyesno("⚰️",f"Удалить {qid} навсегда?"):
            r=self.qm.delete_permanently(qid); self._log(r["message"]); self._jail_ref()
    def _t_miner(self):
        f=ttk.Frame(self.nb); self.nb.add(f,text=" ⛏️ МАЙНЕРЫ ")
        b=tk.Frame(f,bg=T.BG); b.pack(fill=tk.X,padx=10,pady=8)
        ttk.Button(b,text="🔍 Проверка",command=self._miner_chk).pack(side=tk.LEFT,padx=5)
        ttk.Button(b,text="🛡️ Дозор 30с",command=lambda:self._miner_mon(30)).pack(side=tk.LEFT,padx=5)
        self.mtxt=scrolledtext.ScrolledText(f,height=18,bg="#2C1A14",fg=T.GL,font=("Courier New",9),state=tk.DISABLED); self.mtxt.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)
    def _mlog(self,m): self.mtxt.configure(state=tk.NORMAL); self.mtxt.insert(tk.END,m+"\n"); self.mtxt.see(tk.END); self.mtxt.configure(state=tk.DISABLED)
    def _miner_chk(self):
        if not self.antiminer: return
        self._mlog("🔍 Проверка CPU..."); sus=self.antiminer.scan_once()
        for s in sus[:10]: self._mlog(f"{'💀' if s['cpu']>=90 else '⚠️'} PID:{s['pid']} CPU:{s['cpu']:.1f}% {s['name']}")
        if not sus: self._mlog("✅ Чисто")
    def _miner_mon(self,dur):
        if not self.antiminer: return
        self._mlog(f"🛡️ Дозор {dur}с...")
        def w():
            old=self.antiminer.print_slow; self.antiminer.print_slow=lambda x,d=0:self.root.after(0,self._mlog,x)
            self.antiminer.monitor_loop(duration_sec=dur); self.antiminer.print_slow=old; self.root.after(0,self._mlog,"🛑 Дозор окончен")
        threading.Thread(target=w,daemon=True).start()
    def _t_ai(self):
        f=ttk.Frame(self.nb); self.nb.add(f,text=" 🧠 СЛЕДОПЫТ ")
        b=tk.Frame(f,bg=T.BG); b.pack(fill=tk.X,padx=10,pady=8)
        ttk.Button(b,text="📄 Файл",command=self._ai_file).pack(side=tk.LEFT,padx=5)
        ttk.Button(b,text="📂 Папка",command=self._ai_dir).pack(side=tk.LEFT,padx=5)
        self.atree=ttk.Treeview(f,columns=("f","sc","v","e","fa"),show="headings",height=14)
        for c,t,w in [("f","Файл",250),("sc","Риск",60),("v","Вердикт",120),("e","Энтропия",80),("fa","Улики",300)]:
            self.atree.heading(c,text=t); self.atree.column(c,width=w)
        self.atree.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)
    def _ai_file(self):
        if not self.detector: return
        p=filedialog.askopenfilename(filetypes=[("PE","*.exe *.dll *.sys")])
        if not p: return
        r=self.detector.analyze_file(p); fa="; ".join(r.get("risk_factors",[])[:2]) if r.get("is_pe") else "Не PE"
        self.atree.insert("",tk.END,values=(Path(p).name,r.get("risk_score",0),r.get("verdict",""),f"{r.get('entropy',0):.2f}",fa))
    def _ai_dir(self):
        if not self.detector: return
        p=filedialog.askdirectory()
        if not p: return
        def w():
            for r in self.detector.scan_directory(p):
                if r.get("is_pe"): self.root.after(0,self.atree.insert,"",tk.END,values=(Path(r["filepath"]).name,r["risk_score"],r["verdict"],f"{r.get('entropy',0):.2f}","; ".join(r.get("risk_factors",[])[:2])))
            self.root.after(0,self._log,"✅ AI-скан завершён")
        threading.Thread(target=w,daemon=True).start()
    def _t_set(self):
        f=ttk.Frame(self.nb); self.nb.add(f,text=" ⚙️ ЗАКОН ")
        if not self.config: ttk.Label(f,text="❌ Нет конфига").pack(); return
        g1=ttk.LabelFrame(f,text="🔍 Розыск",padding=10); g1.pack(fill=tk.X,padx=15,pady=5)
        self.v1=tk.BooleanVar(value=self.config.get("scanner.auto_scan_on_start",False))
        ttk.Checkbutton(g1,text="Авто-облава при старте",variable=self.v1,command=lambda:self.config.set("scanner.auto_scan_on_start",self.v1.get())).pack(anchor=tk.W)
        g2=ttk.LabelFrame(f,text="🔒 Тюрьма",padding=10); g2.pack(fill=tk.X,padx=15,pady=5)
        self.v2=tk.BooleanVar(value=self.config.get("quarantine.auto_isolate_threats",False))
        ttk.Checkbutton(g2,text="Авто-арест",variable=self.v2,command=lambda:self.config.set("quarantine.auto_isolate_threats",self.v2.get())).pack(anchor=tk.W)
        g3=ttk.LabelFrame(f,text="⛏️ Майнеры",padding=10); g3.pack(fill=tk.X,padx=15,pady=5)
        self.v3=tk.BooleanVar(value=self.config.get("antiminer.auto_suspend",False))
        ttk.Checkbutton(g3,text="Авто-suspend",variable=self.v3,command=lambda:self.config.set("antiminer.auto_suspend",self.v3.get())).pack(anchor=tk.W)
        ttk.Button(f,text="🔥 Сбросить законы",command=self._reset).pack(pady=15)
    def _reset(self):
        if messagebox.askyesno("🔥","Сбросить настройки?"): self.config.reset(); self._log("🔥 Сброшено"); messagebox.showinfo("🏆","Перезапусти приложение")
    def _t_upd(self):
        f=ttk.Frame(self.nb); self.nb.add(f,text=" 🔄 ОБНОВЛЕНИЯ ")
        b=tk.Frame(f,bg=T.BG); b.pack(fill=tk.X,padx=10,pady=8)
        ttk.Button(b,text="🔍 Проверить",command=self._upd_chk).pack(side=tk.LEFT,padx=5)
        ttk.Button(b,text="📦 Создать пакет",command=self._upd_pkg).pack(side=tk.LEFT,padx=5)
        self.uinfo=tk.Label(f,text=f"🤠 Версия: v{self.updater.current_version if self.updater else '0.7'}\n\nНажми «Проверить»",bg=T.BG,fg=T.PARCH,font=T.F,justify=tk.LEFT); self.uinfo.pack(padx=15,pady=10,anchor=tk.W)
        self.uprog=ttk.Progressbar(f); self.uprog.pack(fill=tk.X,padx=15,pady=5)
        self.ubtn=ttk.Button(f,text="⬇️ Установить обновление",command=self._upd_inst,state=tk.DISABLED); self.ubtn.pack(padx=15,pady=5,anchor=tk.W)
        self._pending=None
    def _upd_chk(self):
        if not self.updater: messagebox.showerror("Ошибка","Нет модуля updater"); return
        self.uinfo.config(text="🔍 Ищу обновления на GitHub..."); self._log("🔍 Проверка...")
        def w(): r=self.updater.check_for_updates(); self.root.after(0,self._upd_done,r)
        threading.Thread(target=w,daemon=True).start()
    def _upd_done(self,r):
        if r["has_update"]:
            txt=f"🆕 Новая версия: v{r['latest_version']}\n\n📜 Изменения:\n"+"\n".join(f"  • {x}" for x in r.get("changelog",[]))
            self.uinfo.config(text=txt); self.ubtn.configure(state=tk.NORMAL); self._pending=r; self._log(f"🆕 Доступно v{r['latest_version']}")
            messagebox.showinfo("🤠",f"Доступно обновление v{r['latest_version']}!")
        else:
            self.uinfo.config(text=f"✅ {r['message']}"); self.ubtn.configure(state=tk.DISABLED); self._log(r["message"])
    def _upd_inst(self):
        if not self._pending: return
        if not messagebox.askyesno("⚠️","Скачать и установить с GitHub?"): return
        self.ubtn.configure(state=tk.DISABLED); self.uprog["value"]=0; self._log("⬇️ Скачивание...")
        def w():
            try:
                def cb(d,t): self.root.after(0,self.uprog.configure,{"value":int(d/t*100)})
                zp=self.updater.download_update(self._pending["download_url"],self._pending.get("sha256",""),cb)
                self.root.after(0,self._log,"📦 Установка..."); r=self.updater.apply_update(zp); self.root.after(0,self._upd_inst_done,r)
            except Exception as e: self.root.after(0,self._upd_inst_done,{"success":False,"message":str(e)})
        threading.Thread(target=w,daemon=True).start()
    def _upd_inst_done(self,r):
        self.uprog["value"]=100 if r["success"] else 0
        if r["success"]: self.uinfo.config(text="✅ Обновлено! Перезапусти."); self._log("✅ Обновлено"); messagebox.showinfo("🏆",r["message"])
        else: self.uinfo.config(text=f"❌ {r['message']}"); self.ubtn.configure(state=tk.NORMAL); self._log(f"❌ {r['message']}")
    def _upd_pkg(self):
        if not self.updater: return
        p=filedialog.asksaveasfilename(defaultextension=".zip",initialfile=f"v{self.updater.current_version}.zip")
        if not p: return
        try: h=self.updater.create_update_package(p); self._log(f"✅ Пакет: {p}"); self._log(f"🔐 SHA256: {h}"); messagebox.showinfo("📦",f"Создан:\n{p}\n\nSHA256:\n{h}")
        except Exception as e: messagebox.showerror("Ошибка",str(e))
if __name__=="__main__":
    root=tk.Tk(); App(root); root.mainloop()
