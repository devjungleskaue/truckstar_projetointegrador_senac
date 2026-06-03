# Truckstar — Sistema de Gestão para Mecânica de Caminhões

Sistema desktop em Python para cadastro de clientes, funcionários, caminhões e
ordens de serviço. Login exclusivo de funcionário, envio de email automático
ao cliente, geração de PDF profissional da OS e validação oficial de CPF/CNPJ.

## Stack

- **Python 3.10+**
- **CustomTkinter** — interface gráfica
- **PyMySQL** — conexão MySQL
- **ReportLab** — geração de PDF
- **Resend** — envio de email transacional via API

## Setup

### Opção A — Instalador automático (Windows)

Dê duplo clique em **`Instalar_e_Executar_Truckstar.bat`**. Ele localiza a
instalação existente no PC (ou clona o repo), instala as dependências,
pergunta as credenciais (MySQL + Resend), cria o banco e abre o sistema.
Nas execuções seguintes, se o sistema já estiver pronto, abre direto sem
reconfigurar (use `-Reconfigure` ou `-Reset` para forçar).

### Opção B — Manual

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
Demais funcionários (Atendente, Mecânico) e clientes são cadastrados via
sistema. Cliente **não faz login** — interage apenas como destinatário de
emails sobre suas Ordens de Serviço.

> ⚠️ **Troque a senha do admin imediatamente após o primeiro login** via tela
> de Funcionários. A senha padrão `admin123` é apenas para bootstrap.

## Testes

A suíte de testes automatizados fica em [`tests/`](tests/) (ver
[tests/README.md](tests/README.md)). Para validar todo o sistema:

```bash
py tests/testar_sistema.py
```

## Permissões por cargo

| Cargo      | Clientes | Funcionários | Criar OS | Editar OS | Excluir OS |
|------------|----------|--------------|----------|-----------|------------|
| Admin      | ✓        | ✓            | ✓        | ✓         | ✓          |
| Atendente  | ✓        | —            | ✓        | ✓         | —          |
| Mecânico   | —        | —            | —        | só suas   | —          |

## Funcionalidades

- Login de funcionário com hash PBKDF2-SHA256 + salt
- Rate limit em memória contra brute-force (5 tentativas / 60s)
- Validação oficial de CPF/CNPJ (dígitos verificadores)
- Autocomplete de endereço via API ViaCEP
- Geração de PDF profissional da OS (com endereço completo, valores, assinaturas)
- Envio automático de email ao cliente (síncrono, com confirmação real de entrega):
  - Boas-vindas no cadastro
  - OS criada
  - OS atualizada — em **qualquer alteração** de status, serviços, peças ou valores
- Consulta de OS por placa ou nome do cliente
- Atalhos: `F11` fullscreen, `Esc` sair, `Ctrl+M` maximizar
- Botão "Sair (Logout)" em todas as telas pós-login

## Estrutura

```
├── Instalar_e_Executar_Truckstar.bat  # instalador 1-clique (Windows)
├── setup.ps1            # lógica do instalador (localiza/clona, deps, config, run)
├── config.example.py    # template (copie para config.py)
├── .env.example         # alternativa via variáveis de ambiente
├── db.py                # schema e conexão pymysql
├── seguranca.py         # hash PBKDF2 + salt
├── validacoes.py        # CPF/CNPJ/email/placa/CEP
├── email_sender.py      # envio Resend API + templates HTML
├── pdf_os.py            # gerador de PDF da OS
├── ui_utils.py          # helpers de resize/fullscreen
├── ui_helpers.py        # helper de exibição de erros na UI
├── main.py              # entry point + login + roteamento
├── tela_clientes.py     # CRUD clientes + caminhões
├── tela_funcionarios.py # CRUD funcionários
├── tela_ordens.py       # CRUD OS + consulta + PDF + email
└── tests/               # suíte de testes automatizados
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

### ⚠️ Limitação crítica do free tier do Resend

No plano gratuito, **sem domínio próprio verificado**, o Resend só entrega
emails para **um único destinatário**: o email com que você criou a conta
Resend (chamado *owner email*).

**Tentativas de enviar para qualquer outro email** (cliente real, gmail de
terceiros, etc.) são **rejeitadas pela API do Resend** com a mensagem:

> "You can only send testing emails to your own email address"

O app trata isso corretamente — não mostra "Email enviado" mentirosamente. Se
o Resend recusar, aparece um aviso "Alterações salvas com aviso: email NÃO
enviado". Mas o cliente não recebe nada.

**Como liberar envio para clientes reais:**

1. Compre/registre um domínio (ex: `truckstarmecanica.com.br`)
2. Verifique em https://resend.com/domains (instruções DNS automáticas)
3. Altere `EMAIL_FROM` no `config.py` para algo do tipo `oficina@truckstarmecanica.com.br`
4. Pronto — passa a entregar para qualquer destinatário

Para **testar localmente sem domínio**: cadastre o cliente fictício com o
mesmo email da conta Resend, ou use o endereço de simulação oficial
`delivered@resend.dev`.

### Sobre o sender

`onboarding@resend.dev` é o remetente pré-aprovado do Resend. Você **não
consegue** trocar para `@gmail.com` ou `@outlook.com` no FROM porque não é
dono desses domínios. Use o sender padrão **e** configure `EMAIL_REPLY_TO`
apontando pro Gmail da oficina — assim o cliente vê "Truckstar Mecânica"
como remetente, e qualquer resposta cai na sua caixa real.

## Notas de segurança

- `config.py` está no `.gitignore` — nunca versione credenciais (API key inclusive)
- Senhas no banco são armazenadas como hash PBKDF2-SHA256 (600k iterações, conforme OWASP 2023) + salt aleatório de 16 bytes
- Comparação de senhas é resistente a timing attacks (`hmac.compare_digest`)
- Rate limiting em memória: 5 tentativas / 60s por usuário
- Todo SQL é parametrizado (sem concatenação de strings)
