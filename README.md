<p align="center">
  <img src="docs/screenshots/banner.png" alt="VisionLOL" width="100%"/>
</p>

Ferramenta de análise e monitoramento de performance para times de League of Legends.
Integração completa com a Riot Games API para acompanhamento de soloq, scrims e estatísticas individuais.

![Team Viewer](docs/screenshots/team_viewer.png)

---

## Funcionalidades

### Roster do Time
- Gerenciamento de 5 jogadores com roles (TOP / JG / MID / ADC / SUP)
- Suporte a múltiplas contas por jogador (smurfs / alts)
- Stats agregadas de todas as contas: WR%, KDA médio, top campeões e histórico das últimas partidas
- Indicador ao vivo — detecta se o jogador está em partida no momento

![Roster](docs/screenshots/roster.png)

### Radar de Performance

- 6 métricas normalizadas por role: KDA · CS/min · Visão/min · Gold/min · Damage Share · Kill Participation
- Benchmarks por role (TOP/JGL/MID/ADC/SUP) baseados em padrão pro/soloq alto
- Radar individual por jogador e visão geral do time em grid

![Performance Radar](docs/screenshots/Performance.png)

### Evolução Temporal do Jogador *(novo)*

- Gráfico de linha mostrando a evolução de KDA, CS/min e Vision/min ao longo das últimas 20 partidas
- Linha de benchmark de role para referência
- Pontos coloridos por resultado (vitória/derrota) com tooltip interativo

### Champion Pool por Jogador *(novo)*

- Tabela com estatísticas por campeão: partidas, WR%, KDA médio, CS/min, Vision/min
- Ícones de campeão carregados automaticamente
- Exportação da tabela para clipboard (tab-separated)

### Dashboard de Partidas

- Histórico detalhado das últimas partidas
- Pool de campeões com WR% e KDA por campeão
- Mapa de calor de atividade (heatmap) por partida, gerado a partir das timelines

![Dashboard](docs/screenshots/Dashboard.png)

### Replay Viewer

- Visualização quadro a quadro das posições dos jogadores no mapa
- Rastreamento de abates, objetivos e estruturas destruídas
- Análise de ward lifetimes e movimentação por lane

![Replay Viewer](docs/screenshots/Replay.png)

### Scrims Dashboard

- Registro e acompanhamento de sessões de scrim contra outros times
- Seletor visual de partidas recentes (sem precisar de Match ID)
- Comparativo de métricas por partida e por jogador
- Integração com Discord Webhook — posta resultados formatados direto no canal do time *(novo)*

![Scrims Dashboard](docs/screenshots/Scrims.png)

### Captura de Scrims com Custom Games *(novo)*

Para partidas personalizadas (não visíveis na Match V5 API), o VisionLOL usa uma arquitetura distribuída:

- **VisionLOL.exe** — servidor embutido que recebe dados dos agentes (porta 7654)
- **VisionLOLAgent.exe** — app leve instalado no PC de cada jogador; monitora a Live Client API durante a partida e envia os dados automaticamente ao fim do jogo

```
[PC Jogador 1]  VisionLOLAgent ─┐
[PC Jogador 2]  VisionLOLAgent ─┤  HTTP POST
[PC Jogador 3]  VisionLOLAgent ─┼──► VisionLOL (servidor :7654)
[PC Jogador 4]  VisionLOLAgent ─┤         ↓
[PC Jogador 5]  VisionLOLAgent ─┘   Scrims Dashboard
```

Compatível com LAN e internet. Autenticação por token Bearer gerado automaticamente.

---

## Instalação

### Requisitos

- Python 3.10+
- Chave de API da Riot Games (ver abaixo)

### Passos

```bash
# 1. Clone o repositório
git clone https://github.com/Gor0d/VisionLOL.git
cd VisionLOL

# 2. Crie e ative o ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure a API key
cp config.example.json config.json
# Edite config.json e insira sua Riot API key
# (ou configure diretamente na aba Config do app)
```

### Dependências principais

