// Páginas do modelo de carrossel (camadas do Canva) animadas sobre a narração. Mesma linguagem do vídeo aprovado
// "lavae-carrossel-cheiro" (25/11/2026): troca de página deslizando como um carrossel, textos entrando no momento
// em que são falados, ilustrações subindo e flutuando, bolhas subindo. Tudo é função do tempo (nada aleatório).
import React from 'react';
import {AbsoluteFill, Audio, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONTE_APOIO, FONTE_TITULO} from './fontes';
import {MEDIDAS} from './layout';
import type {CaixaTexto, LayoutCapa, LayoutDica, Pagina, PaginaCapa, PaginaDica, PaginaFinal, Props} from './tipos';

const W = 1080;
const H = 1920;
const COR = {azul: '#1F4BA5', ceuForte: '#58AEE7', verde: '#8EDC3A', marinho: '#0E2350', branco: '#FFFFFF'};
const saida = Easing.bezier(0.16, 1, 0.3, 1);
const overshoot = Easing.bezier(0.34, 1.56, 0.64, 1);
const entradaSaida = Easing.bezier(0.65, 0, 0.35, 1);
const TROCA = 0.55; // duração do deslize entre páginas (s)
const ANTES = 0.2; // o deslize começa um pouco antes da fala da página nova

const AgoraCtx = React.createContext(0);

function useTempo() {
	const agora = React.useContext(AgoraCtx);
	const {fps} = useVideoConfig();
	const progresso = (t: number, d = 0.5, easing = saida) =>
		interpolate(agora, [t, t + Math.max(d, 1 / fps)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing});
	const mola = (t: number, config = {damping: 14, stiffness: 140, mass: 0.8}) =>
		agora < t ? 0 : spring({frame: (agora - t) * fps, fps, config});
	return {agora, progresso, mola};
}

// ------------------------------------------------------------------ peças
const BOLHAS = [
	{x: 0.07, r: 30, v: 0.05, f: 0.0}, {x: 0.2, r: 14, v: 0.075, f: 0.35}, {x: 0.34, r: 22, v: 0.06, f: 0.7},
	{x: 0.52, r: 12, v: 0.085, f: 0.15}, {x: 0.66, r: 34, v: 0.045, f: 0.55}, {x: 0.8, r: 18, v: 0.07, f: 0.9},
	{x: 0.92, r: 26, v: 0.055, f: 0.45}, {x: 0.44, r: 10, v: 0.095, f: 0.8}, {x: 0.12, r: 16, v: 0.065, f: 0.6},
	{x: 0.74, r: 11, v: 0.09, f: 0.25},
];

/** Bolhas subindo só nas faixas livres (0–1 da largura), para nunca passarem por cima dos textos. */
const Bolhas: React.FC<{faixas: [number, number][]; velocidade?: number}> = ({faixas, velocidade = 1}) => {
	const {agora} = useTempo();
	return (
		<>
			{BOLHAS.map((b, i) => {
				const [lo, hi] = faixas[i % faixas.length];
				const ciclo = (agora * b.v * velocidade + b.f) % 1;
				const y = H * (1.08 - ciclo * 1.25);
				const x = W * (lo + b.x * (hi - lo)) + Math.sin(agora * 0.9 + i) * 10;
				const r = b.r * 1.5;
				const o = Math.min(1, ciclo * 6) * Math.min(1, (1 - ciclo) * 5);
				return (
					<div
						key={i}
						style={{
							position: 'absolute', left: x - r, top: y - r, width: r * 2, height: r * 2, borderRadius: '50%',
							background: 'radial-gradient(circle at 32% 28%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.5) 14%, rgba(140,200,242,0.28) 52%, rgba(88,174,231,0.45) 100%)',
							border: '2px solid rgba(88,174,231,0.55)', opacity: 0.8 * o,
						}}
					/>
				);
			})}
		</>
	);
};

const Camada: React.FC<{arquivo: string; t: number; origem?: string; deslocY?: number; subida?: number; flutua?: number; pop?: boolean}> = ({
	arquivo, t, origem = '50% 50%', deslocY = 0, subida = 160, flutua = 8, pop,
}) => {
	const {progresso, mola, agora} = useTempo();
	const p = pop ? mola(t) : progresso(t, 0.7);
	const boia = Math.sin((agora - t) * 1.6) * flutua * Math.min(1, Math.max(0, agora - t));
	return (
		<Img
			src={staticFile(`camadas/${arquivo}.png`)}
			style={{
				position: 'absolute', left: 0, top: 0, width: W, height: H, opacity: progresso(t, 0.3), transformOrigin: origem,
				transform: `translateY(${deslocY + (pop ? 0 : (1 - p) * subida) + boia}px) scale(${pop ? 0.6 + 0.4 * p : 1})`,
			}}
		/>
	);
};

