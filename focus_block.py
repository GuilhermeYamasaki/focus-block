#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse
import tkinter as tk
from tkinter import messagebox, simpledialog

APP_NAME = "Focus Block"
APP_ID = "focusblock"
CONFIG_DIR = Path.home() / ".config" / APP_ID
CONFIG_FILE = CONFIG_DIR / "config.json"
HOSTS_FILE = "/etc/hosts"
BACKUP_FILE = "/etc/hosts.focusblock.bak"
BEGIN_MARKER = "# BEGIN FOCUS_BLOCK"
END_MARKER = "# END FOCUS_BLOCK"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        data = {
            "password_hash": None,
            "password_salt": None,
            "domains": [],
            "unlock_window_until": 0,
        }
        save_config(data)
        return data
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("password_hash", None)
    data.setdefault("password_salt", None)
    data.setdefault("domains", [])
    data.setdefault("unlock_window_until", 0)
    return data


def save_config(data: dict) -> None:
    ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def hash_password(password: str, salt: str) -> str:
    raw = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        base64.b64decode(salt.encode("ascii")),
        200_000,
    )
    return base64.b64encode(raw).decode("ascii")


def set_password_in_config(config: dict, password: str) -> None:
    salt = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
    config["password_salt"] = salt
    config["password_hash"] = hash_password(password, salt)
    save_config(config)


def verify_password(config: dict, password: str) -> bool:
    if not config.get("password_hash") or not config.get("password_salt"):
        return False
    return hash_password(password, config["password_salt"]) == config["password_hash"]


