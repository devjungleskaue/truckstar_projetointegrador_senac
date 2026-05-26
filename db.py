"""
Conexão e schema do banco. Dropa e recria 'truckstar' na primeira chamada de inicializar().
"""
import re
import pymysql
from datetime import date
import config
import seguranca


_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _db_ident() -> str:
    """Valida e retorna o nome do banco quotado com backticks (anti-SQLi em DDL)."""
    name = config.DB_NAME
    if not _IDENT_RE.match(name or ''):
        raise ValueError("DB_NAME inválido: deve casar [A-Za-z_][A-Za-z0-9_]*")
    return "`{}`".format(name)


def conectar():
    return pymysql.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset='utf8mb4',
        autocommit=False,
    )


def _conectar_sem_db():
    return pymysql.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        charset='utf8mb4',
        autocommit=True,
    )


def dropar_e_recriar():
    ident = _db_ident()
    conn = _conectar_sem_db()
    cur = conn.cursor()
    cur.execute("DROP DATABASE IF EXISTS {}".format(ident))
    cur.execute("CREATE DATABASE {} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(ident))
    cur.close()
    conn.close()


def _criar_banco_se_nao_existir():
    ident = _db_ident()
    conn = _conectar_sem_db()
    cur = conn.cursor()
    cur.execute("CREATE DATABASE IF NOT EXISTS {} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(ident))
    cur.close()
    conn.close()


def criar_tabelas():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(120) NOT NULL,
            cpf CHAR(11) UNIQUE NOT NULL,
            cargo ENUM('Admin','Atendente','Mecânico') NOT NULL,
            telefone VARCHAR(20),
            email VARCHAR(120),
            usuario VARCHAR(50) UNIQUE NOT NULL,
            senha_hash CHAR(64) NOT NULL,
            senha_salt CHAR(32) NOT NULL,
            data_admissao DATE,
            ativo TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_func_usuario (usuario),
            INDEX idx_func_cpf (cpf)
        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(120) NOT NULL,
            cpf_cnpj VARCHAR(14) UNIQUE NOT NULL,
            telefone VARCHAR(20),
            email VARCHAR(120),
            cep CHAR(8),
            logradouro VARCHAR(150),
            numero VARCHAR(20),
            complemento VARCHAR(80),
            bairro VARCHAR(80),
            cidade VARCHAR(80),
            estado CHAR(2),
            senha_hash CHAR(64) NOT NULL,
            senha_salt CHAR(32) NOT NULL,
            ativo TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_cli_cpf (cpf_cnpj),
            INDEX idx_cli_nome (nome)
        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS caminhoes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            cliente_id INT NOT NULL,
            placa VARCHAR(10) UNIQUE NOT NULL,
            marca VARCHAR(50),
            modelo VARCHAR(80),
            ano SMALLINT,
            cor VARCHAR(30),
            chassi VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_cam_cliente FOREIGN KEY (cliente_id)
                REFERENCES clientes(id) ON DELETE CASCADE,
            INDEX idx_cam_placa (placa),
            INDEX idx_cam_cliente (cliente_id)
        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INT AUTO_INCREMENT PRIMARY KEY,
            caminhao_id INT NOT NULL,
            cliente_id INT NOT NULL,
            funcionario_id INT NOT NULL,
            data_abertura DATETIME NOT NULL,
            data_fechamento DATETIME,
            descricao_problema TEXT,
            servicos_realizados TEXT,
            pecas_utilizadas TEXT,
            valor_mao_obra DECIMAL(10,2) DEFAULT 0,
            valor_pecas DECIMAL(10,2) DEFAULT 0,
            valor_total DECIMAL(10,2) DEFAULT 0,
            status ENUM('Aberta','Em Andamento','Concluída','Cancelada') DEFAULT 'Aberta',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_os_caminhao FOREIGN KEY (caminhao_id)
                REFERENCES caminhoes(id) ON DELETE RESTRICT,
            CONSTRAINT fk_os_cliente FOREIGN KEY (cliente_id)
                REFERENCES clientes(id) ON DELETE RESTRICT,
            CONSTRAINT fk_os_funcionario FOREIGN KEY (funcionario_id)
                REFERENCES funcionarios(id) ON DELETE RESTRICT,
            INDEX idx_os_cliente (cliente_id),
            INDEX idx_os_caminhao (caminhao_id),
            INDEX idx_os_status (status)
        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            destinatario VARCHAR(120),
            assunto VARCHAR(200),
            sucesso TINYINT(1) NOT NULL,
            erro VARCHAR(500),
            enviado_em DATETIME NOT NULL
        ) ENGINE=InnoDB
    """)

    conn.commit()
    cur.close()
    conn.close()


def _criar_admin_padrao():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM funcionarios WHERE cargo='Admin'")
    if cur.fetchone()[0] == 0:
        salt = seguranca.gerar_salt()
        h = seguranca.hash_senha('admin123', salt)
        cur.execute("""
            INSERT INTO funcionarios
            (nome, cpf, cargo, telefone, email, usuario, senha_hash, senha_salt, data_admissao)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, ('Administrador', '00000000000', 'Admin', '(00) 00000-0000',
              'admin@truckstar.com', 'admin', h, salt, date.today()))
        conn.commit()
        print("[seed] Admin padrão criado. TROQUE A SENHA NO PRIMEIRO LOGIN.")
    cur.close()
    conn.close()


def inicializar(recriar: bool = False):
    """
    recriar=True dropa e recria o banco do zero.
    recriar=False só cria se não existir + cria tabelas faltantes.
    """
    if recriar:
        dropar_e_recriar()
    else:
        _criar_banco_se_nao_existir()
    criar_tabelas()
    _criar_admin_padrao()


if __name__ == '__main__':
    import sys
    recriar = '--reset' in sys.argv
    inicializar(recriar=recriar)
    print("Banco pronto. (--reset para recriar do zero)")
