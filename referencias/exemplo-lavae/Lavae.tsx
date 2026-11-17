// Lavaê — passo a passo do autoatendimento (marca Espuma), narrado por voz neural (Francisca).
// Plano aprovado em 16/11/2026: videos-brutos/lavae/plano.json → dados.json (preparar_render.py).
import React from "react";
import { AbsoluteFill, Audio, Easing, Freeze, Img, interpolate, OffthreadVideo, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import dados from "./dados.json";
import { LegendaMarca, Palavra } from "../marcas/componentes";
import { fontes, marca } from "../marcas/tema";

const M = marca("espuma");
const F = fontes(M);
const AZUL = "#1F4BA5", CEU = "#8CC8F2", VERDE = "#8EDC3A", NEVOA = "#EAF4FC", MARINHO = "#0E2350";

type Plano = { i: number; tag: string; tipo: string; t: number; d: number; texto_cartao: string; congelar: boolean; src?: string; a?: number; b?: number; vel?: number };
const PLANOS = dados.planos as Plano[];
const NARR = dados.narracoes as { src: string; t: number; d: number; id: string }[];
const LEGENDA = dados.legenda as Palavra[];
export const FPS_LV = 30;
const f = (s: number) => Math.round(s * FPS_LV);
export const DUR_LV = f(dados.duracao);
const P = (i: number) => PLANOS[i];

// ------------------------------------------------------------------ passos (selo + barra)
const PASSOS: { plano: number; n: number; texto: string }[] = [
  { plano: 1, n: 1, texto: "Acesse com seu CPF" },
  { plano: 2, n: 2, texto: "Escolha o serviço" },
  { plano: 3, n: 3, texto: "Escolha a máquina" },
  { plano: 4, n: 4, texto: "Pagamento" },
  { plano: 6, n: 5, texto: "Coloque as roupas" },
  { plano: 8, n: 6, texto: "Escolha o ciclo" },
  { plano: 10, n: 7, texto: "Limpe o filtro" },
  { plano: 13, n: 8, texto: "Para secar" },
  { plano: 15, n: 9, texto: "Seque" },
];
const ESPERA = 12, FINAL_CARD = 18;

const Bolhas: React.FC<{ qtd?: number; dur?: number; seed?: number; cor?: string }> = ({ qtd = 14, dur = 30, seed = 1, cor = CEU }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: qtd }).map((_, k) => {
        const r = Math.sin(seed * 97 + k * 13.7) * 0.5 + 0.5;
        const r2 = Math.sin(seed * 31 + k * 7.3) * 0.5 + 0.5;
        const atraso = r2 * dur * 0.5;
        const p = (frame - atraso) / dur;
        if (p < 0 || p > 1) return null;
        const tam = 18 + r * 46;
        return (
          <div key={k} style={{ position: "absolute", left: `${8 + r * 84}%`, top: `${100 - p * 75}%`, width: tam, height: tam, borderRadius: "50%",
            border: `3px solid ${cor}`, background: `radial-gradient(circle at 30% 30%, #ffffffcc, ${cor}33 60%, transparent 70%)`,
            opacity: interpolate(p, [0, 0.15, 0.8, 1], [0, 0.9, 0.7, 0]), transform: `translateX(${Math.sin(p * 6 + k) * 18}px)` }} />
        );
      })}
    </AbsoluteFill>
  );
};

const Selo: React.FC<{ n: number; texto: string }> = ({ n, texto }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const e = spring({ frame, fps, config: { damping: 14, stiffness: 170 } });
  return (
    <div style={{ position: "absolute", left: 56, top: 300, display: "flex", alignItems: "center", gap: 18, transform: `translateX(${(1 - e) * -60}px)`, opacity: e }}>
      <div style={{ width: 96, height: 96, borderRadius: 48, background: AZUL, color: "#fff", display: "grid", placeItems: "center", fontFamily: F.titulo, fontSize: 58, boxShadow: "0 10px 30px #0E235066", border: "5px solid #fff" }}>{n}</div>
      <div style={{ background: "#ffffffEE", color: MARINHO, fontFamily: F.titulo, fontSize: 46, padding: "10px 24px", borderRadius: 999, boxShadow: "0 10px 30px #0E235044" }}>{texto}</div>
    </div>
  );
};

