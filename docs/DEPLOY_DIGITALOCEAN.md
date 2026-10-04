# Deploy do Radar Goiano na DigitalOcean

## Arquitetura e custo

O banco local ocupa aproximadamente 22 GB. O deploy recomendado usa um Droplet Basic com 2 vCPUs, 4 GB de RAM e 80 GB de SSD, que custa US$ 24 por mês. O servidor executa cinco contêineres permanentes:

- `web`: build React/Vite servido pelo Nginx;
- `api`: FastAPI/Uvicorn, acessível internamente em `/backend`;
- `banco`: PostgreSQL 18 em volume Docker persistente.
- `gateway`: Caddy como proxy interno;
- `tunnel`: Cloudflare Tunnel, único caminho público para o site.

O frontend e a API usam a mesma origem. A porta do PostgreSQL não é publicada. O backup semanal opcional da DigitalOcean acrescenta 20% ao preço do Droplet; também é necessário manter uma cópia externa do banco.

## 1. Criar o Droplet

No painel da DigitalOcean:

1. selecionar **Create > Droplets**;
2. escolher Ubuntu 24.04 LTS;
3. escolher uma região próxima do público, preferencialmente Estados Unidos;
4. selecionar Basic, 2 vCPUs, 4 GB RAM e 80 GB SSD;
5. autenticar com chave SSH, não senha;
6. ativar Monitoring e, se couber no orçamento, Weekly Backups;
7. reservar um IP público para administração, sem publicar o site diretamente nesse IP.

O site exige um domínio gerenciado pelo Cloudflare. O Cloudflare Tunnel cria conexões somente de saída e impede acesso direto ao servidor web pelo IP.

## 2. Preparar o Ubuntu

Conectar por SSH e instalar as dependências:

```sh
sudo apt update
sudo apt install -y ca-certificates curl git docker.io docker-compose-v2 ufw fail2ban
sudo systemctl enable --now docker fail2ban
sudo usermod -aG docker "$USER"
sudo ufw allow OpenSSH
sudo ufw --force enable
```

Sair e entrar novamente no SSH para aplicar o grupo `docker`. As portas 80, 443, 5432, 8000 e 8080 não devem ser abertas. No Cloud Firewall da DigitalOcean, permitir somente SSH a partir do seu IP administrativo; o túnel não precisa de regra de entrada.

## 3. Clonar e configurar

```sh
sudo mkdir -p /opt/radar-goiano
sudo chown "$USER":"$USER" /opt/radar-goiano
git clone https://github.com/davy-mota/Radar-Goiano.git /opt/radar-goiano
cd /opt/radar-goiano
cp .env.production.example .env.production
nano .env.production
```

Definir uma senha longa e exclusiva. O arquivo `.env.production` é ignorado pelo Git.

Criar duas senhas diferentes: uma administrativa do PostgreSQL e outra para o usuário somente leitura da API. Configurar o domínio:

```env
CORS_ORIGINS=https://seudominio.com.br
ALLOWED_HOSTS=seudominio.com.br,localhost
```

No painel Cloudflare Zero Trust:

1. abrir **Networks > Tunnels**;
2. criar um túnel chamado `radar-goiano`;
3. copiar somente o token para `CLOUDFLARE_TUNNEL_TOKEN`;
4. criar o hostname público `seudominio.com.br`;
5. definir o serviço como `HTTP` e a URL interna como `http://gateway:80`;
6. ativar Bot Fight Mode na área de segurança do domínio.

O token não deve ser inserido em comandos, commits ou logs. No contêiner ele é fornecido pela variável `TUNNEL_TOKEN`, evitando exposição na lista de processos.

## 4. Transferir o banco inicial

No Windows local:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup_producao.ps1
```

O script cria `backups/radar_goiano.dump` e mostra seu SHA-256. Transferir com `scp` ou WinSCP:

```powershell
scp backups/radar_goiano.dump usuario@IP_DO_DROPLET:/opt/radar-goiano/backups/
```

No servidor, conferir o hash e restaurar:

```sh
sha256sum backups/radar_goiano.dump
docker compose --env-file .env.production -f compose.prod.yml up -d banco
docker compose --env-file .env.production -f compose.prod.yml exec -T banco \
  pg_restore --clean --if-exists --no-owner --no-acl \
  -U radar_admin -d radar_goiano /backups/radar_goiano.dump
