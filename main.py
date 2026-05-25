"""
Truckstar - Entry point.
- Inicializa o banco.
- Tela de login com TABS (Funcionário / Cliente) + auto-cadastro de cliente.
- Rate limiting em memória contra brute-force.
- Hash de senha PBKDF2-SHA256 com salt.
"""
import time
import threading
import customtkinter as ctk
from tkinter import messagebox

import config
from db import conectar, inicializar
import seguranca
import validacoes as v
from email_sender import enviar_email, email_boas_vindas


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
        self.geometry("440x600")
        self.resizable(False, False)

        ctk.CTkLabel(self, text="TRUCKSTAR", font=("Arial", 30, "bold"),
                     text_color="#4a9eff").pack(pady=(20, 0))
        ctk.CTkLabel(self, text=config.EMPRESA_DESC,
                     font=("Arial", 12), text_color="gray").pack(pady=(0, 10))

        self.tabs = ctk.CTkTabview(self, width=400, height=440)
        self.tabs.pack(padx=20, pady=10)
        self.tabs.add("Funcionário")
        self.tabs.add("Cliente")

        self._tab_funcionario(self.tabs.tab("Funcionário"))
        self._tab_cliente(self.tabs.tab("Cliente"))

        self.lbl_info = ctk.CTkLabel(self, text="admin / admin123 (login inicial)",
                                     text_color="gray", font=("Arial", 9))
        self.lbl_info.pack()

    # ---- TAB FUNCIONÁRIO ----
    def _tab_funcionario(self, tab):
        ctk.CTkLabel(tab, text="Acesso de Funcionário",
                     font=("Arial", 14, "bold")).pack(pady=15)

        ctk.CTkLabel(tab, text="Usuário:").pack(pady=(10, 2))
        self.e_func_user = ctk.CTkEntry(tab, width=280)
        self.e_func_user.pack()

        ctk.CTkLabel(tab, text="Senha:").pack(pady=(10, 2))
        self.e_func_senha = ctk.CTkEntry(tab, width=280, show="*")
        self.e_func_senha.pack()
        self.e_func_senha.bind("<Return>", lambda e: self._login_funcionario())

        ctk.CTkButton(tab, text="Entrar", command=self._login_funcionario,
                      width=280, height=40, font=("Arial", 13, "bold")).pack(pady=20)

    # ---- TAB CLIENTE ----
    def _tab_cliente(self, tab):
        ctk.CTkLabel(tab, text="Acesso do Cliente",
                     font=("Arial", 14, "bold")).pack(pady=10)

        ctk.CTkLabel(tab, text="CPF/CNPJ:").pack(pady=(5, 2))
        self.e_cli_cpf = ctk.CTkEntry(tab, width=280)
        self.e_cli_cpf.pack()

        ctk.CTkLabel(tab, text="Senha:").pack(pady=(8, 2))
        self.e_cli_senha = ctk.CTkEntry(tab, width=280, show="*")
        self.e_cli_senha.pack()
        self.e_cli_senha.bind("<Return>", lambda e: self._login_cliente())

        ctk.CTkButton(tab, text="Entrar", command=self._login_cliente,
                      width=280, height=40, font=("Arial", 13, "bold")).pack(pady=15)

        ctk.CTkLabel(tab, text="Não tem conta?",
                     font=("Arial", 10), text_color="gray").pack()
        ctk.CTkButton(tab, text="Criar conta de Cliente",
                      command=self._abrir_cadastro,
                      width=280, height=35, fg_color="gray40").pack(pady=5)

    # ---- AÇÕES ----
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

    def _login_cliente(self):
        cpf_raw = self.e_cli_cpf.get().strip()
        senha = self.e_cli_senha.get()
        cpf = v._so_digitos(cpf_raw)
        if not cpf or not senha:
            messagebox.showwarning("Atenção", "Preencha CPF/CNPJ e senha", parent=self)
            return
        if not v.validar_cpf_ou_cnpj(cpf):
            messagebox.showwarning("Atenção", "CPF ou CNPJ inválido", parent=self)
            return

        chave = "cli:" + cpf
        bloq = _bloqueado(chave)
        if bloq:
            messagebox.showerror("Bloqueado",
                "Muitas tentativas. Aguarde {}s.".format(bloq), parent=self)
            return

        try:
            conn = conectar()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, nome, cpf_cnpj, email, senha_hash, senha_salt, ativo
                FROM clientes WHERE cpf_cnpj=%s
            """, (cpf,))
            r = cur.fetchone()
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erro", "Erro no banco: " + str(e), parent=self)
            return

        if not r or not seguranca.verificar_senha(senha, r[5], r[4]):
            _registrar_tentativa(chave)
            messagebox.showerror("Erro", "CPF/CNPJ ou senha inválidos", parent=self)
            return

        if not r[6]:
            messagebox.showerror("Atenção", "Cadastro inativo", parent=self)
            return

        _limpar_tentativas(chave)
        cliente = {'id': r[0], 'nome': r[1], 'cpf': r[2], 'email': r[3]}
        self.withdraw()
        from tela_cliente import PainelCliente
        PainelCliente(self, cliente)

    def _abrir_cadastro(self):
        TelaCadastroCliente(self)

    # método usado pelo PainelCliente ao sair
    def limpar_campos(self):
        for e in [self.e_func_user, self.e_func_senha, self.e_cli_cpf, self.e_cli_senha]:
            try:
                e.delete(0, "end")
            except Exception:
                pass


# ============================================
class TelaCadastroCliente(ctk.CTkToplevel):
    """Auto-cadastro de cliente."""
    def __init__(self, master):
        super().__init__(master)
        self.title("Criar conta - Cliente")
        self.geometry("520x680")
        self.grab_set()

        ctk.CTkLabel(self, text="Cadastro de Cliente",
                     font=("Arial", 18, "bold")).pack(pady=15)

        frm = ctk.CTkFrame(self)
        frm.pack(fill="both", expand=True, padx=20, pady=10)

        def _campo(label, **kw):
            ctk.CTkLabel(frm, text=label).pack(anchor="w", padx=10, pady=(8, 2))
            e = ctk.CTkEntry(frm, width=460, **kw)
            e.pack(padx=10)
            return e

        self.e_nome = _campo("Nome completo:")
        self.e_cpf = _campo("CPF/CNPJ:")
        self.e_tel = _campo("Telefone:")
        self.e_email = _campo("Email:")

        frm_cep = ctk.CTkFrame(frm, fg_color="transparent")
        ctk.CTkLabel(frm, text="CEP:").pack(anchor="w", padx=10, pady=(8, 2))
        frm_cep.pack(fill="x", padx=10)
        self.e_cep = ctk.CTkEntry(frm_cep, width=150)
        self.e_cep.pack(side="left")
        self.btn_cep = ctk.CTkButton(frm_cep, text="Buscar CEP",
                                     width=120, command=self._buscar_cep)
        self.btn_cep.pack(side="left", padx=8)

        self.e_log = _campo("Logradouro:")
        self.e_num = _campo("Número:")
        self.e_bairro = _campo("Bairro:")
        self.e_cidade = _campo("Cidade:")
        self.e_estado = _campo("UF:")

        self.e_senha = _campo("Senha (mín. {} caracteres):".format(config.SENHA_MIN_CARACTERES),
                              show="*")
        self.e_senha2 = _campo("Confirmar senha:", show="*")

        ctk.CTkButton(self, text="Criar Conta", command=self._criar,
                      width=300, height=42, font=("Arial", 13, "bold"),
                      fg_color="green").pack(pady=15)

    def _buscar_cep(self):
        cep = self.e_cep.get().strip()
        if not cep:
            messagebox.showwarning("Atenção", "Digite o CEP", parent=self)
            return
        self.btn_cep.configure(state="disabled", text="Buscando...")

        def tarefa():
            res = v.buscar_cep(cep)
            self.after(0, lambda: self._aplicar_cep(res))

        threading.Thread(target=tarefa, daemon=True).start()

    def _aplicar_cep(self, res):
        self.btn_cep.configure(state="normal", text="Buscar CEP")
        if not res['ok']:
            messagebox.showerror("CEP", res['erro'], parent=self)
            return
        self.e_log.delete(0, "end"); self.e_log.insert(0, res['logradouro'])
        self.e_bairro.delete(0, "end"); self.e_bairro.insert(0, res['bairro'])
        self.e_cidade.delete(0, "end"); self.e_cidade.insert(0, res['cidade'])
        self.e_estado.delete(0, "end"); self.e_estado.insert(0, res['estado'])

    def _criar(self):
        nome = self.e_nome.get().strip()
        cpf = v._so_digitos(self.e_cpf.get())
        email = self.e_email.get().strip()
        tel = self.e_tel.get().strip()
        cep = v._so_digitos(self.e_cep.get())
        senha = self.e_senha.get()
        senha2 = self.e_senha2.get()
        estado = self.e_estado.get().strip().upper()

        if not nome or len(nome) < 3:
            return messagebox.showwarning("Atenção", "Nome obrigatório (mín. 3 caracteres)", parent=self)
        if not v.validar_cpf_ou_cnpj(cpf):
            return messagebox.showwarning("Atenção", "CPF ou CNPJ inválido", parent=self)
        if email and not v.validar_email(email):
            return messagebox.showwarning("Atenção", "Email inválido", parent=self)
        if tel and not v.validar_telefone(tel):
            return messagebox.showwarning("Atenção", "Telefone inválido", parent=self)
        if cep and len(cep) != 8:
            return messagebox.showwarning("Atenção", "CEP inválido", parent=self)
        if estado and len(estado) != 2:
            return messagebox.showwarning("Atenção", "UF deve ter 2 letras", parent=self)
        if not senha or len(senha) < config.SENHA_MIN_CARACTERES:
            return messagebox.showwarning("Atenção",
                "Senha deve ter ao menos {} caracteres".format(config.SENHA_MIN_CARACTERES),
                parent=self)
        if senha != senha2:
            return messagebox.showwarning("Atenção", "Senhas não conferem", parent=self)

        salt = seguranca.gerar_salt()
        h = seguranca.hash_senha(senha, salt)

        try:
            conn = conectar()
            cur = conn.cursor()
            # verifica duplicidade
            cur.execute("SELECT id FROM clientes WHERE cpf_cnpj=%s", (cpf,))
            if cur.fetchone():
                cur.close(); conn.close()
                return messagebox.showerror("Erro",
                    "Já existe um cadastro com este CPF/CNPJ", parent=self)
            cur.execute("""
                INSERT INTO clientes (nome, cpf_cnpj, telefone, email, cep, logradouro,
                    numero, bairro, cidade, estado, senha_hash, senha_salt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nome, cpf, tel, email, cep or None,
                  self.e_log.get().strip() or None,
                  self.e_num.get().strip() or None,
                  self.e_bairro.get().strip() or None,
                  self.e_cidade.get().strip() or None,
                  estado or None, h, salt))
            conn.commit()
            cur.close()
            conn.close()

            if email:
                assunto, corpo = email_boas_vindas(nome)
                enviar_email(email, assunto, corpo)

            messagebox.showinfo("OK",
                "Conta criada com sucesso!\nAgora você pode fazer login com seu CPF/CNPJ.",
                parent=self)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)


# ============================================
class TelaPrincipal(ctk.CTkToplevel):
    """Painel pós-login do funcionário."""
    def __init__(self, login_window, usuario):
        super().__init__(login_window)
        self.login_window = login_window
        self.usuario = usuario
        self.title("Truckstar - Painel ({})".format(usuario['cargo']))
        self.geometry("640x540")
        self.protocol("WM_DELETE_WINDOW", self.sair)

        topo = ctk.CTkFrame(self, height=80)
        topo.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(topo, text="TRUCKSTAR", font=("Arial", 22, "bold"),
                     text_color="#4a9eff").pack(side="left", padx=15)
        ctk.CTkLabel(topo, text="Logado: {} ({})".format(usuario['nome'], usuario['cargo']),
                     font=("Arial", 12)).pack(side="right", padx=15)

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
    if not config.EMAIL_USUARIO:
        print("[AVISO] Email Gmail não configurado em config.py - emails NÃO serão enviados.")
    app = TelaLogin()
    app.mainloop()


if __name__ == '__main__':
    main()
