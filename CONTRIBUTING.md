# Como contribuir

Leia README.md, AGENTS.md e docs/architecture.md. Crie um ambiente isolado usando os
comandos do README, faça uma alteração pequena e inclua testes quando mudar parsers,
regras de risco, execução de comandos ou contratos de provedores.

Execute Ruff, pytest e build antes de enviar um pull request. Informe o problema,
o comportamento resultante, evidências de teste e limitações. A CI não acessa pacman
real. Use fixtures sintéticas sem dados pessoais.

Novos gerenciadores de pacotes exigem implementação, testes e validação reais. Não
adicione comandos privilegiados, coleta externa automática ou diagnósticos produzidos
por IA apresentados como evidência técnica. Vulnerabilidades seguem SECURITY.md.