```

Se `POSTGRES_USER` ou `POSTGRES_DB` forem alterados, ajustar o comando. A restauração pode demorar devido ao volume dos dados.

## 5. Publicar

```sh
sh scripts/deploy_vps.sh
curl http://127.0.0.1:8080/health
```

Resposta esperada:

```json
{"status":"ok","api":"online","banco":"online"}
```

Depois, acessar `https://seudominio.com.br` no navegador. `127.0.0.1:8080` existe apenas para o health check local e não fica acessível externamente.

## 6. Deploy automático pelo GitHub

Cadastrar estes secrets em **Settings > Secrets and variables > Actions**:

- `DEPLOY_HOST`: IP público do Droplet;
- `DEPLOY_USER`: usuário SSH;
- `DEPLOY_SSH_KEY`: chave privada exclusiva do deploy;
- `DEPLOY_PATH`: caminho absoluto do repositório no servidor.

Criar também a variable `DEPLOY_ENABLED=true`. Sem ela, os testes rodam, mas o acesso SSH fica desativado.

Cada push na `main` executa lint, build e compilação Python. Somente depois dessas validações o workflow atualiza o servidor com `git pull --ff-only` e `scripts/deploy_vps.sh`.

## Atualização normal

```sh
git add .
git commit -m "feat: descricao da atualizacao"
git push origin main
```

O volume PostgreSQL é preservado durante a reconstrução dos contêineres.

## Atualização do banco

Migrações e cargas não são automáticas porque alteram dados públicos. O processo deve ser:

1. gerar backup;
2. executar a migração explicitamente;
3. executar a carga em lote isolado;
4. validar contagens e valores;
5. ativar o lote aprovado.

## Rollback

Para desfazer código sem reescrever o histórico:

```sh
git revert HASH_DO_COMMIT
git push origin main
```

Para dados, restaurar o backup anterior ou reativar o lote arquivado. Não usar `git reset --hard` no servidor.

## Monitoramento e capacidade

- acompanhar `https://seudominio.com.br/health` por um monitor externo;
- configurar alerta de CPU, RAM e disco no painel DigitalOcean;
- manter ao menos 20 GB livres para WAL, restaurações e atualizações;
- executar `docker system prune` somente depois de revisar os alvos;
- nunca remover o volume `postgres_data` durante atualizações;
- manter backup externo e testar restauração periodicamente.

Se o banco ultrapassar aproximadamente 45–50 GB, o plano de 80 GB ficará apertado para backup e operações. Nesse caso, redimensionar o Droplet para 8 GB/160 GB antes de atingir o limite.

## Controles de segurança implementados

- proteção DDoS L3/L4 permanente da DigitalOcean;
- proteção DDoS HTTP, CDN e bots do Cloudflare;
- origem sem portas web públicas, acessível pelo Cloudflare Tunnel;
- PostgreSQL e FastAPI em rede Docker privada;
- credencial `radar_api` somente leitura e com transações read-only por padrão;
- timeout SQL de 30 segundos e pool limitado a dez conexões por processo;
- limite de dez requisições por segundo por IP, com rajada de trinta;
- no máximo vinte conexões simultâneas por IP;
- cache de cinco minutos para respostas GET bem-sucedidas;
- corpo de requisição limitado a 1 MiB;
- documentação OpenAPI desativada em produção;
- validação do cabeçalho `Host`;
- CSP, proteção contra frames, MIME sniffing e restrição de recursos do navegador;
- SSH por chave, UFW, Fail2ban e Cloud Firewall.

O rate limit local usa `CF-Connecting-IP`. Esse cabeçalho é confiável nesta arquitetura porque o Nginx não possui porta pública e só recebe tráfego do contêiner do túnel.

## Atualizações de segurança do Ubuntu

```sh
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Revisar mensalmente as imagens fixadas no `compose.prod.yml`. Atualizar conscientemente as versões do PostgreSQL, Caddy, Nginx, Python e `cloudflared`, executar os testes e gerar backup antes do deploy.
