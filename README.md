# Infraestrutura de Redes e Servidores Linux

Projeto Final da disciplina de Redes e Sistemas Linux.

Infraestrutura segmentada em três zonas (DMZ, LAN e DB), ligadas por um roteador/firewall Linux, com DNS e DHCP internos, servidor web com HTTPS e aplicação, banco PostgreSQL, servidor de arquivos Samba com cotas, backup automatizado e administração por SSH com chaves.

- **Equipe:** [preencher nomes]
- **Ambiente:** VirtualBox com Ubuntu Server 26.04.1 LTS
- **Domínio interno:** `empresa.local`

## Topologia

```
        Internet / máquina hospedeira (Windows)
                       |
               [enp0s3  WAN - NAT]
                +-------------+
                |  fw-router  |   nftables + dnsmasq + Bind9
                +-------------+
          enp0s8     enp0s9     enp0s10
         10.0.1.1   10.0.2.1    10.0.3.1
            |          |           |
      [DMZ: web01] [LAN: file01] [DB: db01]
       10.0.1.10    10.0.2.10     10.0.3.10
```

| Zona | Rede | Gateway | Rede interna do VirtualBox | Interface no fw-router |
|---|---|---|---|---|
| WAN | 192.168.100.0/24 (NAT) | gateway da NAT | NAT | enp0s3 |
| DMZ | 10.0.1.0/24 | 10.0.1.1 | `dmz` | enp0s8 |
| LAN | 10.0.2.0/24 | 10.0.2.1 | `lan` | enp0s9 |
| DB | 10.0.3.0/24 | 10.0.3.1 | `db` | enp0s10 |

## Hosts e serviços

| Host | Zona | IP | Serviços |
|---|---|---|---|
| fw-router | WAN, DMZ, LAN e DB | 10.0.1.1, 10.0.2.1, 10.0.3.1 | Roteamento, nftables, DHCP (dnsmasq), DNS (Bind9), SSH |
| web01 | DMZ | 10.0.1.10 | Nginx (HTTPS, TLS 1.2+, rate limiting), aplicação FastAPI |
| file01 | LAN | 10.0.2.10 (reserva DHCP) | Samba, grupos POSIX, ACL, cotas de disco, rotação de backups |
| db01 | DB | 10.0.3.10 | PostgreSQL (SCRAM-SHA-256), script de backup diário |

## Estrutura do repositório

```
.
├── README.md
├── docs/                         documentação técnica (ver abaixo)
├── fw-router/
│   ├── 01-fw-router.yaml         Netplan
│   ├── nftables.conf             firewall (política DROP) e NAT
│   ├── lan.conf                  DHCP (dnsmasq)
│   ├── named.conf.options        DNS (Bind9)
│   ├── named.conf.local
│   └── zones/                    zona direta e zonas reversas
├── web01/
│   ├── empresa                   site do Nginx (HTTPS, rate limit, páginas de erro)
│   ├── ratelimit.conf
│   ├── errors/                   404.html e 50x.html
│   ├── main.py                   aplicação FastAPI (Mural de Recados)
│   ├── app.service               serviço systemd da aplicação
│   └── app.env.example           modelo das variáveis de ambiente (sem senha real)
├── db01/
│   ├── postgresql.conf
│   ├── pg_hba.conf
│   └── backup_db.sh              backup diário (pg_dump, tar.gz, envio por Samba)
└── file01/
    ├── smb.conf
    └── rotacao_backups.sh        rotação de backups (7 dias)
```

### Onde cada arquivo fica no servidor

| Arquivo no repositório | Caminho no servidor |
|---|---|
| `fw-router/01-fw-router.yaml` | `/etc/netplan/01-fw-router.yaml` |
| `fw-router/nftables.conf` | `/etc/nftables.conf` |
| `fw-router/lan.conf` | `/etc/dnsmasq.d/lan.conf` |
| `fw-router/named.conf.options` e `named.conf.local` | `/etc/bind/` |
| `fw-router/zones/db.*` | `/etc/bind/zones/` |
| `web01/empresa` | `/etc/nginx/sites-available/empresa` (com link em `sites-enabled`) |
| `web01/ratelimit.conf` | `/etc/nginx/conf.d/ratelimit.conf` |
| `web01/errors/*.html` | `/var/www/errors/` |
| `web01/main.py` | `/opt/app/main.py` |
| `web01/app.service` | `/etc/systemd/system/app.service` |
| `web01/app.env.example` | `/etc/app.env`, com a senha real (dono `root:www-data`, modo `640`) |
| `db01/postgresql.conf` e `pg_hba.conf` | pasta do PostgreSQL (caminhos em `SHOW config_file;` e `SHOW hba_file;`) |
| `db01/backup_db.sh` | `/usr/local/bin/backup_db.sh` (modo `750`) |
| `file01/smb.conf` | `/etc/samba/smb.conf` |
| `file01/rotacao_backups.sh` | `/usr/local/bin/rotacao_backups.sh` (modo `750`) |