def normalize_domain(value: str):
    value = value.strip().lower()
    if not value:
        return None

    if "://" not in value:
        value = "http://" + value

    parsed = urlparse(value)
    host = (parsed.netloc or parsed.path).strip().lower()

    if "@" in host:
        host = host.split("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]
    host = host.strip(".")

    if not host or "." not in host:
        return None
    if not re.fullmatch(r"[a-z0-9.-]+", host):
        return None
    return host


def read_hosts() -> str:
    with open(HOSTS_FILE, "r", encoding="utf-8") as f:
        return f.read()


def write_hosts(content: str) -> None:
    if os.path.exists(HOSTS_FILE):
        shutil.copy2(HOSTS_FILE, BACKUP_FILE)
    with open(HOSTS_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def extract_block_domains(content: str):
    pattern = re.compile(
        rf"{re.escape(BEGIN_MARKER)}\n(.*?)\n{re.escape(END_MARKER)}",
        re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        return []

    domains = []
    for line in match.group(1).splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] in ("127.0.0.1", "0.0.0.0"):
            domains.append(parts[1])
    return sorted(set(domains))


def build_block(domains):
    domains = sorted(set(domains))
    if not domains:
        return ""
    lines = [BEGIN_MARKER]
    lines.extend(f"127.0.0.1 {domain}" for domain in domains)
    lines.append(END_MARKER)
    return "\n".join(lines)


def replace_block(content: str, domains):
    pattern = re.compile(
        rf"\n?{re.escape(BEGIN_MARKER)}\n.*?\n{re.escape(END_MARKER)}\n?",
        re.DOTALL,
    )
    cleaned = pattern.sub("\n", content).rstrip() + "\n"
    block = build_block(domains)
    if block:
        cleaned = cleaned.rstrip() + "\n\n" + block + "\n"
    return cleaned


def helper_write_from_payload(payload_path: str) -> int:
    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    domains = payload.get("domains", [])
    content = read_hosts()
    new_content = replace_block(content, domains)
    write_hosts(new_content)
    return 0


def run_pkexec_write(domains):
    payload = {"domains": sorted(set(domains))}
    fd, payload_path = tempfile.mkstemp(prefix="focusblock_", suffix=".json")
    os.close(fd)
    try:
        with open(payload_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        cmd = [
            "pkexec",
            sys.executable,
            os.path.abspath(__file__),
            "--helper-write",
            payload_path,
        ]
        result = subprocess.run(cmd, text=True)
        return result.returncode == 0
    finally:
        try:
            os.remove(payload_path)
        except OSError:
            pass


class PasswordMixin:
    def ensure_password_exists(self):
        if self.config.get("password_hash"):
            return True

        p1 = simpledialog.askstring(
            "Criar senha",
            "Defina uma senha para desbloquear/remover bloqueios:",
            show="*",
            parent=self.root,
        )
        if not p1:
            return False

        p2 = simpledialog.askstring(
            "Confirmar senha",
            "Digite a senha novamente:",
            show="*",
            parent=self.root,
        )
        if p1 != p2:
            messagebox.showerror("Erro", "As senhas não conferem.", parent=self.root)
            return False

        set_password_in_config(self.config, p1)
        self.config = load_config()
        messagebox.showinfo("Sucesso", "Senha definida.", parent=self.root)
        return True

    def verify_password_prompt(self):
        if not self.ensure_password_exists():
            return False

        password = simpledialog.askstring(
            "Senha",
            "Digite a senha para desbloquear:",
            show="*",
            parent=self.root,
        )
        if not password:
            return False
        if not verify_password(self.config, password):
            messagebox.showerror("Erro", "Senha incorreta.", parent=self.root)
            return False
        return True


class App(PasswordMixin):
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("650x520")
        self.root.minsize(620, 500)
        self.config = load_config()
        self.domains = list(self.config.get("domains", []))

        self._build_ui()
        self.refresh_list()
        self.sync_state_from_system()

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=12, pady=(12, 8))

        tk.Label(
            top,
            text="Bloqueador de domínios via /etc/hosts",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w")

        self.status_label = tk.Label(
            top,
            text="",
            fg="#444",
            justify="left",
        )
        self.status_label.pack(anchor="w", pady=(6, 0))

        entry_frame = tk.Frame(self.root)
        entry_frame.pack(fill="x", padx=12, pady=10)

        self.entry = tk.Entry(entry_frame, font=("Arial", 11))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _e: self.add_domain())

        tk.Button(entry_frame, text="Adicionar", command=self.add_domain).pack(side="left", padx=(8, 0))

        presets = tk.Frame(self.root)
        presets.pack(fill="x", padx=12, pady=(0, 10))

        preset_data = [
            ("YouTube", ["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"]),
            ("Instagram", ["instagram.com", "www.instagram.com"]),
            ("Reddit", ["reddit.com", "www.reddit.com"]),
            ("X / Twitter", ["x.com", "www.x.com", "twitter.com", "www.twitter.com"]),
        ]
        for label, items in preset_data:
            tk.Button(presets, text=label, command=lambda ds=items: self.add_many(ds)).pack(side="left", padx=(0, 8))

        list_frame = tk.Frame(self.root)
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.listbox = tk.Listbox(list_frame, font=("Arial", 11), selectmode=tk.EXTENDED)
        self.listbox.pack(side="left", fill="both", expand=True)

        scroll = tk.Scrollbar(list_frame, command=self.listbox.yview)
        scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scroll.set)

        actions = tk.Frame(self.root)
        actions.pack(fill="x", padx=12, pady=(0, 10))

        tk.Button(actions, text="Remover selecionado", command=self.remove_selected).pack(side="left")
        tk.Button(actions, text="Sincronizar com sistema", command=self.sync_state_from_system).pack(side="left", padx=(8, 0))
        tk.Button(actions, text="Trocar senha", command=self.change_password).pack(side="left", padx=(8, 0))

        bottom = tk.Frame(self.root)
        bottom.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(bottom, text="Aplicar bloqueio", command=self.apply_domains, height=2).pack(side="right")
        tk.Button(bottom, text="Desbloquear tudo", command=self.clear_block, height=2).pack(side="right", padx=(0, 8))

        help_text = (
            "Aceita domínio ou URL completa.\n"
            "Para remover itens ou desbloquear tudo, a senha é exigida.\n"
            "Ao aplicar, o sistema pedirá a senha de administrador pelo pkexec."
        )
        tk.Label(self.root, text=help_text, justify="left", fg="#444").pack(anchor="w", padx=12, pady=(0, 12))

        self.update_status()

    def update_status(self):
        active = self.get_system_domains()
        local = sorted(set(self.domains))
        status = []
        status.append(f"Lista do app: {len(local)} domínio(s)")
        status.append(f"Bloqueados no sistema: {len(active)} domínio(s)")
        status.append(f"Configuração: {CONFIG_FILE}")
        self.status_label.config(text="\n".join(status))

    def refresh_list(self):
        self.domains = sorted(set(self.domains))
        self.listbox.delete(0, tk.END)
        for d in self.domains:
            self.listbox.insert(tk.END, d)
        self.config["domains"] = self.domains
        save_config(self.config)
        self.update_status()

    def add_many(self, values):
        changed = False
        for value in values:
            domain = normalize_domain(value)
            if domain and domain not in self.domains:
                self.domains.append(domain)
                changed = True
        if changed:
            self.refresh_list()

    def add_domain(self):
        domain = normalize_domain(self.entry.get())
        if not domain:
            messagebox.showerror("Erro", "Digite um domínio ou URL válida.", parent=self.root)
            return
        if domain in self.domains:
            messagebox.showinfo("Info", "Esse domínio já está na lista.", parent=self.root)
            return
        self.domains.append(domain)
        self.entry.delete(0, tk.END)
        self.refresh_list()

    def remove_selected(self):
        selected = list(self.listbox.curselection())
        if not selected:
            return
        if not self.verify_password_prompt():
            return
        for index in reversed(selected):
            del self.domains[index]
        self.refresh_list()

    def change_password(self):
        if self.config.get("password_hash") and not self.verify_password_prompt():
            return

        p1 = simpledialog.askstring("Nova senha", "Digite a nova senha:", show="*", parent=self.root)
        if not p1:
            return
        p2 = simpledialog.askstring("Confirmar", "Digite a nova senha novamente:", show="*", parent=self.root)
        if p1 != p2:
            messagebox.showerror("Erro", "As senhas não conferem.", parent=self.root)
            return
        set_password_in_config(self.config, p1)
        self.config = load_config()
        messagebox.showinfo("Sucesso", "Senha atualizada.", parent=self.root)

    def get_system_domains(self):
        try:
            return extract_block_domains(read_hosts())
        except Exception:
            return []

    def sync_state_from_system(self):
        system_domains = self.get_system_domains()
        if system_domains:
            self.domains = system_domains
            self.config["domains"] = system_domains
            save_config(self.config)
            self.refresh_list()
        else:
            self.update_status()

    def apply_domains(self):
        self.config["domains"] = sorted(set(self.domains))
        save_config(self.config)
        ok = run_pkexec_write(self.domains)
        if ok:
            messagebox.showinfo("Sucesso", "Bloqueio aplicado no sistema.", parent=self.root)
            self.update_status()
        else:
            messagebox.showerror(
                "Erro",
                "Não foi possível aplicar no sistema.\nVerifique se o pkexec está disponível e se você autorizou a elevação.",
                parent=self.root,
            )

    def clear_block(self):
        if not self.verify_password_prompt():
            return
        ok = run_pkexec_write([])
        if ok:
            messagebox.showinfo("Sucesso", "Bloqueio removido do sistema.", parent=self.root)
            self.update_status()
        else:
            messagebox.showerror(
                "Erro",
                "Não foi possível remover o bloqueio do sistema.",
                parent=self.root,
            )


def main():
    root = tk.Tk()
    try:
        root.iconphoto(True, tk.PhotoImage(file=str(Path(__file__).with_name("focusblock_icon.png"))))
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--helper-write":
        sys.exit(helper_write_from_payload(sys.argv[2]))
    main()
