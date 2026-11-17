# Publicar Lavaê — edição na marca Espuma

Editor de vídeos curtos (9:16) da **Lavaê Lavanderia**, com **uma marca só: Espuma** (copiada do `Editor_Variado`, em `Desktop/Meus Videos/Editor_Variado`). Tudo em português.
Assinatura: *limpo, leve e sem complicação*. Personalidade: calma, clara, acolhedora, prática.

## Pastas

| Pasta | O que vai nela |
|---|---|
| `videos-brutos/<projeto>/` | Clipes originais de cada vídeo. A análise grava em `<projeto>/_analise/` e o plano em `<projeto>/plano.json`. |
| `videos-prontos/` | Só vídeos renderizados **depois** de aprovados: `<projeto>.mp4` (versões: `<projeto>-v2.mp4`). |
| `fichas-de-marca/` | `marcas.json` (só a Espuma — fonte única) e `ficha-de-marca.html` (gerada, para revisar). |
| `storyboards/<projeto>/` | Storyboard de revisão (gerado). |
| `referencias/` | `lavae/logo-lavae.png`, `musicas/espuma/` (trilhas livres de direitos, usadas antes da sintetizada) e `exemplo-lavae/` (plano, roteiro, dados e `Lavae.tsx` do vídeo aprovado em 16/11/2026 — **modelo de referência**). |
| `ferramentas/pipeline/` | `analisar.py`, `storyboard.py`, `narrar.py`, `alinhar_narracao.py`, `preparar_render.py`, `sons_marca.py`, `gerar_ficha.py`. |
| `ferramentas/remotion-projeto/` | Render. Marca em `src/marcas/`: `tema.ts`, `componentes.tsx` (legenda, zoom, transição) e `espuma.tsx` (elementos visuais da Espuma). |
| `ferramentas/sons/espuma/` | Kit sonoro (bolha, clique_suave, ding_suave, swoosh_macio, trilha) — cópia em `remotion-projeto/public/sons/espuma/`. |
| `ferramentas/modelos/` | Redução de ruído `cb.rnnn`/`sh.rnnn` (ffmpeg `arnndn`). |

## Fluxo obrigatório (nesta ordem)

1. **Analisar** — `python ferramentas/pipeline/analisar.py videos-brutos/<projeto> --vocabulario "Lavaê, Pix, CPF, totem"` (≈2 min por minuto de material; rode em segundo plano). Leia `_analise/relatorio.md` e **olhe as folhas de contato** em `_analise/miniaturas/`.
2. **Planejar** — escreva `videos-brutos/<projeto>/plano.json` com `"marca": "espuma"` (formato abaixo; veja `referencias/exemplo-lavae/plano.json`).
3. **Storyboard** — `python ferramentas/pipeline/storyboard.py videos-brutos/<projeto>/plano.json` (adicione `--previa-video` se ajudar). Se sair com código 2 (bloqueios), **corrija o plano antes de mostrar**. Mostre `storyboards/<projeto>/storyboard.html` e **espere aprovação explícita**.
4. **Renderizar só depois do “aprovado”** — `python ferramentas/pipeline/preparar_render.py videos-brutos/<projeto>/plano.json`, depois composição em `ferramentas/remotion-projeto/src/<projeto>/` (copie a estrutura de `referencias/exemplo-lavae/Lavae.tsx`, mas importe os elementos de `../marcas/espuma`), registre em `src/Root.tsx`, saída em `videos-prontos/`.

**Nunca renderize um vídeo (nem “versão de teste”) sem storyboard aprovado.** Prévia crua do storyboard (`previa.mp4`) é permitida.

## Regras de corte

- **Cortar só em pausa real** (`corte_in`/`corte_out` de `analise.json`), nunca dentro de uma palavra; **nunca no meio de uma ideia**. Frases ⚠ não se separam da vizinha.
- **Repetições**: use o take ✓; trocou, marque `"take_escolhido": true` com motivo. **Falsos começos (↺)** saem; **frases ❓** conferir antes de usar.
- **Não perder o interessante**: 🔊, 🎬 e ★ que ficarem de fora vão em `descartados` com motivo.
- **Silêncio máximo 0,6 s.** A narração conduz: cada passo da tela aparece enquanto é narrado.
- Ações longas e repetitivas (colocar roupa, limpar filtro, processando) **aceleradas 2x a 4x**, sem cortar começo e fim da ação.
- Telas do sistema ficam **no mínimo 1,5 s** em velocidade normal.
- **Dados pessoais na tela (nome, CPF, cartão) sempre desfocados** (ver `BlurNome` no exemplo).
- Câmera frontal espelha texto → desespelhar. Plano tremido/desfocado só se for o único take.

## Estilo Espuma (resumo da ficha)

