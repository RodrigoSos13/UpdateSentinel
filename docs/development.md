# Desenvolvimento

Use Python 3.12+ e um venv. Instale `.[gui,dev]` conforme README.
Execute `pytest -q`, `ruff check .`, `ruff format --check .` e `python -m build` pelo venv.
Use `QT_QPA_PLATFORM=offscreen` em testes de interface sem display; isso verifica widgets,
mas não substitui validação interativa em KDE/Wayland.

Fixtures devem ser sintéticas. Injete provedores no ScanService ou runner falso nas
implementações. Nunca execute pacman modificador para preparar testes. A demonstração
usa o mesmo modelo e analisador do aplicativo, com marcação explícita de simulação.

Para experimentar limiares via API, veja `docs/policy-example.py`. Não existe arquivo
de configuração automaticamente carregado nem controles de monitoramento fictícios.

O build produz wheel e sdist usando Hatchling. A dependência Qt é opcional para
preservar uso headless. Não empacote dependências ou publique PKGBUILD sem revisar
licenças e validar o aplicativo instalado em Arch/CachyOS.
