# 🚀 ROADMAP - VisionLOL v3.0

## 📋 Melhorias Planejadas

### 🎮 PRIORIDADE ALTA - Integração com League of Legends

#### 1. **Detecção Automática do Jogo** ⭐⭐⭐
- [ ] Detectar quando o League of Legends está rodando
- [ ] Iniciar monitoramento automaticamente quando entrar em partida
- [ ] Pausar quando voltar ao lobby/menu
- [ ] Parar quando o jogo fechar

**Técnicas:**
- Monitorar processos (League of Legends.exe, LeagueClient.exe)
- Usar Windows API para detectar janela ativa
- Verificar título da janela para diferenciar menu/partida
- Hook no processo do jogo

#### 2. **Interface Gráfica Moderna** ⭐⭐⭐
- [ ] GUI com CustomTkinter ou PyQt5
- [ ] Botões Start/Stop/Pause
- [ ] Configurações ajustáveis em tempo real
- [ ] Preview da câmera reduzido (overlay)
- [ ] Sistema de abas (Monitor/Estatísticas/Configurações/Histórico)

#### 3. **Sistema de Controle** ⭐⭐⭐
- [ ] Modo contínuo (roda indefinidamente)
- [ ] Iniciar com Windows (opcional)
- [ ] Minimizar para system tray
- [ ] Atalhos de teclado (hotkeys)

### 📊 PRIORIDADE MÉDIA - Análise e Visualização

#### 4. **Dashboard em Tempo Real**
- [ ] Gráficos de atenção ao longo do tempo
- [ ] Heatmap de direção do olhar
- [ ] APM gráfico em tempo real
- [ ] Timeline de eventos de distração
- [ ] Indicadores visuais (gauges, barras)

#### 5. **Histórico e Estatísticas**
- [ ] Salvar sessões em banco de dados (SQLite)
- [ ] Comparar performance entre partidas
- [ ] Estatísticas por campeão
- [ ] Estatísticas por horário do dia
- [ ] Gráficos de evolução ao longo do tempo
- [ ] Exportar relatórios (PDF, CSV, JSON)

#### 6. **Alertas e Notificações**
- [ ] Alerta sonoro quando muito distraído
- [ ] Notificação de sonolência
- [ ] Vibração (se suportado)
- [ ] Overlay na tela do jogo (opcional)
- [ ] Mensagens motivacionais

### 🔧 PRIORIDADE MÉDIA - Funcionalidades Avançadas

#### 7. **Calibração Personalizada**
- [ ] Modo de calibração inicial por usuário
- [ ] Aprender padrões individuais
- [ ] Ajuste automático de thresholds
- [ ] Perfis de usuário

#### 8. **Análise de Performance no Jogo**
- [ ] Integrar com Riot API (dados da partida)
- [ ] Correlacionar distração com KDA
- [ ] Identificar momentos críticos (teamfights, objetivos)
- [ ] Sugestões de melhoria baseadas em dados

#### 9. **Recursos Adicionais**
- [ ] Detecção de emoções (frustração, raiva, felicidade)
- [ ] Contador de pausas/breaks
- [ ] Timer de sessão com lembretes
- [ ] Modo "treinamento" vs "competitivo"

### 🌐 PRIORIDADE BAIXA - Extras

#### 10. **Recursos Online**
- [ ] Upload de sessões para nuvem
- [ ] Comparação com outros jogadores
- [ ] Ranking de atenção
- [ ] Comunidade e compartilhamento

#### 11. **Múltiplos Jogos**
- [ ] Suporte para CS:GO, Valorant, Dota 2
- [ ] Templates por tipo de jogo
- [ ] Detecção automática de qual jogo está rodando

#### 12. **Acessibilidade**
- [ ] Modo daltônico
- [ ] Tamanhos de fonte ajustáveis
- [ ] Tema claro/escuro
- [ ] Suporte multi-idioma

## 🛠️ Melhorias Técnicas

### Performance
- [ ] Otimizar detecção (multithreading)
- [ ] Reduzir uso de CPU/RAM
- [ ] Cache de frames
- [ ] GPU acceleration (CUDA/OpenCL)

### Código
- [ ] Refatorar em módulos separados
- [ ] Testes unitários
- [ ] Documentação de código
- [ ] Type hints
- [ ] Logging estruturado

### Deploy
- [ ] Criar executável (PyInstaller)
- [ ] Instalador Windows
- [ ] Auto-update
- [ ] Crash reporting

## 📅 Cronograma Sugerido

### Fase 1: Core (Semana 1-2)
- Detecção automática do LoL
- Interface gráfica básica
- Sistema de controle contínuo

### Fase 2: Visualização (Semana 3-4)
- Dashboard em tempo real
- Histórico de sessões
- Alertas e notificações

### Fase 3: Avançado (Semana 5-6)
- Calibração personalizada
- Integração com Riot API
- Análise de performance

### Fase 4: Polimento (Semana 7-8)
- Otimizações
- Testes extensivos
- Executável final
- Documentação

## 💡 Ideias Futuras

- Sistema de coaching IA (sugestões baseadas em ML)
- VR/AR integration
- Streaming overlay para Twitch/YouTube
- Mobile app para visualizar estatísticas
- Wearables integration (smartwatch, fitness tracker)
- Análise de postura corporal
- Detecção de fadiga ocular
