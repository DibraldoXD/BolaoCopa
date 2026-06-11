# ⚽ Copa 2026 — Bolão Inteligente

> Plataforma web que combina um **bolão de palpites** da Copa do Mundo 2026 com um **motor de previsão por IA** baseado em simulação Monte Carlo e modelos estatísticos.

![Design](pics/image.png)

---

## ✨ Funcionalidades

### Bolão
| Recurso | Descrição |
|---|---|
| **Cadastro com senha** | Registro por nome, e-mail, telefone e senha (PBKDF2-SHA256) |
| **Palpites de grupos** | Top 3 seleções por grupo (A–L), bloqueados ao início do torneio |
| **Palpites de jogos** | Placar exato para cada partida, bloqueado ao início da partida |
| **Chave mata-mata** | R32 gerado automaticamente a partir dos palpites de grupo |
| **Classificação ao vivo** | Ranking com pontuação em tempo real, atualizado a cada 60 s |
| **Painel admin** | Entrada de resultados oficiais para cálculo automático dos pontos |

### Previsões IA
| Recurso | Descrição |
|---|---|
| **Probabilidades** | Chance de título de cada seleção, baseada em 1.000 simulações Monte Carlo |
| **Simulação ao vivo** | Simulação completa do torneio (fase de grupos → final) em tempo real |
| **Explorador de partidas** | xG e probabilidades V/E/D para qualquer confronto entre as 48 seleções |

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| **Frontend** | [Streamlit](https://streamlit.io) — tema ouro/verde Copa |
| **Banco (bolão)** | [Supabase](https://supabase.com) (PostgreSQL + Row Level Security) |
| **Banco (ML)** | PostgreSQL direto via SQLAlchemy/psycopg2 |
| **Modelo preditivo** | GLM Poisson (statsmodels) |
| **Rating** | Sistema ELO sequencial (K-factor por importância do torneio) |
| **Simulação** | Monte Carlo (scipy, numpy) — 1.000 iterações |
| **Bandeiras** | [flagcdn.com](https://flagcdn.com) via `<img>` tags |
| **Empacotamento** | [uv](https://docs.astral.sh/uv/) |

---

## 🏗️ Arquitetura

```
Copa/
├── app.py                  # Entry point: st.navigation, auth, sidebar
├── app_pages/
│   ├── register.py         # Cadastro + login com senha
│   ├── groups.py           # Palpites de grupos (@st.fragment por card)
│   ├── matches.py          # Palpites de placares
│   ├── bracket.py          # Chave mata-mata
│   ├── leaderboard.py      # Classificação ao vivo + projeção IA
│   ├── admin.py            # Resultados oficiais (admin only)
│   ├── probabilidades.py   # Gráfico de probabilidades por fase
│   ├── simulacao.py        # Simulação completa ao vivo
│   └── explorador.py       # Explorador de confrontos
├── src/
│   ├── db.py               # Supabase queries (@st.cache_data)
│   ├── pg_conn.py          # Conexão PostgreSQL (pipeline ML)
│   ├── bandeiras.py        # Flags + traduções PT-BR
│   ├── utils.py            # flag_img() via flagcdn.com
│   ├── bracket.py          # Lógica R32 da Copa 2026
│   ├── scoring.py          # Cálculo de ranking
│   ├── previsao.py         # Wrapper do modelo para o Streamlit
│   ├── monte_carlo.py      # Simulação Monte Carlo
│   ├── poisson.py          # Distribuição Poisson conjunta
│   ├── ingest_bronze.py    # Ingestão de dados brutos
│   ├── transform_silver.py # Padronização e limpeza
│   ├── transform_ponderado.py # Pesos por torneio e recência
│   ├── compute_elo.py      # Cálculo do rating ELO
│   ├── build_gold.py       # Tabela de atributos para treino
│   ├── train_model.py      # Treino dos modelos GLM Poisson
│   ├── predict.py          # Previsão dos jogos da Copa 2026
│   └── simulate.py         # Monte Carlo 1.000 simulações
├── models/                 # Modelos treinados (.pkl)
├── data/
│   ├── grupos_copa2026.csv     # Configuração dos 12 grupos
│   └── calendario_copa2026.csv # Calendário de jogos (mata-mata)
└── .streamlit/
    └── config.toml         # Tema gold/green (secrets.toml — não commitado)
```

### Pipeline de dados (Medallion)

```
results.csv (histórico 2006–2026)
    ↓ ingest_bronze.py
bronze_jogos (PostgreSQL)
    ↓ transform_silver.py
silver_jogos + silver_copa2026
    ↓ transform_ponderado.py
silver_ponderado
    ↓ compute_elo.py
silver_elo_pre_jogo + silver_elo_atual
    ↓ build_gold.py
gold_atributos
    ↓ train_model.py
models/*.pkl  →  predict.py  →  simulate.py  →  gold_probabilidades_copa
```

---

## ⚙️ Setup local

### Pré-requisitos
- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Projeto Supabase configurado
- PostgreSQL acessível (para o pipeline ML)

### 1. Clonar e instalar

```bash
git clone https://github.com/DibraldoXD/Copa.git
cd Copa
uv sync
```

### 2. Configurar credenciais

Crie `.streamlit/secrets.toml`:
```toml
[supabase]
url      = "https://seu-projeto.supabase.co"
anon_key = "sua-anon-key"

# Para o pipeline ML (conexão direta ao PostgreSQL)
DATABASE_URL = "postgresql://user:pass@host:5432/db"
```

Crie `.env` (para rodar scripts ML fora do Streamlit):
```env
DATABASE_URL=postgresql://user:pass@host:5432/db
```

### 3. Rodar o app

```bash
uv run streamlit run app.py
```

### 4. (Opcional) Rodar o pipeline ML

Execute na ordem:
```bash
uv run python -m src.ingest_bronze       # carrega dados históricos
uv run python -m src.transform_silver    # padroniza e filtra
uv run python -m src.transform_ponderado # adiciona pesos
uv run python -m src.compute_elo         # calcula ratings ELO
uv run python -m src.build_gold          # monta tabela de treino
uv run python -m src.train_model         # treina modelos (.pkl)
uv run python -m src.predict             # gera previsões dos jogos
uv run python -m src.simulate            # Monte Carlo 1.000x
```

---

## 🗄️ Banco de dados (Supabase)

### Tabelas do bolão
| Tabela | Descrição |
|---|---|
| `users` | Participantes (nome, e-mail, telefone, senha hash) |
| `teams` | 48 seleções com nomes em PT-BR e bandeiras |
| `matches` | 104 jogos da Copa 2026 |
| `group_predictions` | Palpites de grupo (top 3 por grupo) |
| `match_predictions` | Palpites de placar por jogo |
| `group_results` | Resultados oficiais dos grupos |
| `leaderboard` | View SQL com pontuação calculada automaticamente |

### Tabelas do pipeline ML
| Tabela | Descrição |
|---|---|
| `bronze_jogos` | Dados brutos históricos (19.800+ jogos) |
| `silver_jogos` | Dados padronizados (2006–2025, sem amistosos) |
| `silver_copa2026` | 72 jogos da fase de grupos da Copa 2026 |
| `silver_ponderado` | Com pesos por torneio e recência |
| `silver_elo_pre_jogo` | Rating ELO pré-jogo (anti-leakage) |
| `silver_elo_atual` | Rating ELO atual de cada seleção |
| `gold_atributos` | Features para treino do modelo |
| `gold_probabilidades_copa` | Probabilidades Monte Carlo por fase |

### Pontuação do bolão
| Acerto | Pontos |
|---|---|
| Seleção na posição exata do grupo (1°, 2° ou 3°) | 10 pts |
| Seleção no grupo, posição errada | 5 pts |
| Placar exato do jogo | 3 pts |
| Resultado correto (V/E/D) | 1 pt |

---

## 🚀 Deploy (Streamlit Cloud)

1. Faça o fork ou push para o GitHub
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte o repositório
3. Main file: `app.py`
4. Em **Secrets**, adicione o conteúdo do `secrets.toml`

---

## 📋 Variáveis de ambiente necessárias

| Variável | Onde | Descrição |
|---|---|---|
| `supabase.url` | secrets.toml | URL do projeto Supabase |
| `supabase.anon_key` | secrets.toml | Chave anônima do Supabase |
| `DATABASE_URL` | secrets.toml / .env | Connection string PostgreSQL para ML |

---

## 🤖 Modelo preditivo

- **Dados de treino:** ~13.000 jogos oficiais (Copa do Mundo, Eurocopas, eliminatórias) de 2006 a 2025
- **Features:** Rating ELO das duas equipes, diferença de ELO, campo neutro, peso do torneio, peso de recência
- **Modelo:** GLM Poisson com var_weights (statsmodels) — um modelo por time (casa e visitante)
- **Validação:** Acurácia de resultado ~60%, MAE de gols ~1.04
- **Simulação:** 1.000 iterações Monte Carlo com bipartite matching para os 8 terceiros colocados

---

## 📄 Licença

MIT License — veja [LICENSE](LICENSE) para detalhes.
