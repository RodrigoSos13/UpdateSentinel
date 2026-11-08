"""Executor de consultas autorizadas; nunca recebe instruções de um modelo."""

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CommandError(RuntimeError):
    """Consulta indisponível, inválida ou mal sucedida."""


@dataclass(frozen=True)
class CommandResult:
    code: int
    stdout: str
    stderr: str


class CommandRunner:
    """Lista fechada de argumentos; sem shell, elevação ou mutação de pacotes."""

    FIXED = {
        ("checkupdates", "--nocolor"),
        ("pacman", "-Q"),
        ("lspci", "-nnk"),
        ("snapper", "list-configs"),
    }

    @staticmethod
    def allowed(args: tuple[str, ...]) -> bool:
        if args in CommandRunner.FIXED:
            return True
        if len(args) == 3 and args[:2] == ("pacman", "-Qi"):
            return bool(re.fullmatch(r"[A-Za-z0-9@_+][A-Za-z0-9@_.+:-]*", args[2]))
        if len(args) == 6 and args[:3] == ("findmnt", "-J", "-T"):
            return args[3] in {"/", "/boot", "/efi", "/boot/efi", "/limine"} and args[4:] == (
                "-o",
                "TARGET,FSTYPE",
            )
        if len(args) == 4 and args[:2] == ("snapper", "-c") and args[3] == "list":
            return bool(re.fullmatch(r"[A-Za-z0-9_-]+", args[2]))
        return False

    def run(self, *args: str, timeout: int = 20, env: dict | None = None) -> CommandResult:
        argv = tuple(args)
        if not self.allowed(argv):
            raise CommandError("Operação não autorizada pelo executor.")
        if os.geteuid() == 0:
            raise CommandError("Execute o aplicativo como usuário comum, sem root.")
        binary = shutil.which(args[0])
        if binary is None:
            raise CommandError(f"Ferramenta indisponível: {args[0]}")
        environment = os.environ.copy()
        environment.update({"LC_ALL": "C", "LANG": "C"})
        if env:
            environment.update(env)
        logger.info("Consulta: %s", args[0])  # Não registrar saídas, UUIDs ou caminhos pessoais.
        try:
            result = subprocess.run(
                [binary, *args[1:]],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
                env=environment,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CommandError(f"Tempo esgotado: {args[0]}") from exc
        except OSError as exc:
            raise CommandError(f"Falha ao iniciar: {args[0]}") from exc
        return CommandResult(result.returncode, result.stdout, result.stderr)
