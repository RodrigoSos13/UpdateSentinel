# Validação local — 2026-11-08

Ambiente: CachyOS x86_64, Python 3.14.9, PySide6 6.12.0.
Nenhum pacote do sistema foi instalado/atualizado durante a validação.
Dependências Python foram instaladas em `.venv`.

## Resultados executados

- Instalação editável com extras GUI/dev: concluída.
- Ruff check e format --check: aprovados.
- pytest: **38 testes aprovados**, incluindo Qt offscreen e worker sem bloquear a UI.
- Wheel e sdist gerados; wheel reinstalado sem dependências e suíte novamente aprovada.
- CLI `demo --json`: dados simulados identificados, sem persistir demonstração.
- CLI `doctor --json --no-save`: diagnóstico real coletado sem consultar repositórios.
- CLI `scan --json --no-save`: consulta real encontrou **64 atualizações**, com metadados
  locais dos 64 pacotes. A quantidade é uma observação desta execução, não dado do aplicativo.
- Diagnóstico real identificou duas GPUs, dois kernels com diretórios de módulos e
  montagem separada de `/boot`; cerca de 1,22 GiB disponíveis nessa execução.
- Retenção explícita Limine lida: 20; limite de uso configurado: 85.
- Git inicializado; nenhum remoto criado, nenhum push executado.

O sandbox inicialmente impediu downloads/consulta aos mirrors. A instalação, build
isolado e consulta real foram repetidos com acesso autorizado fora do sandbox.
Uma falha de encerramento do teste Qt foi corrigida liberando explicitamente objetos
Qt no teardown; a suíte completa subsequente encerrou com código 0.

## Limites de validação

A interface foi aberta em modo Qt **offscreen** e testada com dados de demonstração
identificados e provedor injetado. Não foi validada interativamente na sessão KDE/Wayland,
nem foi capturada uma tela real dessa sessão. O teste inclui conclusão do worker,
controles desabilitados durante consulta e reativados após finalizar.

A leitura do arquivo Limine em `/boot` foi negada ao usuário comum. A aplicação manteve
as informações de retenção legíveis em `/etc`, marcou a contagem de entradas como
indisponível e não tentou elevar privilégios. Não foram verificados arquivos de boot,
integridade, restauração de snapshots ou boot após atualização.

CI configurada para Python 3.12 e 3.14; somente Python 3.14 foi executado localmente.
A execução remota do GitHub Actions depende de publicação futura autorizada.
O MVP não foi validado em uma instalação Arch separada, apenas neste CachyOS.

Pesquisa online de documentação e validação de respostas Ollama não têm testes nesta
fase porque esses serviços ainda não foram implementados. SQLite, histórico completo,
PKGBUILD e notificações permanecem no roadmap. Veja as limitações do README.

## Interface de agente — revisão do MVP

A suíte passou a 45 testes, incluindo avaliação priorizada, roteamento limitado a
assuntos, respostas ancoradas no relatório, recusa de instruções livres e integração
da consulta de evidências na interface. As etapas exibidas vêm do serviço real; não
são animações com progresso presumido. Foi inspecionada uma captura Qt offscreen
da tela Agente com dados de demonstração explicitamente identificados. Isso não
substitui validação interativa em KDE/Wayland.

## Simplificação do fluxo inicial

53 testes aprovados após a nova tela Início. Foram verificados resumo com prioridade,
incerteza de recuperação, falha de consulta sem falso resultado de zero atualizações,
acesso a detalhes sob demanda e altura das recomendações em janela de 640 × 560.
As capturas offscreen do início e do resultado de demonstração foram inspecionadas.
Ruff, formatação e build local também foram executados. A validação interativa
na sessão KDE/Wayland permanece pendente.

## Reformulação visual e atividade real

58 testes aprovados, incluindo eventos de etapa emitidos apenas para operações
executadas, interrupção com etapas restantes não executadas, coleta incompleta sem
sucesso indevido, tempo não inventado na demonstração, medição de disco apresentada
e navegação acessível em largura reduzida. Ruff e formatação aprovados.

Foram inspecionadas capturas offscreen dos temas claro/escuro, largura reduzida e
inventário em seções. As capturas versionadas em `docs/images/` usam apenas dados de
demonstração explicitamente identificados; não são capturas de uma sessão KDE real.
Nenhuma nova consulta de pacotes ou alteração no sistema foi necessária para essa revisão.
