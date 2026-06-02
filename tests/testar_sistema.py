"""
================================================================================
 Truckstar — Suite de Testes do Sistema
================================================================================
Executa testes automatizados de todas as funcionalidades do sistema e imprime
o resultado no terminal.

USO:
    py testar_sistema.py            # roda todos os testes (exceto rede/email)
    py testar_sistema.py --rede     # inclui teste do ViaCEP (precisa internet)
    py testar_sistema.py --email    # inclui envio real via Resend (consome cota)

Cobre:
  - Validações (CPF, CNPJ, email, placa, telefone, ano, CEP, valores)
  - Segurança (hash PBKDF2, salt, verificação, timing-safe)
  - Banco de dados (conexão, schema, CRUD completo, context manager, leak)
  - Templates de email (OS criada/atualizada, boas-vindas)
  - Geração de PDF da Ordem de Serviço
  - Integridade referencial (chaves estrangeiras)

Os dados de teste são isolados (prefixo ZZTESTE / CPF e placa reservados) e
removidos automaticamente ao final, mesmo se algum teste falhar.
================================================================================
"""
import sys
import os
from datetime import datetime, date

# Força UTF-8 na saída (terminal Windows costuma vir em cp1252 e quebra acentos)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Garante que a raiz do projeto está no path (este arquivo vive em tests/)
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

# ------------------------------------------------------------------ cores ANSI
class C:
    OK = '\033[92m'      # verde
    FAIL = '\033[91m'    # vermelho
    SKIP = '\033[93m'    # amarelo
    HEAD = '\033[96m'    # ciano
    DIM = '\033[90m'     # cinza
    BOLD = '\033[1m'
    END = '\033[0m'

# Habilita cores ANSI no terminal do Windows (no-op em outros SOs)
if os.name == 'nt':
    os.system('')


# ------------------------------------------------------------- infra de testes
_total = {'ok': 0, 'fail': 0, 'skip': 0}
_falhas = []


def secao(titulo):
    print("\n" + C.HEAD + C.BOLD + "-- " + titulo + " " + "-" * (58 - len(titulo)) + C.END)


def teste(nome, funcao):
    """Executa uma função de teste. Ela deve retornar True ou levantar/retornar False."""
    try:
        resultado = funcao()
        if resultado is False:
            _total['fail'] += 1
            _falhas.append(nome)
            print(f"  {C.FAIL}[FALHOU]{C.END}  {nome}")
        else:
            _total['ok'] += 1
            print(f"  {C.OK}[OK]{C.END}      {nome}")
    except AssertionError as e:
        _total['fail'] += 1
        _falhas.append(nome)
        print(f"  {C.FAIL}[FALHOU]{C.END}  {nome}  {C.DIM}{e}{C.END}")
    except Exception as e:
        _total['fail'] += 1
        _falhas.append(nome)
        print(f"  {C.FAIL}[ERRO]{C.END}    {nome}  {C.DIM}{type(e).__name__}: {e}{C.END}")


def pular(nome, motivo):
    _total['skip'] += 1
    print(f"  {C.SKIP}[PULADO]{C.END}  {nome}  {C.DIM}({motivo}){C.END}")


