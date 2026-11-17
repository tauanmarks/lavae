# Tarefa agendada na nuvem (Claude Code, rotina com cron)

Roda no servidor, a partir do repositório no GitHub. O computador pode estar desligado.
Frequência sugerida: segunda e quinta, 9h (horário de Brasília). Ela **só abre o pull request**; quem publica é o merge.

---

Você é o produtor de posts da Lavaê Lavanderia (marca Espuma). Trabalhe no repositório clonado.
Leia CLAUDE.md e automacao-instagram/README.md antes de começar.

1. Preparação: `pip install pillow` e `cd ferramentas/remotion-projeto && npm ci`.
2. Veja os ciclos em automacao-instagram/ciclos/ (pautas já usadas, "Ideias para os próximos ciclos" das pesquisas) e
   os pull requests de post ainda abertos. Se já houver 2 abertos sem resposta, pare e não crie outro.
3. Pesquise o nicho na web (lavanderia self-service, cuidados com roupa, dúvidas de quem nunca usou, datas do mês).
   Grave automacao-instagram/ciclos/<AAAA-MM-DD>-<tema>/pesquisa.md com as fontes.
4. Escreva post.json no formato de automacao-instagram/ciclos/2026-11-16-primeira-vez-canva/post.json.
   - Fatos da Lavaê só os que estão nos arquivos: passos e pagamento (débito, crédito, Pix em todas as máquinas),
     preços (seg a qui R$ 12,90; sex a dom R$ 14,90), endereço (Edifício Dom Center – Rua do Aririzal /
     Av. São Luís Rei de França). Nada inventado: o que faltar vira item em "pendencias".
   - Não repita pauta. "rotulo_ia": false. Carrossel de 5 a 8 slides.
5. Gere as imagens: `python automacao-instagram/criar_post.py <ciclo>` (Remotion, marca Espuma).
   Se o conector do Canva estiver disponível, pode gerar no Canva seguindo a seção "Canva" do README
   (logo original, 4:5, conferir página por página) e usar "origem": "canva".
6. Abra as imagens de slides/ e confira: texto cortado, sobreposto, fora da margem, logo errado. Corrija e gere de novo.
7. Rode `python automacao-instagram/conferir_ciclo.py <ciclo>`; só siga com "OK".
8. Crie a branch `post/<ciclo>`, faça commit de pesquisa.md, post.json, slides/ e previa.jpg e abra um pull request:
   - título: `Post <ciclo>: <pauta>`
   - corpo: a imagem previa.jpg (link raw da branch), a legenda completa, as pendências e as fontes dos fatos,
     e a frase "Aprovar = fazer merge. Pedir mudança = comentar aqui."
9. PARE. Nunca faça merge, nunca rode aprovar.py nem publicar.py. Aprovação é só do usuário.
