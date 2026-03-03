# 📝 Guia de Logging - VisionLOL

## 🎯 Sistema de Logging Implementado

O VisionLOL agora possui um **sistema completo de logging** para identificar erros e debug!

---

## 📂 Localização dos Logs

### Pasta de Logs
```
VisionLOL/
└── logs/
    └── visionlol_YYYYMMDD_HHMMSS.log
```

**Exemplo:**
```
logs/visionlol_20260203_234008.log
```

Cada execução cria um novo arquivo de log com timestamp.

---

## 📊 Níveis de Log

### DEBUG
Informações detalhadas para diagnóstico
```
2026-02-03 23:40:08 | DEBUG | PlayerMonitor | Configurando propriedades da camera...
```

### INFO
Informações gerais de fluxo
```
2026-02-03 23:40:08 | INFO | GUI | INICIANDO MONITORAMENTO
```

### WARNING
Avisos que não param a execução
```
2026-02-03 23:40:10 | WARNING | GUI | Falha ao ler frame da camera! (erro #1)
```

### ERROR
Erros que afetam funcionalidade
```
2026-02-03 23:40:12 | ERROR | PlayerMonitor | Camera nao abriu!
```

### CRITICAL / EXCEPTION
Erros graves com traceback completo
```
2026-02-03 23:40:15 | ERROR | GUI | ERRO AO INICIAR MONITORAMENTO!
2026-02-03 23:40:15 | ERROR | GUI | Traceback (most recent call last):
  File ...
```

---

## 🔍 O Que é Logado

### Na Inicialização da GUI
```
============================================================
Inicializando VisionLOL GUI v3.5
============================================================
Estado inicial criado
Configurando estilo visual...
Criando widgets da interface...
Iniciando verificacao de status do jogo...
Iniciando loop de preview da camera...
GUI inicializada com sucesso!
Aguardando comandos do usuario...
```

### Ao Clicar em INICIAR
```
============================================================
INICIANDO MONITORAMENTO
============================================================
Passo 1: Criando PlayerMonitor...
Parametros: auto_start_camera=True, show_debug=False
Tentando abrir camera (indice 0)...
cv2.VideoCapture criado: True
Configurando propriedades da camera...
Camera isOpened(): True
Descartando primeiros 3 frames...
Frame 1/3: ret=True, shape=(480, 640, 3)
Frame 2/3: ret=True, shape=(480, 640, 3)
Frame 3/3: ret=True, shape=(480, 640, 3)
Camera aberta e pronta com sucesso!
PlayerMonitor criado com sucesso!
Camera aberta: True
Camera OK: True
Passo 2: Configurando parametros de monitoramento...
Session start time: 1704324008.123
Passo 3: Iniciando monitoramento de inputs (teclado/mouse)...
Input monitoring iniciado!
Passo 4: Atualizando interface...
Interface atualizada!
Passo 5: Iniciando thread de processamento...
Thread iniciada! Thread ID: 12345
============================================================
MONITORAMENTO INICIADO COM SUCESSO!
============================================================
Thread de monitoramento iniciada!
Thread ID: 12345
```

### Durante o Monitoramento
```
Frame #100 processado. Camera funcionando normalmente.
Frame #200 processado. Camera funcionando normalmente.
```

### Se Houver Erros
```
Falha ao ler frame da camera! (erro #1)
Falha ao ler frame da camera! (erro #2)
...
Camera voltou ao normal apos 2 erros
```

### Ao Parar
```
Thread de monitoramento finalizada. Total de frames: 523
```

---

## 🐛 Como Usar os Logs para Debug

### Problema: Câmera não abre

#### 1. Abra a GUI e clique em INICIAR
```bash
.venv\Scripts\python.exe gui_app_integrated.py
```

#### 2. Vá até a pasta logs/
```bash
cd logs
```

#### 3. Abra o arquivo mais recente
```bash
notepad visionlol_YYYYMMDD_HHMMSS.log
```

#### 4. Procure por:
```
Camera isOpened(): False
```

Você verá as possíveis causas listadas:
```
Camera nao abriu! Possiveis causas:
  1. Camera em uso por outro programa
  2. Camera nao conectada
  3. Drivers da camera com problema
  4. Permissoes negadas
```

---

## 📖 Exemplos de Logs de Erro

### Erro: Câmera em Uso
```
2026-02-03 23:45:10 | INFO     | PlayerMonitor | Tentando abrir camera (indice 0)...
2026-02-03 23:45:10 | DEBUG    | PlayerMonitor | cv2.VideoCapture criado: True
2026-02-03 23:45:10 | DEBUG    | PlayerMonitor | Configurando propriedades da camera...
2026-02-03 23:45:10 | DEBUG    | PlayerMonitor | Camera isOpened(): False
2026-02-03 23:45:10 | ERROR    | PlayerMonitor | Camera nao abriu! Possiveis causas:
2026-02-03 23:45:10 | ERROR    | PlayerMonitor |   1. Camera em uso por outro programa
2026-02-03 23:45:10 | ERROR    | PlayerMonitor |   2. Camera nao conectada
2026-02-03 23:45:10 | ERROR    | PlayerMonitor |   3. Drivers da camera com problema
2026-02-03 23:45:10 | ERROR    | PlayerMonitor |   4. Permissoes negadas
```

