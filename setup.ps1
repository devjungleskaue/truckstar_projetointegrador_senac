<#
    setup.ps1 - Instalador/configurador/executor da Truckstar.

    O que faz, em ordem:
      1. Localiza o projeto (usa a pasta atual se ja for o repo; senao clona do GitHub).
      2. Verifica Python e Git.
      3. Instala as dependencias (requirements.txt).
      4. Cria/atualiza config.py perguntando os dados (banco MySQL + Resend).
      5. Testa a conexao com o MySQL (oriente: deixe o MySQL Server rodando -
         via MySQL Workbench ou servico do Windows).
      6. Cria/atualiza o banco 'truckstar' e as tabelas (py db.py).
      7. Executa o sistema (py main.py), a menos que -NoRun.

    Uso tipico (interativo): basta dar duplo clique no .bat.
    Parametros (uteis para automacao/teste):
#>
[CmdletBinding()]
param(
    [string]$RepoUrl      = 'https://github.com/cocteaugaze/truckstar_projetointegrador_senac.git',
    [string]$DbHost       = '',
    [string]$DbUser       = '',
    [string]$DbPassword   = '',
    [string]$DbName       = 'truckstar',
    [string]$ResendKey    = '',
    [string]$EmailFrom    = 'onboarding@resend.dev',
    [string]$EmailReplyTo = '',
    [switch]$Reset,            # recria o banco do zero (apaga dados)
    [switch]$Reconfigure,      # forca regravar o config.py mesmo que ja exista
    [switch]$NoRun,            # nao executa o main.py ao final (so instala/configura)
    [switch]$NonInteractive    # nao pergunta nada: usa parametros/padroes
)

# 'Continue' (nao 'Stop') porque comandos nativos (git/pip/python) escrevem em
# stderr mesmo quando dao certo; no PS 5.1 isso viraria erro terminante. Em vez
# disso, checamos $LASTEXITCODE explicitamente apos cada chamada nativa.
$ErrorActionPreference = 'Continue'

function Titulo($t)  { Write-Host "`n==== $t ====" -ForegroundColor Cyan }
function Ok($t)      { Write-Host "  [OK] $t" -ForegroundColor Green }
function Aviso($t)   { Write-Host "  [!] $t" -ForegroundColor Yellow }
function Erro($t)    { Write-Host "  [X] $t" -ForegroundColor Red }

# Executa comando nativo mostrando a saida como texto comum (sem virar erro
# vermelho) e devolve o exit code real.
# Obs: evitamos $args[1..($args.Count-1)] porque, quando ha so 1 argumento,
# o range vira 1..0 e o PowerShell o inverte (pega indices errados).
function Nativo {
    $exe = $args[0]
    if ($args.Count -gt 1) { $rest = @($args[1..($args.Count - 1)]) } else { $rest = @() }
    & $exe @rest 2>&1 | ForEach-Object { Write-Host $_ }
    return $LASTEXITCODE
}

