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
    [string]$RepoUrl      = 'https://github.com/devjungleskaue/truckstar_projetointegrador_senac.git',
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

# ----------------------------------------------------------------------
# Localizacao do projeto no PC (busca em camadas).
# Uma pasta e' considerada o projeto Truckstar quando contem a assinatura
# de 4 arquivos abaixo (evita falso-positivo com outros projetos Python).
# ----------------------------------------------------------------------
$ASSINATURA = @('main.py', 'db.py', 'tela_ordens.py', 'pdf_os.py')

function Test-EhTruckstar([string]$dir) {
    if (-not $dir) { return $false }
    foreach ($f in $ASSINATURA) {
        if (-not (Test-Path -LiteralPath (Join-Path $dir $f))) { return $false }
    }
    return $true
}

# BFS com poda: varre as raizes procurando pastas-projeto. Nao desce dentro de
# uma pasta ja identificada como projeto, ignora pastas de sistema/lixo e
# reparse points (symlinks/junctions) para nao entrar em loop.
function Find-TruckstarDirs {
    param([string[]]$Roots, [int]$MaxDepth = 6)

    $proibidas = @(
        '$Recycle.Bin', 'Windows', 'Program Files', 'Program Files (x86)',
        'ProgramData', 'AppData', 'node_modules', '.git', 'venv', '.venv',
        'env', '__pycache__', 'System Volume Information', '.vs', '.idea',
        'Microsoft', 'Packages', 'WindowsApps'
    )
    $resultados = New-Object System.Collections.Generic.List[string]
    $vistos = @{}
    $fila = New-Object System.Collections.Generic.Queue[object]
    foreach ($r in $Roots) {
        if ($r -and (Test-Path -LiteralPath $r)) {
            $fila.Enqueue([pscustomobject]@{ Path = $r; Depth = 0 })
        }
    }
    while ($fila.Count -gt 0) {
        $item = $fila.Dequeue()
        $dir = $item.Path
        $chave = $dir.ToLower()
        if ($vistos.ContainsKey($chave)) { continue }
        $vistos[$chave] = $true

        if (Test-EhTruckstar $dir) { $resultados.Add($dir); continue }
        if ($item.Depth -ge $MaxDepth) { continue }

        try {
            $subs = Get-ChildItem -LiteralPath $dir -Directory -Force -ErrorAction SilentlyContinue
        } catch { $subs = @() }
        foreach ($s in $subs) {
            if ($proibidas -contains $s.Name) { continue }
            if ($s.Name.StartsWith('.')) { continue }
            # Pula APENAS reparse points de sistema (junctions/mount points como
            # 'Documents and Settings', 'Application Data' legados) que causam
            # loops. NAO pula pastas do OneDrive (Files On-Demand), que sao
            # reparse points SEM o atributo System e contem dados reais.
            $attr = $s.Attributes
            if (($attr -band [IO.FileAttributes]::ReparsePoint) -and ($attr -band [IO.FileAttributes]::System)) { continue }
            $fila.Enqueue([pscustomobject]@{ Path = $s.FullName; Depth = $item.Depth + 1 })
        }
    }
    return $resultados
}

