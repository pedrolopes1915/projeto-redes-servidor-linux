# 4. Roteiro de testes práticos

Cada teste indica onde rodar, os comandos e o resultado esperado. Use `sudo` onde indicado e tire um print de cada resultado, salvando em `docs/evidencias/`.

**Ordem sugerida na defesa (15 a 20 minutos):** diagrama e arquitetura (2 min), T5 fluxo completo (3 min), T9 bloqueio do banco (3 min), T11 e T12 Samba e cotas (4 min), T13 e T14 backup e rotação (4 min), e o restante como apoio à arguição.

## T1. Rede, rotas e roteamento

```bash
# fw-router
ip -br a                                  # 4 interfaces com os IPs do documento de topologia
sysctl net.ipv4.ip_forward                # = 1
ip route                                  # rotas das 3 zonas e rota padrão pela NAT

# web01 e db01
ping -c 2 10.0.1.1                        # gateway da própria zona (use 10.0.3.1 no db01)
ip route                                  # default via gateway da zona
curl -s -o /dev/null -w "%{http_code}\n" http://archive.ubuntu.com/    # saída HTTP liberada

# file01
ping -c 2 8.8.8.8                         # a LAN tem saída livre
```

Observação: o ping entre zonas é bloqueado pelo firewall de propósito. A conectividade entre zonas é testada por porta em T8.

## T2. DHCP e reserva de IP

```bash
# fw-router
sudo systemctl status dnsmasq --no-pager        # active (running)
sudo cat /var/lib/misc/dnsmasq.leases           # file01 com 10.0.2.10

# file01
ip -br a ; ip route                              # 10.0.2.10 e default via 10.0.2.1
sudo networkctl renew enp0s3                     # renova e mantém o mesmo IP
```

## T3. DNS direto e reverso

```bash
# file01
dig web01.empresa.local +short            # 10.0.1.10
dig db01.empresa.local +short             # 10.0.3.10
dig -x 10.0.3.10 +short                   # db01.empresa.local.
dig google.com +short                     # resolução externa pelo repasse

# fw-router (usa o DNS da NAT, então consulta o Bind direto)
dig @10.0.2.1 web01.empresa.local +short  # 10.0.1.10
```

## T4. HTTPS e TLS 1.2+

```bash
# qualquer servidor
curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" http://web01.empresa.local/   # 301 https://web01.empresa.local/
curl -k -s -o /dev/null -w "%{http_code}\n" https://web01.empresa.local/               # 200

# fw-router
nmap --script ssl-enum-ciphers -p 443 10.0.1.10      # somente TLSv1.2 e TLSv1.3, nota A
```

## T5. Fluxo completo: usuário, HTTPS, aplicação e PostgreSQL (defesa)

```bash
# file01 (usuário interno)
curl -k -i -d "autor=Defesa&mensagem=Teste ao vivo" https://web01.empresa.local/recado   # HTTP/1.1 303 See Other
curl -k -s https://web01.empresa.local/ | grep "Teste ao vivo"                           # recado listado na página

# db01 (prova de que gravou no banco)
sudo -u postgres psql -d appdb -c "SELECT id, autor, mensagem, criado_em FROM recados ORDER BY id DESC LIMIT 3;"
```

Demonstração no navegador (opcional): no VirtualBox, crie na NAT do `fw_router` o redirecionamento `127.0.0.1:8443` para a porta 443 do convidado. No Windows, abra `https://127.0.0.1:8443`, aceite o aviso do certificado autoassinado, envie um recado pelo formulário e mostre o registro no banco com o `SELECT` acima. O caminho percorrido é NAT, DNAT no roteador, Nginx, aplicação e PostgreSQL.

## T6. Rate limiting e páginas de erro

```bash
# web01
for i in $(seq 1 30); do curl -k -s -o /dev/null -w "%{http_code} " https://web01.empresa.local/; done; echo
# esperado: vários 200 e, em seguida, 429. Aguarde 5 segundos antes de repetir.

curl -k -i https://web01.empresa.local/nao-existe     # 404 com a página personalizada
```

Para a página 500, desligue o banco e restaure em seguida:

```bash
# db01
sudo systemctl stop postgresql

# web01
curl -k -i https://web01.empresa.local/               # 500 com a página "Ops, algo deu errado"

# db01
sudo systemctl start postgresql
```

## T7. Logs e retenção

```bash
# web01
sudo tail -n 5 /var/log/nginx/empresa.access.log
sudo grep " 429 " /var/log/nginx/empresa.access.log | tail -n 3
sudo grep "limiting requests" /var/log/nginx/empresa.error.log | tail -n 3
grep -E "daily|rotate|compress" /etc/logrotate.d/nginx          # daily, rotate 30, compress
sudo logrotate -d /etc/logrotate.d/nginx                         # simulação sem erros
```

