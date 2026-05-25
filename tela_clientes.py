"""
CRUD de clientes (apenas para Admin/Atendente).
Inclui: validação de CPF/CNPJ, email, telefone, autocompletar endereço por CEP.
Cadastra senha (hash) - cliente pode logar com CPF + senha.
"""
import threading
import customtkinter as ctk
from tkinter import messagebox, ttk

from db import conectar
import validacoes as v
import seguranca
from email_sender import enviar_email, email_boas_vindas
import config


class TelaClientes(ctk.CTkToplevel):
    def __init__(self, master, usuario_logado):
        super().__init__(master)
        self.usuario = usuario_logado
        self.title("Clientes - Truckstar")
        self.geometry("1000x680")
        self.grab_set()
        self.id_atual = None

        self._montar_formulario()
        self._montar_botoes()
        self._montar_busca()
        self._montar_tabela()
        self.listar()

    def _montar_formulario(self):
        frm = ctk.CTkFrame(self)
        frm.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frm, text="Cadastro de Cliente",
                     font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=4, pady=5)

        # linha 1
        ctk.CTkLabel(frm, text="Nome:").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        self.e_nome = ctk.CTkEntry(frm, width=300)
        self.e_nome.grid(row=1, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="CPF/CNPJ:").grid(row=1, column=2, sticky="e", padx=5, pady=4)
        self.e_cpf = ctk.CTkEntry(frm, width=200)
        self.e_cpf.grid(row=1, column=3, padx=5, pady=4)

        # linha 2
        ctk.CTkLabel(frm, text="Telefone:").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        self.e_tel = ctk.CTkEntry(frm, width=300)
        self.e_tel.grid(row=2, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Email:").grid(row=2, column=2, sticky="e", padx=5, pady=4)
        self.e_email = ctk.CTkEntry(frm, width=200)
        self.e_email.grid(row=2, column=3, padx=5, pady=4)

        # linha 3 - CEP + botão buscar
        ctk.CTkLabel(frm, text="CEP:").grid(row=3, column=0, sticky="e", padx=5, pady=4)
        frm_cep = ctk.CTkFrame(frm, fg_color="transparent")
        frm_cep.grid(row=3, column=1, sticky="w", padx=5, pady=4)
        self.e_cep = ctk.CTkEntry(frm_cep, width=130)
        self.e_cep.pack(side="left")
        self.btn_cep = ctk.CTkButton(frm_cep, text="Buscar CEP", width=110,
                                     command=self.buscar_cep)
        self.btn_cep.pack(side="left", padx=5)

        ctk.CTkLabel(frm, text="Estado:").grid(row=3, column=2, sticky="e", padx=5, pady=4)
        self.e_estado = ctk.CTkEntry(frm, width=60)
        self.e_estado.grid(row=3, column=3, sticky="w", padx=5, pady=4)

        # linha 4 - logradouro/numero
        ctk.CTkLabel(frm, text="Logradouro:").grid(row=4, column=0, sticky="e", padx=5, pady=4)
        self.e_log = ctk.CTkEntry(frm, width=300)
        self.e_log.grid(row=4, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Nº:").grid(row=4, column=2, sticky="e", padx=5, pady=4)
        self.e_num = ctk.CTkEntry(frm, width=80)
        self.e_num.grid(row=4, column=3, sticky="w", padx=5, pady=4)

        # linha 5 - bairro/cidade
        ctk.CTkLabel(frm, text="Bairro:").grid(row=5, column=0, sticky="e", padx=5, pady=4)
        self.e_bairro = ctk.CTkEntry(frm, width=300)
        self.e_bairro.grid(row=5, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Cidade:").grid(row=5, column=2, sticky="e", padx=5, pady=4)
        self.e_cidade = ctk.CTkEntry(frm, width=200)
        self.e_cidade.grid(row=5, column=3, padx=5, pady=4)

        # linha 6 - complemento + senha
        ctk.CTkLabel(frm, text="Complemento:").grid(row=6, column=0, sticky="e", padx=5, pady=4)
        self.e_comp = ctk.CTkEntry(frm, width=300)
        self.e_comp.grid(row=6, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Senha:").grid(row=6, column=2, sticky="e", padx=5, pady=4)
        self.e_senha = ctk.CTkEntry(frm, width=200, show="*")
        self.e_senha.grid(row=6, column=3, padx=5, pady=4)

        ctk.CTkLabel(frm, text="(Senha em branco no Atualizar = mantém atual)",
                     font=("Arial", 9), text_color="gray").grid(row=7, column=2, columnspan=2)

    def _montar_botoes(self):
        frm = ctk.CTkFrame(self)
        frm.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(frm, text="Salvar", command=self.salvar).pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Atualizar", command=self.atualizar).pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Excluir", command=self.excluir,
                      fg_color="darkred").pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Limpar", command=self.limpar).pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Caminhões do Cliente",
                      command=self.abrir_caminhoes).pack(side="left", padx=5)

    def _montar_busca(self):
        frm = ctk.CTkFrame(self)
        frm.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(frm, text="Buscar (nome ou CPF/CNPJ):").pack(side="left", padx=5)
        self.e_busca = ctk.CTkEntry(frm, width=300)
        self.e_busca.pack(side="left", padx=5)
        self.e_busca.bind("<Return>", lambda e: self.listar())
        ctk.CTkButton(frm, text="Buscar", command=self.listar).pack(side="left", padx=5)

    def _montar_tabela(self):
        frm = ctk.CTkFrame(self)
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        cols = ("ID", "Nome", "CPF/CNPJ", "Telefone", "Email", "Cidade/UF")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=10)
        for c, w in zip(cols, [50, 200, 140, 120, 200, 120]):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.selecionar)

    # ---------- AÇÕES ----------
    def buscar_cep(self):
        cep = self.e_cep.get().strip()
        if not cep:
            messagebox.showwarning("Atenção", "Digite o CEP", parent=self)
            return
        self.btn_cep.configure(state="disabled", text="Buscando...")

        def tarefa():
            res = v.buscar_cep(cep)
            self.after(0, lambda: self._aplicar_cep(res))

        threading.Thread(target=tarefa, daemon=True).start()

    def _aplicar_cep(self, res: dict):
        self.btn_cep.configure(state="normal", text="Buscar CEP")
        if not res['ok']:
            messagebox.showerror("CEP", res['erro'], parent=self)
            return
        self.e_log.delete(0, "end"); self.e_log.insert(0, res['logradouro'])
        self.e_bairro.delete(0, "end"); self.e_bairro.insert(0, res['bairro'])
        self.e_cidade.delete(0, "end"); self.e_cidade.insert(0, res['cidade'])
        self.e_estado.delete(0, "end"); self.e_estado.insert(0, res['estado'])

    def _coletar(self) -> dict:
        return {
            'nome': self.e_nome.get().strip(),
            'cpf': v._so_digitos(self.e_cpf.get()),
            'tel': self.e_tel.get().strip(),
            'email': self.e_email.get().strip(),
            'cep': v._so_digitos(self.e_cep.get()),
            'log': self.e_log.get().strip(),
            'num': self.e_num.get().strip(),
            'comp': self.e_comp.get().strip(),
            'bairro': self.e_bairro.get().strip(),
            'cidade': self.e_cidade.get().strip(),
            'estado': self.e_estado.get().strip().upper(),
            'senha': self.e_senha.get(),
        }

    def _validar(self, d: dict, eh_novo: bool) -> str:
        if not d['nome'] or len(d['nome']) < 3:
            return "Nome obrigatório (mín. 3 caracteres)"
        if not v.validar_cpf_ou_cnpj(d['cpf']):
            return "CPF ou CNPJ inválido"
        if d['email'] and not v.validar_email(d['email']):
            return "Email inválido"
        if d['tel'] and not v.validar_telefone(d['tel']):
            return "Telefone inválido"
        if d['cep'] and len(d['cep']) != 8:
            return "CEP deve ter 8 dígitos"
        if d['estado'] and len(d['estado']) != 2:
            return "Estado deve ter 2 letras (UF)"
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
            conn = conectar()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO clientes (nome, cpf_cnpj, telefone, email, cep, logradouro,
                    numero, complemento, bairro, cidade, estado, senha_hash, senha_salt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (d['nome'], d['cpf'], d['tel'], d['email'], d['cep'] or None,
                  d['log'] or None, d['num'] or None, d['comp'] or None,
                  d['bairro'] or None, d['cidade'] or None, d['estado'] or None,
                  h, salt))
            conn.commit()
            cur.close()
            conn.close()
            # email de boas vindas
            if d['email']:
                assunto, corpo = email_boas_vindas(d['nome'])
                enviar_email(d['email'], assunto, corpo)
            messagebox.showinfo("OK", "Cliente cadastrado!", parent=self)
            self.limpar()
            self.listar()
        except Exception as e:
            messagebox.showerror("Erro", "Erro ao salvar: " + str(e), parent=self)

    def atualizar(self):
        if not self.id_atual:
            messagebox.showwarning("Atenção", "Selecione um cliente na lista", parent=self)
            return
        d = self._coletar()
        erro = self._validar(d, eh_novo=False)
        if erro:
            messagebox.showwarning("Atenção", erro, parent=self)
            return
        try:
            conn = conectar()
            cur = conn.cursor()
            if d['senha']:
                salt = seguranca.gerar_salt()
                h = seguranca.hash_senha(d['senha'], salt)
                cur.execute("""
                    UPDATE clientes SET nome=%s, cpf_cnpj=%s, telefone=%s, email=%s,
                        cep=%s, logradouro=%s, numero=%s, complemento=%s,
                        bairro=%s, cidade=%s, estado=%s,
                        senha_hash=%s, senha_salt=%s
                    WHERE id=%s
                """, (d['nome'], d['cpf'], d['tel'], d['email'], d['cep'] or None,
                      d['log'] or None, d['num'] or None, d['comp'] or None,
                      d['bairro'] or None, d['cidade'] or None, d['estado'] or None,
                      h, salt, self.id_atual))
            else:
                cur.execute("""
                    UPDATE clientes SET nome=%s, cpf_cnpj=%s, telefone=%s, email=%s,
                        cep=%s, logradouro=%s, numero=%s, complemento=%s,
                        bairro=%s, cidade=%s, estado=%s
                    WHERE id=%s
                """, (d['nome'], d['cpf'], d['tel'], d['email'], d['cep'] or None,
                      d['log'] or None, d['num'] or None, d['comp'] or None,
                      d['bairro'] or None, d['cidade'] or None, d['estado'] or None,
                      self.id_atual))
            conn.commit()
            cur.close()
            conn.close()
            messagebox.showinfo("OK", "Cliente atualizado!", parent=self)
            self.limpar()
            self.listar()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def excluir(self):
        if self.usuario['cargo'] != 'Admin':
            messagebox.showwarning("Permissão", "Apenas Admin pode excluir clientes", parent=self)
            return
        if not self.id_atual:
            return
        if not messagebox.askyesno("Confirmar",
                                   "Excluir este cliente?\nIsso apagará todos os caminhões dele.",
                                   parent=self):
            return
        try:
            conn = conectar()
            cur = conn.cursor()
            cur.execute("DELETE FROM clientes WHERE id=%s", (self.id_atual,))
            conn.commit()
            cur.close()
            conn.close()
            self.limpar()
            self.listar()
        except Exception as e:
            messagebox.showerror("Erro",
                "Não foi possível excluir (cliente possui OS vinculadas): " + str(e),
                parent=self)

    def limpar(self):
        self.id_atual = None
        for e in [self.e_nome, self.e_cpf, self.e_tel, self.e_email, self.e_cep,
                  self.e_log, self.e_num, self.e_comp, self.e_bairro,
                  self.e_cidade, self.e_estado, self.e_senha]:
            e.delete(0, "end")

    def listar(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        busca = self.e_busca.get().strip()
        conn = conectar()
        cur = conn.cursor()
        if busca:
            like = "%" + busca + "%"
            busca_num = v._so_digitos(busca)
            if busca_num:
                like_num = "%" + busca_num + "%"
                cur.execute("""
                    SELECT id, nome, cpf_cnpj, telefone, email, cidade, estado
                    FROM clientes WHERE nome LIKE %s OR cpf_cnpj LIKE %s
                    ORDER BY nome LIMIT 500
                """, (like, like_num))
            else:
                cur.execute("""
                    SELECT id, nome, cpf_cnpj, telefone, email, cidade, estado
                    FROM clientes WHERE nome LIKE %s
                    ORDER BY nome LIMIT 500
                """, (like,))
        else:
            cur.execute("""
                SELECT id, nome, cpf_cnpj, telefone, email, cidade, estado
                FROM clientes ORDER BY nome LIMIT 500
            """)
        for r in cur.fetchall():
            cid_uf = "{}/{}".format(r[5] or '', r[6] or '').strip('/')
            self.tree.insert("", "end", values=(
                r[0], r[1], v.formatar_cpf_ou_cnpj(r[2]),
                v.formatar_telefone(r[3] or ''), r[4] or '', cid_uf
            ))
        cur.close()
        conn.close()

    def selecionar(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        self.id_atual = int(self.tree.item(sel[0], "values")[0])
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT nome, cpf_cnpj, telefone, email, cep, logradouro, numero,
                   complemento, bairro, cidade, estado
            FROM clientes WHERE id=%s
        """, (self.id_atual,))
        r = cur.fetchone()
        cur.close()
        conn.close()
        if not r:
            return
        id_bak = self.id_atual
        self.limpar()
        self.id_atual = id_bak
        self.e_nome.insert(0, r[0] or '')
        self.e_cpf.insert(0, v.formatar_cpf_ou_cnpj(r[1] or ''))
        self.e_tel.insert(0, v.formatar_telefone(r[2] or ''))
        self.e_email.insert(0, r[3] or '')
        self.e_cep.insert(0, v.formatar_cep(r[4] or ''))
        self.e_log.insert(0, r[5] or '')
        self.e_num.insert(0, r[6] or '')
        self.e_comp.insert(0, r[7] or '')
        self.e_bairro.insert(0, r[8] or '')
        self.e_cidade.insert(0, r[9] or '')
        self.e_estado.insert(0, r[10] or '')

    def abrir_caminhoes(self):
        if not self.id_atual:
            messagebox.showwarning("Atenção", "Selecione um cliente primeiro", parent=self)
            return
        TelaCaminhoes(self, self.id_atual, self.e_nome.get())


# =========================================
class TelaCaminhoes(ctk.CTkToplevel):
    def __init__(self, master, cliente_id, cliente_nome):
        super().__init__(master)
        self.cliente_id = cliente_id
        self.id_atual = None
        self.title("Caminhões de " + cliente_nome)
        self.geometry("850x560")
        self.grab_set()

        frm = ctk.CTkFrame(self)
        frm.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frm, text="Cadastro de Caminhão",
                     font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=4, pady=5)

        ctk.CTkLabel(frm, text="Placa:").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        self.e_placa = ctk.CTkEntry(frm, width=150)
        self.e_placa.grid(row=1, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Marca:").grid(row=1, column=2, sticky="e", padx=5, pady=4)
        self.e_marca = ctk.CTkEntry(frm, width=200)
        self.e_marca.grid(row=1, column=3, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Modelo:").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        self.e_modelo = ctk.CTkEntry(frm, width=150)
        self.e_modelo.grid(row=2, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Ano:").grid(row=2, column=2, sticky="e", padx=5, pady=4)
        self.e_ano = ctk.CTkEntry(frm, width=200)
        self.e_ano.grid(row=2, column=3, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Cor:").grid(row=3, column=0, sticky="e", padx=5, pady=4)
        self.e_cor = ctk.CTkEntry(frm, width=150)
        self.e_cor.grid(row=3, column=1, padx=5, pady=4)

        ctk.CTkLabel(frm, text="Chassi:").grid(row=3, column=2, sticky="e", padx=5, pady=4)
        self.e_chassi = ctk.CTkEntry(frm, width=200)
        self.e_chassi.grid(row=3, column=3, padx=5, pady=4)

        frm_b = ctk.CTkFrame(self)
        frm_b.pack(fill="x", padx=10)
        ctk.CTkButton(frm_b, text="Salvar", command=self.salvar).pack(side="left", padx=5)
        ctk.CTkButton(frm_b, text="Excluir", command=self.excluir,
                      fg_color="darkred").pack(side="left", padx=5)
        ctk.CTkButton(frm_b, text="Limpar", command=self.limpar).pack(side="left", padx=5)

        cols = ("ID", "Placa", "Marca", "Modelo", "Ano", "Cor")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=10)
        for c, w in zip(cols, [50, 100, 120, 150, 80, 100]):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.selecionar)

        self.listar()

    def salvar(self):
        placa = self.e_placa.get().strip().upper().replace('-', '').replace(' ', '')
        if not v.validar_placa(placa):
            messagebox.showwarning("Atenção", "Placa inválida (ex: ABC1234 ou ABC1D23)", parent=self)
            return
        ano_str = self.e_ano.get().strip()
        ano_int = None
        if ano_str:
            if not v.validar_ano(ano_str):
                messagebox.showwarning("Atenção", "Ano inválido", parent=self)
                return
            ano_int = int(ano_str)
        try:
            conn = conectar()
            cur = conn.cursor()
            if self.id_atual:
                cur.execute("""
                    UPDATE caminhoes SET placa=%s, marca=%s, modelo=%s, ano=%s,
                        cor=%s, chassi=%s WHERE id=%s
                """, (placa, self.e_marca.get().strip(), self.e_modelo.get().strip(),
                      ano_int, self.e_cor.get().strip(), self.e_chassi.get().strip(),
                      self.id_atual))
            else:
                cur.execute("""
                    INSERT INTO caminhoes (cliente_id, placa, marca, modelo, ano, cor, chassi)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (self.cliente_id, placa, self.e_marca.get().strip(),
                      self.e_modelo.get().strip(), ano_int, self.e_cor.get().strip(),
                      self.e_chassi.get().strip()))
            conn.commit()
            cur.close()
            conn.close()
            messagebox.showinfo("OK", "Caminhão salvo!", parent=self)
            self.limpar()
            self.listar()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def excluir(self):
        if not self.id_atual:
            return
        if not messagebox.askyesno("Confirmar", "Excluir este caminhão?", parent=self):
            return
        try:
            conn = conectar()
            cur = conn.cursor()
            cur.execute("DELETE FROM caminhoes WHERE id=%s", (self.id_atual,))
            conn.commit()
            cur.close()
            conn.close()
            self.limpar()
            self.listar()
        except Exception as e:
            messagebox.showerror("Erro",
                "Não foi possível excluir (existem OS vinculadas): " + str(e),
                parent=self)

    def limpar(self):
        self.id_atual = None
        for e in [self.e_placa, self.e_marca, self.e_modelo, self.e_ano,
                  self.e_cor, self.e_chassi]:
            e.delete(0, "end")

    def listar(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, placa, marca, modelo, ano, cor FROM caminhoes
            WHERE cliente_id=%s ORDER BY placa
        """, (self.cliente_id,))
        for r in cur.fetchall():
            self.tree.insert("", "end", values=(
                r[0], v.formatar_placa(r[1]), r[2] or '', r[3] or '',
                r[4] or '', r[5] or ''
            ))
        cur.close()
        conn.close()

    def selecionar(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        self.id_atual = int(self.tree.item(sel[0], "values")[0])
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT placa, marca, modelo, ano, cor, chassi FROM caminhoes WHERE id=%s",
                    (self.id_atual,))
        r = cur.fetchone()
        cur.close()
        conn.close()
        if not r:
            return
        id_bak = self.id_atual
        self.limpar()
        self.id_atual = id_bak
        self.e_placa.insert(0, v.formatar_placa(r[0]))
        self.e_marca.insert(0, r[1] or '')
        self.e_modelo.insert(0, r[2] or '')
        self.e_ano.insert(0, str(r[3]) if r[3] else '')
        self.e_cor.insert(0, r[4] or '')
        self.e_chassi.insert(0, r[5] or '')
