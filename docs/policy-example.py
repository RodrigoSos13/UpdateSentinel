"""Exemplo de composição via API; não é configuração carregada automaticamente."""

from update_sentinel.analyzers.risk import RiskAnalyzer, RiskPolicy
from update_sentinel.core.service import ScanService

service = ScanService(
    analyzer=RiskAnalyzer(
        RiskPolicy(
            boot_warning_percent=80,
            boot_high_percent=95,
            minimum_free_bytes=512 * 1024**2,
        )
    )
)
if __name__ == "__main__":
    print(service.scan(updates=False).to_dict())
