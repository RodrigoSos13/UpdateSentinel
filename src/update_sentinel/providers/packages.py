"""Consultas Arch: checkupdates isolado e metadados locais via pacman -Qi."""

import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from update_sentinel.core.models import PackageUpdate
from update_sentinel.security.commands import CommandError, CommandRunner


class PackageProvider(Protocol):
    def updates(self) -> list[PackageUpdate]: ...


LINE = re.compile(r"^([A-Za-z0-9@_+][A-Za-z0-9@_.+:-]*)\s+(\S+)\s+->\s+(\S+)$")


def parse_updates(output: str) -> list[PackageUpdate]:
    packages = []
    names = set()
    for line in output.splitlines():
        if not line.strip():
            continue
        match = LINE.fullmatch(line.strip())
        if not match or match[1] in names:
            raise CommandError(
                "Saída inesperada ou duplicada de checkupdates; consulta incompleta."
            )
        names.add(match[1])
        packages.append(PackageUpdate(*match.groups()))
    return packages


def parse_metadata(output: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    key = ""
    for line in output.splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z ]+)\s+:\s*(.*)$", line)
        if match:
            key = match[1].strip()
            fields[key] = match[2].strip()
        elif line.startswith(" ") and key:
            fields[key] += " " + line.strip()
    return fields


def classify(name: str, fields: dict[str, str]) -> tuple[str, str]:
    """Classificação descritiva baseada em metadados; não é uma regra de risco."""
    if "usr/lib/modules" in fields.get("Install Script", ""):
        return "Kernel", "Kernel (indício em metadados)"
    if name.startswith("linux") and (
        name == "linux" or re.match(r"linux-(lts|zen|hardened|cachyos)(-|$)", name)
    ):
        return "Kernel", "Kernel ou ferramentas associadas; impacto exato não verificado"
    if "nvidia" in name or name in {"mesa", "vulkan-radeon", "xf86-video-amdgpu"}:
        return "Drivers", "Pilha gráfica; compatibilidade não verificada"
    groups = fields.get("Groups", "")
    if any(group in groups.split() for group in ("plasma", "kde-applications", "gnome")):
        return "Interface gráfica", "Ambiente gráfico"
    if name.startswith(("lib", "qt6-", "glib")):
        return "Bibliotecas", "Aplicações dependentes"
    if name in {"gcc", "clang", "cmake", "rust", "python", "git"}:
        return "Desenvolvimento", "Ferramentas e aplicações dependentes"
    return "Aplicações", "Impacto específico não verificado"


class ArchPackages:
    def __init__(self, runner: CommandRunner):
        self.runner = runner

    def updates(self) -> list[PackageUpdate]:
        # Ignora CHECKUPDATES_DB herdado para nunca apontar à base principal.
        with TemporaryDirectory(prefix="updatesentinel-") as directory:
            result = self.runner.run(
                "checkupdates",
                "--nocolor",
                timeout=180,
                env={"CHECKUPDATES_DB": str(Path(directory) / "db")},
            )
        if result.code == 2 and not result.stdout.strip():
            return []
        if result.code != 0:
            raise CommandError(
                f"checkupdates falhou (código {result.code}); verifique rede e repositórios. "
                "Nenhuma lista parcial foi aceita."
            )
        packages = parse_updates(result.stdout)
        if not packages:
            raise CommandError("checkupdates retornou sucesso sem lista; saída inconsistente.")
        for package in packages:
            try:
                metadata = self.runner.run("pacman", "-Qi", package.name)
                if metadata.code == 0:
                    fields = parse_metadata(metadata.stdout)
                    package.description = fields.get("Description", package.description)
                    package.dependencies = fields.get("Depends On", package.dependencies)
                    package.category, package.components = classify(package.name, fields)
            except CommandError:
                pass  # Metadados opcionais não invalidam a lista real de atualizações.
        return packages