const Barra: React.FC<{ atual: number; tudo?: boolean }> = ({ atual, tudo }) => (
  <div style={{ position: "absolute", left: 60, right: 200, top: 236, display: "flex", gap: 10 }}>
    {PASSOS.map((p) => (
      <div key={p.n} style={{ flex: 1, height: 12, borderRadius: 6, background: tudo || p.n < atual ? VERDE : p.n === atual ? "#fff" : "#ffffff55", boxShadow: "0 2px 8px #0E235055" }} />
    ))}
  </div>
);

const Check: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const e = spring({ frame, fps, config: { damping: 11, stiffness: 160 } });
  const traco = interpolate(frame, [4, 14], [60, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ alignItems: "center", top: 520 }}>
      <svg width={260} height={260} viewBox="0 0 100 100" style={{ transform: `scale(${e})`, filter: "drop-shadow(0 12px 24px #0E235066)" }}>
        <circle cx={50} cy={50} r={46} fill={VERDE} stroke="#fff" strokeWidth={5} />
        <path d="M28 52 L44 67 L73 36" fill="none" stroke="#fff" strokeWidth={10} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={60} strokeDashoffset={traco} />
      </svg>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ desfoque do nome (tela de boas-vindas do 9300)
const NOME: { t: number; x: number; y: number; w: number; h: number }[] = [
  { t: 0.25, x: 290, y: 698, w: 280, h: 112 },
  { t: 1.0, x: 330, y: 662, w: 280, h: 118 },
  { t: 1.8, x: 318, y: 642, w: 300, h: 128 },
  { t: 2.45, x: 318, y: 642, w: 300, h: 128 },
];
const BlurNome: React.FC<{ a: number; vel: number; congelar: boolean }> = ({ a, vel, congelar }) => {
  const frame = useCurrentFrame();
  const t = congelar ? a : a + (frame / FPS_LV) * vel;
  if (t > 2.45) return null;
  const k = (campo: "x" | "y" | "w" | "h") => interpolate(t, NOME.map((n) => n.t), NOME.map((n) => n[campo]), { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", left: k("x"), top: k("y"), width: k("w"), height: k("h"), transform: "rotate(-12deg)", transformOrigin: "left center",
      backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", background: "#ffffff40", borderRadius: 14 }} />
  );
};

// ------------------------------------------------------------------ enquadramento por plano
type Z = { lento?: number; punch?: number; de?: number; suave?: number; origem?: string };
const ZOOM: Record<number, Z> = {
  0: { lento: 1.06 },
  1: { lento: 1.18, origem: "44% 42%" },
  2: { lento: 1.1, origem: "50% 58%" },
  3: { punch: 1.3, de: 0, suave: 0.6, origem: "48% 50%" },
  4: { punch: 1.25, de: 0, suave: 0.6, origem: "45% 55%" },
  5: { lento: 1.06, origem: "50% 50%" },
  7: { lento: 1.04 },
  9: { punch: 1.35, de: 0.2, suave: 0.6, origem: "36% 52%" },
  13: { punch: 1.6, de: 0.1, suave: 1.0, origem: "58% 55%" },
  17: { lento: 1.06 },
};
const Enquadramento: React.FC<{ z?: Z; children: React.ReactNode }> = ({ z, children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  let s = interpolate(frame, [0, durationInFrames], [1, z?.lento ?? 1]);
  if (z?.punch) {
    const k = interpolate(frame / FPS_LV - (z.de ?? 0), [0, z.suave ?? 0.01], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
    s *= 1 + (z.punch - 1) * k;
  }
  return <AbsoluteFill style={{ transform: `scale(${s})`, transformOrigin: z?.origem ?? "50% 50%" }}>{children}</AbsoluteFill>;
};

const Video: React.FC<{ p: Plano }> = ({ p }) =>
  p.congelar ? (
    <Freeze frame={0}>
      <OffthreadVideo src={staticFile(p.src!)} trimBefore={f(p.a!)} muted style={{ width: 1080, height: 1920 }} />
    </Freeze>
  ) : (
    <OffthreadVideo src={staticFile(p.src!)} trimBefore={f(p.a!)} trimAfter={f(p.b!) + 2} playbackRate={p.vel ?? 1} muted style={{ width: 1080, height: 1920 }} />
  );

// ------------------------------------------------------------------ cartões
const CartaoEspera: React.FC = () => {
  const frame = useCurrentFrame();
  const ang = frame * 6;
  const e = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: `linear-gradient(170deg, ${AZUL}, ${CEU})`, justifyContent: "center", alignItems: "center" }}>
      <Bolhas qtd={22} dur={60} seed={4} cor="#ffffff" />
      <svg width={200} height={200} viewBox="0 0 100 100" style={{ opacity: e, marginBottom: 40 }}>
        <circle cx={50} cy={50} r={44} fill="none" stroke="#fff" strokeWidth={6} />
        <line x1={50} y1={50} x2={50} y2={18} stroke="#fff" strokeWidth={6} strokeLinecap="round" transform={`rotate(${ang} 50 50)`} />
        <line x1={50} y1={50} x2={72} y2={50} stroke={VERDE} strokeWidth={6} strokeLinecap="round" transform={`rotate(${ang / 12} 50 50)`} />
      </svg>
      <div style={{ fontFamily: F.titulo, fontSize: 104, color: "#fff", textAlign: "center", lineHeight: 1.05, opacity: e, transform: `translateY(${(1 - e) * 30}px)` }}>
        enquanto lava…<br /><span style={{ color: VERDE }}>relaxa ☕</span>
      </div>
    </AbsoluteFill>
  );
};

