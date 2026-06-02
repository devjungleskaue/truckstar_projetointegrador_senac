# Testes — Truckstar

Esta pasta contém a suíte de testes automatizados do sistema, separada do
código-fonte da aplicação.

## `testar_sistema.py`

Script único que valida **todas as funcionalidades do sistema** e imprime o
resultado no terminal, com contagem de aprovados/reprovados e código de saída
apropriado (`0` = tudo passou, `1` = houve falha).

### Para que serve

Verificação rápida de que o sistema está íntegro — útil antes de entregar,
apresentar ou empacotar. Cada funcionalidade tem um teste objetivo que passa
ou falha, sem depender de clicar na interface.

### Como executar

A partir da **raiz do projeto** (a pasta que contém `main.py` e `config.py`):

```bash
py tests/testar_sistema.py            # 63 testes (validações, segurança, banco, CRUD, email, PDF)
py tests/testar_sistema.py --rede     # inclui consulta real ao ViaCEP (precisa de internet)
py tests/testar_sistema.py --email    # inclui envio real via Resend (consome cota gratuita)
```

> O script lê o `config.py` da raiz para conectar ao MySQL. Garanta que o
> banco está acessível antes de rodar.

### O que é testado

| Seção | Cobertura |
|-------|-----------|
| 1. Validações | CPF, CNPJ, e-mail, placa (antiga e Mercosul), telefone, ano, CEP, valores monetários (incl. rejeição de `inf`/`NaN`/overflow) |
| 2. Segurança | Hash PBKDF2-SHA256, geração de salt, verificação de senha (timing-safe) |
| 3. Banco de dados | Conexão, schema (5 tabelas), context manager `db.cursor()`, rollback automático em erro |
| 4. CRUD completo | Ciclo real cliente → caminhão → ordem de serviço → consulta → atualização, usando as mesmas queries das telas; valida FK RESTRICT |
| 5. Templates de e-mail | Geração dos 3 e-mails (OS criada, OS atualizada, boas-vindas) + escape de HTML |
| 6. Geração de PDF | PDF da Ordem de Serviço, incluindo caracteres especiais (`<`, `>`, `&`) |
| 7. Rede / e-mail | (Opcionais) ViaCEP e envio real via Resend |

### Isolamento dos dados

Os testes de CRUD criam registros temporários identificados por um CPF e uma
placa reservados (`ZZTESTE`). **Todos são removidos automaticamente ao final**,
mesmo se algum teste falhar — o banco volta ao estado anterior. Ao final, o
script ainda reporta `Threads_connected` do MySQL para confirmar que nenhuma
conexão ficou aberta (verificação de *connection leak*).

### Exemplo de saída

```
-- 1. VALIDAÇÕES (validacoes.py) -----------------------------
  [OK]      CPF válido aceito
  [OK]      CPF inválido rejeitado
  ...

================================================================
 RESUMO
  Passaram: 63   Falharam: 0   Pulados: 1   (de 63 testes executados)

  Taxa de sucesso: 100%

 RESULTADO: TODOS OS TESTES PASSARAM [OK]
================================================================
```
