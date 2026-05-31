"""
CRUD de clientes (apenas para Admin/Atendente).
Inclui: validação de CPF/CNPJ, email, telefone, autocompletar endereço por CEP.
Cliente nao faz login — recebe apenas emails de notificacao das OS.
"""
import threading
import customtkinter as ctk
from tkinter import messagebox, ttk

from db import cursor
import validacoes as v
from email_sender import enviar_email, email_boas_vindas
from ui_utils import habilitar_resize_e_fullscreen, botao_tela_cheia
from ui_helpers import mostrar_erro


class TelaClientes(ctk.CTkToplevel):
    def __init__(self, master, usuario_logado):
        super().__init__(master)
        self.master_painel = master
        self.usuario = usuario_logado
        self.title("Clientes - Truckstar")
        self.geometry("1000x720")
        self.grab_set()
        habilitar_resize_e_fullscreen(self, min_w=820, min_h=620)
        self.id_atual = None

        self._montar_topbar()
        self._montar_formulario()
        self._montar_botoes()
        self._montar_busca()
        self._montar_tabela()
        self.listar()

    def _montar_topbar(self):
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

        # linha 6 - complemento
        ctk.CTkLabel(frm, text="Complemento:").grid(row=6, column=0, sticky="e", padx=5, pady=4)
        self.e_comp = ctk.CTkEntry(frm, width=300)
        self.e_comp.grid(row=6, column=1, padx=5, pady=4)

    def _montar_botoes(self):
        frm = ctk.CTkFrame(self)
        frm.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(frm, text="Salvar", command=self.salvar).pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Atualizar", command=self.atualizar).pack(side="left", padx=5)
        # Excluir: so Admin (Atendente nao pode — botao oculto pra ele)
        if self.usuario['cargo'] == 'Admin':
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
            # Guard: se a janela foi fechada durante a requisição HTTP,
            # agendar no widget morto lançaria "application destroyed".
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self._aplicar_cep(res))
            except Exception:
                pass

        threading.Thread(target=tarefa, daemon=True).start()

    def _aplicar_cep(self, res: dict):
        if not self.winfo_exists():
            return
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
        }

    def _validar(self, d: dict) -> str:
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
        return ''

    def salvar(self):
        d = self._coletar()
        erro = self._validar(d)
        if erro:
            messagebox.showwarning("Atenção", erro, parent=self)
            return
        try:
            with cursor() as (conn, cur):
                cur.execute("""
                    INSERT INTO clientes (nome, cpf_cnpj, telefone, email, cep, logradouro,
                        numero, complemento, bairro, cidade, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (d['nome'], d['cpf'], d['tel'], d['email'], d['cep'] or None,
                      d['log'] or None, d['num'] or None, d['comp'] or None,
                      d['bairro'] or None, d['cidade'] or None, d['estado'] or None))
            # email de boas vindas — sincrono pra mostrar resultado real
            msg_ok = "Cliente cadastrado!"
            if d['email']:
                assunto, corpo = email_boas_vindas(d['nome'])
                sucesso, erro = enviar_email(d['email'], assunto, corpo, em_thread=False)
                if sucesso:
                    msg_ok += "\nEmail de boas-vindas enviado."
                else:
                    msg_ok += "\n(Aviso: email de boas-vindas NÃO foi enviado.\n{})".format(erro)
            messagebox.showinfo("OK", msg_ok, parent=self)
            self.limpar()
            self.listar()
        except Exception as e:
            mostrar_erro(self, "Não foi possível salvar o cliente. Verifique se o CPF/CNPJ já está cadastrado.", e)

    def atualizar(self):
        if not self.id_atual:
            messagebox.showwarning("Atenção", "Selecione um cliente na lista", parent=self)
            return
        d = self._coletar()
        erro = self._validar(d)
        if erro:
            messagebox.showwarning("Atenção", erro, parent=self)
            return
        try:
            with cursor() as (conn, cur):
                cur.execute("""
                    UPDATE clientes SET nome=%s, cpf_cnpj=%s, telefone=%s, email=%s,
                        cep=%s, logradouro=%s, numero=%s, complemento=%s,
                        bairro=%s, cidade=%s, estado=%s
                    WHERE id=%s
                """, (d['nome'], d['cpf'], d['tel'], d['email'], d['cep'] or None,
                      d['log'] or None, d['num'] or None, d['comp'] or None,
                      d['bairro'] or None, d['cidade'] or None, d['estado'] or None,
                      self.id_atual))
            messagebox.showinfo("OK", "Cliente atualizado!", parent=self)
            self.limpar()
            self.listar()
        except Exception as e:
            mostrar_erro(self, "Não foi possível atualizar o cliente.", e)

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
            with cursor() as (conn, cur):
                cur.execute("DELETE FROM clientes WHERE id=%s", (self.id_atual,))
            self.limpar()
            self.listar()
        except Exception as e:
            mostrar_erro(self, "Não foi possível excluir. O cliente pode ter OS vinculadas.", e)

    def limpar(self):
        self.id_atual = None
        for e in [self.e_nome, self.e_cpf, self.e_tel, self.e_email, self.e_cep,
                  self.e_log, self.e_num, self.e_comp, self.e_bairro,
                  self.e_cidade, self.e_estado]:
            e.delete(0, "end")

    def listar(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        busca = self.e_busca.get().strip()
        try:
            with cursor() as (conn, cur):
                if busca:
                    like = "%" + busca + "%"
                    busca_num = v._so_digitos(busca)
                    if busca_num:
                        like_num = "%" + busca_num + "%"
                        cur.execute("""
                            SELECT id, nome, cpf_cnpj, telefone, email, cidade, estado
                            FROM clientes WHERE ativo=1 AND (nome LIKE %s OR cpf_cnpj LIKE %s)
                            ORDER BY nome LIMIT 500
                        """, (like, like_num))
                    else:
                        cur.execute("""
                            SELECT id, nome, cpf_cnpj, telefone, email, cidade, estado
                            FROM clientes WHERE ativo=1 AND nome LIKE %s
                            ORDER BY nome LIMIT 500
                        """, (like,))
                else:
                    cur.execute("""
                        SELECT id, nome, cpf_cnpj, telefone, email, cidade, estado
                        FROM clientes WHERE ativo=1 ORDER BY nome LIMIT 500
                    """)
                linhas = cur.fetchall()
        except Exception as e:
            mostrar_erro(self, "Não foi possível carregar a lista de clientes.", e)
            return
        for r in linhas:
            cid_uf = "{}/{}".format(r[5] or '', r[6] or '').strip('/')
            self.tree.insert("", "end", values=(
                r[0], r[1], v.formatar_cpf_ou_cnpj(r[2]),
                v.formatar_telefone(r[3] or ''), r[4] or '', cid_uf
            ))

    def selecionar(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        self.id_atual = int(self.tree.item(sel[0], "values")[0])
        try:
            with cursor() as (conn, cur):
                cur.execute("""
                    SELECT nome, cpf_cnpj, telefone, email, cep, logradouro, numero,
                           complemento, bairro, cidade, estado
                    FROM clientes WHERE id=%s
                """, (self.id_atual,))
                r = cur.fetchone()
        except Exception as e:
            mostrar_erro(self, "Não foi possível carregar o cliente.", e)
            return
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
        self.geometry("850x580")
        self.grab_set()
        habilitar_resize_e_fullscreen(self, min_w=720, min_h=480)

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
            with cursor() as (conn, cur):
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
            messagebox.showinfo("OK", "Caminhão salvo!", parent=self)
            self.limpar()
            self.listar()
        except Exception as e:
            mostrar_erro(self, "Não foi possível salvar o caminhão. Verifique se a placa já está cadastrada.", e)

    def excluir(self):
        if not self.id_atual:
            return
        if not messagebox.askyesno("Confirmar", "Excluir este caminhão?", parent=self):
            return
        try:
            with cursor() as (conn, cur):
                cur.execute("DELETE FROM caminhoes WHERE id=%s", (self.id_atual,))
            self.limpar()
            self.listar()
        except Exception as e:
            mostrar_erro(self, "Não foi possível excluir o caminhão. Pode haver OS vinculadas.", e)

    def limpar(self):
        self.id_atual = None
        for e in [self.e_placa, self.e_marca, self.e_modelo, self.e_ano,
                  self.e_cor, self.e_chassi]:
            e.delete(0, "end")

    def listar(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            with cursor() as (conn, cur):
                cur.execute("""
                    SELECT id, placa, marca, modelo, ano, cor FROM caminhoes
                    WHERE cliente_id=%s ORDER BY placa
                """, (self.cliente_id,))
                linhas = cur.fetchall()
        except Exception as e:
            mostrar_erro(self, "Não foi possível carregar os caminhões.", e)
            return
        for r in linhas:
            self.tree.insert("", "end", values=(
                r[0], v.formatar_placa(r[1]), r[2] or '', r[3] or '',
                r[4] or '', r[5] or ''
            ))

    def selecionar(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        self.id_atual = int(self.tree.item(sel[0], "values")[0])
        try:
            with cursor() as (conn, cur):
                cur.execute("SELECT placa, marca, modelo, ano, cor, chassi FROM caminhoes WHERE id=%s",
                            (self.id_atual,))
                r = cur.fetchone()
        except Exception as e:
            mostrar_erro(self, "Não foi possível carregar o caminhão.", e)
            return
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
