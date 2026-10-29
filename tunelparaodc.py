import os
import sys
import subprocess
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime
import urllib.request

APP_TITLE = "Discord VPN Helper Pro"
OFFICIAL_DOWNLOAD = "https://golivebypass.dev/downloads"
OFFICIAL_GUIDE = "https://golivebypass.dev/instalacao"
POLL_MS = 4000

def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def run_hidden(args, timeout=6):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                          creationflags=flags, errors="replace")

def process_running(exe_name):
    try:
        result = run_hidden(["tasklist", "/FI", f"IMAGENAME eq {exe_name}"], timeout=5)
        return exe_name.lower() in result.stdout.lower()
    except Exception:
        return False

def get_adapter_status():
    # Read-only status check. Does not change routes or network configuration.
    ps = (
        "Get-NetAdapter -ErrorAction SilentlyContinue | "
        "Select-Object -Property Name,Status,InterfaceDescription | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    try:
        result = run_hidden(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], timeout=8)
        lines = result.stdout.lower()
        candidates = []
        for line in lines.splitlines()[1:]:
            if any(word in line for word in ("wireguard", "wintun", "proton", "vpn", "tunnel")):
                candidates.append(line)
        if any(",up," in line or line.startswith('"') and ',"up",' in line for line in candidates):
            return "Adaptador VPN parece ativo (indicador aproximado)."
        if candidates:
            return "Adaptador VPN encontrado, mas não aparece ativo."
        return "Nenhum adaptador VPN reconhecido pelo nome foi encontrado."
    except Exception:
        return "Não foi possível consultar adaptadores (PowerShell)."

def internet_test():
    try:
        req = urllib.request.Request("https://discord.com", headers={"User-Agent": "DiscordVPNHelper/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status in (200, 301, 302, 403)
    except Exception:
        return False

def locate_tunnel_app():
    candidates = [
        app_dir() / "GoLiveBypass.exe",
        app_dir() / "GoLiveBypass-2.0.4.exe",
        app_dir() / "GoLiveBypass-2.0.4" / "GoLiveBypass.exe",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("620x560")
        self.root.minsize(560, 510)
        self.root.configure(bg="#171923")
        self.child = None
        self.monitor_on = True
        self.last_refresh = None

        tk.Label(root, text="Discord VPN Helper Pro", font=("Segoe UI", 21, "bold"),
                 bg="#171923", fg="#f7f7fb").pack(pady=(20, 3))
        tk.Label(root, text="Painel de controle • Windows 11",
                 font=("Segoe UI", 10), bg="#171923", fg="#c5c8d3").pack(pady=(0, 14))

        self.status_box = tk.Frame(root, bg="#242838", padx=16, pady=12)
        self.status_box.pack(fill="x", padx=22, pady=5)
        self.discord_label = self.add_status_line("Discord:", "Verificando...")
        self.tool_label = self.add_status_line("GoLiveBypass:", "Verificando...")
        self.vpn_label = self.add_status_line("Adaptador VPN:", "Verificando...")
        self.internet_label = self.add_status_line("Acesso ao Discord:", "Aguardando teste...")
        self.updated_label = tk.Label(self.status_box, text="", font=("Segoe UI", 8),
                                      bg="#242838", fg="#9aa3b5")
        self.updated_label.pack(anchor="w", pady=(6, 0))

        tk.Label(root, text="CONTROLES", font=("Segoe UI", 9, "bold"),
                 bg="#171923", fg="#8d96aa").pack(anchor="w", padx=25, pady=(16, 5))
        self.button(root, "Abrir / trazer GoLiveBypass", self.open_tunnel, "#5865F2").pack(fill="x", padx=60, pady=4)
        self.button(root, "Verificar agora", self.refresh, "#3b4252").pack(fill="x", padx=60, pady=4)
        self.button(root, "Testar acesso ao Discord", self.test_discord, "#3b4252").pack(fill="x", padx=60, pady=4)
        self.button(root, "Abrir download oficial", lambda: webbrowser.open(OFFICIAL_DOWNLOAD), "#3b4252").pack(fill="x", padx=60, pady=4)
        self.button(root, "Abrir guia oficial", lambda: webbrowser.open(OFFICIAL_GUIDE), "#3b4252").pack(fill="x", padx=60, pady=4)

        tk.Label(root,
                 text=("Nota: este painel não liga/desliga o túnel por conta própria. "
                       "Use os controles dentro do GoLiveBypass para conectar/desconectar.\n"
                       "O estado do adaptador é apenas uma indicação; não confirma que só o Discord usa a VPN."),
                 font=("Segoe UI", 8), bg="#171923", fg="#aab0c0",
                 wraplength=560, justify="center").pack(pady=(12, 8), padx=20)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()
        self.schedule_refresh()

    def add_status_line(self, title, initial):
        frame = tk.Frame(self.status_box, bg="#242838")
        frame.pack(fill="x", pady=2)
        tk.Label(frame, text=title, font=("Segoe UI", 9, "bold"), bg="#242838",
                 fg="#d8dce7", width=19, anchor="w").pack(side="left")
        value = tk.Label(frame, text=initial, font=("Segoe UI", 9), bg="#242838",
                         fg="#c5c8d3", anchor="w", wraplength=340)
        value.pack(side="left", fill="x", expand=True)
        return value

    def button(self, parent, label, command, color):
        return tk.Button(parent, text=label, command=command, font=("Segoe UI", 10, "bold"),
                         bg=color, fg="white", activebackground=color, activeforeground="white",
                         relief="flat", cursor="hand2", padx=12, pady=9)

    def set_value(self, label, value, color="#c5c8d3"):
        label.config(text=value, fg=color)

    def refresh(self):
        discord = process_running("Discord.exe")
        tool = process_running("GoLiveBypass.exe") or process_running("GoLiveBypass-2.0.4.exe")
        self.set_value(self.discord_label, "Em execução" if discord else "Não detectado",
                       "#72d49a" if discord else "#f0bd72")
        self.set_value(self.tool_label, "Aberto" if tool else "Não detectado",
                       "#72d49a" if tool else "#f0bd72")
        self.set_value(self.vpn_label, get_adapter_status())
        self.updated_label.config(text="Última verificação: " + datetime.now().strftime("%H:%M:%S"))

    def test_discord(self):
        self.set_value(self.internet_label, "Testando...")
        def worker():
            ok = internet_test()
            self.root.after(0, lambda: self.set_value(
                self.internet_label,
                "Site do Discord acessível" if ok else "Falha no teste HTTP; pode ser rede, DNS ou bloqueio",
                "#72d49a" if ok else "#f07070"))
        threading.Thread(target=worker, daemon=True).start()

    def open_tunnel(self):
        path = locate_tunnel_app()
        if path:
            try:
                subprocess.Popen([str(path)], cwd=str(path.parent))
                messagebox.showinfo("GoLiveBypass", "Solicitei a abertura da ferramenta. Conecte o túnel dentro dela.")
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Erro ao abrir", str(exc))
        else:
            messagebox.showinfo(
                "Ferramenta não encontrada",
                "Não encontrei o executável do GoLiveBypass na pasta deste painel.\n\n"
                "Abra o GoLiveBypass pelo local onde ele foi instalado ou coloque o executável "
                "na mesma pasta deste painel. O painel não baixa nem instala programas automaticamente."
            )
            webbrowser.open(OFFICIAL_DOWNLOAD)

    def schedule_refresh(self):
        if self.monitor_on:
            self.refresh()
            self.root.after(POLL_MS, self.schedule_refresh)

    def close(self):
        self.monitor_on = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