const Surge: React.FC<{t: number; style?: React.CSSProperties; children: React.ReactNode}> = ({t, style, children}) => {
	const {progresso} = useTempo();
	return <div style={{position: 'absolute', opacity: progresso(t, 0.25), transform: `translateY(${(1 - progresso(t, 0.45)) * 40}px)`, ...style}}>{children}</div>;
};

const Selo: React.FC<{t: number; texto: string; fonte: number; cor?: string; x: number; y: number; centro?: boolean}> = ({t, texto, fonte, cor = COR.verde, x, y, centro}) => {
	const {progresso} = useTempo();
	const p = progresso(t, 0.4, overshoot);
	return (
		<div
			style={{
				position: 'absolute', left: centro ? 0 : x, right: centro ? 0 : undefined, top: y, display: 'flex', justifyContent: centro ? 'center' : 'flex-start',
				opacity: progresso(t, 0.2),
			}}
		>
			<div
				style={{
					background: cor, color: COR.branco, fontFamily: FONTE_APOIO, fontWeight: 800, fontSize: fonte, lineHeight: 1,
					padding: `${fonte * 0.42}px ${fonte * 0.7}px`, borderRadius: 999, whiteSpace: 'nowrap',
					transform: `scale(${0.6 + 0.4 * p})`, transformOrigin: centro ? '50% 50%' : '0% 50%', boxShadow: '0 8px 22px rgba(14,35,80,0.12)',
				}}
			>
				{texto}
			</div>
		</div>
	);
};

const estiloTitulo = (f: number): React.CSSProperties => ({
	fontFamily: FONTE_TITULO, fontWeight: 700, fontSize: f, lineHeight: 1.02, color: COR.marinho, letterSpacing: '-0.5px', whiteSpace: 'nowrap',
});

const Titulo: React.FC<{caixa: CaixaTexto; x: number}> = ({caixa, x}) => (
	<>
		{caixa.linhas.map((l, i) => (
			<Surge key={i} t={l.t} style={{left: x, top: caixa.y + i * caixa.fonte * 1.02}}>
				<div style={{...estiloTitulo(caixa.fonte), color: l.destaque ? COR.azul : COR.marinho}}>{l.texto}</div>
			</Surge>
		))}
	</>
);