## T8. Firewall: matriz de conectividade

Se o `nc` não existir, instale com `sudo apt install -y netcat-openbsd`. Falhas aparecem como tempo esgotado depois de 3 segundos.

```bash
# web01
nc -zv -w 3 10.0.3.10 5432      # succeeded (web01 para o banco)
nc -zv -w 3 10.0.3.10 22        # falha (DMZ não administra o DB)
nc -zv -w 3 10.0.2.10 445       # falha (DMZ não acessa o Samba)

# file01 (LAN)
nc -zv -w 3 10.0.1.10 22        # succeeded (SSH admin para a DMZ)
nc -zv -w 3 10.0.3.10 22        # succeeded (SSH admin para o DB)
nc -zv -w 3 10.0.3.10 5432      # falha (a LAN não acessa o banco)
curl -k -s -o /dev/null -w "%{http_code}\n" https://web01.empresa.local/   # 200

# db01
nc -zv -w 3 10.0.2.10 445       # succeeded (backup para o file01)
nc -zv -w 3 10.0.1.10 22        # falha (o DB não inicia conexões para a DMZ)

# fw-router
sudo nft list chain inet filter forward     # regras e contadores
```

## T9. Bloqueio da porta 5432 vindo da DMZ ou da internet (defesa)

Como o web01 é o único host autorizado, simula-se outro host da DMZ dando ao web01 um segundo endereço e usando-o como origem:

```bash
# web01
sudo ip addr add 10.0.1.20/24 dev enp0s3
nc -s 10.0.1.20 -zv -w 3 10.0.3.10 5432     # BLOQUEADO (origem não autorizada)
nc -zv -w 3 10.0.3.10 5432                  # succeeded (IP oficial do web01)
sudo ip addr del 10.0.1.20/24 dev enp0s3

# fw-router
sudo nft list chain inet filter forward | grep FW-DROP-DB      # contador de pacotes maior que zero
sudo journalctl -k --no-pager | grep FW-DROP-DB | tail -n 3    # pacotes recusados, com origem e destino
```

Do lado da internet, não há redirecionamento (DNAT) para a porta 5432, e a regra de bloqueio também cobre a interface WAN.

## T10. Controle de acesso e privilégio mínimo no PostgreSQL

```bash
# web01 (instale o cliente: sudo apt install -y postgresql-client)
psql -h 10.0.3.10 -U postgres -d appdb                       # FATAL: no pg_hba.conf entry (usuário não liberado)
psql -h db01.empresa.local -U app_user -d appdb -c "\conninfo"   # conecta, pedindo a senha do app_user

# db01
sudo ss -tlnp | grep 5432                                    # 127.0.0.1 e 10.0.3.10, sem 0.0.0.0
sudo -u postgres psql -c "\du"                               # app_user sem Superuser, Create role e Create DB
sudo -u postgres psql -c "SHOW password_encryption;"         # scram-sha-256
```

## T11. Samba: mapeamento de pasta e restrição de escrita (defesa)

Um cliente da LAN é o próprio fw-router (instale `sudo apt install -y smbclient cifs-utils`).

```bash
# fw-router
smbclient //10.0.2.10/projetos -U dev1 -c "put /etc/hostname teste.txt; ls"   # grava e lista
smbclient //10.0.2.10/projetos -U dir1 -c "ls"                                # lista (leitura permitida)
smbclient //10.0.2.10/projetos -U dir1 -c "put /etc/hostname proibido.txt"    # NT_STATUS_ACCESS_DENIED
smbclient //10.0.2.10/projetos -U mkt1 -c "ls"                                # NT_STATUS_ACCESS_DENIED
smbclient //10.0.2.10/backups -U dir1 -c "ls"                                 # lista (a diretoria lê os backups)

# mapeamento (montagem) da pasta
sudo mkdir -p /mnt/projetos
sudo mount -t cifs //10.0.2.10/projetos /mnt/projetos -o username=dev1,vers=3.0
ls /mnt/projetos
sudo touch /mnt/projetos/mapeado.txt
sudo umount /mnt/projetos

# limpeza (no file01)
sudo rm -f /compartilhado/projetos/teste.txt /compartilhado/projetos/mapeado.txt
```

Permissões no servidor:

```bash
# file01
ls -ld /compartilhado/*              # publico (rwxrwsr-x), projetos e backups (rwxrws---+)
getfacl /compartilhado/projetos      # group:diretoria:r-x
sudo -u dir1 touch /compartilhado/projetos/x.txt     # Permission denied
```

## T12. Cotas de disco (defesa)

