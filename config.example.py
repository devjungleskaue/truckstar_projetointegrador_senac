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

# ===== EMAIL (RESEND) =====
# 1) Crie conta gratuita em https://resend.com (100 emails/dia, 3k/mês)
# 2) Gere API key em https://resend.com/api-keys
# 3) Cole abaixo (formato: re_xxxxxxxxxxxxxxxxxxxx)
# Se RESEND_API_KEY ficar vazia, o sistema NÃO envia email mas salva no log.
RESEND_API_KEY = ''                       # ex: 're_xxxxxxxxxxxxxxxxxxxx'
EMAIL_FROM = 'onboarding@resend.dev'      # sender pré-aprovado (sem precisar de domínio próprio)
EMAIL_REMETENTE_NOME = 'Truckstar Mecânica'
# Quando o cliente responder ao email, a resposta vai para este endereço.
# Use o Gmail/Outlook da oficina que receberá as respostas.
EMAIL_REPLY_TO = ''                       # ex: 'oficina@gmail.com'

# ===== SEGURANÇA =====
# 600k iterações: OWASP 2023 recommendation para PBKDF2-HMAC-SHA256.
HASH_ITERACOES = 600_000
SENHA_MIN_CARACTERES = 8
LOGIN_MAX_TENTATIVAS = 5
LOGIN_BLOQUEIO_SEGUNDOS = 60

# ===== APLICAÇÃO =====
EMPRESA_NOME = 'Truckstar'
EMPRESA_DESC = 'Mecânica de Caminhões'