const Check: React.FC<{t: number; y: number; fonte: number; linhas: string[]}> = ({t, y, fonte, linhas}) => {
	const {progresso, mola} = useTempo();
	const bola = MEDIDAS.check.tamanho * 1.25;
	const alt = Math.max(bola, linhas.length * fonte * MEDIDAS.check.alturaLinha);
	return (
		<div style={{position: 'absolute', left: MEDIDAS.dica.x, top: y, height: alt, display: 'flex', alignItems: 'center', gap: 22, opacity: progresso(t, 0.25), transform: `translateX(${(1 - progresso(t, 0.45)) * -30}px)`}}>
			<div style={{flex: '0 0 auto', width: bola, height: bola, borderRadius: '50%', background: COR.verde, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${mola(t)})`}}>
				<svg width={bola * 0.56} height={bola * 0.56} viewBox="0 0 24 24">
					<path d="M4 12.5 L10 18 L20 6" fill="none" stroke="#fff" strokeWidth={3.6} strokeLinecap="round" strokeLinejoin="round" />
				</svg>
			</div>
			<div style={{fontFamily: FONTE_APOIO, fontWeight: 800, fontSize: fonte, color: COR.marinho, lineHeight: MEDIDAS.check.alturaLinha, whiteSpace: 'nowrap'}}>
				{linhas.map((l, i) => <div key={i}>{l}</div>)}
			</div>
		</div>
	);
};

// ------------------------------------------------------------------ páginas
const Capa: React.FC<{p: PaginaCapa; L: LayoutCapa}> = ({p, L}) => {
	const M = MEDIDAS.capa;
	return (
		<>
			<Img src={staticFile('camadas/fundo-capa.png')} style={{position: 'absolute', inset: 0, width: W, height: H}} />
			<Camada arquivo="capa-toalhas" t={p.inicio + 0.25} origem="73% 85%" />
			<Bolhas faixas={[[0.8, 0.98]]} />
			<Camada arquivo="capa-logo" t={p.inicio} origem="50% 11%" pop flutua={0} />
			<Selo t={p.inicio + 0.15} texto={p.selo} fonte={L.seloFonte} x={M.x} y={M.seloY} />
			<Titulo caixa={L.titulo} x={M.x} />
			{p.subtitulo && L.subtitulo ? <Selo t={p.subtitulo.t} texto={p.subtitulo.texto} fonte={L.subtitulo.fonte} cor={COR.azul} x={M.x} y={L.subtitulo.y} /> : null}
		</>
	);
};

const Numero: React.FC<{t: number; n: number}> = ({t, n}) => {
	const {mola} = useTempo();
	const s = MEDIDAS.dica.numero;
	return (
		<div
			style={{
				position: 'absolute', left: MEDIDAS.dica.x, top: MEDIDAS.dica.numeroY, width: s, height: s, borderRadius: '50%',
				background: `radial-gradient(circle at 35% 30%, #3E6FD0 0%, ${COR.azul} 60%, #173C88 100%)`,
				boxShadow: '0 14px 34px rgba(31,75,165,0.35), inset 0 0 0 6px rgba(140,200,242,0.55)',
				display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${mola(t + 0.15)})`,
			}}
		>
			<span style={{fontFamily: FONTE_TITULO, fontWeight: 700, fontSize: s * 0.6, color: COR.branco, lineHeight: 1}}>{n}</span>
		</div>
	);
};

const Dica: React.FC<{p: PaginaDica; L: LayoutDica}> = ({p, L}) => {
	const {progresso} = useTempo();
	const M = MEDIDAS.dica;
	const tTraco = Math.max(...L.titulo.linhas.map((l) => l.t)) + 0.2;
	return (
		<>
			<Img src={staticFile('camadas/fundo-dica.png')} style={{position: 'absolute', inset: 0, width: W, height: H}} />
			<Camada arquivo="dica-maquina" t={p.inicio + 0.2} origem="78% 70%" />
			<Bolhas faixas={[[0.72, 0.97]]} />
			<Numero t={p.inicio} n={p.n} />
			{p.selo_topo && L.seloTopo ? <Selo t={p.selo_topo.t} texto={p.selo_topo.texto} fonte={L.seloTopo.fonte} x={M.x} y={L.seloTopo.y} /> : null}
			<Titulo caixa={L.titulo} x={M.x} />
			<div style={{position: 'absolute', left: M.x, top: L.tracoY, width: 130 * progresso(tTraco, 0.45), height: 16, borderRadius: 8, background: COR.verde}} />
			{L.blocos.map((b, i) =>
				b.tipo === 'apoio' ? (
					<Surge key={i} t={b.t} style={{left: M.x, top: b.y}}>
						<div style={{fontFamily: FONTE_APOIO, fontWeight: 700, fontSize: b.fonte, lineHeight: MEDIDAS.apoio.alturaLinha, color: COR.marinho, whiteSpace: 'nowrap'}}>
							{b.linhas.map((l, j) => <div key={j}>{l}</div>)}
						</div>
					</Surge>
				) : b.tipo === 'selo' ? (
					<Selo key={i} t={b.t} texto={b.texto} fonte={b.fonte} cor={b.destaque ? COR.azul : COR.verde} x={M.x} y={b.y} />
				) : (
					<Check key={i} t={b.t} y={b.y} fonte={b.fonte} linhas={b.linhas} />
				),
			)}
		</>
	);
};

const SOBE = -200; // ilustrações + faixa mais altas que no post (fora da área dos botões do Instagram)

const Ondas: React.FC<{t: number}> = ({t}) => {
	const {agora, progresso} = useTempo();
	const p = progresso(t, 0.8);
	const onda = (base: number, amp: number, fase: number) => {
		let d = `M0 260 L0 ${base}`;
		for (let x = 0; x <= 1080; x += 30) d += ` L${x} ${(base + Math.sin(x / 170 + agora * 0.8 + fase) * amp).toFixed(1)}`;
		return `${d} L1080 260 Z`;
	};
	return (
		<svg width={1080} height={260} viewBox="0 0 1080 260" style={{position: 'absolute', left: 0, top: 1660, transform: `translateY(${(1 - p) * 260}px)`}}>
			<path d={onda(70, 26, 0)} fill="#9CC8F0" />
			<path d={onda(140, 20, 2.2)} fill="#2A5CAE" />
		</svg>
	);
};

const Final: React.FC<{p: PaginaFinal}> = ({p}) => {
	const {progresso} = useTempo();
	const T = p.t;
	const f = progresso(T.facil, 0.5, overshoot);
	const pe = progresso(T.faixa, 0.7);
	const end: React.CSSProperties = {fontFamily: FONTE_APOIO, fontWeight: 800, fontSize: 33, color: '#F0F4F8', lineHeight: 1.25, textAlign: 'center', whiteSpace: 'nowrap'};
	return (
		<>
			<Img src={staticFile('camadas/fundo-final.png')} style={{position: 'absolute', inset: 0, width: W, height: H}} />
			<Bolhas faixas={[[0.0, 0.07], [0.91, 0.99]]} />
			<Ondas t={p.inicio + 0.1} />
			<Camada arquivo="final-cena" t={T.cena} deslocY={SOBE} origem="50% 75%" flutua={5} />
			<Camada arquivo="final-faixa" t={T.faixa} deslocY={SOBE} subida={220} flutua={0} />
			<div style={{position: 'absolute', left: 40, width: 999, top: 1648 + SOBE, height: 127, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: progresso(T.faixa, 0.3), transform: `translateY(${(1 - pe) * 220}px)`}}>
				<div style={end}>📍 Edifício Dom Center · Rua do Aririzal /</div>
				<div style={end}>Av. São Luís Rei de França</div>
			</div>
			<Camada arquivo="final-logo" t={T.logo} origem="50% 16%" pop flutua={0} />
			<Surge t={T.lavar} style={{left: 0, right: 0, top: 560, textAlign: 'center'}}>
				<div style={{fontFamily: FONTE_TITULO, fontWeight: 700, fontSize: 132, color: '#053270', lineHeight: 1}}>lavar ficou</div>
			</Surge>
			<div style={{position: 'absolute', left: 0, right: 0, top: 692, textAlign: 'center', opacity: progresso(T.facil, 0.2), transform: `scale(${0.5 + 0.5 * f})`, fontFamily: FONTE_TITULO, fontWeight: 700, fontSize: 216, color: COR.ceuForte, lineHeight: 1.05}}>
				fácil!
			</div>
			<Selo t={T.horario} texto="todos os dias · 6h30 à meia-noite" fonte={42} x={0} y={1000} centro />
		</>
	);
};

// ------------------------------------------------------------------ montagem
const PaginaComTroca: React.FC<{p: Pagina; i: number; total: number; L: Props['layout']}> = ({p, i, total, L}) => {
	const {agora} = useTempo();
	const entra = i === 0 ? 1 : interpolate(agora, [p.inicio - ANTES, p.inicio - ANTES + TROCA], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: entradaSaida});
	const sai = i === total - 1 ? 0 : interpolate(agora, [p.fim - ANTES, p.fim - ANTES + TROCA], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: entradaSaida});
	if (agora < p.inicio - ANTES || (i < total - 1 && agora > p.fim - ANTES + TROCA)) return null;
	const x = (1 - entra) * W - sai * W;
	const lay = L?.[i];
	return (
		<AbsoluteFill style={{transform: `translateX(${x}px)`, overflow: 'hidden', zIndex: i}}>
			{p.tipo === 'capa' ? <Capa p={p} L={lay as LayoutCapa} /> : p.tipo === 'dica' ? <Dica p={p} L={lay as LayoutDica} /> : <Final p={p} />}
		</AbsoluteFill>
	);
};

export const Video: React.FC<Props> = (props) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const agora = frame / fps;
	if (props.erros?.length) {
		// nunca deve ir ao ar: o gerar_video.py para antes do render se houver erro de layout
		return (
			<AbsoluteFill style={{background: '#300', color: '#fff', fontSize: 40, padding: 60, fontFamily: 'sans-serif'}}>
				{props.erros.map((e, i) => <div key={i}>{e}</div>)}
			</AbsoluteFill>
		);
	}
	return (
		<AgoraCtx.Provider value={agora}>
			<AbsoluteFill style={{background: '#EFF5FC'}}>
				{props.paginas.map((p, i) => (
					<PaginaComTroca key={i} p={p} i={i} total={props.paginas.length} L={props.layout} />
				))}
				{props.audio ? <Audio src={staticFile(props.audio)} /> : null}
			</AbsoluteFill>
		</AgoraCtx.Provider>
	);
};