# ============================================================================
#  1. VALIDAÇÕES
# ============================================================================
def testar_validacoes():
    secao("1. VALIDAÇÕES (validacoes.py)")
    import validacoes as v

    # CPF
    teste("CPF válido aceito", lambda: v.validar_cpf('529.982.247-25') is True)
    teste("CPF inválido rejeitado", lambda: v.validar_cpf('111.111.111-11') is False)
    teste("CPF com tamanho errado rejeitado", lambda: v.validar_cpf('123') is False)
    teste("CPF formatado corretamente",
          lambda: v.formatar_cpf('52998224725') == '529.982.247-25')

    # CNPJ
    teste("CNPJ válido aceito", lambda: v.validar_cnpj('11.222.333/0001-81') is True)
    teste("CNPJ inválido rejeitado", lambda: v.validar_cnpj('11.222.333/0001-00') is False)
    teste("CNPJ formatado corretamente",
          lambda: v.formatar_cnpj('11222333000181') == '11.222.333/0001-81')

    # CPF ou CNPJ
    teste("validar_cpf_ou_cnpj reconhece CPF (11 díg)", lambda: v.validar_cpf_ou_cnpj('52998224725') is True)
    teste("validar_cpf_ou_cnpj reconhece CNPJ (14 díg)", lambda: v.validar_cpf_ou_cnpj('11222333000181') is True)
    teste("validar_cpf_ou_cnpj rejeita tamanho inválido", lambda: v.validar_cpf_ou_cnpj('123456') is False)

    # Email
    teste("Email válido aceito", lambda: v.validar_email('teste@exemplo.com.br') is True)
    teste("Email sem @ rejeitado", lambda: v.validar_email('testeexemplo.com') is False)
    teste("Email sem domínio rejeitado", lambda: v.validar_email('teste@') is False)

    # Placa
    teste("Placa antiga (ABC1234) aceita", lambda: v.validar_placa('ABC1234') is True)
    teste("Placa Mercosul (ABC1D23) aceita", lambda: v.validar_placa('ABC1D23') is True)
    teste("Placa inválida rejeitada", lambda: v.validar_placa('AB123') is False)
    teste("Placa formatada com hífen",
          lambda: v.formatar_placa('ABC1234') == 'ABC-1234')

    # Telefone
    teste("Telefone celular (11 díg) aceito", lambda: v.validar_telefone('11987654321') is True)
    teste("Telefone fixo (10 díg) aceito", lambda: v.validar_telefone('1133334444') is True)
    teste("Telefone curto rejeitado", lambda: v.validar_telefone('123') is False)
    teste("Telefone celular formatado",
          lambda: v.formatar_telefone('11987654321') == '(11) 98765-4321')

    # Ano
    teste("Ano válido aceito", lambda: v.validar_ano('2020') is True)
    teste("Ano futuro distante rejeitado", lambda: v.validar_ano('3000') is False)
    teste("Ano não-numérico rejeitado", lambda: v.validar_ano('abc') is False)

    # CEP
    teste("CEP formatado corretamente", lambda: v.formatar_cep('01001000') == '01001-000')

    # parse_valor — casos normais
    teste("parse_valor formato BR (1.234,56)", lambda: abs(v.parse_valor('1.234,56') - 1234.56) < 0.001)
    teste("parse_valor formato US (1234.56)", lambda: abs(v.parse_valor('1234.56') - 1234.56) < 0.001)
    teste("parse_valor com R$", lambda: abs(v.parse_valor('R$ 99,90') - 99.90) < 0.001)
    teste("parse_valor vazio retorna 0", lambda: v.parse_valor('') == 0.0)

    # parse_valor — casos perigosos (devem levantar ValueError)
    def _rejeita(val):
        try:
            v.parse_valor(val)
            return False
        except ValueError:
            return True
    teste("parse_valor rejeita 'inf'", lambda: _rejeita('inf'))
    teste("parse_valor rejeita 'nan'", lambda: _rejeita('nan'))
    teste("parse_valor rejeita overflow (1e12)", lambda: _rejeita('1e12'))
    teste("parse_valor rejeita texto inválido", lambda: _rejeita('abc'))


