"""
Template de configuração da Truckstar.
COPIE este arquivo como `config.py` e preencha os valores reais.
NUNCA versione o `config.py` (já está no .gitignore).
"""

# ===== BANCO DE DADOS =====
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'SUA_SENHA_DO_MYSQL'
DB_NAME = 'truckstar'

# ===== EMAIL (GMAIL SMTP) =====
# Para usar Gmail:
# 1) Ative verificação em 2 etapas: https://myaccount.google.com/security
# 2) Gere uma senha de app: https://myaccount.google.com/apppasswords
# 3) Cole a senha de 16 caracteres (sem espaços) em EMAIL_SENHA
# Se EMAIL_USUARIO ficar vazio, o sistema NÃO envia email mas salva no log.
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORTA = 587
EMAIL_USUARIO = ''   # ex: 'truckstar.oficina@gmail.com'
EMAIL_SENHA = ''     # senha de app de 16 caracteres
EMAIL_REMETENTE_NOME = 'Truckstar Mecânica'

# ===== SEGURANÇA =====
HASH_ITERACOES = 100_000
SENHA_MIN_CARACTERES = 6
LOGIN_MAX_TENTATIVAS = 5
LOGIN_BLOQUEIO_SEGUNDOS = 60

# ===== APLICAÇÃO =====
EMPRESA_NOME = 'Truckstar'
EMPRESA_DESC = 'Mecânica de Caminhões'