# Entre varios candidatos, escolhe o melhor: instalacao COM config.py vem
# primeiro; em empate, a modificada mais recentemente.
function Select-MelhorProjeto([string[]]$dirs) {
    if (-not $dirs -or $dirs.Count -eq 0) { return $null }
    $info = foreach ($d in $dirs) {
        $temCfg = Test-Path -LiteralPath (Join-Path $d 'config.py')
        try { $mod = (Get-Item -LiteralPath $d -Force).LastWriteTime } catch { $mod = [datetime]::MinValue }
        [pscustomobject]@{ Path = $d; TemCfg = [bool]$temCfg; Mod = $mod }
    }
    $best = $info |
        Sort-Object @{ Expression = 'TemCfg'; Descending = $true }, @{ Expression = 'Mod'; Descending = $true } |
        Select-Object -First 1
    return $best.Path
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

# --- Camada 0: a propria pasta do script ou a pasta atual ja sao o projeto? ---
if (Test-EhTruckstar $PSScriptRoot) {
    $projeto = $PSScriptRoot
    Ok "Projeto encontrado na pasta do script."
} elseif (Test-EhTruckstar (Get-Location).Path) {
    $projeto = (Get-Location).Path
    Ok "Projeto encontrado na pasta atual."
}

# --- Camada 1: locais provaveis (perfil do usuario + onde o .bat esta) ---
# Cobre Desktop, Documentos, Downloads, OneDrive (qualquer idioma), etc.,
# independentemente de onde o .bat foi executado.
if (-not $projeto) {
    Write-Host "  Procurando instalacao existente nos locais comuns..." -ForegroundColor DarkGray
    $raizes = @($PSScriptRoot, (Get-Location).Path, $env:USERPROFILE) |
        Where-Object { $_ } | Select-Object -Unique
    $achados = Find-TruckstarDirs -Roots $raizes -MaxDepth 6
    if ($achados.Count -gt 0) {
        $projeto = Select-MelhorProjeto $achados
        Ok "Instalacao encontrada: $projeto"
        if ($achados.Count -gt 1) {
            Write-Host "    ($($achados.Count) copias encontradas; usando a configurada/mais recente)" -ForegroundColor DarkGray
        }
    }
}

# --- Camada 2 (fallback): varredura dos drives fixos inteiros ---
# So roda se nada foi achado nos locais comuns. Pode demorar.
if (-not $projeto) {
    Aviso "Nao achei nos locais comuns. Varrendo os drives fixos (pode demorar)..."
    $fixos = @()
    foreach ($drv in [System.IO.DriveInfo]::GetDrives()) {
        if ($drv.DriveType -eq [System.IO.DriveType]::Fixed -and $drv.IsReady) {
            $fixos += $drv.RootDirectory.FullName
        }
    }
    $achados = Find-TruckstarDirs -Roots $fixos -MaxDepth 12
    if ($achados.Count -gt 0) {
        $projeto = Select-MelhorProjeto $achados
        Ok "Instalacao encontrada: $projeto"
        if ($achados.Count -gt 1) {
            Write-Host "    ($($achados.Count) copias encontradas; usando a configurada/mais recente)" -ForegroundColor DarkGray
        }
    }
}

# --- Nada no PC inteiro: clonar do GitHub ---
if (-not $projeto) {
    Write-Host "  Nenhuma instalacao encontrada no PC. Sera baixada uma nova." -ForegroundColor DarkGray
    if (-not $temGit) {
        Erro "Git e necessario para clonar o projeto. Instale em https://git-scm.com/download/win"
        exit 1
    }
    $nome = [System.IO.Path]::GetFileNameWithoutExtension(($RepoUrl -replace '\.git$', ''))
    $alvo = Join-Path (Get-Location).Path $nome
    $temConteudo = (Test-Path -LiteralPath $alvo) -and ([bool](Get-ChildItem -Force -LiteralPath $alvo -ErrorAction SilentlyContinue | Select-Object -First 1))
    if (Test-EhTruckstar $alvo) {
        Ok "Repositorio ja clonado em '$nome'. Atualizando..."
        Push-Location $alvo
        Nativo git pull --ff-only | Out-Null
        Pop-Location
    } elseif ($temConteudo) {
        Erro "Ja existe uma pasta chamada '$nome' (incompleta) em:"
        Write-Host "      $alvo" -ForegroundColor Yellow
        Write-Host "    Remova/renomeie essa pasta e rode novamente, ou execute" -ForegroundColor Yellow
        Write-Host "    o instalador a partir de outra pasta." -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "  Clonando $RepoUrl ..." -ForegroundColor DarkGray
        $rc = Nativo git clone $RepoUrl $alvo
        if ($rc -ne 0) { Erro "Falha ao clonar o repositorio."; exit 1 }
    }
    $projeto = $alvo
}

Set-Location -LiteralPath $projeto -ErrorAction Stop
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
EMAIL_REMETENTE_NOME = 'Truckstar Mec$([char]0xE2)nica'
EMAIL_REPLY_TO = '$(Esc-Py $er)'

# ===== SEGURANCA =====
HASH_ITERACOES = 600_000
SENHA_MIN_CARACTERES = 8
LOGIN_MAX_TENTATIVAS = 5
LOGIN_BLOQUEIO_SEGUNDOS = 60

# ===== APLICACAO =====
EMPRESA_NOME = 'Truckstar'
EMPRESA_DESC = 'Mec$([char]0xE2)nica de Caminh$([char]0xF5)es'
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
