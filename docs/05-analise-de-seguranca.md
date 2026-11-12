# 5. Análise de segurança

## Controles adotados

| Controle | Ameaça reduzida | Onde |
|---|---|---|
| Segmentação em DMZ, LAN e DB | Movimento lateral e exposição do banco | `fw-router/nftables.conf` |
| Firewall com DROP por padrão e logs | Acesso não autorizado entre zonas | `fw-router/nftables.conf` |
| Banco numa zona própria, sem rota da internet | Ataque direto ao PostgreSQL | nftables, `db01/` |
| `pg_hba.conf` com IP único e SCRAM-SHA-256 | Roubo de credencial e conexão de hosts não autorizados | `db01/pg_hba.conf` |
| Usuário de aplicação sem privilégios | Dano limitado se a aplicação for comprometida | PostgreSQL (`app_user`) |
| HTTPS com TLS 1.2+ | Interceptação do tráfego web | `web01/empresa` |
| Rate limiting | Força bruta e abuso de requisições | `web01/ratelimit.conf` |
| Aplicação só em 127.0.0.1, atrás do Nginx | Acesso direto ao serviço da aplicação | `web01/app.service` |
| Escape de HTML e SQL parametrizado | XSS e SQL injection | `web01/main.py` |
| Samba com SMB2+, `hosts allow` e `valid users` | Acesso indevido e protocolo legado | `file01/smb.conf` |
| Grupos POSIX, ACL e cotas | Acesso além do necessário e esgotamento do disco | `file01/` |
| Credencial de backup em arquivo 600 e conta sem shell | Vazamento da senha do backup | `db01/backup_db.sh` |
| SSH só por chave, sem login de root | Força bruta de senha no SSH | `sshd_config.d/00-hardening.conf` |

## Limitações conhecidas

- O certificado é autoassinado, então os clientes recebem um aviso do navegador.
- O backup fica na mesma rede interna e não há cópia externa.
- Os logs não são centralizados.
- A LAN tem saída livre para a internet.
- A regra de SSH vinda da faixa da NAT existe só para o laboratório e deve ser removida em produção.
- O tráfego entre os usuários da LAN e o file01 não passa pelo roteador, então o controle fica no Samba.
