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

O ecossistema roda inteiramente local em **Python**, sem requisições na nuvem:
*   **Pygame**: Renderização de tela, motor de física para frutas fatiadas, sistemas de partículas cintilantes de suco e renderização neon.
*   **OpenCV (cv2)**: Inicialização rápida de câmera, processamento de imagem em tempo real e espelhamento horizontal intuitivo.
*   **MediaPipe**: Framework de inteligência artificial do Google para detecção de 21 landmarks tridimensionais das mãos com altíssima taxa de quadros e precisão.
*   **NumPy**: Processamento veloz das matrizes de imagem.

---

## 💻 Instalação e Execução

### 1. Pré-requisitos
Certifique-se de possuir o **Python 3.8 a 3.14** instalado.

### 2. Instalação das Dependências
Abra o prompt de comando (CMD) ou PowerShell na pasta raiz do projeto e execute:

```bash
pip install pygame opencv-python mediapipe numpy
```

*(Caso utilize o Python 3.14+, execute também o patch incluído: `python patch_mediapipe.py`)*

### 3. Jogando

*   Para jogar o **Fruit Ninja**:
    ```bash
    python fruit_ninja.py
    ```
*   Para jogar o **Tetris**:
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
