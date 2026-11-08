# Arquitetura

`core/models.py` define dataclasses serializáveis. `ScanService` coordena a coleta
Linux, o provedor Arch e o analisador determinístico. CLI e Qt usam o mesmo serviço.
`PackageProvider` permite adicionar provedores testados sem simular outras distribuições.
As implementações de sistema e analisador são injetáveis no serviço para testes.

`security/commands.py` centraliza a allowlist, argumentos, locale C, recusa de root,
timeout e erros. Não expõe execução genérica. A consulta checkupdates recebe uma base
exclusiva em diretório temporário, independentemente da variável herdada do processo.

`providers/system.py` separa leitura literal de configurações de sua interpretação.
Nunca usa source/eval. Dados ausentes e formatos desconhecidos permanecem desconhecidos.
Não persiste UUIDs ou cmdlines. `analyzers/risk.py` recebe apenas modelos e devolve
alertas com origem, confiança, recomendação e limites. `RiskPolicy` permite ajustar
limiares via API; não existe ainda editor de regras na interface.

`core/reports.py` mantém somente o último relatório real em JSON conforme XDG.
Migrações SQLite e histórico de múltiplas análises são entregas da Fase 2.

A UI usa QThread com signals; só a thread principal modifica widgets. Fechar a janela
durante consulta pede aguardar a conclusão em vez de destruir uma thread ativa.
Traduções usam `tr()` na interface; mensagens do núcleo ainda precisam de catálogo
para internacionalização completa. Qt usa o tema/paleta do sistema.

Fases futuras devem introduzir serviços de pesquisa e IA atrás de contratos explícitos,
sem modificar resultados determinísticos. Conteúdo externo é dado não confiável e
nunca concede acesso ao executor. Nenhuma camada privilegiada foi criada.

A aba Perguntas guiadas usa `core/assistant.py` para priorizar achados e responder por assuntos
predefinidos sobre o relatório. Não há geração de comandos nem LLM. O serviço emite
etapas reais via callback opcional; a UI as recebe por signal do worker. Uma consulta
nova invalida o contexto anterior do agente enquanto coleta, e falhas são identificadas
como coleta parcial. Respostas de demonstração preservam a marcação de simulação.

A tela Início usa `core/guidance.py` para apresentar achados existentes em linguagem
simples. Esse módulo não avalia novos riscos: preserva prioridades, falhas de consulta
e limitações. A interface mantém dados técnicos recolhidos, invalida resultados antigos
ao iniciar nova coleta e só permite acessar uma lista obtida nessa consulta.

A identidade visual fica em `ui/theme.py`, com paletas Qt clara/escura e regras de
estilo comuns. `ui/activity.py` recebe eventos de etapa explícitos do ScanService;
QElapsedTimer mede tempo real, QTimer só atualiza a apresentação. Etapas não são
inferidas por temporizadores, e consultas malsucedidas não aparecem como concluídas.
A navegação lateral controla as páginas Qt; em larguras menores mostra ícones com
nomes acessíveis. `ui/system_view.py` apresenta o inventário em seções legíveis.

As transições não interferem na coleta. As barras animadas de disco têm como destino
exclusivamente medições coletadas; não estimam progresso da consulta ou chance de falha.
`UPDATESENTINEL_REDUCED_MOTION=1` desativa transições e interpolação das barras.
A seleção de tema é local à janela, sem persistência de preferências nesta fase.