**Solução**: Feche programas usando câmera (Zoom, Teams, Skype)

---

### Erro: Frames Não Lidos
```
2026-02-03 23:50:15 | INFO     | GUI | Thread de monitoramento iniciada!
2026-02-03 23:50:15 | WARNING  | GUI | Falha ao ler frame da camera! (erro #1)
2026-02-03 23:50:15 | WARNING  | GUI | Falha ao ler frame da camera! (erro #2)
2026-02-03 23:50:15 | WARNING  | GUI | Falha ao ler frame da camera! (erro #3)
...
2026-02-03 23:50:20 | ERROR    | GUI | Muitos erros consecutivos ao ler camera! Encerrando...
```

**Solução**: Câmera foi desconectada durante uso ou falha de hardware

---

### Erro: Exception no Loop
```
2026-02-03 23:55:10 | ERROR    | GUI | Erro no loop de monitoramento (frame #234)
2026-02-03 23:55:10 | ERROR    | GUI | Traceback (most recent call last):
  File "gui_app_integrated.py", line 435, in monitoring_loop
    attention_data, display_frame = self.player_monitor.analyze_attention(frame)
  File "main.py", line 200, in analyze_attention
    ...
AttributeError: 'NoneType' object has no attribute 'shape'
```

**Solução**: Bug no código, verificar linha indicada

---

## 🛠️ Comandos Úteis

### Ver últimos logs
```bash
# Windows
cd logs
type visionlol_*.log | findstr "ERROR"

# Linux/Mac
cat logs/visionlol_*.log | grep ERROR
```

### Ver apenas INFOs
```bash
type visionlol_*.log | findstr "INFO"
```

### Ver apenas WARNINGs e ERRORs
```bash
type visionlol_*.log | findstr /C:"WARNING" /C:"ERROR"
```

### Contar erros
```bash
type visionlol_*.log | findstr "ERROR" | find /c "ERROR"
```

---

## 📱 Console vs Arquivo

### Console (Terminal)
- Mostra apenas **INFO** e acima
- Logs em tempo real
- Boa para acompanhar execução

### Arquivo (logs/)
- Mostra **DEBUG** e acima
- Permanente (não desaparece)
- Boa para análise posterior
- Inclui tracebacks completos

---

## 🔧 Configurar Logging

### Desabilitar logs em arquivo
```python
from logger import VisionLogger

logger = VisionLogger(
    name="VisionLOL",
    log_to_file=False,  # Desabilita arquivo
    log_to_console=True
)
```

### Desabilitar logs no console
```python
logger = VisionLogger(
    name="VisionLOL",
    log_to_file=True,
    log_to_console=False  # Desabilita console
)
```

### Ambos desabilitados
```python
logger = VisionLogger(
    name="VisionLOL",
    log_to_file=False,
    log_to_console=False
)
```

---

## 📊 Formato do Log

```
TIMESTAMP | NÍVEL | MÓDULO | MENSAGEM
```

**Exemplo:**
```
2026-02-03 23:40:08 | INFO | GUI | Monitoramento iniciado!
│                     │      │     └─ Mensagem
│                     │      └─ Módulo (GUI, PlayerMonitor, etc)
│                     └─ Nível (DEBUG, INFO, WARNING, ERROR)
└─ Timestamp (YYYY-MM-DD HH:MM:SS)
```

---

## 💡 Dicas

### Para Reportar Bugs
1. Reproduza o erro
2. Vá em `logs/`
3. Copie o arquivo mais recente
4. Envie junto com descrição do problema

### Para Debug Próprio
1. Procure por `ERROR` no arquivo
2. Leia as linhas antes do erro (contexto)
3. Veja o traceback completo
4. Identifique a linha exata do código

### Logs Antigos
- Logs não são deletados automaticamente
- Você pode deletar logs antigos manualmente
- Cada log ~5-50 KB dependendo da duração

---

## 🎯 Checklist de Debug

Quando a câmera não funciona:

- [ ] Verifique se há arquivo de log em `logs/`
- [ ] Abra o log mais recente
- [ ] Procure por `Camera isOpened(): False`
- [ ] Veja possíveis causas listadas
- [ ] Verifique se há `ERROR` ou `EXCEPTION`
- [ ] Leia o traceback completo se houver
- [ ] Identifique a linha do código problemática
- [ ] Tente soluções sugeridas no log

---

## 📁 Estrutura de Arquivos

```
VisionLOL/
├── logger.py                    # Módulo de logging
├── gui_app_integrated.py        # GUI com logs
├── .venv/
│   └── main.py                  # PlayerMonitor com logs
└── logs/                        # Pasta de logs (criada automaticamente)
    ├── visionlol_20260203_234008.log
    ├── visionlol_20260203_234521.log
    └── ...
```

---

**Agora você tem logging completo para identificar qualquer erro! 🎉**

**Para usar:**
1. Execute a GUI normalmente
2. Se der erro, vá em `logs/`
3. Abra o arquivo mais recente
4. Encontre o erro e corrija!
