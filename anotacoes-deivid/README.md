
# EDW - Root Cause Analysis & Alert Correlation

> Documentação da descoberta dos cenários de falha EDW e regra de correlação para Keep / Grafana

## 🎯 Objetivo

Reduzir de **7 tickets para 1 ticket** quando o EDW ou Technology One falham, e documentar falha silenciosa dos Workers.

Substitui regra cara do Splunk (correlation search) por workflow no Keep.

## 🧪 Cenários Testados

### 1. EDW-DB Down

- **Ação:** stop EDW-DB
- **Alarmes:** `edw is running but its database is unreachable` **[REAL ROOT]** + 6 sintomas STUDENT/GENERAL/CURRICULUM
- **Obs:** O próprio EDW-DB não tem alarme!

### 2. EDW-APP Down

- **Alarmes:** `EDW cannot be scraped` + `Technology One (SM) cannot be scraped` **[REAL ROOT]** + 6 sintomas

### 3. T1-SM-DB Down (technology-one-sm-DB)

- **Alarmes:** `technology-one-sm is running but its database is unreachable` **[REAL ROOT]**

### 4. T1-SM-APP Down (Technology One SM App)

- **Alarmes:** `Technology One (SM) cannot be scraped` **[REAL ROOT]** + 6 sintomas

### 5. 🔴 BURACO CEGO - Workers Down

- **Ação:** EDW-STUDENT / GENERAL / CURRICULUM workers down
- **Alarmes:** NENHUM! 0 alarmes! Falha silenciosa
- **Risco:** Se worker morre, só descobre com `no successful run 90s` ou cliente reclamando

## 🌳 Mapa de Dependência

EDW-DB | EDW-APP | T1-SM-DB | T1-SM-APP
            v
REAL ROOT ALARMS (Name=EDW) -> unreachable / cannot be scraped
            v
SYMPTOMS -> STUDENT/GENERAL/CURRICULUM - latest failed (target edw)

## ✅ Regra de Ouro - Keep

IF Name == EDW AND Description contains (unreachable OR cannot be scraped):
  -> ROOT - ABRE 1 TICKET: "EDW DOWN - Impactando STUDENT, GENERAL, CURRICULUM"ELSE IF STUDENT/GENERAL/CURRICULUM AND existe ROOT EDW nos últimos 5 min:
  -> SINTOMA - NÃO ABRE TICKET, vira Warning



**Antes:** 7 tickets | **Depois:** 1 ticket

## 🚨 TODO - Corrigir Buraco Cego

Criar alerta Grafana:

absent(up{job="edw-student-worker"}) == 1


Nomes: `EDW-WORKER-STUDENT - worker down`, etc.

## 📂 Estrutura

/keep-workflows/edw-correlation.yaml
/docs/images/ (prints dos 4 cenários)
README.md
