"""
Validações: CPF (algoritmo oficial), CNPJ, email, placa, telefone, ano, CEP via ViaCEP.
Tudo stdlib (urllib, re, json).
"""
import re
import json
import math
import urllib.request
import urllib.error
import socket
from datetime import datetime


# Teto compatível com a coluna DECIMAL(10,2) do schema (valores monetários)
VALOR_MAX = 99_999_999.99


def _so_digitos(s: str) -> str:
    return re.sub(r'\D', '', s or '')


# ---------- CPF ----------
def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelos dígitos verificadores oficiais."""
    cpf = _so_digitos(cpf)
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    # primeiro dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = (soma * 10) % 11
    if d1 == 10:
        d1 = 0
    if d1 != int(cpf[9]):
        return False
    # segundo dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = (soma * 10) % 11
    if d2 == 10:
        d2 = 0
    return d2 == int(cpf[10])


def formatar_cpf(cpf: str) -> str:
    cpf = _so_digitos(cpf)
    if len(cpf) != 11:
        return cpf
    return "{}.{}.{}-{}".format(cpf[:3], cpf[3:6], cpf[6:9], cpf[9:])


# ---------- CNPJ ----------
def validar_cnpj(cnpj: str) -> bool:
    cnpj = _so_digitos(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    d1 = (soma % 11)
    d1 = 0 if d1 < 2 else 11 - d1
    if d1 != int(cnpj[12]):
        return False
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    d2 = soma % 11
    d2 = 0 if d2 < 2 else 11 - d2
    return d2 == int(cnpj[13])


def formatar_cnpj(cnpj: str) -> str:
    c = _so_digitos(cnpj)
    if len(c) != 14:
        return c
    return "{}.{}.{}/{}-{}".format(c[:2], c[2:5], c[5:8], c[8:12], c[12:])


def validar_cpf_ou_cnpj(doc: str) -> bool:
    d = _so_digitos(doc)
    if len(d) == 11:
        return validar_cpf(d)
    if len(d) == 14:
        return validar_cnpj(d)
    return False


def formatar_cpf_ou_cnpj(doc: str) -> str:
    d = _so_digitos(doc)
    if len(d) == 11:
        return formatar_cpf(d)
    if len(d) == 14:
        return formatar_cnpj(d)
    return d


# ---------- EMAIL ----------
EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')


def validar_email(email: str) -> bool:
    if not email or len(email) > 254:
        return False
    return EMAIL_RE.match(email.strip()) is not None


# ---------- PLACA ----------
# antiga: AAA1234  |  mercosul: AAA1A23
PLACA_RE = re.compile(r'^[A-Z]{3}[0-9][0-9A-Z][0-9]{2}$')


def validar_placa(placa: str) -> bool:
    if not placa:
        return False
    p = placa.upper().replace('-', '').replace(' ', '')
    return PLACA_RE.match(p) is not None


def formatar_placa(placa: str) -> str:
    p = (placa or '').upper().replace('-', '').replace(' ', '')
    if len(p) == 7:
        return "{}-{}".format(p[:3], p[3:])
    return p


# ---------- TELEFONE ----------
def validar_telefone(tel: str) -> bool:
    t = _so_digitos(tel)
    return len(t) in (10, 11)


def formatar_telefone(tel: str) -> str:
    t = _so_digitos(tel)
    if len(t) == 11:
        return "({}) {}-{}".format(t[:2], t[2:7], t[7:])
    if len(t) == 10:
        return "({}) {}-{}".format(t[:2], t[2:6], t[6:])
    return t


# ---------- ANO ----------
def validar_ano(ano) -> bool:
    try:
        a = int(ano)
    except (ValueError, TypeError):
        return False
    atual = datetime.now().year
    return 1950 <= a <= atual + 1


# ---------- CEP / VIACEP ----------
def buscar_cep(cep: str, timeout: int = 5) -> dict:
    """
    Consulta ViaCEP. Retorna dict com chaves:
      ok (bool), cep, logradouro, bairro, cidade, estado, erro
    Não levanta exceção - sempre retorna dict.
    """
    cep_num = _so_digitos(cep)
    resultado = {
        'ok': False, 'cep': cep_num,
        'logradouro': '', 'bairro': '', 'cidade': '', 'estado': '',
        'erro': ''
    }
    if len(cep_num) != 8:
        resultado['erro'] = 'CEP deve ter 8 dígitos'
        return resultado

    url = 'https://viacep.com.br/ws/{}/json/'.format(cep_num)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Truckstar/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8')
            dados = json.loads(raw)
    except urllib.error.URLError as e:
        resultado['erro'] = 'Sem conexão com ViaCEP: ' + str(e.reason)
        return resultado
    except socket.timeout:
        resultado['erro'] = 'Tempo esgotado consultando CEP'
        return resultado
    except (json.JSONDecodeError, ValueError) as e:
        resultado['erro'] = 'Resposta inválida do ViaCEP'
        return resultado
    except Exception as e:
        resultado['erro'] = 'Erro ao consultar CEP: ' + str(e)
        return resultado

    if dados.get('erro'):
        resultado['erro'] = 'CEP não encontrado'
        return resultado

    resultado['ok'] = True
    resultado['cep'] = dados.get('cep', cep_num)
    resultado['logradouro'] = dados.get('logradouro', '')
    resultado['bairro'] = dados.get('bairro', '')
    resultado['cidade'] = dados.get('localidade', '')
    resultado['estado'] = dados.get('uf', '')
    return resultado


def formatar_cep(cep: str) -> str:
    c = _so_digitos(cep)
    if len(c) == 8:
        return "{}-{}".format(c[:5], c[5:])
    return c


# ---------- VALOR MONETARIO ----------
def _validar_faixa(v: float) -> float:
    """Rejeita inf/nan e valores acima do teto do DECIMAL(10,2)."""
    if not math.isfinite(v):
        raise ValueError("Valor inválido (infinito ou NaN)")
    v = max(0.0, v)
    if v > VALOR_MAX:
        raise ValueError("Valor acima do máximo permitido (R$ 99.999.999,99)")
    return v


def parse_valor(s) -> float:
    """Aceita '1.234,56' ou '1234.56' ou número. Retorna float em [0, VALOR_MAX].
    Levanta ValueError se inválido, infinito, NaN ou acima do teto."""
    if isinstance(s, (int, float)):
        return _validar_faixa(float(s))
    if not s:
        return 0.0
    s = str(s).strip().replace('R$', '').replace(' ', '')
    # se tem virgula, assumir BR (1.234,56)
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        v = float(s)
    except ValueError:
        raise ValueError("Valor inválido: " + str(s))
    return _validar_faixa(v)
