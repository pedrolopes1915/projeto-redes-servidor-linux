# 3. Procedimentos operacionais padrão (SOP)

## 3.1 Restabelecer um backup do banco

1. No **file01**, escolha o arquivo: `sudo ls -l /compartilhado/backups/`.
2. No **db01**, traga e extraia o arquivo (troque pelo nome real):

```bash
cd /var/backups/db
sudo smbclient //10.0.2.10/backups -A /root/.backup_cred -c "get appdb_AAAAMMDD_HHMMSS.tar.gz"
sudo tar -xzf appdb_AAAAMMDD_HHMMSS.tar.gz
```

3. No **web01**, pare a aplicação: `sudo systemctl stop app`.
4. No **db01**, recrie o banco e restaure o dump:

```bash
sudo -u postgres dropdb appdb
sudo -u postgres createdb -O app_user appdb
sudo -u postgres psql -c "REVOKE ALL ON DATABASE appdb FROM PUBLIC;"
sudo -u postgres psql -d appdb -f appdb_AAAAMMDD_HHMMSS.sql
```

5. No **web01**, suba a aplicação: `sudo systemctl start app`.
6. Verifique: no db01, `sudo -u postgres psql -d appdb -c "SELECT count(*) FROM recados;"`, e abra o site no web01.
7. Limpe os temporários: `sudo rm -f /var/backups/db/appdb_*`.

## 3.2 Adicionar um novo usuário ao servidor de arquivos

No **file01** (troque `novo_usuario` e escolha o grupo entre `devs`, `mkt` e `diretoria`):

```bash
sudo useradd -M -s /usr/sbin/nologin -G colaboradores,devs novo_usuario
sudo smbpasswd -a novo_usuario
sudo setquota -u novo_usuario 40960 51200 0 0 /compartilhado
id novo_usuario
sudo pdbedit -L | grep novo_usuario
sudo quota -vs -u novo_usuario
```

Para trocar de grupo: `sudo usermod -aG outro_grupo novo_usuario`.
Para remover o usuário: `sudo smbpasswd -x novo_usuario` e `sudo userdel novo_usuario`.

### Permissões por grupo

| Pasta | devs | mkt | diretoria | backup_mgr |
|---|---|---|---|---|
| `/compartilhado/publico` | ler e escrever | ler e escrever | ler e escrever | sem acesso |
| `/compartilhado/projetos` | ler e escrever | sem acesso | somente leitura | sem acesso |
| `/compartilhado/backups` | sem acesso | sem acesso | somente leitura | ler e escrever |

### Cotas de disco (KB: suave e rígido)

| Alvo | Suave | Rígido |
|---|---|---|
| usuário dev1 | 40 MB | 50 MB |
| usuário mkt1 | 20 MB | 30 MB |
| usuário dir1 | 40 MB | 50 MB |
| usuário bkp1 | 1 GB | 1,5 GB |
| grupo devs | 200 MB | 250 MB |
| grupo mkt | 100 MB | 120 MB |
| grupo diretoria | 100 MB | 120 MB |
| grupo colaboradores | 500 MB | 600 MB |
| grupo backup_mgr | 1,5 GB | 2 GB |

Relatório de uso: `sudo repquota -vs -u /compartilhado` e `sudo repquota -vs -g /compartilhado`.

## 3.3 Ordem para ligar o ambiente

1. `db01`, pois a aplicação consulta o banco ao iniciar.
2. `fw-router`, que fornece rotas, DNS, DHCP e firewall.
3. `file01`, que recebe o IP por DHCP do roteador.
4. `web01`. Se a aplicação não subir (erro 502), rode `sudo systemctl restart app` depois que o banco estiver no ar.

## 3.4 Acesso administrativo

O acesso é por chave SSH, sem senha. Para autorizar uma nova chave, acrescente a chave pública em `~/.ssh/authorized_keys` do usuário na VM. A autenticação por senha e o login de root estão desativados em `/etc/ssh/sshd_config.d/00-hardening.conf`. O console do VirtualBox continua disponível como acesso de emergência.
