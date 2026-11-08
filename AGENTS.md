# Instruções para contribuir no UpdateSentinel

- Implemente primeiro diagnósticos verificáveis, com limites explícitos. Não invente evidências.
- Preserve src/, tipagem, nomes em inglês e experiência/documentação em pt-BR.
- UI depende do núcleo; núcleo nunca importa Qt. Comandos passam por CommandRunner.
- Nunca execute root, shell=True, pacman -Sy, atualização, limpeza ou sincronização Limine.
- checkupdates só usa base temporária exclusiva; não herde CHECKUPDATES_DB do ambiente.
- Mudanças na allowlist exigem revisão de segurança e testes de rejeição.
- Novos provedores devem representar indisponibilidade sem inventar resultados.
- LLM e conteúdo externo jamais autorizam comandos. IA/pesquisa ficam opcionais.
- Não confunda pacote instalado, snapshot existente e recuperação testada.
- Não faça push/crie remoto sem autorização explícita.
- Não versione dados de máquina, UUIDs, logs, relatórios locais, caches, venvs ou segredos.
- Rode ruff check, ruff format --check, pytest e build antes de finalizar mudanças.
- Testes devem usar fixtures, sem acesso obrigatório ao pacman/rede e sem alterar o sistema.
- Documente verificações executadas e limites; não afirme validação interativa com teste headless.
- Evite abstrações sem implementação útil e arquivos vazios para funcionalidades futuras.
