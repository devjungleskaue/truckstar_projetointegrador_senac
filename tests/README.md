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
py tests/testar_sistema.py            # 62 testes (validações, segurança, banco, CRUD, email, PDF)
py tests/testar_sistema.py --rede     # inclui consulta real ao ViaCEP (precisa de internet)
py tests/testar_sistema.py --email    # inclui envio real via Resend (consome cota gratuita)
```

> O script lê o `config.py` da raiz para conectar ao MySQL. Garanta que o
> banco está acessível antes de rodar.

> **Sobre os 2 testes opcionais (`--rede`/`--email`):** eles acessam a internet
> (ViaCEP e Resend). Em redes com firewall restritivo (ex: Wi-Fi institucional)
> ficam bloqueados; numa rede sem restrição passam normalmente. Por isso ficam
> **fora** da execução padrão — os 62 testes core não dependem de internet, e a
> **taxa de 100%** se refere a eles. Com a rede liberada e as flags, o total
> também fecha em 100%.

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
  Passaram: 62   Falharam: 0   Pulados: 2   (de 62 testes executados)

  Taxa de sucesso: 100%

 RESULTADO: TODOS OS TESTES PASSARAM [OK]
================================================================
```