```
Pillow
requests
numpy
opencv-contrib-python
flask
pynput
psutil
```

---

## Configuração da Riot API Key

1. Acesse [developer.riotgames.com](https://developer.riotgames.com)
2. Faça login com sua conta Riot
3. Gere uma **Development API Key** (válida por 24h) ou solicite uma **Personal/Production Key**
4. Cole a chave no app — aba **Config** → campo **API Key** → Salvar

Ou diretamente no `config.json`:

```json
{
    "riot_api_key": "RGAPI-sua-chave-aqui",
    "game_name": "SeuNomeIngame",
    "tag_line": "BR1",
    "region": "br1",
    "routing": "americas",
    "discord_webhook": "",
    "scrim_server": {
        "enabled": false,
        "port": 7654,
        "token": ""
    }
}
```

> **Regiões disponíveis**
> | Servidor | `region` | `routing` |
> |----------|----------|-----------|
> | Brasil | `br1` | `americas` |
> | NA | `na1` | `americas` |
> | EUW | `euw1` | `europe` |
> | KR | `kr` | `asia` |

---

## Uso

```bash
python gui_app_integrated.py
```

Na aba **Time**, configure o roster com os Riot IDs dos jogadores (formato `NomeIngame#TAG`).
Os dados são carregados automaticamente da API.

Para cada jogador, os botões de ação disponíveis são:
- **📊** Dashboard de partidas (heatmap, histórico)
- **🕸** Radar de performance (6 métricas vs. benchmarks de role)
- **📈** Evolução temporal (KDA, CS/min, Vision/min ao longo do tempo)
- **🏆** Champion pool (estatísticas por campeão)

---

## Estrutura do Projeto

```
VisionLOL/
├── gui_app_integrated.py      # Ponto de entrada — GUI principal
├── main.py                    # PlayerMonitor (monitoramento de câmera/atenção)
├── game_detector.py           # Detecção de processo do League of Legends
├── logger.py                  # Logger centralizado
├── config.example.json        # Template de configuração
├── requirements.txt
│
├── agent/
│   ├── agent_main.py          # VisionLOLAgent — app de captura por jogador
│   └── agent_config.py        # Gerenciamento de config do agente
│
├── docs/
│   └── screenshots/           # Imagens do README
│
└── riot_api/
    ├── config.py              # Endpoints e config da Riot API
    ├── riot_http.py           # Cliente HTTP com rate limiting
    ├── match_api.py           # Match-V5 + Account-V1 + Spectator-V5
    ├── live_client.py         # Live Client API (dados em partida)
    ├── map_visualizer.py      # Download e renderização do minimap
    ├── team_viewer.py         # Aba de roster do time
    ├── performance_radar.py   # Radar de performance (6 métricas)
    ├── evolution_viewer.py    # Evolução temporal (gráfico de linha)
    ├── champion_pool.py       # Champion pool por jogador
    ├── dashboard_viewer.py    # Dashboard com heatmap
    ├── replay_viewer.py       # Replay quadro a quadro
    ├── replay_engine.py       # Motor de replay (timeline processing)
    ├── scrim_dashboard.py     # Dashboard de scrims + Discord webhook
    ├── scrim_server.py        # Servidor Flask embutido (captura ao vivo)
    ├── pathing_visualizer.py  # Visualização de movimentação
    ├── proximity_tracker.py   # Rastreamento de proximidade ao vivo
    ├── reaction_analyzer.py   # Análise de tempo de reação
    └── data_correlator.py     # Correlação atenção × eventos do jogo
```

---

## Aviso Legal

VisionLOL não é endossado pela Riot Games e não reflete as opiniões da Riot Games ou de qualquer pessoa envolvida na produção ou gerenciamento de League of Legends. League of Legends e Riot Games são marcas registradas da Riot Games, Inc.

Este projeto usa a [Riot Games API](https://developer.riotgames.com/) e está sujeito à [Política de Uso da API da Riot](https://developer.riotgames.com/policies/general).

---

## Licença

[MIT](LICENSE)