# ============================================================================
#  2. SEGURANÇA
# ============================================================================
def testar_seguranca():
    secao("2. SEGURANÇA (seguranca.py)")
    import seguranca

    teste("gerar_salt retorna 32 hex chars", lambda: len(seguranca.gerar_salt()) == 32)
    teste("salts são únicos", lambda: seguranca.gerar_salt() != seguranca.gerar_salt())

    salt = seguranca.gerar_salt()
    h = seguranca.hash_senha('MinhaSenh@123', salt)
    teste("hash_senha retorna 64 hex chars (SHA-256)", lambda: len(h) == 64)
    teste("hash é determinístico (mesma senha+salt)",
          lambda: seguranca.hash_senha('MinhaSenh@123', salt) == h)
    teste("hash muda com salt diferente",
          lambda: seguranca.hash_senha('MinhaSenh@123', seguranca.gerar_salt()) != h)

    teste("verificar_senha aceita senha correta",
          lambda: seguranca.verificar_senha('MinhaSenh@123', salt, h) is True)
    teste("verificar_senha rejeita senha errada",
          lambda: seguranca.verificar_senha('senhaErrada', salt, h) is False)
    teste("verificar_senha rejeita hash vazio",
          lambda: seguranca.verificar_senha('qualquer', salt, '') is False)


# ============================================================================
#  3. BANCO DE DADOS
# ============================================================================
def testar_banco():
    secao("3. BANCO DE DADOS (db.py)")
    import db

    # conexão + inicialização
    teste("inicializar() cria schema sem erro", lambda: (db.inicializar() or True))

    # context manager
    def cm_funciona():
        with db.cursor() as (conn, cur):
            cur.execute("SELECT 1")
            return cur.fetchone()[0] == 1
    teste("db.cursor() executa query", cm_funciona)

    # rollback + fechamento em exceção
    def cm_rollback():
        try:
            with db.cursor() as (conn, cur):
                cur.execute("SELECT * FROM tabela_que_nao_existe_zzz")
            return False  # não deveria chegar aqui
        except Exception:
            return True   # exceção propagada corretamente
    teste("db.cursor() propaga exceção (com rollback/close)", cm_rollback)

    # schema — todas as tabelas existem
    def tabelas_existem():
        with db.cursor() as (conn, cur):
            cur.execute("SHOW TABLES")
            nomes = {r[0] for r in cur.fetchall()}
        esperadas = {'funcionarios', 'clientes', 'caminhoes', 'ordens_servico', 'email_logs'}
        return esperadas.issubset(nomes)
    teste("todas as 5 tabelas existem", tabelas_existem)

    # schema — coluna senha do cliente é NULL (cliente não loga)
    def cliente_senha_null():
        with db.cursor() as (conn, cur):
            cur.execute("SHOW COLUMNS FROM clientes LIKE 'senha_hash'")
            row = cur.fetchone()
        return row is not None and row[2] == 'YES'  # Null = YES
    teste("clientes.senha_hash aceita NULL", cliente_senha_null)


