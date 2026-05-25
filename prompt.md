Corrija e otimize o sistema de frutas e detecção da mão no jogo.

Atualmente, algumas frutas estão saindo da área visível da tela, fazendo com que o jogador não consiga cortá-las. Isso prejudica a jogabilidade, pois o jogador acaba perdendo pontos mesmo sem ter chance real de interagir com essas frutas.

Além disso, depois de algum tempo jogando, a detecção da mão começa a ficar lenta, travando ou desaparecendo da tela. Isso causa atraso nos movimentos, falhas no corte das frutas e prejudica a experiência geral do jogador.

Ajustes necessários
Corrigir o spawn das frutas
As frutas não devem nascer fora da tela.
Elas devem aparecer sempre dentro da área jogável.
A trajetória das frutas precisa ser calculada para que elas permaneçam visíveis tempo suficiente para o jogador conseguir cortá-las.
Evite que frutas ultrapassem completamente as bordas laterais ou superiores da tela de forma injusta.
Melhorar os limites da tela
Criar uma margem segura para o surgimento das frutas.
Impedir que frutas sejam geradas muito perto das bordas.
Caso uma fruta saia da tela sem ser cortada, ela só deve contar como erro se realmente passou por uma área acessível ao jogador.
Otimizar a detecção da mão
Reduzir travamentos e atrasos na detecção.
Evitar que a mão suma durante a gameplay.
Melhorar a estabilidade do rastreamento.
Se possível, aplicar suavização no movimento da mão para evitar tremidas.
Melhorar a performance geral
Verificar se há vazamento de memória ou processamento acumulado com o tempo.
Evitar múltiplas chamadas desnecessárias da câmera ou do modelo de IA.
Garantir que o jogo continue fluido mesmo após vários minutos de gameplay.
Separar melhor a lógica do jogo da lógica de detecção da mão.
Melhorar a experiência do jogador
O jogador não deve perder ponto por falhas técnicas do jogo.
A colisão entre mão e fruta deve continuar precisa.
O jogo deve manter uma taxa de quadros estável.
A dificuldade pode aumentar com o tempo, mas sem tornar o jogo injusto.