const CartaoFinal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const e = spring({ frame, fps, config: { damping: 13, stiffness: 140 } });
  const e2 = spring({ frame: frame - 10, fps, config: { damping: 13, stiffness: 140 } });
  return (
    <AbsoluteFill style={{ background: `radial-gradient(120% 80% at 50% 30%, #ffffff, ${NEVOA})`, justifyContent: "center", alignItems: "center" }}>
      <Bolhas qtd={20} dur={70} seed={9} />
      <Img src={staticFile("lavae/logo-lavae.png")} style={{ width: 900, transform: `scale(${0.85 + 0.15 * e})`, opacity: e }} />
      <div style={{ marginTop: 50, background: VERDE, color: MARINHO, fontFamily: F.titulo, fontSize: 62, padding: "14px 44px", borderRadius: 999, opacity: e2, transform: `translateY(${(1 - e2) * 30}px)`, boxShadow: "0 12px 30px #0E235033" }}>
        lavar ficou fácil!
      </div>
    </AbsoluteFill>
  );
};

const TituloAbertura: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const e = spring({ frame: frame - 6, fps, config: { damping: 14, stiffness: 150 } });
  const e2 = spring({ frame: frame - 18, fps, config: { damping: 14, stiffness: 150 } });
  return (
    <>
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${MARINHO}CC 0%, ${MARINHO}66 32%, transparent 52%)`, opacity: e }} />
    <div style={{ position: "absolute", left: 60, right: 180, top: 300 }}>
      <div style={{ fontFamily: F.titulo, fontSize: 112, lineHeight: 0.98, color: "#fff", textShadow: `0 6px 24px ${MARINHO}`, opacity: e, transform: `translateY(${(1 - e) * 40}px)` }}>
        lavar e secar<br />na <span style={{ color: CEU }}>lavaê</span>
      </div>
      <div style={{ marginTop: 22, display: "inline-block", background: VERDE, color: MARINHO, fontFamily: F.titulo, fontSize: 48, padding: "8px 28px", borderRadius: 999, opacity: e2, transform: `scale(${0.8 + 0.2 * e2})` }}>
        em poucos passos
      </div>
    </div>
    </>
  );
};

const Extras: React.FC<{ i: number }> = ({ i }) => {
  switch (i) {
    case 0: return <TituloAbertura />;
    case 5: return <Sequence from={f(4.3)}><Check /></Sequence>;
    case 9: return <div style={{ position: "absolute", left: 60, top: 1080, background: "#ffffffEE", color: MARINHO, fontFamily: F.apoio, fontSize: 36, padding: "8px 20px", borderRadius: 16 }}>NORMAL · DELICADAS → INICIAR</div>;
    case 12: return <CartaoEspera />;
    case 16: return <div style={{ position: "absolute", left: 60, top: 1080, background: "#ffffffEE", color: MARINHO, fontFamily: F.apoio, fontSize: 34, padding: "8px 20px", borderRadius: 16 }}>temperatura: alta · média · baixa</div>;
    case 18: return <CartaoFinal />;
    default: return null;
  }
};

// ------------------------------------------------------------------ som
const em = (i: number, rel: number) => P(i).t + rel;
const SFX: { t: number; nome: string; vol?: number }[] = [
  ...PASSOS.map((p) => ({ t: P(p.plano).t + 0.05, nome: "bolha", vol: 0.45 })),
  { t: em(0, 0.2), nome: "bolha", vol: 0.4 },
  { t: em(2, 2.75), nome: "clique_suave" },
  { t: em(3, 1.15), nome: "clique_suave" },
  { t: em(3, 4.3), nome: "clique_suave" },
  { t: em(4, 3.42), nome: "clique_suave" },
  { t: em(5, 4.3), nome: "ding_suave", vol: 0.55 },
  { t: em(6, 0.0), nome: "swoosh_macio", vol: 0.4 },
  { t: em(8, 2.65), nome: "clique_suave" },
  { t: em(9, 1.2), nome: "clique_suave" },
  { t: em(9, 3.2), nome: "clique_suave" },
  { t: em(10, 0.0), nome: "swoosh_macio", vol: 0.4 },
  { t: em(18, 0.1), nome: "ding_suave", vol: 0.5 },
];
const falando = (t: number) => NARR.some((n) => t >= n.t - 0.25 && t <= n.t + n.d + 0.25);
const volMusica = (frame: number) => {
  let s = 0;
  for (let k = -6; k <= 6; k++) s += falando((frame + k) / FPS_LV) ? 0.1 : 0.24;
  const base = s / 13;
  const fadeIn = interpolate(frame, [0, f(1)], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [DUR_LV - f(2), DUR_LV], [1, 0], { extrapolateLeft: "clamp" });
  return base * fadeIn * fadeOut;
};

// ------------------------------------------------------------------ composição
export const Lavae: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS_LV;
  const passoAtual = [...PASSOS].reverse().find((p) => t >= P(p.plano).t);
  const mostraBarra = t >= P(1).t - 0.3 && t < P(FINAL_CARD).t && !(t >= P(ESPERA).t && t < P(ESPERA).t + P(ESPERA).d);
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {PLANOS.map((p, k) => {
        const de = f(p.t);
        const dur = Math.max(1, f(p.t + p.d) - de);
        return (
          <Sequence key={k} from={de} durationInFrames={dur} name={`${p.i + 1} ${p.tag || p.tipo}`}>
            {p.src ? (
              <Enquadramento z={ZOOM[p.i]}>
                <Video p={p} />
                {p.src.endsWith("IMG_9300.mp4") && p.a! < 2.45 ? <BlurNome a={p.a!} vel={p.vel ?? 1} congelar={p.congelar} /> : null}
              </Enquadramento>
            ) : null}
            <Extras i={p.i} />
          </Sequence>
        );
      })}
      {mostraBarra ? <Barra atual={passoAtual?.n ?? 0} tudo={t >= P(17).t} /> : null}
      {PASSOS.map((p, k) => {
        const de = f(P(p.plano).t);
        const ate = k + 1 < PASSOS.length ? f(P(PASSOS[k + 1].plano).t) : f(P(17).t);
        const fimEspera = p.n === 7 ? f(P(ESPERA).t) : ate;
        return (
          <Sequence key={`selo${k}`} from={de} durationInFrames={Math.max(1, Math.min(ate, fimEspera) - de)}>
            <Selo n={p.n} texto={p.texto} />
            <Sequence durationInFrames={f(1.2)}><Bolhas qtd={10} dur={36} seed={k + 2} /></Sequence>
          </Sequence>
        );
      })}
      <LegendaMarca marca="espuma" palavras={LEGENDA} />
      {dados.narracao_unica ? (
        <Audio src={staticFile(dados.narracao_unica)} volume={1} />
      ) : (
        NARR.map((n, k) => (
          <Sequence key={`n${k}`} from={f(n.t)} durationInFrames={f(n.d) + 6}>
            <Audio src={staticFile(n.src)} volume={1} />
          </Sequence>
        ))
      )}
      <Audio src={staticFile("sons/espuma/trilha.wav")} volume={volMusica} />
      {SFX.map((s, k) => (
        <Sequence key={`sfx${k}`} from={f(s.t)} durationInFrames={f(2)}>
          <Audio src={staticFile(`sons/espuma/${s.nome}.wav`)} volume={s.vol ?? 0.5} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