# Escapa uma string para virar literal Python entre aspas simples.
function Esc-Py([string]$s) {
    if ($null -eq $s) { return '' }
    return $s.Replace('\', '\\').Replace("'", "\'")
}

# Pergunta um valor: usa o parametro se veio preenchido; senao usa padrao em
# modo nao-interativo; senao pergunta via Read-Host mostrando o padrao.
function Pergunta($rotulo, $valorParam, $padrao, [switch]$Senha) {
    if ($valorParam -ne '') { return $valorParam }
    if ($NonInteractive)    { return $padrao }
    if ($Senha) {
        $sec = Read-Host "$rotulo" -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
        try   { $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
        return $plain
    }
    if ($padrao -ne '') { $msg = "$rotulo [$padrao]" } else { $msg = "$rotulo" }
    $r = Read-Host $msg
    if ($r -eq '') { return $padrao }
    return $r
}

# Verifica se o sistema JA esta instalado e operante: dependencias importam,
# config.py existe, conecta no MySQL e as 5 tabelas existem. Retorna $true
# somente quando tudo esta pronto (permite pular a configuracao).
function Sistema-Ja-Funciona {
    if (-not (Test-Path '.\config.py')) { return $false }
    $verif = @'
import os, sys
sys.path.insert(0, os.getcwd())
try:
    import config, pymysql, customtkinter, reportlab, resend
except Exception as e:
    print("[check] dependencia/config ausente:", e); sys.exit(2)
try:
    conexao = pymysql.connect(host=config.DB_HOST, user=config.DB_USER,
                              password=config.DB_PASSWORD, database=config.DB_NAME,
                              charset="utf8mb4", connect_timeout=5)
except Exception as e:
    print("[check] banco inacessivel:", e); sys.exit(3)
try:
    cur = conexao.cursor()
    cur.execute("SHOW TABLES")
    tabelas = set(r[0] for r in cur.fetchall())
    necessarias = {"funcionarios", "clientes", "caminhoes", "ordens_servico", "email_logs"}
    faltam = necessarias - tabelas
    if faltam:
        print("[check] faltam tabelas:", faltam); sys.exit(4)
    print("[check] sistema OK")
    sys.exit(0)
finally:
    conexao.close()
'@
    $enc = New-Object System.Text.UTF8Encoding($false)
    $tmp = Join-Path $env:TEMP ("ts_health_" + [System.Guid]::NewGuid().ToString('N') + ".py")
    $rc = 1
    try {
        [System.IO.File]::WriteAllText($tmp, $verif, $enc)
        & $PY $tmp 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
        $rc = $LASTEXITCODE
    } finally {
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
    return ($rc -eq 0)
}

Write-Host ""
Write-Host "  TRUCKSTAR - Instalador" -ForegroundColor Blue
Write-Host "  Mecanica de Caminhoes" -ForegroundColor DarkGray
Write-Host ""

# ----------------------------------------------------------------------
# 1. Python e Git
# ----------------------------------------------------------------------
Titulo "Verificando ferramentas"

$PY = $null
foreach ($cand in @('py', 'python', 'python3')) {
    $cmd = Get-Command $cand -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $ver = & $cand --version 2>&1
            if ($LASTEXITCODE -eq 0 -and "$ver" -match 'Python') { $PY = $cand; break }
        } catch { }
    }
}
if (-not $PY) {
    Erro "Python nao encontrado. Instale em https://www.python.org/downloads/ (marque 'Add to PATH')."
    exit 1
}
Ok "Python: $(& $PY --version 2>&1)"

$temGit = [bool](Get-Command git -ErrorAction SilentlyContinue)
if ($temGit) { Ok "Git: $(git --version)" } else { Aviso "Git nao encontrado (so necessario para clonar)." }

# ----------------------------------------------------------------------
# 2. Localizar / clonar o projeto
# ----------------------------------------------------------------------
Titulo "Localizando o projeto"

$projeto = $null
# Ja estamos dentro do repo?
if ((Test-Path (Join-Path $PSScriptRoot 'main.py')) -and (Test-Path (Join-Path $PSScriptRoot 'db.py'))) {
    $projeto = $PSScriptRoot
    Ok "Projeto encontrado na pasta do script."
} elseif ((Test-Path '.\main.py') -and (Test-Path '.\db.py')) {
    $projeto = (Get-Location).Path
    Ok "Projeto encontrado na pasta atual."
} else {
    if (-not $temGit) {
        Erro "Git e necessario para clonar o projeto. Instale em https://git-scm.com/download/win"
        exit 1
    }
    $nome = [System.IO.Path]::GetFileNameWithoutExtension(($RepoUrl -replace '\.git$',''))
    $alvo = Join-Path (Get-Location).Path $nome
    $temConteudo = (Test-Path $alvo) -and ([bool](Get-ChildItem -Force -LiteralPath $alvo -ErrorAction SilentlyContinue | Select-Object -First 1))
    if ((Test-Path (Join-Path $alvo 'main.py'))) {
        # Repo ja clonado -> atualiza.
        Ok "Repositorio ja clonado em '$nome'. Atualizando..."
        Push-Location $alvo
        Nativo git pull --ff-only | Out-Null
        Pop-Location
    } elseif ($temConteudo) {
        # Pasta existe, NAO-vazia e sem main.py: clone anterior interrompido ou
        # conflito de nome. git clone falharia ("not an empty directory").
        Erro "Ja existe uma pasta chamada '$nome' (incompleta) em:"
        Write-Host "      $alvo" -ForegroundColor Yellow
        Write-Host "    Remova/renomeie essa pasta e rode novamente, ou execute" -ForegroundColor Yellow
        Write-Host "    o instalador a partir de outra pasta." -ForegroundColor Yellow
        exit 1
    } else {
        # Pasta nao existe ou esta vazia: git clone funciona normalmente.
        Write-Host "  Clonando $RepoUrl ..." -ForegroundColor DarkGray
        $rc = Nativo git clone $RepoUrl $alvo
        if ($rc -ne 0) { Erro "Falha ao clonar o repositorio."; exit 1 }
    }
    $projeto = $alvo
}

Set-Location $projeto -ErrorAction Stop
Ok "Pasta de trabalho: $projeto"

# ----------------------------------------------------------------------
# Fast-path: se o sistema JA existe e funciona, pula direto para a execucao.
# So entra em instalacao/configuracao se algo faltar (ou com -Reconfigure/-Reset).
# ----------------------------------------------------------------------
$jaFunciona = $false
if (-not $Reconfigure -and -not $Reset) {
    Titulo "Verificando instalacao existente"
    if (Sistema-Ja-Funciona) {
        Ok "Sistema ja instalado e operante. Pulando para a execucao."
        $jaFunciona = $true
    } else {
        Write-Host "  Ainda nao esta pronto; seguindo para instalacao/configuracao." -ForegroundColor DarkGray
    }
}

if (-not $jaFunciona) {

# ----------------------------------------------------------------------
# 3. Dependencias
# ----------------------------------------------------------------------
Titulo "Instalando dependencias"
if (Test-Path '.\requirements.txt') {
    $rc = Nativo $PY -m pip install --disable-pip-version-check -r requirements.txt
    if ($rc -ne 0) { Erro "Falha ao instalar dependencias (pip)."; exit 1 }
    Ok "Dependencias instaladas (pymysql, customtkinter, reportlab, resend)."
} else {
    Aviso "requirements.txt nao encontrado; pulando."
}

# ----------------------------------------------------------------------
# 4 + 5. Configuracao + teste de conexao (em loop ate conectar)
# ----------------------------------------------------------------------
Titulo "Configuracao e banco de dados (MySQL)"
Write-Host "  Deixe o MySQL Server rodando (MySQL Workbench ou servico do Windows)." -ForegroundColor DarkGray
Write-Host "  O banco e as tabelas sao criados automaticamente - nao precisa criar a mao." -ForegroundColor DarkGray

$precisaConfig = (-not (Test-Path '.\config.py')) -or $Reconfigure
if ((Test-Path '.\config.py') -and -not $Reconfigure) {
    Ok "config.py ja existe (use -Reconfigure para refazer)."
}

while ($true) {
    if ($precisaConfig) {
        Write-Host ""
        Write-Host "  -- Dados do banco MySQL --" -ForegroundColor White
        $h = Pergunta "Host do MySQL"      $DbHost     'localhost'
        $u = Pergunta "Usuario do MySQL"   $DbUser     'root'
        $p = Pergunta "Senha do MySQL"     $DbPassword ''  -Senha
        $n = Pergunta "Nome do banco"      $DbName     'truckstar'

        Write-Host ""
        Write-Host "  -- Email (Resend) - opcional, ENTER para pular --" -ForegroundColor White
        $k  = Pergunta "RESEND_API_KEY (re_...)"          $ResendKey    ''
        $ef = Pergunta "Remetente (EMAIL_FROM)"           $EmailFrom    'onboarding@resend.dev'
        $er = Pergunta "Responder-para (EMAIL_REPLY_TO)"  $EmailReplyTo ''

        $conteudo = @"
"""
Configuracoes da Truckstar (LOCAL - nao versionar).
Gerado automaticamente por setup.ps1.
"""

# ===== BANCO DE DADOS =====
DB_HOST = '$(Esc-Py $h)'
DB_USER = '$(Esc-Py $u)'
DB_PASSWORD = '$(Esc-Py $p)'
DB_NAME = '$(Esc-Py $n)'

# ===== EMAIL (RESEND) =====
RESEND_API_KEY = '$(Esc-Py $k)'
EMAIL_FROM = '$(Esc-Py $ef)'
EMAIL_REMETENTE_NOME = 'Truckstar Mecânica'
EMAIL_REPLY_TO = '$(Esc-Py $er)'

# ===== SEGURANCA =====
HASH_ITERACOES = 600_000
SENHA_MIN_CARACTERES = 8
LOGIN_MAX_TENTATIVAS = 5
LOGIN_BLOQUEIO_SEGUNDOS = 60

# ===== APLICACAO =====
EMPRESA_NOME = 'Truckstar'
EMPRESA_DESC = 'Mecânica de Caminhões'
"@
        $enc = New-Object System.Text.UTF8Encoding($false)  # UTF-8 sem BOM
        try {
            [System.IO.File]::WriteAllText((Join-Path $projeto 'config.py'), $conteudo, $enc)
        } catch {
            Erro "Nao foi possivel gravar config.py: $($_.Exception.Message)"
            exit 1
        }
        Ok "config.py gravado."
        $precisaConfig = $false
    }

    # Testa conexao usando o proprio config.py (sem precisar reescapar nada).
    Write-Host "  Testando conexao com o MySQL..." -ForegroundColor DarkGray
    $rc = Nativo $PY -c "import config, pymysql; pymysql.connect(host=config.DB_HOST, user=config.DB_USER, password=config.DB_PASSWORD, charset='utf8mb4', connect_timeout=5).close(); print('CONEXAO_OK')"
    if ($rc -eq 0) {
        Ok "Conexao com o MySQL bem-sucedida."
        break
    }

    Erro "Nao foi possivel conectar ao MySQL."
    Write-Host "    - O MySQL Server esta rodando? (abra o MySQL Workbench e teste a conexao)" -ForegroundColor Yellow
    Write-Host "    - Usuario/senha corretos?" -ForegroundColor Yellow
    Write-Host "    - O host/porta estao certos? (padrao localhost:3306)" -ForegroundColor Yellow
    if ($NonInteractive) { exit 1 }
    $resp = Read-Host "  Tentar novamente reconfigurando os dados? (S/N)"
    if ($resp -notmatch '^[Ss]') { exit 1 }
    $precisaConfig = $true
}

# ----------------------------------------------------------------------
# 6. Criar/atualizar banco e tabelas
# ----------------------------------------------------------------------
Titulo "Preparando o banco 'truckstar'"
if ($Reset) {
    Aviso "Modo -Reset: o banco sera recriado do zero (dados apagados)."
    $rc = Nativo $PY db.py --reset
} else {
    $rc = Nativo $PY db.py
}
if ($rc -ne 0) { Erro "Falha ao inicializar o banco."; exit 1 }
Ok "Banco e tabelas prontos."

}  # fim do if (-not $jaFunciona) -- bloco de instalacao/configuracao

# ----------------------------------------------------------------------
# 7. Executar
# ----------------------------------------------------------------------
if ($NoRun) {
    Titulo "Concluido (sem executar)"
    Ok "Tudo pronto. Para iniciar: py main.py"
    exit 0
}

Titulo "Iniciando o sistema"
Write-Host "  Login inicial -> usuario: admin   senha: admin123" -ForegroundColor Green
Write-Host "  (Feche a janela do sistema para encerrar.)" -ForegroundColor DarkGray
& $PY main.py
exit $LASTEXITCODE
