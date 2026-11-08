# Desenvolvimento

Use Python 3.12+ e um venv. Instale `.[gui,dev]` conforme README.
Execute `pytest -q`, `ruff check .`, `ruff format --check .` e `python -m build` pelo venv.
Use `QT_QPA_PLATFORM=offscreen` em testes de interface sem display; isso verifica widgets,
mas não substitui validação interativa em KDE/Wayland.

Na CI Ubuntu, o workflow instala `libegl1`, `libgl1`, `libxkbcommon0` e
`libfontconfig1` antes das dependências Python. São bibliotecas de execução para
EGL, OpenGL, teclado e fontes carregadas pelo QtGui e pelo plugin offscreen.
`QT_QPA_PLATFORM=offscreen` dispensa um monitor, mas não essas bibliotecas nativas;
os wheels PySide6 não substituem todas as dependências do sistema. Veja os
[requisitos oficiais do Qt para Linux](https://doc.qt.io/qt-6/linux-requirements.html)
e o [pacote EGL do Ubuntu](https://packages.ubuntu.com/noble/libegl1).
A instalação por `apt-get` é exclusiva do runner Ubuntu, sem alterar o procedimento
de instalação no Arch/CachyOS. A matriz mantém Python 3.12 e 3.14 e usa
`fail-fast: false` para que uma falha não cancele a verificação da outra versão.

Fixtures devem ser sintéticas. Injete provedores no ScanService ou runner falso nas
implementações. Nunca execute pacman modificador para preparar testes. A demonstração
usa o mesmo modelo e analisador do aplicativo, com marcação explícita de simulação.

Para experimentar limiares via API, veja `docs/policy-example.py`. Não existe arquivo
de configuração automaticamente carregado nem controles de monitoramento fictícios.

O build produz wheel e sdist usando Hatchling. A dependência Qt é opcional para
preservar uso headless. Não empacote dependências ou publique PKGBUILD sem revisar
licenças e validar o aplicativo instalado em Arch/CachyOS.
