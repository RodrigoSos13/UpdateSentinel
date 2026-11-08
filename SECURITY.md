# Segurança

A versão 0.1.x é exclusivamente diagnóstica. Não execute com sudo/root.
O executor aceita consultas específicas com timeout e argumentos separados.
checkupdates sincroniza apenas uma base temporária exclusiva; nenhum download ou
instalação de pacotes é solicitado. Não há executor modificador nem acesso LLM ao terminal.

Relatórios contêm inventário técnico local, com permissão 0600. Não contêm a configuração
completa do boot, UUIDs nem saídas brutas de logs. Evite publicar relatórios sem revisão.
O acesso à rede em scan é o próprio acesso aos mirrors configurados pelo checkupdates.

Se encontrar uma vulnerabilidade, evite expor dados ou instruções exploráveis em issues
públicas. Enquanto não houver canal privado publicado pelo mantenedor, peça um canal
privado de contato sem revelar detalhes da falha. Não existe endereço de segurança
fictício ou serviço de recebimento configurado neste MVP.
