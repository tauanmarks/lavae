// Mede cada texto com a fonte de verdade (no navegador do render) e calcula onde cada coisa fica.
// Qualquer texto que não caiba no espaço da arte vira um ERRO: o gerar_video.py então não publica o vídeo
// (sai o carrossel de reserva). Nada é cortado, encolhido demais ou empurrado para cima da ilustração.
import {measureText} from '@remotion/layout-utils';
import {FAMILIA_APOIO, FAMILIA_TITULO} from './fontes';
import type {Bloco, BlocoPosto, Entrada, Linha, LayoutCapa, LayoutDica, PaginaCapa, PaginaDica, Trecho} from './tipos';

export const MEDIDAS = {
	capa: {x: 82, seloY: 500, tituloY: 620, tituloLarg: 700, tituloFonte: [128, 96], tituloLinhas: 3, subLarg: 700, limiteY: 1380},
	dica: {x: 64, numeroY: 300, numero: 210, colunaY: 580, tituloLarg: 660, tituloFonte: [104, 80], tituloLinhas: 3, colunaLarg: 450, limiteY: 1500},
	gap: 40,
	apoio: {fonte: 52, min: 44, alturaLinha: 1.3, maxLinhas: 5},
	selo: {fonte: 46, min: 36},
	check: {tamanho: 52, alturaLinha: 1.15, maxLinhas: 2},
};

const largura = (texto: string, fonte: number, familia: string, peso: string, espaco = '0px') =>
	measureText({text: texto, fontFamily: familia, fontSize: fonte, fontWeight: peso, letterSpacing: espaco, validateFontIsLoaded: true}).width;

const larguraTitulo = (t: string, f: number) => largura(t, f, FAMILIA_TITULO, '700', '-0.5px');

/** Quebra em linhas que caibam em maxL. Devolve null se alguma palavra sozinha já não cabe. */
function quebrar(texto: string, maxL: number, medir: (s: string) => number): string[] | null {
	const palavras = texto.trim().split(/\s+/);
	const linhas: string[] = [];
	let atual = '';
	for (const p of palavras) {
		if (medir(p) > maxL) return null;
		const teste = atual ? `${atual} ${p}` : p;
		if (medir(teste) <= maxL) atual = teste;
		else {
			linhas.push(atual);
			atual = p;
		}
	}
	if (atual) linhas.push(atual);
	return linhas;
}

function titulo(trechos: Trecho[], maxL: number, [f0, fmin]: number[], maxLinhas: number, onde: string, erros: string[]) {
	for (let f = f0; f >= fmin; f -= 4) {
		const linhas: Linha[] = [];
		let ok = true;
		for (const tr of trechos) {
			const q = quebrar(tr.texto, maxL, (s) => larguraTitulo(s, f));
			if (!q) {
				ok = false;
				break;
			}
			q.forEach((texto, i) => linhas.push({texto, destaque: !!tr.destaque, t: tr.t + i * 0.15}));
		}
		if (ok && linhas.length <= maxLinhas) return {fonte: f, linhas};
	}
	erros.push(`${onde}: título não cabe em ${maxLinhas} linhas nem com fonte ${fmin}px`);
	return {fonte: fmin, linhas: trechos.map((tr) => ({texto: tr.texto, destaque: !!tr.destaque, t: tr.t}))};
}

/** Fonte de um selo (pílula) de uma linha só que caiba em maxL (texto + respiro lateral 0,7 × fonte de cada lado). */
function fonteSelo(texto: string, maxL: number, f0: number, fmin: number, onde: string, erros: string[]) {
	for (let f = f0; f >= fmin; f -= 2) {
		if (largura(texto, f, FAMILIA_APOIO, '800') + 1.4 * f <= maxL) return f;
	}
	erros.push(`${onde}: selo "${texto}" não cabe em ${maxL}px`);
	return fmin;
}

const alturaSelo = (f: number) => f * 1.84;

export function layoutCapa(p: PaginaCapa, onde: string, erros: string[]): LayoutCapa {
	const M = MEDIDAS.capa;
	const seloFonte = fonteSelo(p.selo, 600, 40, 32, `${onde} (selo)`, erros);
	const tit = titulo(p.titulo, M.tituloLarg, M.tituloFonte, M.tituloLinhas, onde, erros);
	let y = M.tituloY + tit.linhas.length * tit.fonte * 1.02;
	let subtitulo: LayoutCapa['subtitulo'];
	if (p.subtitulo) {
		y += MEDIDAS.gap;
		const f = fonteSelo(p.subtitulo.texto, M.subLarg, 44, 34, `${onde} (subtítulo)`, erros);
		subtitulo = {y, fonte: f};
		y += alturaSelo(f);
	}
	if (y > M.limiteY) erros.push(`${onde}: textos descem até y=${Math.round(y)} (limite ${M.limiteY}, senão encostam nas toalhas)`);
	return {seloFonte, titulo: {y: M.tituloY, ...tit}, subtitulo};
}

