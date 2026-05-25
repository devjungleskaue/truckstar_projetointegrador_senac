"""
Painel do cliente (somente leitura).
Mostra dados do cliente, lista de veículos e lista de OS dele.
Permite baixar PDF da OS.
"""
import os
import sys
import subprocess
import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog

from db import conectar
from pdf_os import gerar_pdf_os
import validacoes as v


class PainelCliente(ctk.CTkToplevel):
    def __init__(self, master, cliente):
        super().__init__(master)
        self.cliente = cliente  # dict id, nome, cpf, email
        self.master_win = master
        self.title("Truckstar - Portal do Cliente")
        self.geometry("1000x680")
        self.protocol("WM_DELETE_WINDOW", self.sair)

        # cabeçalho
        topo = ctk.CTkFrame(self, height=70)
        topo.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(topo, text="TRUCKSTAR", font=("Arial", 22, "bold"),
                     text_color="#4a9eff").pack(side="left", padx=15)
        ctk.CTkLabel(topo, text="Bem-vindo(a), " + cliente['nome'],
                     font=("Arial", 13)).pack(side="left", padx=20)
        ctk.CTkButton(topo, text="Sair", command=self.sair,
                      fg_color="darkred", width=80).pack(side="right", padx=15)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)
        tabs.add("Meus Dados")
        tabs.add("Meus Veículos")
        tabs.add("Minhas Ordens de Serviço")

        self._aba_dados(tabs.tab("Meus Dados"))
        self._aba_veiculos(tabs.tab("Meus Veículos"))
        self._aba_os(tabs.tab("Minhas Ordens de Serviço"))

    def _aba_dados(self, tab):
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT nome, cpf_cnpj, telefone, email, cep, logradouro, numero,
                   complemento, bairro, cidade, estado
            FROM clientes WHERE id=%s
        """, (self.cliente['id'],))
        r = cur.fetchone()
        cur.close()
        conn.close()

        frm = ctk.CTkFrame(tab)
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frm, text="Dados Cadastrais",
                     font=("Arial", 18, "bold")).pack(pady=10)

        if not r:
            ctk.CTkLabel(frm, text="Dados não encontrados").pack()
            return

        endereco = ', '.join(filter(None, [
            r[5] or '', (r[6] or ''), (r[7] or ''), (r[8] or ''),
            "{}/{}".format(r[9] or '', r[10] or '').strip('/'),
            "CEP " + v.formatar_cep(r[4] or '') if r[4] else ''
        ]))

        infos = [
            ("Nome:", r[0]),
            ("CPF/CNPJ:", v.formatar_cpf_ou_cnpj(r[1] or '')),
            ("Telefone:", v.formatar_telefone(r[2] or '')),
            ("Email:", r[3] or '---'),
            ("Endereço:", endereco or '---'),
        ]
        for lbl, val in infos:
            linha = ctk.CTkFrame(frm, fg_color="transparent")
            linha.pack(fill="x", pady=4, padx=20)
            ctk.CTkLabel(linha, text=lbl, font=("Arial", 12, "bold"),
                         width=120, anchor="e").pack(side="left", padx=5)
            ctk.CTkLabel(linha, text=val, font=("Arial", 12),
                         anchor="w").pack(side="left", padx=5)

        ctk.CTkLabel(frm, text="\nPara atualizar seus dados, entre em contato com a Truckstar.",
                     font=("Arial", 10), text_color="gray").pack(pady=10)

    def _aba_veiculos(self, tab):
        ctk.CTkLabel(tab, text="Meus Veículos Cadastrados",
                     font=("Arial", 16, "bold")).pack(pady=10)

        cols = ("ID", "Placa", "Marca", "Modelo", "Ano", "Cor")
        tree = ttk.Treeview(tab, columns=cols, show="headings", height=15)
        for c, w in zip(cols, [60, 110, 130, 200, 80, 110]):
            tree.heading(c, text=c)
            tree.column(c, width=w)
        tree.pack(fill="both", expand=True, padx=15, pady=10)

        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, placa, marca, modelo, ano, cor FROM caminhoes
            WHERE cliente_id=%s ORDER BY placa
        """, (self.cliente['id'],))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            ctk.CTkLabel(tab, text="\nNenhum veículo cadastrado.\nContate a Truckstar para cadastrar.",
                         font=("Arial", 12), text_color="gray").pack(pady=10)
        for r in rows:
            tree.insert("", "end", values=(
                r[0], v.formatar_placa(r[1]), r[2] or '', r[3] or '',
                r[4] or '', r[5] or ''
            ))

    def _aba_os(self, tab):
        ctk.CTkLabel(tab, text="Histórico de Ordens de Serviço",
                     font=("Arial", 16, "bold")).pack(pady=10)

        cols = ("ID", "Data", "Placa", "Mecânico", "Status", "Total")
        self.tree_os = ttk.Treeview(tab, columns=cols, show="headings", height=15)
        for c, w in zip(cols, [60, 150, 110, 200, 130, 120]):
            self.tree_os.heading(c, text=c)
            self.tree_os.column(c, width=w)
        self.tree_os.pack(fill="both", expand=True, padx=15, pady=10)

        frm = ctk.CTkFrame(tab)
        frm.pack(fill="x", padx=15, pady=10)
        ctk.CTkButton(frm, text="🖨  Baixar PDF da OS", command=self._baixar_pdf,
                      fg_color="green", height=40, width=200,
                      font=("Arial", 13, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Ver Detalhes", command=self._ver_detalhes,
                      height=40, width=150).pack(side="left", padx=5)
        ctk.CTkButton(frm, text="Atualizar Lista", command=self._listar_os,
                      height=40, width=150).pack(side="left", padx=5)

        self._listar_os()

    def _listar_os(self):
        for i in self.tree_os.get_children():
            self.tree_os.delete(i)
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id, o.data_abertura, ca.placa, f.nome, o.status, o.valor_total
            FROM ordens_servico o
            JOIN caminhoes ca ON ca.id = o.caminhao_id
            JOIN funcionarios f ON f.id = o.funcionario_id
            WHERE o.cliente_id=%s
            ORDER BY o.data_abertura DESC
        """, (self.cliente['id'],))
        for r in cur.fetchall():
            data_str = r[1].strftime('%d/%m/%Y %H:%M') if r[1] else ''
            self.tree_os.insert("", "end", values=(
                r[0], data_str, v.formatar_placa(r[2]),
                r[3], r[4], 'R$ {:.2f}'.format(float(r[5] or 0))
            ))
        cur.close()
        conn.close()

    def _os_id_selecionada(self):
        sel = self.tree_os.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma OS", parent=self)
            return None
        return int(self.tree_os.item(sel[0], "values")[0])

    def _buscar_dados_os(self, os_id):
        conn = conectar()
        cur = conn.cursor()
        # também filtra por cliente_id pra impedir acesso a OS de outros
        cur.execute("""
            SELECT o.id, o.data_abertura, o.data_fechamento, o.descricao_problema,
                   o.servicos_realizados, o.pecas_utilizadas, o.valor_mao_obra,
                   o.valor_pecas, o.valor_total, o.status,
                   cl.nome, cl.cpf_cnpj, cl.telefone, cl.email,
                   cl.cep, cl.logradouro, cl.numero, cl.complemento,
                   cl.bairro, cl.cidade, cl.estado,
                   ca.placa, ca.marca, ca.modelo, ca.ano, ca.cor, ca.chassi,
                   f.nome
            FROM ordens_servico o
            JOIN clientes cl ON cl.id = o.cliente_id
            JOIN caminhoes ca ON ca.id = o.caminhao_id
            JOIN funcionarios f ON f.id = o.funcionario_id
            WHERE o.id=%s AND o.cliente_id=%s
        """, (os_id, self.cliente['id']))
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
        }

    def _baixar_pdf(self):
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
            messagebox.showinfo("OK", "PDF salvo:\n" + caminho, parent=self)
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
            messagebox.showerror("Erro", str(e), parent=self)

    def _ver_detalhes(self):
        os_id = self._os_id_selecionada()
        if not os_id:
            return
        d = self._buscar_dados_os(os_id)
        if not d:
            return
        win = ctk.CTkToplevel(self)
        win.title("OS #{:06d}".format(os_id))
        win.geometry("650x550")
        win.grab_set()
        txt = ctk.CTkTextbox(win, wrap="word")
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        linhas = [
            "==== ORDEM DE SERVIÇO #{:06d} ====".format(d['id']),
            "Status: " + d['status'],
            "Abertura: " + (d['data_abertura'].strftime('%d/%m/%Y %H:%M') if d['data_abertura'] else '---'),
            "Fechamento: " + (d['data_fechamento'].strftime('%d/%m/%Y %H:%M') if d['data_fechamento'] else '---'),
            "",
            "Veículo: {} - {} {}".format(
                v.formatar_placa(d['placa']), d['marca'] or '', d['modelo'] or ''),
            "Mecânico: " + (d['funcionario_nome'] or ''),
            "",
            "PROBLEMA:",
            d['descricao_problema'] or '---',
            "",
            "SERVIÇOS:",
            d['servicos_realizados'] or '---',
            "",
            "PEÇAS:",
            d['pecas_utilizadas'] or '---',
            "",
            "Mão de obra: R$ {:.2f}".format(float(d['valor_mao_obra'] or 0)),
            "Peças: R$ {:.2f}".format(float(d['valor_pecas'] or 0)),
            "TOTAL: R$ {:.2f}".format(float(d['valor_total'] or 0)),
        ]
        txt.insert("1.0", "\n".join(linhas))
        txt.configure(state="disabled")

    def sair(self):
        self.destroy()
        try:
            self.master_win.deiconify()
            self.master_win.limpar_campos()
        except Exception:
            pass
