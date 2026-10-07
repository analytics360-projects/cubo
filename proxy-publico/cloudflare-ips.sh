#!/usr/bin/env bash
# Descarga los rangos de Cloudflare y regenera:
#  - /etc/nginx/conf.d/cloudflare-realip.conf (IP real del visitante vía CF-Connecting-IP)
#  - reglas de ufw: 80/443 solo desde Cloudflare y la LAN 10.19.5.0/24
# Se instala en /usr/local/sbin/ y corre cada semana con cloudflare-ips.timer.
set -euo pipefail

v4=$(curl -fsS --max-time 20 https://www.cloudflare.com/ips-v4)
v6=$(curl -fsS --max-time 20 https://www.cloudflare.com/ips-v6)
[ "$(echo "$v4" | wc -l)" -ge 10 ] || { echo "lista de Cloudflare incompleta" >&2; exit 1; }

tmp=$(mktemp)
{
  echo "# Generado por cloudflare-ips.sh $(date -Is). No editar."
  for r in $v4 $v6; do echo "set_real_ip_from $r;"; done
  echo "real_ip_header CF-Connecting-IP;"
} > "$tmp"
install -m 644 "$tmp" /etc/nginx/conf.d/cloudflare-realip.conf
rm -f "$tmp"
nginx -t -q && systemctl reload nginx

# ufw: borra las reglas previas de Cloudflare y las vuelve a crear.
{ ufw status numbered | grep -E "\(cloudflare\)" | grep -oE "^\[ *[0-9]+\]" | tr -d "[] " | sort -rn || true; } |
  while read -r n; do ufw --force delete "$n" >/dev/null; done
for r in $v4 $v6; do
  ufw allow proto tcp from "$r" to any port 80,443 comment cloudflare >/dev/null
done
echo "Cloudflare: $(echo $v4 $v6 | wc -w) rangos aplicados"
