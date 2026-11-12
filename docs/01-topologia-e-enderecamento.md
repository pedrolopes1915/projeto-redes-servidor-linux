# 1. Topologia e endereçamento

## Diagrama lógico

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

## Zonas e redes internas do VirtualBox

| Zona | Rede | Gateway | Rede interna do VirtualBox | Interface no fw-router |
|---|---|---|---|---|
| WAN | 192.168.100.0/24 (NAT) | gateway da NAT | NAT | enp0s3 |
| DMZ | 10.0.1.0/24 | 10.0.1.1 | `dmz` | enp0s8 |
| LAN | 10.0.2.0/24 | 10.0.2.1 | `lan` | enp0s9 |
| DB | 10.0.3.0/24 | 10.0.3.1 | `db` | enp0s10 |

O `fw-router` usa quatro adaptadores (1 NAT, 2 `dmz`, 3 `lan`, 4 `db`). Cada servidor usa um adaptador de rede interna ligado à rede da sua zona.

A NAT padrão do VirtualBox usa `10.0.2.0/24`, a mesma faixa da LAN. Por isso, com a VM desligada, a faixa da NAT do roteador foi trocada:

```
VBoxManage modifyvm "fw_router" --natnet1 "192.168.100.0/24"
```

## Hosts

| Host (VM) | IP | Observação |
|---|---|---|
| fw-router (`fw_router`) | 10.0.1.1, 10.0.2.1, 10.0.3.1 e WAN por DHCP da NAT | Roteador, firewall, DHCP e DNS |
| web01 | 10.0.1.10 | IP estático |
| file01 | 10.0.2.10 | Reserva DHCP por MAC |
| db01 (`db1`) | 10.0.3.10 | IP estático |

## Tabelas de roteamento

| Host | Destino | Via | Interface |
|---|---|---|---|
| fw-router | 192.168.100.0/24 | direta | enp0s3 |
| fw-router | default | gateway da NAT (192.168.100.2) | enp0s3 |
| fw-router | 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24 | direta | enp0s8, enp0s9, enp0s10 |
| web01 | 10.0.1.0/24 / default | direta / 10.0.1.1 | enp0s3 |
| file01 | 10.0.2.0/24 / default | direta / 10.0.2.1 (via DHCP) | enp0s3 |
| db01 | 10.0.3.0/24 / default | direta / 10.0.3.1 | enp0s3 |

O roteamento entre as zonas depende de `net.ipv4.ip_forward=1`, gravado em `/etc/sysctl.d/99-forward.conf` no `fw-router`.

## Nomes DNS (domínio empresa.local)

| Nome | IP |
|---|---|
| ns1.empresa.local, fw-router.empresa.local | 10.0.2.1 |
| web01.empresa.local | 10.0.1.10 |
| file01.empresa.local | 10.0.2.10 |
| db01.empresa.local | 10.0.3.10 |

A resolução reversa existe para as três sub-redes (`1.0.10.in-addr.arpa`, `2.0.10.in-addr.arpa` e `3.0.10.in-addr.arpa`). Os arquivos de zona estão em `fw-router/zones/`.

O `systemd-resolved` trata nomes `.local` como mDNS. Por isso, os servidores têm `search: [empresa.local]` no Netplan; sem isso, ele não consulta o DNS interno.

## DHCP

O dnsmasq atende só a LAN (interface `enp0s9`), com `port=0` (o DNS fica com o Bind9). Faixa dinâmica `10.0.2.100` a `10.0.2.200`, com concessão de 12 horas, e reserva do IP `10.0.2.10` para o `file01`. Configuração em `fw-router/lan.conf`.

## Mapeamento de portas

| Serviço | Host | Porta | Escuta em |
|---|---|---|---|
| DNS | fw-router | 53/UDP e TCP | 10.0.1.1, 10.0.2.1, 10.0.3.1, 127.0.0.1 |
| DHCP | fw-router | 67/UDP | enp0s9 (LAN) |
| HTTP (redireciona) e HTTPS | web01 | 80/TCP e 443/TCP | todas as interfaces |
| Aplicação FastAPI | web01 | 8000/TCP | somente 127.0.0.1 |
| PostgreSQL | db01 | 5432/TCP | localhost e 10.0.3.10 |
| Samba | file01 | 139 e 445/TCP | localhost e 10.0.2.10 |
| SSH | todas | 22/TCP | todas as interfaces |

## Acesso de gerenciamento pelo Windows

Na NAT do `fw_router` existe um redirecionamento de porta do VirtualBox: `127.0.0.1:2222` para a porta 22 do convidado. O Windows chega ao roteador por ele e aos servidores passando pelo roteador (`ProxyJump` no arquivo `~/.ssh/config`). Opcionalmente, `127.0.0.1:8443` para a porta 443 serve para demonstrar o site no navegador.
