"""
Truckstar - Entry point.
- Inicializa o banco.
- Tela de login (somente funcionário).
- Rate limiting em memória contra brute-force.
- Hash de senha PBKDF2-SHA256 com salt.
"""
import time
import customtkinter as ctk
from tkinter import messagebox

import config
from db import conectar, inicializar
import seguranca
from ui_utils import habilitar_resize_e_fullscreen, botao_tela_cheia


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ---- rate limit em memória ----
_tentativas = {}  # chave -> [(timestamp), ...]


def _registrar_tentativa(chave: str):
    agora = time.time()
    lista = _tentativas.get(chave, [])
    # remove tentativas mais velhas que o bloqueio
    lista = [t for t in lista if agora - t < config.LOGIN_BLOQUEIO_SEGUNDOS]
    lista.append(agora)
    _tentativas[chave] = lista


def _bloqueado(chave: str) -> int:
    """Retorna segundos restantes de bloqueio, ou 0 se livre."""
    agora = time.time()
    lista = _tentativas.get(chave, [])
    lista = [t for t in lista if agora - t < config.LOGIN_BLOQUEIO_SEGUNDOS]
    _tentativas[chave] = lista
    if len(lista) >= config.LOGIN_MAX_TENTATIVAS:
        mais_antiga = min(lista)
        restante = int(config.LOGIN_BLOQUEIO_SEGUNDOS - (agora - mais_antiga))
        return max(1, restante)
    return 0


def _limpar_tentativas(chave: str):
    _tentativas.pop(chave, None)


# ============================================
class TelaLogin(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(config.EMPRESA_NOME + " - Login")
        self.geometry("440x480")
        habilitar_resize_e_fullscreen(self, min_w=380, min_h=440)

        ctk.CTkLabel(self, text="TRUCKSTAR", font=("Arial", 30, "bold"),
                     text_color="#4a9eff").pack(pady=(20, 0))
        ctk.CTkLabel(self, text=config.EMPRESA_DESC,
                     font=("Arial", 12), text_color="gray").pack(pady=(0, 20))

        frm = ctk.CTkFrame(self)
        frm.pack(padx=30, pady=10, fill="both", expand=True)

        ctk.CTkLabel(frm, text="Acesso de Funcionário",
                     font=("Arial", 14, "bold")).pack(pady=(15, 10))

        ctk.CTkLabel(frm, text="Usuário:").pack(pady=(10, 2))
        self.e_func_user = ctk.CTkEntry(frm, width=300)
        self.e_func_user.pack()

        ctk.CTkLabel(frm, text="Senha:").pack(pady=(10, 2))
        self.e_func_senha = ctk.CTkEntry(frm, width=300, show="*")
        self.e_func_senha.pack()
        self.e_func_senha.bind("<Return>", lambda e: self._login_funcionario())

        ctk.CTkButton(frm, text="Entrar", command=self._login_funcionario,
                      width=300, height=42, font=("Arial", 13, "bold")).pack(pady=25)

    # ---- AÇÃO ----
    def _login_funcionario(self):
        usuario = self.e_func_user.get().strip()
        senha = self.e_func_senha.get()
        if not usuario or not senha:
            messagebox.showwarning("Atenção", "Preencha usuário e senha", parent=self)
            return

        chave = "func:" + usuario.lower()
        bloq = _bloqueado(chave)
        if bloq:
            messagebox.showerror("Bloqueado",
                "Muitas tentativas. Aguarde {}s.".format(bloq), parent=self)
            return

        try:
            conn = conectar()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, nome, cargo, senha_hash, senha_salt, ativo
                FROM funcionarios WHERE usuario=%s
            """, (usuario,))
            r = cur.fetchone()
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erro", "Erro no banco: " + str(e), parent=self)
            return

        if not r or not seguranca.verificar_senha(senha, r[4], r[3]):
            _registrar_tentativa(chave)
            messagebox.showerror("Erro", "Usuário ou senha inválidos", parent=self)
            return

        if not r[5]:
            messagebox.showerror("Atenção", "Usuário inativo", parent=self)
            return

        _limpar_tentativas(chave)
        usuario_logado = {'id': r[0], 'nome': r[1], 'cargo': r[2]}
        self.withdraw()
        TelaPrincipal(self, usuario_logado)

    def limpar_campos(self):
        for e in [self.e_func_user, self.e_func_senha]:
            try:
                e.delete(0, "end")
            except Exception:
                pass


# ============================================
class TelaPrincipal(ctk.CTkToplevel):
    """Painel pós-login do funcionário."""
    def __init__(self, login_window, usuario):
        super().__init__(login_window)
        self.login_window = login_window
        self.usuario = usuario
        self.title("Truckstar - Painel ({})".format(usuario['cargo']))
        self.geometry("680x560")
        self.protocol("WM_DELETE_WINDOW", self.sair)
        habilitar_resize_e_fullscreen(self, min_w=560, min_h=500)

        topo = ctk.CTkFrame(self, height=80)
        topo.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(topo, text="TRUCKSTAR", font=("Arial", 22, "bold"),
                     text_color="#4a9eff").pack(side="left", padx=15)
        botao_tela_cheia(topo, self).pack(side="right", padx=5)
        ctk.CTkLabel(topo, text="Logado: {} ({})".format(usuario['nome'], usuario['cargo']),
                     font=("Arial", 12)).pack(side="right", padx=10)

        frm = ctk.CTkFrame(self)
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frm, text="Menu Principal",
                     font=("Arial", 16, "bold")).pack(pady=15)

        cargo = usuario['cargo']

        # Clientes/caminhões: Admin e Atendente cadastram. Mecânico apenas consulta via OS.
        if cargo in ('Admin', 'Atendente'):
            ctk.CTkButton(frm, text="Clientes / Caminhões",
                          command=self._abrir_clientes,
                          width=320, height=45, font=("Arial", 13)).pack(pady=8)

        # OS: todos
        ctk.CTkButton(frm, text="Ordens de Serviço",
                      command=self._abrir_os,
                      width=320, height=45, font=("Arial", 13)).pack(pady=8)

        # Funcionários: só Admin
        if cargo == 'Admin':
            ctk.CTkButton(frm, text="Funcionários",
                          command=self._abrir_funcionarios,
                          width=320, height=45, font=("Arial", 13)).pack(pady=8)

        ctk.CTkButton(frm, text="Sair", command=self.sair,
                      width=320, height=45, fg_color="darkred",
                      font=("Arial", 13)).pack(pady=20)

    def _abrir_clientes(self):
        from tela_clientes import TelaClientes
        TelaClientes(self, self.usuario)

    def _abrir_funcionarios(self):
        from tela_funcionarios import TelaFuncionarios
        TelaFuncionarios(self, self.usuario)

    def _abrir_os(self):
        from tela_ordens import TelaOrdens
        TelaOrdens(self, self.usuario)

    def sair(self):
        self.destroy()
        self.login_window.limpar_campos()
        self.login_window.deiconify()


def main():
    print("Inicializando banco de dados...")
    inicializar()
    if not getattr(config, 'RESEND_API_KEY', ''):
        print("[AVISO] RESEND_API_KEY não configurada em config.py - emails NÃO serão enviados.")
    app = TelaLogin()
    app.mainloop()


if __name__ == '__main__':
    main()
