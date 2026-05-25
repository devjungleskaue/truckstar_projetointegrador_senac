"""
Ordens de Serviço: criar, consultar, editar status, imprimir PDF.
Envia email automático ao cliente quando OS é criada ou tem mudança de status.
Consulta por placa ou nome.
Permissões:
  - Admin: tudo
  - Atendente: criar/editar (mas não excluir)
  - Mecânico: ver e atualizar STATUS / serviços / peças das suas OS
"""
import os
import sys
import subprocess
import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
from datetime import datetime

from db import conectar
from pdf_os import gerar_pdf_os
import validacoes as v
from email_sender import enviar_email, email_os_criada, email_os_atualizada
from ui_utils import habilitar_resize_e_fullscreen, botao_tela_cheia


class TelaOrdens(ctk.CTkToplevel):
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

    def __init__(self, master, usuario_logado):
        super().__init__(master)
        self.master_painel = master
        self.usuario = usuario_logado  # dict id, nome, cargo
        self.title("Ordens de Serviço - Truckstar")
        self.geometry("1150x770")
        self.grab_set()
        habilitar_resize_e_fullscreen(self, min_w=920, min_h=620)

        self._topbar()

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        if self.usuario['cargo'] in ('Admin', 'Atendente'):
            self.tabs.add("Nova OS")
        self.tabs.add("Consultar OS")
        if self.usuario['cargo'] in ('Admin', 'Atendente', 'Mecânico'):
            self.tabs.add("Editar OS")

        if self.usuario['cargo'] in ('Admin', 'Atendente'):
            self._aba_nova()
        self._aba_consulta()
        if self.usuario['cargo'] in ('Admin', 'Atendente', 'Mecânico'):
            self._aba_editar()

    # =================== NOVA OS ===================
    def _aba_nova(self):
        tab = self.tabs.tab("Nova OS")

        frm1 = ctk.CTkFrame(tab)
        frm1.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(frm1, text="Cliente:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.cb_cliente = ctk.CTkComboBox(frm1, values=[], width=450,
                                          command=self._on_cliente, state="readonly")
        self.cb_cliente.grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(frm1, text="Atualizar Listas", command=self._carregar_combos,
                      width=140).grid(row=0, column=2, padx=5)

        ctk.CTkLabel(frm1, text="Caminhão:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.cb_caminhao = ctk.CTkComboBox(frm1, values=[], width=450, state="readonly")
        self.cb_caminhao.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(frm1, text="Mecânico:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.cb_mecanico = ctk.CTkComboBox(frm1, values=[], width=450, state="readonly")
        self.cb_mecanico.grid(row=2, column=1, padx=5, pady=5)

        ctk.CTkLabel(frm1, text="Status:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.cb_status = ctk.CTkComboBox(frm1, values=["Aberta", "Em Andamento", "Concluída", "Cancelada"],
                                         width=450, state="readonly")
        self.cb_status.grid(row=3, column=1, padx=5, pady=5)
        self.cb_status.set("Aberta")

        frm2 = ctk.CTkFrame(tab)
        frm2.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(frm2, text="Problema relatado:").grid(row=0, column=0, sticky="nw", padx=5, pady=2)
        self.t_problema = ctk.CTkTextbox(frm2, height=70, width=900)
        self.t_problema.grid(row=0, column=1, padx=5, pady=2)

        ctk.CTkLabel(frm2, text="Serviços realizados:").grid(row=1, column=0, sticky="nw", padx=5, pady=2)
        self.t_servicos = ctk.CTkTextbox(frm2, height=70, width=900)
        self.t_servicos.grid(row=1, column=1, padx=5, pady=2)

        ctk.CTkLabel(frm2, text="Peças utilizadas:").grid(row=2, column=0, sticky="nw", padx=5, pady=2)
        self.t_pecas = ctk.CTkTextbox(frm2, height=70, width=900)
        self.t_pecas.grid(row=2, column=1, padx=5, pady=2)

        frm3 = ctk.CTkFrame(tab)
        frm3.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(frm3, text="Valor Mão de Obra (R$):").grid(row=0, column=0, padx=5)
        self.e_mo = ctk.CTkEntry(frm3, width=130)
        self.e_mo.grid(row=0, column=1, padx=5)
        self.e_mo.insert(0, "0.00")

        ctk.CTkLabel(frm3, text="Valor Peças (R$):").grid(row=0, column=2, padx=5)
        self.e_pc = ctk.CTkEntry(frm3, width=130)
        self.e_pc.grid(row=0, column=3, padx=5)
        self.e_pc.insert(0, "0.00")

        ctk.CTkButton(frm3, text="Salvar Ordem de Serviço", command=self._salvar_os,
                      fg_color="green", width=240, height=35).grid(row=0, column=4, padx=20)

        self._carregar_combos()

    def _carregar_combos(self):
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT id, nome, cpf_cnpj FROM clientes WHERE ativo=1 ORDER BY nome")
        self.clientes_map = {}
        lista = []
        for r in cur.fetchall():
            label = "{} - {} ({})".format(r[0], r[1], v.formatar_cpf_ou_cnpj(r[2]))
            self.clientes_map[label] = r[0]
            lista.append(label)
        self.cb_cliente.configure(values=lista)
        if lista:
            self.cb_cliente.set(lista[0])
            self._on_cliente(lista[0])

        cur.execute("""
            SELECT id, nome, cargo FROM funcionarios
            WHERE cargo IN ('Mecânico','Admin') AND ativo=1
            ORDER BY nome
        """)
        self.mec_map = {}
        lista_m = []
        for r in cur.fetchall():
            label = "{} - {} ({})".format(r[0], r[1], r[2])
            self.mec_map[label] = r[0]
            lista_m.append(label)
        self.cb_mecanico.configure(values=lista_m)
        if lista_m:
            self.cb_mecanico.set(lista_m[0])

        cur.close()
        conn.close()

    def _on_cliente(self, valor):
        cli_id = self.clientes_map.get(valor)
        if not cli_id:
            return
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, placa, marca, modelo FROM caminhoes
            WHERE cliente_id=%s ORDER BY placa
        """, (cli_id,))
        self.cam_map = {}
        lista = []
        for r in cur.fetchall():
            label = "{} - {} ({} {})".format(
                r[0], v.formatar_placa(r[1]), r[2] or '', r[3] or ''
            )
            self.cam_map[label] = r[0]
            lista.append(label)
        cur.close()
        conn.close()
        self.cb_caminhao.configure(values=lista)
        self.cb_caminhao.set(lista[0] if lista else '')

    def _salvar_os(self):
        cli_label = self.cb_cliente.get()
        cam_label = self.cb_caminhao.get()
        mec_label = self.cb_mecanico.get()
        if cli_label not in self.clientes_map:
            messagebox.showwarning("Atenção", "Selecione um cliente", parent=self)
            return
        if cam_label not in self.cam_map:
            messagebox.showwarning("Atenção", "Cliente não possui caminhões cadastrados", parent=self)
            return
        if mec_label not in self.mec_map:
            messagebox.showwarning("Atenção", "Selecione um mecânico", parent=self)
            return
        try:
            v_mo = v.parse_valor(self.e_mo.get())
            v_pc = v.parse_valor(self.e_pc.get())
        except ValueError as e:
            messagebox.showwarning("Atenção", str(e), parent=self)
            return

        v_total = round(v_mo + v_pc, 2)
        status = self.cb_status.get()
        data_fech = datetime.now() if status in ("Concluída", "Cancelada") else None

        try:
            conn = conectar()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO ordens_servico (caminhao_id, cliente_id, funcionario_id,
                    data_abertura, data_fechamento, descricao_problema,
                    servicos_realizados, pecas_utilizadas,
                    valor_mao_obra, valor_pecas, valor_total, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                self.cam_map[cam_label], self.clientes_map[cli_label], self.mec_map[mec_label],
                datetime.now(), data_fech,
                self.t_problema.get("1.0", "end").strip(),
                self.t_servicos.get("1.0", "end").strip(),
                self.t_pecas.get("1.0", "end").strip(),
                v_mo, v_pc, v_total, status
            ))
            os_id = cur.lastrowid
            conn.commit()

            # busca dados pra email
            cur.execute("""
                SELECT cl.nome, cl.email, ca.placa, f.nome
                FROM ordens_servico o
                JOIN clientes cl ON cl.id = o.cliente_id
                JOIN caminhoes ca ON ca.id = o.caminhao_id
                JOIN funcionarios f ON f.id = o.funcionario_id
                WHERE o.id=%s
            """, (os_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()

            if row and row[1]:  # tem email
                assunto, corpo = email_os_criada(row[0], os_id, v.formatar_placa(row[2]),
                                                 self.t_problema.get("1.0", "end").strip(),
                                                 row[3])
                enviar_email(row[1], assunto, corpo)
                messagebox.showinfo("OK",
                    "Ordem de serviço #{:06d} criada!\nEmail enviado para {}".format(os_id, row[1]),
                    parent=self)
            else:
                messagebox.showinfo("OK",
                    "Ordem de serviço #{:06d} criada!\n(Cliente sem email cadastrado)".format(os_id),
                    parent=self)

            self._limpar_nova()
            # recarregar consulta
            self._listar_todas()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def _limpar_nova(self):
        self.t_problema.delete("1.0", "end")
        self.t_servicos.delete("1.0", "end")
        self.t_pecas.delete("1.0", "end")
        self.e_mo.delete(0, "end"); self.e_mo.insert(0, "0.00")
        self.e_pc.delete(0, "end"); self.e_pc.insert(0, "0.00")
        self.cb_status.set("Aberta")

    # =================== CONSULTA ===================
    def _aba_consulta(self):
        tab = self.tabs.tab("Consultar OS")

        frm = ctk.CTkFrame(tab)
        frm.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(frm, text="Buscar por placa ou nome do cliente:").pack(side="left", padx=5)
        self.e_busca_os = ctk.CTkEntry(frm, width=300)
        self.e_busca_os.pack(side="left", padx=5)
        self.e_busca_os.bind("<Return>", lambda e: self._consultar())
        ctk.CTkButton(frm, text="Buscar", command=self._consultar).pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Listar Todas", command=self._listar_todas).pack(side="left", padx=5)

        cols = ("ID", "Data Abertura", "Placa", "Cliente", "Mecânico", "Status", "Total")
        self.tree_os = ttk.Treeview(tab, columns=cols, show="headings", height=15)
        for c, w in zip(cols, [60, 150, 100, 220, 180, 120, 100]):
            self.tree_os.heading(c, text=c)
            self.tree_os.column(c, width=w)
        self.tree_os.pack(fill="both", expand=True, padx=5, pady=5)

        frm_btn = ctk.CTkFrame(tab)
        frm_btn.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(frm_btn, text="🖨  Imprimir OS (PDF)", command=self._imprimir_pdf,
                      fg_color="green", width=220, height=42,
                      font=("Arial", 13, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(frm_btn, text="Ver Detalhes", command=self._ver_detalhes,
                      width=150, height=42).pack(side="left", padx=5)
        if self.usuario['cargo'] == 'Admin':
            ctk.CTkButton(frm_btn, text="Excluir OS", command=self._excluir_os,
                          fg_color="darkred", width=150, height=42).pack(side="left", padx=5)

        self._listar_todas()

    def _consultar(self):
        termo = self.e_busca_os.get().strip()
        if not termo:
            self._listar_todas()
            return
        # tenta dois formatos de placa: o digitado e sem hífen
        termo_norm = termo.upper().replace('-', '').replace(' ', '')
        like1 = "%" + termo + "%"
        like2 = "%" + termo_norm + "%"
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id, o.data_abertura, ca.placa, cl.nome, f.nome, o.status, o.valor_total
            FROM ordens_servico o
            JOIN caminhoes ca ON ca.id = o.caminhao_id
            JOIN clientes cl ON cl.id = o.cliente_id
            JOIN funcionarios f ON f.id = o.funcionario_id
            WHERE ca.placa LIKE %s OR ca.placa LIKE %s OR cl.nome LIKE %s
            ORDER BY o.data_abertura DESC LIMIT 500
        """, (like2, like1, like1))
        self._preencher(cur.fetchall())
        cur.close()
        conn.close()

    def _listar_todas(self):
        if not hasattr(self, 'tree_os'):
            return
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id, o.data_abertura, ca.placa, cl.nome, f.nome, o.status, o.valor_total
            FROM ordens_servico o
            JOIN caminhoes ca ON ca.id = o.caminhao_id
            JOIN clientes cl ON cl.id = o.cliente_id
            JOIN funcionarios f ON f.id = o.funcionario_id
            ORDER BY o.data_abertura DESC LIMIT 500
        """)
        self._preencher(cur.fetchall())
        cur.close()
        conn.close()

    def _preencher(self, registros):
        for i in self.tree_os.get_children():
            self.tree_os.delete(i)
        for r in registros:
            data_str = r[1].strftime('%d/%m/%Y %H:%M') if r[1] else ''
            total_str = 'R$ {:.2f}'.format(float(r[6] or 0))
            self.tree_os.insert("", "end", values=(
                r[0], data_str, v.formatar_placa(r[2]), r[3], r[4], r[5], total_str
            ))

    def _os_id_selecionada(self):
        sel = self.tree_os.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma OS na lista", parent=self)
            return None
        return int(self.tree_os.item(sel[0], "values")[0])

    def _buscar_dados_os(self, os_id):
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id, o.data_abertura, o.data_fechamento, o.descricao_problema,
                   o.servicos_realizados, o.pecas_utilizadas, o.valor_mao_obra,
                   o.valor_pecas, o.valor_total, o.status,
                   cl.nome, cl.cpf_cnpj, cl.telefone, cl.email,
                   cl.cep, cl.logradouro, cl.numero, cl.complemento,
                   cl.bairro, cl.cidade, cl.estado,
                   ca.placa, ca.marca, ca.modelo, ca.ano, ca.cor, ca.chassi,
                   f.nome, o.cliente_id, o.funcionario_id
            FROM ordens_servico o
            JOIN clientes cl ON cl.id = o.cliente_id
            JOIN caminhoes ca ON ca.id = o.caminhao_id
            JOIN funcionarios f ON f.id = o.funcionario_id
            WHERE o.id=%s
        """, (os_id,))
        r = cur.fetchone()
        cur.close()
        conn.close()
        if not r:
            return None
        return {
            'id': r[0], 'data_abertura': r[1], 'data_fechamento': r[2],
            'descricao_problema': r[3], 'servicos_realizados': r[4],
            'pecas_utilizadas': r[5],
            'valor_mao_obra': r[6], 'valor_pecas': r[7], 'valor_total': r[8],
            'status': r[9],
            'cliente_nome': r[10], 'cliente_cpf': r[11],
            'cliente_telefone': r[12], 'cliente_email': r[13],
            'cliente_cep': r[14], 'cliente_logradouro': r[15],
            'cliente_numero': r[16], 'cliente_complemento': r[17],
            'cliente_bairro': r[18], 'cliente_cidade': r[19], 'cliente_estado': r[20],
            'placa': r[21], 'marca': r[22], 'modelo': r[23],
            'ano': r[24], 'cor': r[25], 'chassi': r[26],
            'funcionario_nome': r[27],
            'cliente_id': r[28], 'funcionario_id': r[29],
        }

    def _imprimir_pdf(self):
        os_id = self._os_id_selecionada()
        if not os_id:
            return
        dados = self._buscar_dados_os(os_id)
        if not dados:
            messagebox.showerror("Erro", "OS não encontrada", parent=self)
            return
        nome = "OS_{:06d}.pdf".format(os_id)
        caminho = filedialog.asksaveasfilename(
            parent=self, defaultextension=".pdf",
            initialfile=nome, filetypes=[("PDF", "*.pdf")]
        )
        if not caminho:
            return
        try:
            gerar_pdf_os(dados, caminho)
            messagebox.showinfo("OK", "PDF gerado:\n" + caminho, parent=self)
            try:
                if sys.platform.startswith('win'):
                    os.startfile(caminho)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', caminho])
                else:
                    subprocess.run(['xdg-open', caminho])
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erro", "Falha ao gerar PDF: " + str(e), parent=self)

    def _ver_detalhes(self):
        os_id = self._os_id_selecionada()
        if not os_id:
            return
        d = self._buscar_dados_os(os_id)
        if not d:
            return
        win = ctk.CTkToplevel(self)
        win.title("Detalhes OS #{:06d}".format(os_id))
        win.geometry("700x600")
        win.grab_set()
        txt = ctk.CTkTextbox(win, wrap="word")
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        linhas = [
            "==== ORDEM DE SERVIÇO #{:06d} ====".format(d['id']),
            "Status: " + str(d['status']),
            "Abertura: " + (d['data_abertura'].strftime('%d/%m/%Y %H:%M') if d['data_abertura'] else '---'),
            "Fechamento: " + (d['data_fechamento'].strftime('%d/%m/%Y %H:%M') if d['data_fechamento'] else '---'),
            "",
            "-- CLIENTE --",
            "Nome: " + (d['cliente_nome'] or ''),
            "Documento: " + v.formatar_cpf_ou_cnpj(d['cliente_cpf'] or ''),
            "Telefone: " + v.formatar_telefone(d['cliente_telefone'] or ''),
            "Email: " + (d['cliente_email'] or '---'),
            "",
            "-- VEÍCULO --",
            "Placa: " + v.formatar_placa(d['placa'] or ''),
            "Marca/Modelo: {} {}".format(d['marca'] or '', d['modelo'] or ''),
            "Ano: " + str(d['ano'] or ''),
            "Chassi: " + (d['chassi'] or ''),
            "",
            "-- MECÂNICO --",
            d['funcionario_nome'] or '',
            "",
            "-- PROBLEMA --",
            d['descricao_problema'] or '---',
            "",
            "-- SERVIÇOS --",
            d['servicos_realizados'] or '---',
            "",
            "-- PEÇAS --",
            d['pecas_utilizadas'] or '---',
            "",
            "-- VALORES --",
            "Mão de obra: R$ {:.2f}".format(float(d['valor_mao_obra'] or 0)),
            "Peças: R$ {:.2f}".format(float(d['valor_pecas'] or 0)),
            "TOTAL: R$ {:.2f}".format(float(d['valor_total'] or 0)),
        ]
        txt.insert("1.0", "\n".join(linhas))
        txt.configure(state="disabled")

    def _excluir_os(self):
        os_id = self._os_id_selecionada()
        if not os_id:
            return
        if not messagebox.askyesno("Confirmar", "Excluir OS #{:06d}?".format(os_id), parent=self):
            return
        try:
            conn = conectar()
            cur = conn.cursor()
            cur.execute("DELETE FROM ordens_servico WHERE id=%s", (os_id,))
            conn.commit()
            cur.close()
            conn.close()
            self._listar_todas()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    # =================== EDITAR ===================
    def _aba_editar(self):
        tab = self.tabs.tab("Editar OS")

        topo = ctk.CTkFrame(tab)
        topo.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(topo, text="Nº da OS:").pack(side="left", padx=5)
        self.e_os_edit = ctk.CTkEntry(topo, width=120)
        self.e_os_edit.pack(side="left", padx=5)
        ctk.CTkButton(topo, text="Carregar", command=self._carregar_edit).pack(side="left", padx=5)
        self.lbl_info_edit = ctk.CTkLabel(topo, text="", font=("Arial", 11, "bold"))
        self.lbl_info_edit.pack(side="left", padx=15)

        frm = ctk.CTkFrame(tab)
        frm.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(frm, text="Status:").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        self.cb_status_edit = ctk.CTkComboBox(frm,
            values=["Aberta", "Em Andamento", "Concluída", "Cancelada"],
            width=300, state="readonly")
        self.cb_status_edit.grid(row=0, column=1, sticky="w", padx=5, pady=4)

        ctk.CTkLabel(frm, text="Serviços realizados:").grid(row=1, column=0, sticky="nw", padx=5)
        self.t_serv_edit = ctk.CTkTextbox(frm, height=80, width=850)
        self.t_serv_edit.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(frm, text="Peças utilizadas:").grid(row=2, column=0, sticky="nw", padx=5)
        self.t_pec_edit = ctk.CTkTextbox(frm, height=80, width=850)
        self.t_pec_edit.grid(row=2, column=1, padx=5, pady=5)

        ctk.CTkLabel(frm, text="Mão de obra (R$):").grid(row=3, column=0, sticky="e", padx=5)
        self.e_mo_edit = ctk.CTkEntry(frm, width=130)
        self.e_mo_edit.grid(row=3, column=1, sticky="w", padx=5, pady=4)

        ctk.CTkLabel(frm, text="Peças (R$):").grid(row=4, column=0, sticky="e", padx=5)
        self.e_pc_edit = ctk.CTkEntry(frm, width=130)
        self.e_pc_edit.grid(row=4, column=1, sticky="w", padx=5, pady=4)

        ctk.CTkButton(frm, text="Salvar Alterações", command=self._salvar_edit,
                      fg_color="green", width=240, height=40,
                      font=("Arial", 13, "bold")).grid(row=5, column=1, sticky="w", padx=5, pady=10)

        self.os_em_edicao = None

    def _carregar_edit(self):
        txt = self.e_os_edit.get().strip()
        if not txt.isdigit():
            messagebox.showwarning("Atenção", "Informe o número da OS", parent=self)
            return
        d = self._buscar_dados_os(int(txt))
        if not d:
            messagebox.showerror("Erro", "OS não encontrada", parent=self)
            self.os_em_edicao = None
            self.lbl_info_edit.configure(text="")
            return
        if self.usuario['cargo'] == 'Mecânico' and d['funcionario_id'] != self.usuario['id']:
            messagebox.showwarning("Permissão",
                "Você só pode editar OS atribuídas a você", parent=self)
            self.os_em_edicao = None
            return
        self.os_em_edicao = d
        self.lbl_info_edit.configure(
            text="OS #{:06d} | {} | Placa {}".format(d['id'], d['cliente_nome'],
                                                     v.formatar_placa(d['placa']))
        )
        self.cb_status_edit.set(d['status'])
        self.t_serv_edit.delete("1.0", "end")
        self.t_serv_edit.insert("1.0", d['servicos_realizados'] or '')
        self.t_pec_edit.delete("1.0", "end")
        self.t_pec_edit.insert("1.0", d['pecas_utilizadas'] or '')
        self.e_mo_edit.delete(0, "end"); self.e_mo_edit.insert(0, str(d['valor_mao_obra'] or 0))
        self.e_pc_edit.delete(0, "end"); self.e_pc_edit.insert(0, str(d['valor_pecas'] or 0))

    def _salvar_edit(self):
        if not self.os_em_edicao:
            messagebox.showwarning("Atenção", "Carregue uma OS primeiro", parent=self)
            return
        try:
            v_mo = v.parse_valor(self.e_mo_edit.get())
            v_pc = v.parse_valor(self.e_pc_edit.get())
        except ValueError as e:
            messagebox.showwarning("Atenção", str(e), parent=self)
            return

        v_total = round(v_mo + v_pc, 2)
        novo_status = self.cb_status_edit.get()
        status_antigo = self.os_em_edicao['status']

        data_fech = self.os_em_edicao['data_fechamento']
        if novo_status in ("Concluída", "Cancelada") and not data_fech:
            data_fech = datetime.now()
        elif novo_status not in ("Concluída", "Cancelada"):
            data_fech = None

        try:
            conn = conectar()
            cur = conn.cursor()
            cur.execute("""
                UPDATE ordens_servico SET status=%s, data_fechamento=%s,
                    servicos_realizados=%s, pecas_utilizadas=%s,
                    valor_mao_obra=%s, valor_pecas=%s, valor_total=%s
                WHERE id=%s
            """, (novo_status, data_fech,
                  self.t_serv_edit.get("1.0", "end").strip(),
                  self.t_pec_edit.get("1.0", "end").strip(),
                  v_mo, v_pc, v_total, self.os_em_edicao['id']))
            conn.commit()
            cur.close()
            conn.close()

            # email se mudou status
            if novo_status != status_antigo and self.os_em_edicao['cliente_email']:
                assunto, corpo = email_os_atualizada(
                    self.os_em_edicao['cliente_nome'],
                    self.os_em_edicao['id'],
                    v.formatar_placa(self.os_em_edicao['placa']),
                    novo_status, v_total
                )
                enviar_email(self.os_em_edicao['cliente_email'], assunto, corpo)

            messagebox.showinfo("OK", "Alterações salvas!", parent=self)
            self._listar_todas()
            self._carregar_edit()  # recarrega
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)
