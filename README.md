# 🚛 Truckstar — Sistema de Gestão para Mecânica de Caminhões

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8%2B-4479A1?logo=mysql&logoColor=white)
![UI](https://img.shields.io/badge/UI-CustomTkinter-1f6feb)
![Plataforma](https://img.shields.io/badge/plataforma-Windows-0078D6?logo=windows&logoColor=white)
![Status](https://img.shields.io/badge/status-acad%C3%AAmico-success)

Aplicação **desktop em Python** para gestão de uma oficina de caminhões:
cadastro de clientes, funcionários e caminhões, abertura e acompanhamento de
**ordens de serviço (OS)**, envio automático de email ao cliente e geração de
**PDF profissional** da OS — tudo com login por funcionário e validação oficial
de CPF/CNPJ.

> Projeto desenvolvido como **Projeto Integrador (1º módulo)** do curso
> **Jovem Programador — SENAC/SC**.

---

## Índice

- [Sobre o projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Stack](#stack)
- [Pré-requisitos](#pré-requisitos)
- [Setup](#setup)
- [Login inicial](#login-inicial-seed-automático)
- [Permissões por cargo](#permissões-por-cargo)
- [Capturas de tela](#capturas-de-tela)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Testes](#testes)
- [Configuração de email (Resend)](#configuração-de-email-resend)
- [Notas de segurança](#notas-de-segurança)
- [Autor e licença](#autor-e-licença)

---

## Sobre o projeto

O Truckstar resolve a rotina de uma oficina: o atendente cadastra o cliente e o
caminhão, abre a OS descrevendo o problema e os valores, e o sistema **avisa o
cliente por email automaticamente** a cada etapa — sem ninguém precisar ligar.
No fim, gera a OS em PDF pronta para impressão e assinatura.

A arquitetura é em camadas simples: as telas (`tela_*.py`) conversam com o
módulo de dados (`db.py`, via PyMySQL) e com módulos de apoio isolados por
responsabilidade — segurança, validações, email e PDF.

## Funcionalidades

- **Login de funcionário** com hash PBKDF2-SHA256 + salt e rate limit contra brute-force (5 tentativas / 60s)
- **Controle de acesso por cargo** (Admin / Atendente / Mecânico) — cada um só vê e faz o que lhe cabe
- **Validação oficial de CPF/CNPJ** (dígitos verificadores) e de email, placa e CEP
- **Autocomplete de endereço** via API ViaCEP (digita o CEP → endereço preenchido)
- **Geração de PDF** profissional da OS (endereço completo, valores, assinaturas)
- **Email automático ao cliente** (síncrono, com confirmação real de entrega):
  - Boas-vindas no cadastro
  - OS criada
  - OS atualizada — em **qualquer alteração** de status, serviços, peças ou valores
- **Consulta de OS** por placa ou nome do cliente
- Atalhos: `F11` tela cheia · `Esc` sair · `Ctrl+M` maximizar · botão **Sair (Logout)** em todas as telas

## Stack

- **Python 3.10+** (testado em 3.12 e 3.14)
- **CustomTkinter** — interface gráfica
- **PyMySQL** — conexão com o MySQL
- **ReportLab** — geração de PDF
- **Resend** — envio de email transacional via API

## Pré-requisitos

- **Python 3.10 ou superior**
- **Servidor MySQL 8+ rodando** e acessível (local ou remoto) — o app cria o
  banco `truckstar` sozinho, mas o **servidor** precisa estar de pé e as
  credenciais corretas em `config.py`
- (Opcional) **Conta no [Resend](https://resend.com)** para enviar emails — sem
  ela o sistema funciona normalmente, apenas não dispara emails

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
cp config.example.py config.py     # preencha as credenciais (MySQL + Resend)
python main.py
```

Na primeira execução, `db.inicializar()` cria o banco `truckstar` e as tabelas
automaticamente, além do usuário admin de bootstrap (veja abaixo).

## Login inicial (seed automático)

| Tipo  | Usuário | Senha      |
|-------|---------|------------|
| Admin | `admin` | `admin123` |

Apenas o admin é criado automaticamente na primeira inicialização.
Demais funcionários (Atendente, Mecânico) e clientes são cadastrados via
sistema. O cliente **não faz login** — interage apenas como destinatário de
emails sobre suas Ordens de Serviço.

> ⚠️ **Troque a senha do admin imediatamente após o primeiro login** (tela de
> Funcionários). A senha padrão `admin123` é apenas para bootstrap.

## Permissões por cargo

| Cargo      | Clientes | Funcionários | Criar OS | Editar OS | Excluir OS |
|------------|----------|--------------|----------|-----------|------------|
| Admin      | ✓        | ✓            | ✓        | ✓         | ✓          |
| Atendente  | ✓        | —            | ✓        | ✓         | —          |
| Mecânico   | —        | —            | —        | só suas   | —          |

## Capturas de tela

<!--
Adicione imagens aqui para valorizar o repositório (login, lista de OS, PDF gerado).
Sugestão: salve os prints em docs/img/ e referencie:

![Tela de login](docs/img/login.png)
![Ordens de serviço](docs/img/ordens.png)
-->

_Em breve._

## Estrutura do projeto

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

## Testes

A suíte automatizada fica em [`tests/`](tests/) (detalhes em
[tests/README.md](tests/README.md)). Para validar todo o sistema:

```bash
py tests/testar_sistema.py
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

<details>
<summary><strong>⚠️ Limitação crítica do free tier (leia antes de testar com clientes reais)</strong></summary>

No plano gratuito, **sem domínio próprio verificado**, o Resend só entrega
emails para **um único destinatário**: o email com que você criou a conta
Resend (o *owner email*).

Tentativas de enviar para qualquer outro endereço (cliente real, gmail de
terceiros, etc.) são **rejeitadas pela API** com:

> "You can only send testing emails to your own email address"

O app trata isso corretamente — **não** mostra "Email enviado" mentirosamente.
Se o Resend recusar, aparece "Alterações salvas com aviso: email NÃO enviado".
Mas o cliente não recebe nada.

**Como liberar envio para clientes reais:**

1. Compre/registre um domínio (ex: `truckstarmecanica.com.br`)
2. Verifique em https://resend.com/domains (instruções DNS automáticas)
3. Altere `EMAIL_FROM` no `config.py` para algo como `oficina@truckstarmecanica.com.br`
4. Pronto — passa a entregar para qualquer destinatário

**Para testar localmente sem domínio:** cadastre o cliente fictício com o mesmo
email da conta Resend, ou use o endereço de simulação oficial `delivered@resend.dev`.

**Sobre o sender:** `onboarding@resend.dev` é o remetente pré-aprovado do Resend.
Você **não** consegue trocar para `@gmail.com`/`@outlook.com` no FROM porque não
é dono desses domínios. Use o sender padrão **e** configure `EMAIL_REPLY_TO`
apontando pro Gmail da oficina — assim o cliente vê "Truckstar Mecânica" como
remetente e qualquer resposta cai na sua caixa real.

</details>

## Notas de segurança

- `config.py` está no `.gitignore` — **nunca versione credenciais** (API key inclusive)
- Senhas armazenadas como hash **PBKDF2-SHA256** (600k iterações, OWASP 2023) + salt aleatório de 16 bytes
- Comparação de senha resistente a *timing attacks* (`hmac.compare_digest`)
- Rate limiting em memória: 5 tentativas / 60s por usuário
- Todo SQL é **parametrizado** (sem concatenação de strings)

## Autor e licença

Desenvolvido por [@devjungleskaue](https://github.com/devjungleskaue) como
Projeto Integrador do curso Jovem Programador (SENAC/SC).

Distribuído sob a licença **MIT** — veja [LICENSE](LICENSE).
