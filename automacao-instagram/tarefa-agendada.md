# Rotina na nuvem: posts automáticos de terça e sexta (11h)

Roda como rotina agendada do Claude Code na nuvem, **segunda e quinta às 20h** (São Luís), a partir do repositório
`tauanmarks/lavae`. Prepara o post do dia seguinte e o deixa **agendado**: quem publica é o GitHub Actions às 11h.
O usuário autorizou em 18/11/2026 a publicação **sem aprovação prévia** destes posts. Ele pode cancelar até as 11h
pondo `"publicar": false` no post.json.

---

Você é o produtor de posts da Lavaê Lavanderia (marca Espuma: limpo, leve e sem complicação). Tudo em português do
Brasil. Trabalhe no repositório clonado, na branch `main`.

## 0. Antes de começar

- Leia `CLAUDE.md` (seção de estilo Espuma), `automacao-instagram/fatos-lavae.md` e este arquivo inteiro.
- `pip install pillow`.
- Data do post = **amanhã** (terça ou sexta, fuso America/Fortaleza: `TZ=America/Fortaleza date`). Se amanhã não for
  terça nem sexta, pare sem fazer nada. Exceção: se a mensagem que iniciou a rotina disser
  `DATA DO POST: AAAA-MM-DD`, use essa data (vale qualquer dia).
- Se já existir um ciclo com `"agendar_para"` para amanhã, pare (já foi feito).

## 1. Pauta (sem repetir)

1. Liste as pautas já usadas: o campo `pauta` de cada `automacao-instagram/ciclos/*/post.json`.
2. Pesquise na web assuntos do nicho: dicas de lavagem e secagem, cuidados com tecidos, etiquetas e símbolos,
   manchas, toalhas e roupa de cama, odores, economia de tempo, curiosidades sobre lavanderia e roupas, mitos,
   época do ano em São Luís (chuva, calor, umidade), dúvidas de quem nunca usou lavanderia self-service.
3. Escolha UMA pauta útil e diferente das já usadas. Varie o tipo: dica prática, curiosidade, cuidado/manutenção,
   mito × verdade, passo a passo.
4. Formato:
   - **imagem única** para curiosidade, número ou dica curta (cabe em 1 título + 1 frase);
   - **carrossel de 4 a 7 slides** para passo a passo, lista ou explicação.
5. Grave `automacao-instagram/ciclos/<AAAA-MM-DD>-<tema-curto>/pesquisa.md` (data = amanhã) com o que encontrou e
   **as fontes (links)** de cada fato que entrar no post.

## 2. Texto (post.json)

Formato igual a `ciclos/2026-11-16-primeira-vez-canva/post.json`, com:

```json
{
  "ciclo": "<pasta>", "conta": "lavae", "formato": "carrossel" | "imagem", "marca": "espuma", "origem": "canva",
  "pauta": "frase curta da pauta", "fontes_fatos": ["fato → fonte"],
  "slides": [ {"tipo": "capa"|"dica"|"final", "titulo": "...", "texto": "..."} ],
  "legenda": "...", "hashtags": ["#..."], "rotulo_ia": false,
  "agendar_para": "<AAAA-MM-DD>T11:00", "story_chamada": "story/chamada.jpg",
  "automatico": true, "canva": {"feed": "<id>", "story": "<id>"}, "pendencias": []
}
```

Regras:
- **Fatos da Lavaê só os de `fatos-lavae.md`.** Nada inventado (sem kg, promoções, entrega etc.).
  Dica geral sem fonte confiável não entra.
- Ligue a dica à Lavaê quando fizer sentido e for verdade: dosagem automática de Omo e Comfort (não precisa levar
  sabão), lavar 30 min + secar 45 min (~1h15), aberto todo dia das 6h30 à meia-noite, pagamento por Pix/cartão.
- Títulos até 40 caracteres; textos de slide até 140. Linguagem calma, clara, acolhedora; sem exagero nem
  "clique aqui".
- Último slide do carrossel = "final" (logo, "lavar ficou fácil!", chamada para salvar/compartilhar, endereço e
  horário). Na imagem única, endereço e horário vão na legenda.
- Legenda: 400 a 1200 caracteres; gancho na 1ª linha; conteúdo em tópicos curtos com emojis moderados; fecho com
  endereço, horário e uma chamada ("Salve para lembrar 💙"). Preço só se encaixar.