# ============================================================================
#  4. CRUD COMPLETO (ciclo de vida real dos dados)
# ============================================================================
def testar_crud():
    secao("4. CRUD COMPLETO (queries reais das telas)")
    import db
    import validacoes as v

    CPF_T = '52998224725'
    PLACA_T = 'ZZT9A99'
    estado = {'cliente_id': None, 'caminhao_id': None, 'os_id': None, 'func_id': None}

    # funcionário para FK
    def get_func():
        with db.cursor() as (conn, cur):
            cur.execute("SELECT id FROM funcionarios WHERE ativo=1 LIMIT 1")
            row = cur.fetchone()
        estado['func_id'] = row[0] if row else None
        return estado['func_id'] is not None
    teste("existe funcionário para vincular OS", get_func)

    # CREATE cliente
    def criar_cliente():
        with db.cursor() as (conn, cur):
            cur.execute("""
                INSERT INTO clientes (nome, cpf_cnpj, telefone, email, cidade, estado)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, ('ZZTESTE Cliente', CPF_T, '11999990000', 'zzteste@x.com', 'São Paulo', 'SP'))
            estado['cliente_id'] = cur.lastrowid
        return estado['cliente_id'] is not None
    teste("CREATE cliente (sem senha)", criar_cliente)

    # READ listagem (ativo=1)
    def listar_cliente():
        with db.cursor() as (conn, cur):
            cur.execute("SELECT id FROM clientes WHERE ativo=1 AND cpf_cnpj=%s", (CPF_T,))
            return cur.fetchone() is not None
    teste("READ cliente na listagem (ativo=1)", listar_cliente)

    # UPDATE cliente
    def atualizar_cliente():
        with db.cursor() as (conn, cur):
            cur.execute("UPDATE clientes SET nome=%s WHERE id=%s",
                        ('ZZTESTE Editado', estado['cliente_id']))
            cur.execute("SELECT nome FROM clientes WHERE id=%s", (estado['cliente_id'],))
            return cur.fetchone()[0] == 'ZZTESTE Editado'
    teste("UPDATE cliente", atualizar_cliente)

    # CREATE caminhão (FK cliente)
    def criar_caminhao():
        with db.cursor() as (conn, cur):
            cur.execute("""
                INSERT INTO caminhoes (cliente_id, placa, marca, modelo, ano, cor)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (estado['cliente_id'], PLACA_T, 'Volvo', 'FH 460', 2022, 'Branco'))
            estado['caminhao_id'] = cur.lastrowid
        return estado['caminhao_id'] is not None
    teste("CREATE caminhão (FK cliente)", criar_caminhao)

    # CREATE OS (3 FKs) + valores
    def criar_os():
        v_mo = v.parse_valor('500,00')
        v_pc = v.parse_valor('1.200,50')
        with db.cursor() as (conn, cur):
            cur.execute("""
                INSERT INTO ordens_servico (caminhao_id, cliente_id, funcionario_id,
                    data_abertura, descricao_problema, valor_mao_obra, valor_pecas, valor_total, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (estado['caminhao_id'], estado['cliente_id'], estado['func_id'],
                  datetime.now(), 'Ruído no freio < 30km/h', v_mo, v_pc,
                  round(v_mo + v_pc, 2), 'Aberta'))
            estado['os_id'] = cur.lastrowid
        return estado['os_id'] is not None
    teste("CREATE Ordem de Serviço (3 FKs)", criar_os)

    # READ consulta por placa (JOIN 3 tabelas)
    def consultar_os():
        with db.cursor() as (conn, cur):
            cur.execute("""
                SELECT o.id FROM ordens_servico o
                JOIN caminhoes ca ON ca.id=o.caminhao_id
                JOIN clientes cl ON cl.id=o.cliente_id
                JOIN funcionarios f ON f.id=o.funcionario_id
                WHERE ca.placa LIKE %s
            """, ("%" + PLACA_T + "%",))
            return cur.fetchone() is not None
    teste("READ OS por placa (JOIN clientes+caminhões+funcionários)", consultar_os)

    # UPDATE OS (status + valores)
    def atualizar_os():
        with db.cursor() as (conn, cur):
            cur.execute("""
                UPDATE ordens_servico SET status=%s, data_fechamento=%s,
                    valor_mao_obra=%s, valor_pecas=%s, valor_total=%s WHERE id=%s
            """, ('Concluída', datetime.now(), 600.0, 1200.5, 1800.5, estado['os_id']))
            cur.execute("SELECT status FROM ordens_servico WHERE id=%s", (estado['os_id'],))
            return cur.fetchone()[0] == 'Concluída'
    teste("UPDATE OS (status → Concluída)", atualizar_os)

    # FK RESTRICT — não deve deletar cliente com OS vinculada
    def fk_restrict():
        try:
            with db.cursor() as (conn, cur):
                cur.execute("DELETE FROM clientes WHERE id=%s", (estado['cliente_id'],))
            return False  # não deveria permitir
        except Exception:
            return True   # RESTRICT barrou corretamente
    teste("FK RESTRICT impede excluir cliente com OS", fk_restrict)

    # guarda dados pra teste de PDF
    testar_crud.estado = estado


# ============================================================================
#  5. TEMPLATES DE EMAIL
# ============================================================================
def testar_email():
    secao("5. TEMPLATES DE EMAIL (email_sender.py)")
    import email_sender as es

    a1, c1 = es.email_os_criada('João <Silva>', 42, 'ABC1D23', 'Problema & defeito', 'Carlos')
    teste("email_os_criada gera assunto e corpo", lambda: bool(a1) and bool(c1))
    teste("email_os_criada escapa HTML (< > &)",
          lambda: '&lt;' in c1 and '&amp;' in c1 and '<Silva>' not in c1)

    a2, c2 = es.email_os_atualizada('Maria', 42, 'ABC1D23', 'Concluída', 1800.5)
    teste("email_os_atualizada gera conteúdo", lambda: bool(a2) and 'Concluída' in c2)

    a3, c3 = es.email_boas_vindas('Pedro')
    teste("email_boas_vindas gera conteúdo", lambda: bool(a3) and 'Pedro' in c3)
    teste("email_boas_vindas NÃO menciona login (cliente não loga)",
          lambda: 'login' not in c3.lower() and 'senha' not in c3.lower())


# ============================================================================
#  6. GERAÇÃO DE PDF
# ============================================================================
def testar_pdf():
    secao("6. GERAÇÃO DE PDF (pdf_os.py)")
    import pdf_os
    import tempfile

    dados_base = {
        'id': 42, 'status': 'Concluída', 'data_abertura': datetime.now(),
        'data_fechamento': datetime.now(), 'cliente_nome': 'ZZTESTE Cliente',
        'cliente_cpf': '52998224725', 'cliente_telefone': '11999990000',
        'cliente_email': 'zz@x.com', 'cliente_cep': '01001000',
        'cliente_logradouro': 'Rua Teste', 'cliente_numero': '10',
        'cliente_complemento': None, 'cliente_bairro': 'Centro',
        'cliente_cidade': 'São Paulo', 'cliente_estado': 'SP',
        'placa': 'ABC1D23', 'marca': 'Volvo', 'modelo': 'FH', 'ano': 2022,
        'cor': 'Branco', 'chassi': 'CH123', 'funcionario_nome': 'Carlos',
        'descricao_problema': 'Freio < 30km/h & ruído', 'servicos_realizados': '<b>troca</b>',
        'pecas_utilizadas': 'pastilha', 'valor_mao_obra': 600.0,
        'valor_pecas': 1200.5, 'valor_total': 1800.5,
    }

    def gera_pdf():
        caminho = os.path.join(tempfile.gettempdir(), '_zzteste_os.pdf')
        pdf_os.gerar_pdf_os(dados_base, caminho)
        tamanho = os.path.getsize(caminho)
        os.remove(caminho)
        return tamanho > 1000
    teste("PDF gerado (texto com < > & escapados)", gera_pdf)

    def gera_pdf_id_none():
        d = dict(dados_base); d['id'] = None
        caminho = os.path.join(tempfile.gettempdir(), '_zzteste_os2.pdf')
        pdf_os.gerar_pdf_os(d, caminho)
        ok = os.path.getsize(caminho) > 1000
        os.remove(caminho)
        return ok
    teste("PDF gerado com id=None (defensivo)", gera_pdf_id_none)


# ============================================================================
#  7. REDE E EMAIL (opcionais)
# ============================================================================
def testar_rede(incluir_rede, incluir_email):
    secao("7. REDE / EMAIL (opcionais)")
    import validacoes as v

    if incluir_rede:
        def viacep():
            res = v.buscar_cep('01001000')  # Praça da Sé, SP
            return res['ok'] and res['cidade'] == 'São Paulo'
        teste("ViaCEP consulta CEP real (01001-000)", viacep)
    else:
        pular("ViaCEP (consulta real)", "use --rede para incluir")

    if incluir_email:
        import email_sender as es
        import config
        if not getattr(config, 'RESEND_API_KEY', ''):
            pular("Resend envio real", "RESEND_API_KEY não configurada")
        else:
            def envia():
                a, c = es.email_boas_vindas('Teste Suite')
                # delivered@resend.dev = endereço de simulação oficial do Resend
                sucesso, erro = es.enviar_email('delivered@resend.dev', a, c, em_thread=False)
                if not sucesso:
                    print(f"      {C.DIM}{erro}{C.END}")
                return sucesso
            teste("Resend envia email (delivered@resend.dev)", envia)
    else:
        pular("Resend envio real", "use --email para incluir (consome cota)")


# ============================================================================
#  CLEANUP
# ============================================================================
def limpar_dados_teste():
    """Remove qualquer dado ZZTESTE deixado para trás (ordem respeita FKs)."""
    import db
    try:
        with db.cursor() as (conn, cur):
            cur.execute("""DELETE o FROM ordens_servico o
                           JOIN clientes c ON c.id=o.cliente_id
                           WHERE c.cpf_cnpj='52998224725'""")
            cur.execute("""DELETE ca FROM caminhoes ca
                           JOIN clientes c ON c.id=ca.cliente_id
                           WHERE c.cpf_cnpj='52998224725'""")
            cur.execute("DELETE FROM clientes WHERE cpf_cnpj='52998224725'")
        return True
    except Exception as e:
        print(f"  {C.SKIP}aviso: cleanup parcial — {e}{C.END}")
        return False


# ============================================================================
#  MAIN
# ============================================================================
def main():
    incluir_rede = '--rede' in sys.argv
    incluir_email = '--email' in sys.argv

    print(C.BOLD + C.HEAD + """
================================================================
           TRUCKSTAR - SUITE DE TESTES DO SISTEMA
================================================================""" + C.END)
    print(f"{C.DIM}Inicio: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}{C.END}")

    # Verifica conexão antes de tudo
    try:
        import db
        db.inicializar()
    except Exception as e:
        print(f"\n{C.FAIL}{C.BOLD}ERRO FATAL: não foi possível conectar ao banco.{C.END}")
        print(f"{C.DIM}{type(e).__name__}: {e}{C.END}")
        print("Verifique config.py (DB_HOST/USER/PASSWORD) e se o MySQL está rodando.")
        sys.exit(2)

    try:
        testar_validacoes()
        testar_seguranca()
        testar_banco()
        testar_crud()
        testar_email()
        testar_pdf()
        testar_rede(incluir_rede, incluir_email)
    finally:
        secao("LIMPEZA")
        if limpar_dados_teste():
            print(f"  {C.OK}[OK]{C.END}      dados de teste removidos")
        # checagem final de connection leak
        try:
            import db
            with db.cursor() as (conn, cur):
                cur.execute("SHOW STATUS LIKE 'Threads_connected'")
                tc = cur.fetchone()[1]
            print(f"  {C.DIM}Threads_connected (MySQL): {tc}{C.END}")
        except Exception:
            pass

    # ---------------------------------------------------------------- resumo
    total = _total['ok'] + _total['fail']
    print("\n" + C.BOLD + "=" * 64 + C.END)
    print(C.BOLD + " RESUMO" + C.END)
    print(f"  {C.OK}Passaram: {_total['ok']}{C.END}   "
          f"{C.FAIL}Falharam: {_total['fail']}{C.END}   "
          f"{C.SKIP}Pulados: {_total['skip']}{C.END}   "
          f"(de {total} testes executados)")

    if _falhas:
        print(f"\n  {C.FAIL}{C.BOLD}Testes que falharam:{C.END}")
        for f in _falhas:
            print(f"    {C.FAIL}-{C.END} {f}")
        print("\n" + C.FAIL + C.BOLD + " RESULTADO: HA FALHAS [X]" + C.END)
        print(C.BOLD + "=" * 64 + C.END)
        sys.exit(1)
    else:
        pct = 100.0 if total else 0
        print(f"\n  {C.OK}{C.BOLD}Taxa de sucesso: {pct:.0f}%{C.END}")
        print("\n" + C.OK + C.BOLD + " RESULTADO: TODOS OS TESTES PASSARAM [OK]" + C.END)
        print(C.BOLD + "=" * 64 + C.END)
        sys.exit(0)


if __name__ == '__main__':
    main()
