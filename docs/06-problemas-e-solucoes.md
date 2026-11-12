# 6. Problemas encontrados e soluções

| Sintoma | Causa | Solução |
|---|---|---|
| Conflito de rotas no roteador | A NAT do VirtualBox usa 10.0.2.0/24, igual à LAN | `VBoxManage modifyvm "fw_router" --natnet1 "192.168.100.0/24"` |
| Rede não aplicava a configuração | Mais de um `.yaml` ativo no Netplan e cloud-init recriando a rede | Renomear os antigos para `.bak` e desativar a rede do cloud-init |
| dnsmasq não iniciava | Porta 53 já usada | `port=0` (só DHCP) e DNS no Bind9 |
| Zonas do Bind9 não carregavam | Caminho sem `/` inicial, nome de arquivo errado e falta de ponto final no NS | `named-checkconf`, `named-checkzone` e `journalctl -u named` |
| Nome `.local` não resolvia no file01 | `systemd-resolved` trata `.local` como mDNS | `search: [empresa.local]` no Netplan e DHCP entregando só o DNS interno |
| PostgreSQL escutando em 0.0.0.0 | Valor definido em outro arquivo ou sem restart | `pg_settings` mostra o arquivo de origem, e depois `restart` |
| Erro `wrong version number` no HTTPS | `listen 443;` sem a palavra `ssl` | `listen 443 ssl;` |
| Nginx não achava a chave do certificado | Caminho sem `/` inicial | Usar caminhos absolutos |
| 403 na página inicial | Não havia `index.html` | Criar o arquivo ou apontar para a aplicação |
| 502 Bad Gateway | Serviço `app` fora do ar: `EnvironmentFile` mal escrito, seção `[Unit]` errada, banco desligado ou erro de SQL | `journalctl -u app` e `systemd-analyze verify` |
| Aviso de cotas com arquivos externos obsoletos | Cotas antigas (`aquota.user`) | `tune2fs -O quota` e cotas nativas |
| `repquota` não listava usuários | Usuários com uso zero ficam ocultos | `repquota -vs`, com o `s` por último |
| Samba recusava todos | Parâmetro `hosts allow` escrito errado | `testparm -s` após toda edição |
| Backup parava no meio | `$WORKDIR` sem o `$`, argumentos do `tar` trocados e primeira linha do script errada | Revisar o script e a linha `#!/bin/bash` |
| Cron não executava | Pacote não instalado ou nome de arquivo com ponto em `/etc/cron.d` | `apt install cron` e nome sem ponto |
| Senha SSH continuava ativa | Outro arquivo em `sshd_config.d` vencia | Arquivo `00-hardening.conf`, lido primeiro |
| Windows não achava `web01` | Arquivo salvo como `config.txt` | Renomear para `config`, sem extensão |