- **Cores**: Azul Lavaê `#1F4BA5` (cartões, títulos) · Azul Céu `#8CC8F2` (bolhas, detalhes) · Verde Totem `#8EDC3A` (destaque da legenda, check) · Névoa `#EAF4FC` (fundos claros) · Marinho `#0E2350` (contorno, texto em fundo claro) · Algodão `#FFFFFF`.
- **Fontes**: Quicksand 700 (títulos, números) · Nunito Sans 800 (legenda) · Lexend 500 (etiquetas, valores).
- **Legenda**: branca, contorno Marinho 6 px, 3–6 palavras por bloco, base a 72% da altura, entra com fade + subida (0,2 s). Ação do passo em Verde Totem (`kw: true`: “aproxime”, “Pix”).
- **Zoom**: na tela 100→135% em 0,6 s (botão/informação citada); deriva lenta 100→106% em planos de máquina e roupa.
- **Ritmo**: planos de 2,5–4 s, calmo e contínuo, um passo por vez com número.
- **Elementos** (`src/marcas/espuma.tsx`): `TituloAbertura`, `Selo` (número do passo), `Barra` (progresso no topo), `Bolhas`, `Check`, `Etiqueta`, `CartaoEspera` (“39 min depois” / “enquanto lava…”), `CartaoFinal` (logo + “lavar ficou fácil!”), `volumeTrilha` (ducking).
- **Transições**: dissolve curto 0,3 s (`TransicaoMarca`), bolhas subindo, corte seco no meio da ação.
- **Som**: bolha (entrada de selos/etiquetas), clique suave (toques na tela), ding suave (pagamento aprovado / fim), swoosh macio (troca de etapa). Trilha ambiente 72 BPM sem bateria, −20 dB sob a fala, sobe nos intervalos.
- **Cor da imagem**: limpa e fresca, branco neutro, leve frio nas sombras, saturação suave nos azuis.
- **Extras**: resumo final em 4 ícones (CPF, máquina, pagamento, roupa); versão sem narração com legendas; endereço e horário no encerramento.

## Formato do plano.json

```json
{
  "projeto": "nome-da-pasta",
  "titulo": "Título do vídeo",
  "marca": "espuma",
  "resumo": "Uma ou duas frases sobre o vídeo e a abordagem.",
  "clipes": [{ "clip": "IMG_0001", "uso": "usado | parcial | fora", "motivo": "o que entra e o que sai" }],
  "planos": [
    { "clip": "IMG_0001", "a": 1.65, "b": 6.6, "tipo": "fala", "tag": "gancho",
      "fala": "texto falado", "legenda": "como a legenda aparece", "velocidade": 1,
      "edicao": ["Zoom na tela 135% em 'Pix'"], "som": ["clique_suave"] },
    { "tipo": "cartao", "duracao": 1.0, "texto_cartao": "39 min depois", "edicao": ["Cartão de espera"] }
  ],
  "descartados": [{ "clip": "IMG_0001", "a": 7.2, "b": 8.4, "texto": "...", "motivo": "repetição / ruído / fora do tema" }],
  "musica": { "arquivo": "ferramentas/sons/espuma/trilha.wav", "faixa": "descrição da trilha", "bpm": 72, "volume_sob_fala_db": -20, "notas": "..." },
  "pendencias": ["decisões para o usuário"]
}
```
`tipo`: `fala` | `broll` | `acao` | `cartao`. Opcionais: `velocidade`, `mudo`, `intencional`, `take_escolhido`.

Vídeos narrados: escreva `videos-brutos/<projeto>/roteiro.json` (modelo em `referencias/exemplo-lavae/roteiro.json`), rode `narrar.py` (Francisca ou Thalita) e use `"narracao": {"id", "em"}` nos planos, com `"mudo": true` quando o áudio original não deve aparecer. Quadro congelado: `"congelar": true` + `"duracao"`. Reuso de imagem: `"reuso": true`. Voz de outro clipe: `"audio_clip"` + `"audio_a"`.
Mudou algo em `fichas-de-marca/marcas.json` → `python ferramentas/pipeline/gerar_ficha.py`. Refazer o kit sonoro → `python ferramentas/pipeline/sons_marca.py espuma 60` (sempre com `espuma`, senão gera o kit de todas as marcas do script).

## Render (Remotion)

- `npm run dev` em `ferramentas/remotion-projeto` → composição `DemoEspuma` mostra todos os elementos da marca.
- Clipes do projeto vão para `remotion-projeto/public/<projeto>/` (o `preparar_render.py` faz isso).
- Áudio final: fala tratada (arnndn + EQ), trilha com ducking, master −14 LUFS / −1 dBTP.
- Zonas seguras: nada importante nos 220 px de cima, 380 px de baixo e 160 px da direita.
- Antes de entregar: `npx remotion still` em 3–4 pontos para conferir legenda nas zonas seguras.