## Como reproduzir o ambiente

A ordem e os comandos completos de cada etapa estão na documentação em `docs/`. Em resumo:

1. Criar a VM base (Ubuntu Server) e clonar para `fw-router`, `web01`, `file01` e `db01`, com as redes internas `dmz`, `lan` e `db` e a faixa da NAT trocada para `192.168.100.0/24`.
2. **fw-router:** Netplan, `ip_forward`, `nftables.conf`, DHCP (`lan.conf`) e DNS (Bind9 com as zonas).
3. **db01:** PostgreSQL, usuário `app_user`, banco `appdb`, `listen_addresses` e `pg_hba.conf`.
4. **web01:** Nginx com certificado autoassinado, `ratelimit.conf`, páginas de erro, aplicação FastAPI e serviço systemd.
5. **file01:** disco de dados com cotas, grupos, pastas com ACL, `smb.conf` e senhas do Samba.
6. **Backup:** credencial da conta `bkp1`, `backup_db.sh` no `db01` e `rotacao_backups.sh` no `file01`, ambos no cron.
7. **SSH:** chaves ed25519, bloqueio de senha em `sshd_config.d/00-hardening.conf`.

## Aplicação web (Mural de Recados)

Aplicação FastAPI em `web01/main.py`. Ela lista os últimos recados (`GET /`) e grava novos (`POST /recado`) numa tabela do PostgreSQL, criada automaticamente na primeira execução. Escuta apenas em `127.0.0.1:8000`, e o acesso externo passa pelo Nginx em HTTPS. As credenciais do banco vêm das variáveis `DB_HOST`, `DB_NAME`, `DB_USER` e `DB_PASS` (arquivo `/etc/app.env`), e nunca do código.

Para rodar fora do projeto (desenvolvimento):

```bash
python3 -m venv venv
./venv/bin/pip install fastapi uvicorn "psycopg[binary]" python-multipart
export DB_HOST=localhost DB_NAME=appdb DB_USER=app_user DB_PASS=sua_senha
./venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

## Backup

O `backup_db.sh` roda todo dia às 2h no `db01`: faz o `pg_dump` do `appdb`, compacta em `.tar.gz`, envia ao compartilhamento `backups` do `file01` (Samba, conta `bkp1`) e apaga a cópia local. Às 2h30, o `rotacao_backups.sh` do `file01` remove os backups com mais de 7 dias. O procedimento de restauração está em `docs/03-procedimentos-operacionais.md`.

## Documentação

| Arquivo | Conteúdo |
|---|---|
| `docs/01-topologia-e-enderecamento.md` | Topologia, zonas, rotas, nomes DNS, portas e ambiente do VirtualBox |
| `docs/02-firewall.md` | Matriz de conectividade, regras adicionais e justificativas |
| `docs/03-procedimentos-operacionais.md` | SOP: restaurar backup, adicionar usuário e ordem de inicialização |
| `docs/04-roteiro-de-testes.md` | Testes T1 a T16 com resultados esperados, evidências e perguntas de arguição |
| `docs/05-analise-de-seguranca.md` | Controles adotados e limitações conhecidas |
| `docs/06-problemas-e-solucoes.md` | Problemas encontrados durante a implantação e como foram resolvidos |
| `docs/evidencias/` | Prints dos testes |

O relatório técnico completo em PDF fica em `docs/relatorio-tecnico.pdf`.

## Segredos fora do repositório

Estes arquivos existem nos servidores, mas **não** são versionados:

- `/etc/app.env` (senha do banco da aplicação; o repositório tem só o `app.env.example`)
- `/root/.backup_cred` (senha da conta de backup)
- `/etc/nginx/ssl/web01.key` (chave privada do certificado)
- chaves privadas do SSH (`id_ed25519`)
