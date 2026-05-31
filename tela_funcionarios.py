"""
CRUD de funcionários (apenas Admin).
Senha sempre armazenada com hash + salt.
Valida CPF, email, telefone.
"""
import customtkinter as ctk
from tkinter import messagebox, ttk

from db import cursor
import validacoes as v
import seguranca
import config
from ui_utils import habilitar_resize_e_fullscreen, botao_tela_cheia
from ui_helpers import mostrar_erro


class TelaFuncionarios(ctk.CTkToplevel):
    def __init__(self, master, usuario_logado):
        super().__init__(master)
        self.master_painel = master
        self.usuario = usuario_logado
        self.title("Funcionários - Truckstar")
        self.geometry("980x700")
        self.grab_set()
        habilitar_resize_e_fullscreen(self, min_w=820, min_h=600)
        self.id_atual = None

        self._topbar()
        self._formulario()
        self._botoes()
        self._busca()
        self._tabela()
        self.listar()

    def _topbar(self):
        bar = ctk.CTkFrame(self, height=42, fg_color="#1a4d8f")
        bar.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(bar, text="Logado: {} ({})".format(self.usuario['nome'], self.usuario['cargo']),
                     font=("Arial", 11, "bold"), text_color="white").pack(side="left", padx=10, pady=6)
        ctk.CTkButton(bar, text="Sair (Logout)", width=120, height=28,
                      fg_color="darkred", hover_color="#8b0000",
                      command=self._sair_logout).pack(side="right", padx=10, pady=6)
        botao_tela_cheia(bar, self).pack(side="right", padx=5, pady=6)

    def _sair_logout(self):
        self.destroy()
        try:
            self.master_painel.sair()
        except Exception:
            pass

    def _formulario(self):
        frm = ctk.CTkFrame(self)
        frm.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frm, text="Cadastro de Funcionário",
                     font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=4, pady=5)

        ctk.CTkLabel(frm, text="Nome:").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        self.e_nome = ctk.CTkEntry(frm, width=300)
        self.e_nome.grid(row=1, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="CPF:").grid(row=1, column=2, sticky="e", padx=5, pady=4)
        self.e_cpf = ctk.CTkEntry(frm, width=200)
        self.e_cpf.grid(row=1, column=3, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Cargo:").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        self.cb_cargo = ctk.CTkComboBox(frm, values=["Admin", "Atendente", "Mecânico"],
                                        width=300, state="readonly")
        self.cb_cargo.grid(row=2, column=1, padx=5, pady=4)
        self.cb_cargo.set("Mecânico")

        ctk.CTkLabel(frm, text="Telefone:").grid(row=2, column=2, sticky="e", padx=5, pady=4)
        self.e_tel = ctk.CTkEntry(frm, width=200)
        self.e_tel.grid(row=2, column=3, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Email:").grid(row=3, column=0, sticky="e", padx=5, pady=4)
        self.e_email = ctk.CTkEntry(frm, width=300)
        self.e_email.grid(row=3, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Admissão (AAAA-MM-DD):").grid(row=3, column=2, sticky="e", padx=5, pady=4)
        self.e_data = ctk.CTkEntry(frm, width=200)
        self.e_data.grid(row=3, column=3, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Usuário:").grid(row=4, column=0, sticky="e", padx=5, pady=4)
        self.e_user = ctk.CTkEntry(frm, width=300)
        self.e_user.grid(row=4, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Senha:").grid(row=4, column=2, sticky="e", padx=5, pady=4)
        self.e_senha = ctk.CTkEntry(frm, width=200, show="*")
        self.e_senha.grid(row=4, column=3, padx=5, pady=4)

        ctk.CTkLabel(frm, text="(Senha em branco no Atualizar = mantém atual)",
                     font=("Arial", 9), text_color="gray").grid(row=5, column=2, columnspan=2)

    def _botoes(self):
        frm = ctk.CTkFrame(self)
        frm.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(frm, text="Salvar", command=self.salvar).pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Atualizar", command=self.atualizar).pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Excluir", command=self.excluir,
                      fg_color="darkred").pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Limpar", command=self.limpar).pack(side="left", padx=5)

    def _busca(self):
        frm = ctk.CTkFrame(self)
        frm.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(frm, text="Buscar:").pack(side="left", padx=5)
        self.e_busca = ctk.CTkEntry(frm, width=300)
        self.e_busca.pack(side="left", padx=5)
        self.e_busca.bind("<Return>", lambda e: self.listar())
        ctk.CTkButton(frm, text="Buscar", command=self.listar).pack(side="left", padx=5)

    def _tabela(self):
        cols = ("ID", "Nome", "CPF", "Cargo", "Telefone", "Usuário", "Ativo")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=10)
        for c, w in zip(cols, [50, 200, 130, 100, 130, 130, 70]):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.selecionar)

    def _coletar(self):
        return {
            'nome': self.e_nome.get().strip(),
            'cpf': v._so_digitos(self.e_cpf.get()),
            'cargo': self.cb_cargo.get(),
            'tel': self.e_tel.get().strip(),
            'email': self.e_email.get().strip(),
            'usuario': self.e_user.get().strip(),
            'senha': self.e_senha.get(),
            'data': self.e_data.get().strip() or None,
        }

    def _validar(self, d, eh_novo):
        if not d['nome'] or len(d['nome']) < 3:
            return "Nome obrigatório (mín. 3 caracteres)"
        if not v.validar_cpf(d['cpf']):
            return "CPF inválido"
        if d['cargo'] not in ('Admin', 'Atendente', 'Mecânico'):
            return "Cargo inválido"
        if d['email'] and not v.validar_email(d['email']):
            return "Email inválido"
        if d['tel'] and not v.validar_telefone(d['tel']):
            return "Telefone inválido"
        if not d['usuario'] or len(d['usuario']) < 3:
            return "Usuário obrigatório (mín. 3 caracteres)"
        if eh_novo:
            if not d['senha'] or len(d['senha']) < config.SENHA_MIN_CARACTERES:
                return "Senha obrigatória (mín. {} caracteres)".format(config.SENHA_MIN_CARACTERES)
        elif d['senha'] and len(d['senha']) < config.SENHA_MIN_CARACTERES:
            return "Nova senha deve ter mín. {} caracteres".format(config.SENHA_MIN_CARACTERES)
        return ''

    def salvar(self):
        d = self._coletar()
        erro = self._validar(d, eh_novo=True)
        if erro:
            messagebox.showwarning("Atenção", erro, parent=self)
            return
        salt = seguranca.gerar_salt()
        h = seguranca.hash_senha(d['senha'], salt)
        try:
            with cursor() as (conn, cur):
                cur.execute("""
                    INSERT INTO funcionarios (nome, cpf, cargo, telefone, email,
                        usuario, senha_hash, senha_salt, data_admissao)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (d['nome'], d['cpf'], d['cargo'], d['tel'], d['email'],
                      d['usuario'], h, salt, d['data']))
            messagebox.showinfo("OK", "Funcionário cadastrado!", parent=self)
            self.limpar()
            self.listar()
        except Exception as e:
            mostrar_erro(self, "Não foi possível salvar. Verifique se CPF ou usuário já existem.", e)

    def atualizar(self):
        if not self.id_atual:
            messagebox.showwarning("Atenção", "Selecione um funcionário", parent=self)
            return
        d = self._coletar()
        erro = self._validar(d, eh_novo=False)
        if erro:
            messagebox.showwarning("Atenção", erro, parent=self)
            return
        try:
            with cursor() as (conn, cur):
                if d['senha']:
                    salt = seguranca.gerar_salt()
                    h = seguranca.hash_senha(d['senha'], salt)
                    cur.execute("""
                        UPDATE funcionarios SET nome=%s, cpf=%s, cargo=%s, telefone=%s,
                            email=%s, usuario=%s, senha_hash=%s, senha_salt=%s, data_admissao=%s
                        WHERE id=%s
                    """, (d['nome'], d['cpf'], d['cargo'], d['tel'], d['email'],
                          d['usuario'], h, salt, d['data'], self.id_atual))
                else:
                    cur.execute("""
                        UPDATE funcionarios SET nome=%s, cpf=%s, cargo=%s, telefone=%s,
                            email=%s, usuario=%s, data_admissao=%s
                        WHERE id=%s
                    """, (d['nome'], d['cpf'], d['cargo'], d['tel'], d['email'],
                          d['usuario'], d['data'], self.id_atual))
            messagebox.showinfo("OK", "Funcionário atualizado!", parent=self)
            self.limpar()
            self.listar()
        except Exception as e:
            mostrar_erro(self, "Não foi possível atualizar o funcionário.", e)

    def excluir(self):
        if not self.id_atual:
            return
        if self.id_atual == self.usuario['id']:
            messagebox.showwarning("Atenção", "Você não pode excluir a si mesmo!", parent=self)
            return
        if not messagebox.askyesno("Confirmar", "Excluir este funcionário?", parent=self):
            return
        try:
            with cursor() as (conn, cur):
                cur.execute("DELETE FROM funcionarios WHERE id=%s", (self.id_atual,))
            self.limpar()
            self.listar()
        except Exception as e:
            mostrar_erro(self, "Não foi possível excluir. O funcionário pode ter OS vinculadas.", e)

    def limpar(self):
        self.id_atual = None
        for e in [self.e_nome, self.e_cpf, self.e_tel, self.e_email,
                  self.e_user, self.e_senha, self.e_data]:
            e.delete(0, "end")
        self.cb_cargo.set("Mecânico")

    def listar(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        busca = self.e_busca.get().strip()
        try:
            with cursor() as (conn, cur):
                if busca:
                    like = "%" + busca + "%"
                    cur.execute("""
                        SELECT id, nome, cpf, cargo, telefone, usuario, ativo FROM funcionarios
                        WHERE nome LIKE %s OR cpf LIKE %s OR usuario LIKE %s
                        ORDER BY nome LIMIT 500
                    """, (like, like, like))
                else:
                    cur.execute("""
                        SELECT id, nome, cpf, cargo, telefone, usuario, ativo FROM funcionarios
                        ORDER BY nome LIMIT 500
                    """)
                linhas = cur.fetchall()
        except Exception as e:
            mostrar_erro(self, "Não foi possível carregar a lista de funcionários.", e)
            return
        for r in linhas:
            self.tree.insert("", "end", values=(
                r[0], r[1], v.formatar_cpf(r[2] or ''), r[3],
                v.formatar_telefone(r[4] or ''), r[5], 'Sim' if r[6] else 'Não'
            ))

    def selecionar(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        self.id_atual = int(self.tree.item(sel[0], "values")[0])
        try:
            with cursor() as (conn, cur):
                cur.execute("""
                    SELECT nome, cpf, cargo, telefone, email, usuario, data_admissao
                    FROM funcionarios WHERE id=%s
                """, (self.id_atual,))
                r = cur.fetchone()
        except Exception as e:
            mostrar_erro(self, "Não foi possível carregar o funcionário.", e)
            return
        if not r:
            return
        id_bak = self.id_atual
        self.limpar()
        self.id_atual = id_bak
        self.e_nome.insert(0, r[0] or '')
        self.e_cpf.insert(0, v.formatar_cpf(r[1] or ''))
        self.cb_cargo.set(r[2] or 'Mecânico')
        self.e_tel.insert(0, v.formatar_telefone(r[3] or ''))
        self.e_email.insert(0, r[4] or '')
        self.e_user.insert(0, r[5] or '')
        self.e_data.insert(0, str(r[6]) if r[6] else '')
