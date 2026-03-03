# Melhorias no Sistema de Detecção de Distração

## Resumo das Mudanças

### 1. **Correção do Bug Principal**
- ❌ **Problema**: MediaPipe 0.10.32+ removeu o módulo `solutions`
- ✅ **Solução**: Substituído por OpenCV Haar Cascades (mais leve e confiável)

### 2. **Suporte para Óculos**
Implementado sistema híbrido de detecção de olhos:
- Usa `haarcascade_eye.xml` para detecção padrão
- Usa `haarcascade_eye_tree_eyeglasses.xml` para usuários com óculos
- Tenta múltiplos parâmetros de detecção (scaleFactor, minNeighbors)
- Funciona com óculos normais, de grau e até óculos escuros (com limitações)

### 3. **Detecção Multi-Fator de Distração**

O sistema agora detecta **4 tipos principais de distração**:

#### a) **Posição do Rosto**
- Detecta se o usuário está olhando muito para os lados (< 25% ou > 75% horizontal)
- Detecta se a cabeça está muito alta/baixa (postura incorreta)
- Detecta se o rosto está muito longe da câmera

#### b) **Movimento Excessivo da Cabeça**
- Analisa últimos 5 frames de posição do rosto
- Calcula movimento médio
- Alerta se movimento > 50 pixels (instabilidade/ansiedade)

#### c) **Sonolência**
- Monitora últimos 10-15 frames
- Conta quantos frames não detectam olhos
- Se > 40% dos frames sem olhos = alerta de sonolência
- Contador de "piscadas" longas

#### d) **Ausência de Rosto**
- Só alerta após 5+ frames consecutivos sem detecção
- Evita falsos positivos de detecção momentânea

### 4. **Sistema de Confiança Adaptativo**
- **Alta confiança (85-90%)**: Múltiplos indicadores de distração
- **Média confiança (50-70%)**: Detecção com rosto presente
- **Baixa confiança (30%)**: Primeiros frames sem rosto

### 5. **Visualização Melhorada**
```
FOCADO / DISTRAIDO / MUITO DISTRAIDO (cores diferentes)
Motivo: posicao_rosto, movimento_cabeca, sonolencia
Olhar: ESQUERDA / CENTRO / DIREITA
Confianca: 85%
Distracoes: 3
ALERTA: Possivel sonolencia! (se detectado)
```

### 6. **Redução de Falsos Positivos**
- **Frames consecutivos**: Só registra distração após 3+ frames
- **Cooldown de eventos**: Mínimo 2 segundos entre registros de distração
- **Benefício da dúvida**: Primeiros frames sem rosto não contam como distração

## Parâmetros Ajustáveis

### Sensibilidade de Detecção
```python
# Em analyze_attention() - linha 168
minNeighbors=4  # Aumentar = menos sensível, menos falsos positivos
minSize=(100, 100)  # Aumentar = só detecta rostos maiores/próximos
```

### Thresholds de Olhar
```python
# Em detect_gaze_direction() - linhas 82-86
offset_ratio > 0.08  # Ajustar para mudar sensibilidade DIREITA
offset_ratio < -0.08  # Ajustar para mudar sensibilidade ESQUERDA
```

### Movimento da Cabeça
```python
# Em detect_head_movement() - linha 118
avg_movement > 50  # Aumentar = menos sensível a movimento
```

### Sonolência
```python
# Em detect_drowsiness() - linha 132
no_eyes_count > 4  # Aumentar = mais tolerante (40% -> outro valor)
```

## Como Usar

### Execução Normal
```bash
.venv\Scripts\python.exe .venv\main.py
```

### Teste de Detecção (sem câmera)
```bash
.venv\Scripts\python.exe test_detection.py
```

### Ajustando Duração
```python
# No final do main.py - linha 373
monitor.run(duration=30)  # Mudar para quantidade de segundos desejada
```

## Métricas Coletadas

- **Direção do olhar**: Histórico de últimos 30 frames
- **Eventos de distração**: Timestamps de todas as distrações
- **APM (Actions Per Minute)**: Teclas + cliques
- **Inputs**: Últimas 100 teclas e 100 cliques
- **Posições do rosto**: Últimas 10 posições
- **Detecção de olhos**: Últimos 15 frames

## Relatório Final

Após executar, o sistema gera um relatório com:
- Duração total da sessão
- Número de eventos de distração
- Total de teclas pressionadas
- Total de cliques do mouse
- APM médio
- Distribuição do olhar (% ESQUERDA/CENTRO/DIREITA)

## Limitações Conhecidas

1. **Óculos escuros/muito reflexivos**: Pode ter dificuldade em detectar olhos
2. **Iluminação muito baixa**: Haar Cascades precisam de boa iluminação
3. **Múltiplas pessoas**: Sistema focado em 1 jogador (pega o maior rosto)
4. **Performance**: ~30 FPS em hardware moderno

## Próximas Melhorias Possíveis

- [ ] Suporte para múltiplos jogadores
- [ ] Detecção de emoções (frustração, raiva)
- [ ] Heatmap de olhar na tela
- [ ] Integração com análise de jogo (correlacionar distração com performance)
- [ ] Modo noturno (detecção em baixa luminosidade)
- [ ] Calibração automática por usuário