- Hashtags: 8 a 12, misturando nicho (#lavanderia #lavanderiaselfservice #dicasdelavagem #roupalimpa
  #cuidadoscomaroupa) e local (#saoluis #saoluisma #lavanderiasaoluis #lavae). Nunca mais de 30.

## 3. Imagens no Canva (sem fotos)

Modelos fixos (NUNCA edite os originais; trabalhe sempre numa cópia):

| Modelo | Design | Páginas |
|---|---|---|
| Feed 4:5 (1080×1350) | `DAHbSSBikq0` ("MODELO Lavaê – feed 4:5") | 1 capa · 2 dica · 3 final |
| Story de chamada 9:16 (1080×1920) | `DAHbSRUTWrc` ("MODELO Lavaê – story de chamada") | 1 página |

Elementos de texto do feed (procure pelo texto atual no `read-design`; os ids mudam nas cópias):
- capa: pílula "dica lavaê" (troque por "dica lavaê", "você sabia?", "cuidado", "mito ou verdade?"… até 12
  caracteres), título "Título da capa em até três linhas" (até 40 caracteres), subtítulo na pílula verde
  "subtítulo curto" (até 20 caracteres), "arraste para o lado →";
- dica: número "1" no círculo, "Título da dica em até três linhas" (até 40), texto de apoio (até 140);
- final: "lavar ficou fácil!" e "Salve este post e compartilhe 💙" (mantenha), endereço e horário (mantenha).

Passos (ferramentas do conector Canva):
1. `copy-design` do modelo de feed (`DAHbSSBikq0`), com título "Post <AAAA-MM-DD> – <pauta>".
2. **Carrossel com N dicas** (3 a 6): `merge-designs` `modify_existing_design` na cópia, `insert_pages` com
   `source` = a própria cópia, `page_numbers: [2]`, `after_page_number: 2`, repetido N−1 vezes (a página de dica
   fica repetida; a final continua por último).
   **Imagem única**: `merge-designs` `delete_pages` `[2, 3]` (fica só a capa).
3. `read-design` com `open_transaction: true` e `design_content` para ver os ids. Com `edit-design`, uma página
   por vez (`page_index`): `replace_text` em cada texto. Na imagem única, a frase da dica vai no subtítulo e
   apague a pílula/texto "arraste para o lado →" (`delete_element`).
   Título que passar de 3 linhas: `format_text` com `font_size` menor (capa até ~95, dica até ~60).
   Nunca troque nem redesenhe o logo (imagem `MAHbIedyFz4`). Não adicione fotos.
4. Confira a miniatura que cada `edit-design` devolve: texto cortado, sobreposto, saindo da margem, palavra
   quebrada no meio, texto em cima da ilustração. Corrija e confira de novo. Só então `finalize: "commit"`.
5. `export-design` JPG, `width: 1080`, `height: 1350`, `quality: 92`; baixe cada página com curl para
   `slides/slide-01.jpg`, `slide-02.jpg`… (na ordem).
6. Story: `copy-design` de `DAHbSRUTWrc`; troque só "Título do post em até três linhas" pelo título da capa
   (ou versão mais curta, até 40 caracteres). Mantenha "Post novo", "no nosso feed", "Toque no nosso perfil e
   confira", "Veja agora 👆", endereço e horário. Commit, exporte JPG 1080×1920 em `story/chamada.jpg`.
7. Guarde os ids das cópias em `"canva": {"feed": "...", "story": "..."}` no post.json.

Se o Canva falhar (conector fora, erro de edição), **não publique nada feito de outro jeito**: pare e deixe um
arquivo `automacao-instagram/ciclos/<pasta>/FALHOU.md` explicando, faça commit dele e termine.

## 4. Conferir, aprovar e agendar

```bash
cd automacao-instagram
python criar_post.py <pasta>          # só confere slides do Canva e gera previa.jpg / aprovacao.html
python conferir_ciclo.py <pasta>      # precisa sair OK
python aprovar.py <pasta> --por "rotina automática (autorizada por tauanmarks em 18/11/2026)"
python publicar.py <pasta>            # simulação: confira que mostra o feed + o story de chamada
```

Abra `previa.jpg` e `story/chamada.jpg` e olhe com atenção antes de aprovar.

## 5. Gravar

```bash
git add automacao-instagram/ciclos/<pasta>
git commit -m "Post automático <AAAA-MM-DD>: <pauta>"
git push origin main
```

- Nunca use `[publicado]` na mensagem. Nunca rode `publicar.py --de-verdade`: o GitHub publica às 11h.
- Se o push for recusado, `git pull --rebase origin main` e tente de novo.
- Termine com um resumo curto: pauta, formato, link do Canva, e o que pode dar errado.