```bash
# file01
sudo quotaon -p /compartilhado                      # user quota e group quota is on
sudo repquota -vs -u /compartilhado                 # limites por usuário
sudo repquota -vs -g /compartilhado                 # limites por grupo
sudo -u dev1 dd if=/dev/zero of=/compartilhado/projetos/enchimento.bin bs=1M count=60
# esperado: Disk quota exceeded, parando perto de 50 MB (limite rígido do dev1)
sudo repquota -vs -u /compartilhado                 # dev1 no limite, com carência
sudo rm -f /compartilhado/projetos/enchimento.bin
```

## T13. Backup automatizado em tempo real (defesa)

```bash
# db01
sudo cat /etc/cron.d/backup_db                        # 0 2 * * * root /usr/local/bin/backup_db.sh
sudo /usr/local/bin/backup_db.sh
sudo tail -n 6 /var/log/backup_db.log                 # termina com "Backup concluido"

# file01
sudo ls -l /compartilhado/backups/                    # novo appdb_AAAAMMDD_HHMMSS.tar.gz, dono bkp1
sudo tar -tzf /compartilhado/backups/appdb_AAAAMMDD_HHMMSS.tar.gz     # lista o arquivo .sql (use o nome real)
```

## T14. Rotação de backups no servidor de arquivos (defesa)

```bash
# file01
sudo cat /etc/cron.d/rotacao_backups
sudo touch -d "10 days ago" /compartilhado/backups/appdb_antigo_teste.tar.gz
sudo ls -l /compartilhado/backups/                    # arquivo falso e backup real
sudo /usr/local/bin/rotacao_backups.sh
sudo ls -l /compartilhado/backups/                    # só o arquivo antigo sumiu
sudo cat /var/log/rotacao_backups.log                 # registra a remoção
```

## T15. SSH somente por chaves

```powershell
ssh web01 hostname                                    # entra sem pedir senha
ssh -o PubkeyAuthentication=no web01                  # Permission denied (publickey)
ssh -t db01 "sudo sshd -T | grep -E 'passwordauthentication|permitrootlogin'"   # ambos "no"
```

## T16. Persistência após reinicialização (opcional)

Ligue o ambiente na ordem do documento de procedimentos, confirme os serviços e repita T3 e T5:

```bash
systemctl is-enabled nginx app nftables named dnsmasq smbd cron postgresql 2>/dev/null
```

Cada serviço deve aparecer como `enabled` na máquina em que existe.

## Evidências para o relatório

| Teste | O que registrar (print) |
|---|---|
| T2 | arquivo de concessões do DHCP com o file01 em 10.0.2.10 |
| T3 | `dig` direto e reverso |
| T4 | `nmap` mostrando só TLSv1.2 e TLSv1.3, e o redirecionamento 301 |
| T5 | resposta 303 e a linha do recado no `SELECT` |
| T6 | sequência de 200 e 429, página 404 e página 500 |
| T7 | trechos dos logs e a simulação do `logrotate` |
| T8 e T9 | testes `nc` com sucesso e com falha, contador e log `FW-DROP-DB` |
| T10 | erro de `pg_hba.conf`, `ss` e `\du` |
| T11 e T12 | `ACCESS_DENIED`, montagem CIFS, `Disk quota exceeded` e `repquota` |
| T13 e T14 | log do backup, listagem dos arquivos antes e depois da rotação |
| T15 | `Permission denied (publickey)` |

## Perguntas prováveis na arguição

| Pergunta | Resposta curta |
|---|---|
| Por que política padrão DROP? | Só trafega o que foi explicitamente permitido, e um serviço novo não fica exposto por esquecimento. |
| Por que o `pg_hba.conf` libera só o IP do web01? | Menor privilégio: só a aplicação precisa do banco, então nem os outros hosts da DMZ conectam. |
| Por que SCRAM-SHA-256? | Guarda a senha com hash forte e salt, mais seguro que MD5. |
| Para que serve o DNAT? | Faz o tráfego público das portas 80 e 443 chegar ao web01, que fica numa rede privada. |
| Qual a diferença entre cota suave e rígida? | A suave avisa e dá um prazo de carência, e a rígida bloqueia a gravação. |
| Por que ACL para a diretoria? | Dá leitura a um grupo extra sem torná-lo dono nem permitir escrita. |
| Por que o Samba não passa pelo firewall para a LAN? | O file01 está na mesma sub-rede dos usuários, então o controle fica no Samba, com `hosts allow` e `valid users`. |
| Por que HTTPS autoassinado? | Em laboratório não há domínio público para o Let's Encrypt, e a criptografia é a mesma. |
| Por que `search: [empresa.local]` no file01? | O `systemd-resolved` trata `.local` como mDNS e só consulta o DNS interno se o domínio estiver na placa. |
| Como o backup é protegido? | Conta de serviço sem shell, credencial em arquivo 600, cota própria e rotação de 7 dias. |
