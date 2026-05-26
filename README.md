# Truckstar — Sistema de Gestão para Mecânica de Caminhões

Sistema desktop em Python para cadastro de clientes, funcionários, caminhões e
ordens de serviço. Login dividido por tipo de usuário, envio de email automático
ao cliente, geração de PDF profissional da OS e validação oficial de CPF/CNPJ.

## Stack

- **Python 3.10+**
- **CustomTkinter** — interface gráfica
- **PyMySQL** — conexão MySQL
- **ReportLab** — geração de PDF
- **Resend** — envio de email transacional via API

## Setup

```bash
pip install -r requirements.txt
cp config.example.py config.py     # preencha as credenciais
python main.py
```

O script cria o banco `truckstar` automaticamente na primeira execução
(via `db.inicializar()`).

## Login inicial (seed automático)

| Tipo  | Usuário | Senha      |
|-------|---------|------------|
| Admin | `admin` | `admin123` |

Apenas o admin é criado automaticamente na primeira inicialização.
Demais funcionários (Atendente, Mecânico) e clientes devem ser cadastrados via
sistema. Cliente faz login com **CPF + senha** na aba "Cliente" — há botão
"Criar conta de Cliente" para auto-cadastro.

> ⚠️ **Troque a senha do admin imediatamente após o primeiro login** via tela
> de Funcionários. A senha padrão `admin123` é apenas para bootstrap.

## Permissões por cargo

| Cargo      | Clientes | Funcionários | Criar OS | Editar OS | Excluir OS |
|------------|----------|--------------|----------|-----------|------------|
| Admin      | ✓        | ✓            | ✓        | ✓         | ✓          |
| Atendente  | ✓        | —            | ✓        | ✓         | —          |
| Mecânico   | —        | —            | —        | só suas   | —          |
| Cliente    | só visualiza | —        | —        | —         | —          |

## Funcionalidades

- Login dividido (Funcionário / Cliente) com hash PBKDF2-SHA256 + salt
- Rate limit em memória contra brute-force (5 tentativas / 60s)
- Validação oficial de CPF/CNPJ (dígitos verificadores)
- Autocomplete de endereço via API ViaCEP
- Geração de PDF profissional da OS (com endereço completo, valores, assinaturas)
- Envio automático de email ao cliente:
  - Boas-vindas no cadastro
  - OS criada
  - OS atualizada (mudança de status)
- Consulta de OS por placa ou nome do cliente
- Painel cliente read-only (vê seus veículos, OS, baixa PDF)
- Atalhos: `F11` fullscreen, `Esc` sair, `Ctrl+M` maximizar
- Botão "Sair (Logout)" em todas as telas pós-login

## Estrutura

```
├── config.example.py    # template (copie para config.py)
├── .env.example         # alternativa via variáveis de ambiente
├── db.py                # schema e conexão pymysql
├── seguranca.py         # hash PBKDF2 + salt
├── validacoes.py        # CPF/CNPJ/email/placa/CEP
├── email_sender.py      # SMTP Gmail + templates HTML + thread
├── pdf_os.py            # gerador de PDF da OS
├── ui_utils.py          # helpers de resize/fullscreen
├── main.py              # entry point + login + roteamento
├── tela_clientes.py     # CRUD clientes + caminhões
├── tela_funcionarios.py # CRUD funcionários
├── tela_ordens.py       # CRUD OS + consulta + PDF + email
└── tela_cliente.py      # portal read-only do cliente
```

## Configuração de email (Resend)

1. Crie uma conta gratuita em https://resend.com (100 emails/dia, 3 mil/mês)
2. Gere uma API key em https://resend.com/api-keys
3. Cole o valor em `RESEND_API_KEY` no seu `config.py`
4. Configure `EMAIL_REPLY_TO` com o Gmail/Outlook da oficina — quando o cliente
   responder o email, a resposta cai nessa caixa
5. (Opcional) Para enviar de um domínio próprio em vez de `onboarding@resend.dev`,
   verifique o domínio em https://resend.com/domains e altere `EMAIL_FROM`

Se `RESEND_API_KEY` ficar vazia, o app continua funcionando normalmente, apenas
não envia emails (cada tentativa é registrada na tabela `email_logs` com erro).

> ℹ️ No free tier do Resend, o `EMAIL_FROM` precisa ser `onboarding@resend.dev`
> ou um endereço em domínio próprio verificado — não dá pra usar
> `@gmail.com`/`@outlook.com` como remetente porque você não possui esses
> domínios. O fluxo correto é usar o sender pré-aprovado **e** o `EMAIL_REPLY_TO`
> apontando pro seu Gmail real (assim cliente vê "Truckstar Mecânica" como
> remetente e respostas vão pro seu Gmail).

## Notas de segurança

- `config.py` está no `.gitignore` — nunca versione credenciais (API key inclusive)
- Senhas no banco são armazenadas como hash PBKDF2-SHA256 (600k iterações, conforme OWASP 2023) + salt aleatório de 16 bytes
- Comparação de senhas é resistente a timing attacks (`hmac.compare_digest`)
- Rate limiting em memória: 5 tentativas / 60s por usuário ou CPF
- Todo SQL é parametrizado (sem concatenação de strings)
- Cliente só acessa suas próprias OS (filtro `cliente_id` no SQL)
