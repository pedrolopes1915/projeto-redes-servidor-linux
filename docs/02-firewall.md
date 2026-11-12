# 2. Firewall (nftables no fw-router)

Arquivo de regras: `fw-router/nftables.conf` (instalado em `/etc/nftables.conf`).

A política padrão das cadeias `input` e `forward` é **DROP**: só passa o que foi explicitamente permitido. A tabela `nat` faz o DNAT das portas 80 e 443 para o `web01` e o mascaramento (masquerade) da saída pela WAN.

## Matriz de conectividade implementada

| Origem | Destino | Porta | Ação | Justificativa |
|---|---|---|---|---|
| WAN | DMZ (web01) | 80, 443/TCP | PERMITIR (DNAT) | Acesso público ao serviço web. |
| DMZ (web01) | DB (db01) | 5432/TCP | PERMITIR | Comunicação estrita de dados da aplicação. |
| LAN | file01 | 139, 445/TCP | PERMITIR | Acesso a pastas e backups. O file01 fica na mesma sub-rede, então o controle é do Samba (`hosts allow`). |
| LAN (admin) | DMZ, DB e roteador | 22/TCP | PERMITIR | Gerenciamento por chaves SSH. |
| DMZ / WAN | DB | qualquer | BLOQUEAR (DROP) com log | Impede ataques diretos ao banco. |

## Regras adicionais e justificativas

| Regra | Motivo |
|---|---|
| DB (db01) para file01, 139/445 | O backup diário precisa enviar o arquivo ao servidor de arquivos, e a matriz original não previa esse fluxo. Limitada ao IP do db01 e ao IP do file01. |
| LAN para DMZ, 80/443 | Os usuários internos acessam o site. |
| Saída para a internet (LAN livre; DMZ e DB só 80/443) | Atualizações de pacotes. DNS não precisa de regra de repasse, pois os servidores consultam o Bind9 do roteador. |
| `ct state established,related` | Permite as respostas das conexões já autorizadas. |
| DNS (53) e DHCP (67) na cadeia `input` | O roteador atende essas consultas das zonas internas. |
| SSH da faixa da NAT (192.168.100.0/24) | Acesso de gerenciamento pelo Windows, via redirecionamento de porta do VirtualBox. Existe só por causa do laboratório. |

## Interpretação da matriz

O enunciado cita "DMZ/WAN para DB: bloquear" e também "DMZ (servidor web) para DB: permitir". A interpretação adotada é que o único host da DMZ com acesso ao banco é o `web01`, identificado pelo IP. Qualquer outro endereço da DMZ, ou qualquer porta diferente da 5432, é bloqueado e registrado com o prefixo `FW-DROP-DB:`.

O mesmo vale no PostgreSQL: o `pg_hba.conf` libera somente `10.0.1.10/32`.

## Comandos úteis

```bash
sudo nft -c -f /etc/nftables.conf            # valida a sintaxe sem aplicar
sudo systemctl restart nftables              # aplica as regras
sudo nft list ruleset                        # mostra tudo
sudo nft list chain inet filter forward      # regras e contadores do encaminhamento
sudo journalctl -k --no-pager | grep FW-DROP-DB    # pacotes bloqueados
```