export function layoutDica(p: PaginaDica, onde: string, erros: string[]): LayoutDica {
	const M = MEDIDAS.dica;
	let y = M.colunaY;
	let seloTopo: LayoutDica['seloTopo'];
	if (p.selo_topo) {
		const f = fonteSelo(p.selo_topo.texto, M.colunaLarg, MEDIDAS.selo.fonte, MEDIDAS.selo.min, `${onde} (selo do topo)`, erros);
		seloTopo = {y, fonte: f};
		y += alturaSelo(f) + MEDIDAS.gap;
	}
	const tit = titulo(p.titulo, M.tituloLarg, M.tituloFonte, M.tituloLinhas, onde, erros);
	const tituloY = y;
	y += tit.linhas.length * tit.fonte * 1.02 + MEDIDAS.gap;
	const tracoY = y;
	y += 16;
	const blocos: BlocoPosto[] = [];
	let anterior: Bloco['tipo'] | 'traco' = 'traco';
	p.blocos.forEach((b, i) => {
		const ondeB = `${onde}, bloco ${i + 1} (${b.tipo})`;
		y += anterior === b.tipo && b.tipo === 'selo' ? 18 : anterior === b.tipo && b.tipo === 'check' ? 30 : MEDIDAS.gap;
		if (b.tipo === 'apoio') {
			const A = MEDIDAS.apoio;
			let feito = false;
			for (let f = A.fonte; f >= A.min; f -= 2) {
				const q = quebrar(b.texto, M.colunaLarg, (s) => largura(s, f, FAMILIA_APOIO, '700'));
				if (q && q.length <= A.maxLinhas) {
					blocos.push({tipo: 'apoio', y, fonte: f, linhas: q, t: b.t});
					y += q.length * f * A.alturaLinha;
					feito = true;
					break;
				}
			}
			if (!feito) erros.push(`${ondeB}: texto de apoio passa de ${A.maxLinhas} linhas`);
		} else if (b.tipo === 'selo') {
			const f = fonteSelo(b.texto, M.colunaLarg, MEDIDAS.selo.fonte, MEDIDAS.selo.min, ondeB, erros);
			blocos.push({tipo: 'selo', y, fonte: f, texto: b.texto, destaque: !!b.destaque, t: b.t});
			y += alturaSelo(f);
		} else {
			const C = MEDIDAS.check;
			const bola = C.tamanho * 1.25;
			const f = C.tamanho * 0.92;
			const q = quebrar(b.texto, M.colunaLarg - bola - 22, (s) => largura(s, f, FAMILIA_APOIO, '800'));
			if (!q || q.length > C.maxLinhas) erros.push(`${ondeB}: item "${b.texto}" passa de ${C.maxLinhas} linhas`);
			const linhas = q ?? [b.texto];
			blocos.push({tipo: 'check', y, fonte: f, linhas, t: b.t});
			y += Math.max(bola, linhas.length * f * C.alturaLinha);
		}
		anterior = b.tipo;
	});
	if (y > M.limiteY) erros.push(`${onde}: coluna de texto desce até y=${Math.round(y)} (limite ${M.limiteY}: área dos botões do Instagram)`);
	return {seloTopo, titulo: {y: tituloY, ...tit}, tracoY, blocos, base: y};
}

export function calcularLayout(e: Entrada) {
	const erros: string[] = [];
	const layout = e.paginas.map((p, i) => {
		const onde = `página ${i + 1} (${p.tipo})`;
		if (p.tipo === 'capa') return layoutCapa(p, onde, erros);
		if (p.tipo === 'dica') return layoutDica(p, onde, erros);
		return null;
	});
	// tempos: tudo dentro da duração e páginas em ordem, sem buraco
	e.paginas.forEach((p, i) => {
		if (p.fim - p.inicio < 2.5) erros.push(`página ${i + 1}: dura só ${(p.fim - p.inicio).toFixed(2)} s`);
		if (i > 0 && Math.abs(p.inicio - e.paginas[i - 1].fim) > 0.001) erros.push(`página ${i + 1}: não começa onde a anterior termina`);
	});
	if (e.paginas[0]?.tipo !== 'capa') erros.push('a primeira página precisa ser a capa');
	if (e.paginas[e.paginas.length - 1]?.tipo !== 'final') erros.push('a última página precisa ser a final');
	return {layout, erros};
}
