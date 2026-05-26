# Vision AI Games Suite 🎮🤖

Este é um projeto completo e interativo que reúne dois jogos clássicos controlados por Inteligência Artificial (Visão Computacional) em tempo real: **Tetris Vision AI** e **Fruit Ninja Vision AI**. Ambos foram desenvolvidos com um visual escuro moderno, detalhes em cores neon e efeitos visuais premium, ideais para apresentações interativas em feiras de ciências, como a do **SENAI**.

Os jogos rodam de forma 100% local e contam com controle de gestos por câmera ou controles tradicionais por teclado como fallback.

---

## 📂 Jogos Disponíveis

### 1. Fruit Ninja Vision AI 🍉 (`fruit_ninja.py`)
Um jogo de cortar frutas voadoras em realidade aumentada! A ponta do seu dedo indicador é a sua lâmina — mova-a rapidamente para realizar cortes espetaculares, desvie das bombas e acumule combos!

*   **Como Iniciar**: Execute `python fruit_ninja.py`.
*   **Menu Interativo (Premium)**: O menu inicial exibe a câmera ao vivo com um efeito de vidro fosco (glassmorphism). Há uma **melancia dourada girando no centro**; use seu dedo na frente da câmera para fazer um gesto de corte e fatiá-la para iniciar o jogo!
*   **Controles**:
    *   **Mover Lâmina**: Aponte e mova o dedo indicador em frente à câmera.
    *   **Corte Rápido**: Mova o dedo rapidamente para fatiar as frutas e desencadear combos multiplicadores de pontos.
    *   **Evite as Bombas**: Slicing em uma bomba causa uma explosão massiva de partículas e encerra o jogo instantaneamente!
    *   **Vidas**: Você tem 3 vidas. Cada fruta não cortada que cai da tela custa 1 vida.
    *   **Teclado / Mouse (Fallback)**: Clique na tela ou pressione `ENTER` no menu para iniciar; pressione `R` para reiniciar (após o game over); pressione `ESC` para sair.

### 2. Tetris Vision AI 🧱 (`main.py`)
O clássico jogo de empilhar blocos controlado inteiramente pela posição e formato da sua mão!
*   **Como Iniciar**: Execute `python main.py`.
*   **Controles por Gestos**:
    *   **Mover para a Esquerda**: Mão aberta posicionada no lado esquerdo do feed da câmera.
    *   **Mover para a Direita**: Mão aberta posicionada no lado direito do feed da câmera.
    *   **Rotacionar Peça (90°)**: Feche a mão em um punho por pelo menos **220ms** (debounce integrado para evitar rotações acidentais ao coçar o nariz). O Z e todas as outras peças agora giram por 4 posições completas e previsíveis!
    *   **Descida Rápida (Soft Drop)**: Mantenha a mão aberta abaixo da linha divisória verde.
    *   **Pausar / Despausar**: Mostre ambas as mãos na tela por **700ms** contínuos (com barra de progresso visual para evitar pausas acidentais).
*   **Filtros de IA Robustos**: O sistema inclui validação geométrica de proporções de mão real (`_is_valid_hand`) para ignorar rostos e objetos que a câmera possa confundir acidentalmente.

---

## 🚀 Tecnologias Utilizadas

O ecossistema roda inteiramente local em **Python**, sem necessidade de processamento na nuvem:
*   **Pygame-CE (Community Edition)**: Motor de renderização ultra-veloz, manipulação de superfícies em tempo real, física de partículas para o suco das frutas e brilho neon premium. *(Recomendado no lugar do Pygame clássico para compatibilidade total com Python moderno)*.
*   **OpenCV (cv2)**: Captura e inicialização assíncrona de webcams, processamento rápido de frames de vídeo e espelhamento horizontal intuitivo.
*   **MediaPipe (Google AI)**: Framework de inteligência artificial de alta performance para detecção e rastreamento tridimensional dos 21 landmarks das mãos em tempo real.
*   **NumPy**: Processamento matemático acelerado de matrizes de imagem.

---

## 💻 Instalação e Configuração

Siga os passos abaixo para preparar o seu ambiente e rodar os jogos com desempenho máximo.

### 1. Pré-requisitos
*   **Python**: Versões **3.8 a 3.14** instaladas.
*   **Hardware**: Uma Webcam conectada e ambiente com iluminação adequada para o rastreamento da IA.

### 2. Instalação das Bibliotecas
Abra o seu terminal (Prompt de Comando/CMD ou PowerShell no Windows, ou Terminal no Linux/macOS) na pasta raiz deste projeto e execute o comando abaixo para instalar todas as dependências recomendadas:

```bash
pip install pygame-ce opencv-python mediapipe numpy
```

> [!TIP]
> **Por que Pygame-CE?**
> O *Pygame Community Edition* (pygame-ce) traz melhorias massivas de performance, correções de bugs ativos e suporte completo para as versões mais novas do Python (como Python 3.12, 3.13 e 3.14), onde o Pygame padrão frequentemente falha ao compilar ou renderizar no Windows.

### 3. Aplicando o Patch do MediaPipe (Crucial para Windows & Python 3.12+)
No Windows, devido a mudanças internas de compilação da DLL do MediaPipe, pode ocorrer um erro crítico ao tentar inicializar o rastreamento de mãos (`AttributeError: _shared_lib.free.argtypes`).

Para resolver isso de forma 100% automática, execute o script de patch portátil incluído no projeto:

```bash
python patch_mediapipe.py
```

*Este script localiza dinamicamente o arquivo de bindings do MediaPipe instalado no seu ambiente Python e aplica uma correção de compatibilidade robusta.*

### 4. Executando os Jogos

Com as dependências instaladas e o patch aplicado, você está pronto para iniciar:

*   **Para jogar o Fruit Ninja Vision AI 🍉**:
    ```bash
    python fruit_ninja.py
    ```
*   **Para jogar o Tetris Vision AI 🧱**:
    ```bash
    python main.py
    ```

---

## 🛠️ Solução de Problemas (Troubleshooting)

1.  **A câmera não abre ou a interface diz "Câmera Indisponível"**:
    *   Certifique-se de que a webcam não está sendo usada por outro software (Teams, Zoom, Discord, OBS, etc.).
    *   Ambos os jogos entram automaticamente em modo Teclado/Mouse caso a webcam não seja detectada, garantindo que o programa nunca quebre.
2.  **Os gestos parecem muito sensíveis ou imprecisos**:
    *   **Iluminação**: Garanta que o jogador esteja sob luz clara e bem focada. Sombras pesadas dificultam o mapeamento da rede neural.
    *   **Distância**: O jogador deve ficar a uma distância confortável de **60 cm a 1,20 m** da câmera.
    *   **Fundo**: Evite que outras pessoas fiquem passando ou levantando os braços logo atrás do jogador.
