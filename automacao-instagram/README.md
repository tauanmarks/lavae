# Automação de posts no Instagram — Lavaê (marca Espuma)

Ciclo: **pesquisa → roteiro → criação → aprovação → publicação**. Nada é publicado sem o seu "aprovado".

| Etapa | Quem faz | Arquivo |
|---|---|---|
| 1. Pesquisa do nicho | Claude (busca na web) | `ciclos/<ciclo>/pesquisa.md` |
| 2. Roteiro (slides + legenda) | Claude, usando só fatos com fonte | `ciclos/<ciclo>/post.json` |
| 3. Criação das imagens | `criar_post.py` → Remotion `CarrosselEspuma` (1080×1350 JPEG), **ou** Canva (`"origem": "canva"` no post.json: o design é gerado e exportado pelo conector do Canva, e `criar_post.py` só confere os slides) | `ciclos/<ciclo>/slides/` |
| 4. Revisão | Você, na página | `ciclos/<ciclo>/aprovacao.html` |
| 5. Aprovação | Você diz `aprovado <ciclo>` → Claude roda `aprovar.py` | `ciclos/<ciclo>/aprovacao.json` |
| 6. Publicação | `publicar.py --de-verdade` (API oficial do Instagram) | `ciclos/<ciclo>/publicacao.json` |
| 7. Repetição | Rotina agendada na nuvem (`tarefa-agendada.md`) — **ainda não ligada** | — |

```bash
python automacao-instagram/criar_post.py 2026-11-16-primeira-vez
python automacao-instagram/aprovar.py 2026-11-16-primeira-vez --por "Tauan"
python automacao-instagram/publicar.py 2026-11-16-primeira-vez
python automacao-instagram/publicar.py 2026-11-16-primeira-vez --de-verdade
```
(o terceiro só simula; o quarto publica)

## Rodando na nuvem (sem o computador ligado)

```
Claude agendado (nuvem) ──► pull request "Post <ciclo>" ──► você faz merge pelo celular ──► GitHub Actions publica
   pesquisa, roteiro,          (prévia + legenda +            (= aprovação)                   no Instagram e grava
   slides, conferência          pendências no corpo)                                          publicacao.json
```

| Peça | Arquivo |
|---|---|
| Rotina agendada (o que o Claude faz na nuvem) | `tarefa-agendada.md` |
| Conferência de cada pull request (não publica) | `.github/workflows/conferir-post.yml` → `conferir_ciclo.py` |
| Publicação no merge / manual (Actions → Run workflow) | `.github/workflows/publicar-instagram.yml` → `ci_publicar.py` |

- O merge do pull request **é** a aprovação: `ci_publicar.py` grava `aprovacao.json` em nome de quem fez o merge.
- Só publica ciclos **alterados** naquele merge; ignora `"publicar": false` e o que já tem `publicacao.json`.
- As imagens vão para a API pelo link "raw" do GitHub no commit publicado → o repositório precisa ser **público**
  (não há segredo nele; token fica em *Settings → Secrets and variables → Actions*: `IG_USER_ID`, `IG_ACCESS_TOKEN`).
  Repositório privado: definir a variável `IG_BASE_URL` apontando para outra hospedagem.
- Vídeos com filmagem nova continuam no computador (os clipes brutos não vão para o GitHub).

Testado em 16/11/2026 numa cópia do repositório: push inicial não publica nada; merge de um ciclo novo grava a
aprovação e tenta publicar (falha clara sem token); ciclo `"publicar": false` e ciclo já publicado são pulados;
URLs saem como `raw.githubusercontent.com/<repo>/<commit>/.../slides/slide-01.jpg` (o GitHub serve com tipo de imagem).

## Travas (testadas em 16/11/2026, numa cópia do ciclo)

| Situação | Resultado |
|---|---|
| Publicar sem aprovação | recusado |
| Legenda ou imagem mudou depois da aprovação | recusado (impressão digital não bate) |
| Publicar de novo um ciclo já publicado | recusado |
| Carrossel com mais de 10 slides, legenda > 2200, > 30 hashtags, título/texto longo demais | `criar_post.py` para antes de gerar |
| `--de-verdade` sem token/conta/endereço público | erro, nada é enviado |
| Imagem não acessível publicamente como JPEG | erro antes de chamar a API |

## O que falta para publicar de verdade (você)

1. **Conta profissional** no Instagram (Empresa ou Criador de conteúdo). Com o login do Instagram não precisa de página do Facebook.
2. **App na Meta**: developers.facebook.com → Criar app → adicionar o produto *Instagram* → "Configuração da API com login do
   Instagram" → adicionar a conta da Lavaê → gerar token. Permissões: `instagram_business_basic` e
   `instagram_business_content_publish`. Para uso só na própria conta, o app em modo de desenvolvimento basta (você é admin).
3. Colocar `IG_USER_ID` e `IG_ACCESS_TOKEN` em `automacao-instagram/.env` (você cola; o Claude não digita tokens).
   O token de longa duração vale ~60 dias e precisa ser renovado.
4. **Hospedagem pública das imagens** (`IG_BASE_URL`): a API não recebe arquivo, ela baixa a imagem de um link público.
   Precisa escolher onde: um site/servidor seu, um bucket (Cloudflare R2, S3) ou um serviço de imagens.

## Canva (testado em 16/11/2026, ciclo `2026-11-16-primeira-vez-canva`)

- Fotos reais saem dos clipes brutos (quadros sem dado pessoal) e sobem para o Canva junto com o logo.
- O Canva **redesenha o logo** em vez de usar o arquivo (saiu "lavaâê"): sempre trocar pelo logo enviado.
- O Canva gera em **3:4 (1080×1440)**, que a API do Instagram recusa: redimensionar para 1080×1350 no Canva e
  conferir de novo (o redimensionamento desalinhou texto e fundo numa página).
- `criar_post.py` recusa slides fora de 4:5–1,91:1 ou que não sejam JPEG.
- Para estabilizar: criar um **Kit de Marca da Lavaê** no Canva (hoje só existem os da Caravana).

## Limites

- Só carrossel e imagem única por enquanto. Reels: o vídeo já sai do fluxo da Espuma; falta o envio de vídeo na API.
- Vídeos automáticos sem filmagem nova ficam limitados a animação + narração.
- Limite da API: dezenas de posts por dia por conta (Meta cita 50 em parte da documentação) — longe do que vamos usar.
- O computador precisa estar ligado no horário da tarefa agendada (o render roda aqui).
