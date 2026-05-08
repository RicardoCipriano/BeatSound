# 🎵 BeatSoundSearch - Plataforma de Experiência Musical Avançada

![BeatSound Logo](logoInicial.png)

O **BeatSoundSearch** é uma aplicação desktop de alta performance para gerenciamento e reprodução de música, projetada para audiófilos e colecionadores. Desenvolvido em Python com uma arquitetura modular e moderna, o projeto combina uma interface visual rica no estilo Dark Mode com um ecossistema poderoso de APIs, ferramentas de automação e um servidor backend integrado.

Este projeto foi construído focando em boas práticas de desenvolvimento, modularidade e performance, sendo um excelente exemplo de aplicação full-stack híbrida (Desktop + API).

---

## ✨ Recursos Destacados & Melhorias Recentes

### 🖥️ Interface de Usuário Premium (GUI)
- **Modo Flow (Deezer Inspired):** Experiência de audição contínua e personalizada. Escolha seu gênero e deixe o sistema criar um mix inteligente baseado na sua biblioteca.
- **Efeitos Visuais Avançados:** Botões com efeito de brilho arco-íris dinâmico (*Glow Effects*) e bordas pulsantes que acompanham o ritmo.
- **Visualizador de Espectro em Tempo Real:** Análise de áudio em tempo real com visualização gráfica do espectro sonoro.
- **Player em Tela Cheia:** Modo imersivo para exibição de capas de álbuns e informações da música em destaque.
- **Design Responsivo & Dark Mode:** Construído com `customtkinter`, oferecendo uma experiência visual moderna, carrosséis horizontais e transições suaves.

### 🌐 Ecossistema Multi-API & Backend
- **Servidor API Integrado (FastAPI):** O projeto conta com um servidor API completo que espelha as funcionalidades do banco de dados, permitindo futuras integrações com web ou mobile.
- **Enriquecimento Multi-API:** Integração profunda com as APIs do **Spotify** e **Discogs** para busca automática de biografias de artistas, capas em alta resolução e informações de gravadoras.
- **Sistema de Download Integrado:** Baixe músicas diretamente pela aplicação utilizando o poder do `yt-dlp`.

### 🛠️ Gerenciamento Inteligente de Biblioteca
- **AI Batch Editor:** Edição em massa de metadados assistida, permitindo organizar milhares de faixas e atualizar tags ID3 de uma só vez.
- **Smart Cleanup (Verify Music):** Módulo para detecção de duplicatas e limpeza de arquivos órfãos ou inconsistentes.
- **Cérebro de Dados (SQLite):** Banco de dados local robusto para cache de metadados, garantindo buscas instantâneas mesmo em bibliotecas gigantescas.

---

## 🛠️ Stack Tecnológica

O projeto utiliza uma combinação poderosa de bibliotecas modernas do ecossistema Python:

| Camada | Tecnologia | Descrição |
| :--- | :--- | :--- |
| **Linguagem** | `Python 3.10+` | Núcleo do sistema |
| **Interface (GUI)** | `CustomTkinter` | Framework principal para a interface moderna |
| **Extensões GUI** | `CTkTable`, `CTkMenuBar`, `CTkToolTip` | Componentes avançados de interface |
| **Áudio** | `PyGame` | Gerenciamento de reprodução de áudio de baixa latência |
| **Processamento de Áudio**| `sounddevice`, `soundfile` | Captura e processamento para o visualizador de espectro |
| **Backend / API** | `FastAPI`, `Uvicorn` | Servidor API RESTful integrado |
| **Banco de Dados** | `SQLite3` | Persistência de dados e cache de metadados |
| **Metadados** | `Mutagen` | Manipulação e edição de tags ID3 de arquivos de áudio |
| **Download** | `yt-dlp` | Motor de download de mídia |
| **Web Scraping** | `BeautifulSoup4`, `lxml` | Extração de dados complementares da web |
| **Processamento de Imagem**| `Pillow (PIL)` | Manipulação e renderização de capas e efeitos visuais |
| **Gráficos** | `Matplotlib` | Geração de gráficos para o painel de estatísticas |

---

## 🏗️ Arquitetura do Projeto

O projeto segue uma abordagem modular, onde cada funcionalidade principal é isolada em seu próprio módulo, facilitando a manutenção e a escalabilidade.

```text
SearchMusic_Novo/
│
├── main.py                  # Ponto de entrada da aplicação Desktop
├── config.json              # Configurações do usuário e caminhos
├── music.db                 # Banco de dados SQLite
│
├── modules/                 # Módulos especializados
│   ├── api_server.py        # Servidor FastAPI
│   ├── database.py          # Wrapper de comunicação com SQLite
│   ├── player.py            # Core de reprodução de áudio
│   ├── glow_button.py       # Componentes visuais com efeitos especiais
│   ├── multi_api_enhancer.py# Integração com Spotify/Discogs
│   ├── downloader.py        # Lógica de download com yt-dlp
│   ├── spectrum_visualizer.py# Visualizador de espectro em tempo real
│   └── ...                  # Visualizações específicas (Home, Search, Stats, etc.)
│
└── assets/                  # Imagens, logos e recursos visuais
```

---

## 🚀 Como Executar o Projeto

### Requisitos Prévios
- Python 3.10 ou superior instalado.

### Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/BeatSoundSearch.git
cd BeatSoundSearch/SearchMusic_Novo
```

2. Crie um ambiente virtual e ative-o:
```bash
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure suas variáveis de ambiente ou arquivo `config.json` com suas credenciais de API (Spotify e Discogs).

### Execução

Para iniciar a aplicação Desktop:
```bash
python main.py
```

Para iniciar o servidor API (opcional):
```bash
python modules/api_server.py
```

---

## 📊 Estatísticas e Insights
A aplicação monitora seu comportamento de audição e gera insights visuais através do módulo de estatísticas, mostrando seus artistas mais ouvidos, gêneros predominantes e o crescimento da sua biblioteca ao longo do tempo.

---

## 🤝 Contribuição
Sinta-se à vontade para abrir *Issues* ou enviar *Pull Requests* com melhorias no sistema de áudio, novas integrações de API ou otimizações de interface!

---
*Desenvolvido com ❤️ para apaixonados por música e tecnologia.*
