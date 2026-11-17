// Componentes que aplicam a marca escolhida. Todos recebem `marca` (id do marcas.json).
// Tempos em segundos, relativos à <Sequence> onde o componente está.
import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fontes, marca as getMarca, maxPalavras, Marca } from "./tema";

export type Palavra = { w: string; a: number; b: number; kw?: boolean };

/** Agrupa palavras em blocos conforme o modo da marca: quebra em pontuação, pausa > 0,5 s ou no máximo de palavras. */
export const blocos = (m: Marca, ps: Palavra[]): Palavra[][] => {
  const max = maxPalavras(m);
  const out: Palavra[][] = [];
  let cur: Palavra[] = [];
  ps.forEach((p, i) => {
    cur.push(p);
    const prox = ps[i + 1];
    const pont = /[.!?…,;:]$/.test(p.w);
    if (!prox || cur.length >= max || (pont && m.codigo.legenda.modo !== "palavra") || prox.a - p.b > 0.5) {
      out.push(cur);
      cur = [];
    }
  });
  return out;
};

/** Texto escuro ou claro conforme o fundo (contraste). */
export const textoSobre = (hex: string): string => {
  const h = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.55 ? "#141414" : "#FFFFFF";
};

const contornoCss =(px: number, cor: string): React.CSSProperties =>
  px > 0 ? { WebkitTextStroke: `${px}px ${cor}`, paintOrder: "stroke fill" } : { textShadow: `0 4px 18px ${cor}AA, 0 2px 4px ${cor}88` };

/** Legenda no estilo da marca (posição, fonte, contorno, destaque e animação de entrada). */
export const LegendaMarca: React.FC<{ marca: string; palavras: Palavra[] }> = ({ marca, palavras }) => {
  const m = getMarca(marca);
  const L = m.codigo.legenda;
  const F = fontes(m);
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const t = frame / fps;
  const bs = blocos(m, palavras);
  const i = bs.findIndex((b, k) => t >= b[0].a && t < (bs[k + 1]?.[0].a ?? b[b.length - 1].b + 0.4));
  if (i < 0) return null;
  const b = bs[i];
  const dt = t - b[0].a;
  const fr = dt * fps;
  let transform = "none";
  let opacity = 1;
  let filter = "none";
  if (L.entrada === "pop") transform = `scale(${interpolate(fr, [0, 4], [0.9, 1], { extrapolateRight: "clamp" })})`;
  if (L.entrada === "elastico") transform = `scale(${interpolate(fr, [0, 3, 5], [0.8, 1.12, 1], { extrapolateRight: "clamp" })})`;
  if (L.entrada === "subir") {
    transform = `translateY(${interpolate(fr, [0, 5], [12, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) })}px)`;
    opacity = interpolate(fr, [0, 4], [0, 1], { extrapolateRight: "clamp" });
  }
  if (L.entrada === "fade") opacity = interpolate(fr, [0, 6], [0, 1], { extrapolateRight: "clamp" });
  if (L.entrada === "desfoque" && L.modo !== "frase") {
    opacity = interpolate(fr, [0, 9], [0, 1], { extrapolateRight: "clamp" });
    filter = `blur(${interpolate(fr, [0, 9], [8, 0], { extrapolateRight: "clamp" })}px)`;
  }
  const grito = L.modo === "palavra" && b.some((p) => p.kw);
  if (grito) transform += ` rotate(${Math.sin(frame * 2.1) * 2}deg)`;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute", left: width * 0.07, right: width * 0.12, top: `${L.y * 100}%`, transform: `translateY(-50%) ${transform}`,
          opacity, filter, textAlign: "center", fontFamily: F.legenda, fontSize: L.tamanho, lineHeight: 1.15, color: L.corTexto,
          textTransform: L.caixaAlta ? "uppercase" : L.minusculas ? "lowercase" : "none", letterSpacing: L.espacamento ?? 0,
          ...contornoCss(L.contorno, L.corContorno),
        }}
      >
        {b.filter((p) => L.modo !== "palavra" || t >= p.a).map((p, k) => {
          // modo frase com desfoque: palavra por palavra
          const pf = (t - p.a) * fps;
          const porPalavra = L.modo === "frase" && L.entrada === "desfoque";
          const st: React.CSSProperties = porPalavra
            ? { opacity: interpolate(pf, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }), filter: `blur(${interpolate(pf, [0, 8], [6, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)` }
            : {};
          if (p.kw) {
            st.color = L.corDestaque;
            if (L.fundoDestaque) Object.assign(st, { background: L.fundoDestaque, padding: "0 0.18em", borderRadius: "0.12em", WebkitTextStroke: "0px" });
            if (L.destaqueItalico) Object.assign(st, { fontFamily: F.titulo, fontStyle: "italic" });
            if (L.sublinhado) {
              const w = interpolate(fr, [3, 12], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
              Object.assign(st, { backgroundImage: `linear-gradient(${L.sublinhado},${L.sublinhado})`, backgroundSize: `${w}% 0.12em`, backgroundPosition: "0 92%", backgroundRepeat: "no-repeat" });
            }
          }
          return (
            <span key={k} style={{ display: "inline-block", marginRight: "0.25em", ...st }}>
              {p.w}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** Enquadramento: zoom lento contínuo + punches da marca. punches: tempos (s) em que o zoom de ênfase entra e sai. */
export const ZoomMarca: React.FC<{ marca: string; children: React.ReactNode; punches?: { t: number; ate: number }[]; lento?: boolean; centro?: [number, number] }> = ({
  marca, children, punches = [], lento = true, centro = [50, 40],
}) => {
  const m = getMarca(marca);
  const Z = m.codigo.zoom;
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  let s = lento ? interpolate(frame, [0, durationInFrames], [1, Z.lento], { extrapolateRight: "clamp" }) : 1;
  for (const p of punches) {
    if (t >= p.t && t < p.ate && Z.punch > 1) {
      const k = Z.duracaoPunch > 0 ? interpolate(t - p.t, [0, Z.duracaoPunch], [0, 1], { extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }) : 1;
      s *= 1 + (Z.punch - 1) * k;
    }
  }
  return <AbsoluteFill style={{ transform: `scale(${s})`, transformOrigin: `${centro[0]}% ${centro[1]}%` }}>{children}</AbsoluteFill>;
};

/** Cartão de título no estilo da marca (entrada com mola). */
export const TituloMarca: React.FC<{ marca: string; texto: string; sub?: string; y?: number }> = ({ marca, texto, sub, y = 0.22 }) => {
  const m = getMarca(marca);
  const F = fontes(m);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const e = spring({ frame, fps, config: { damping: 14, stiffness: 160 } });
  const cor = m.cores[2]?.hex ?? "#fff";
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", top: `${y * 100}%`, left: 80, right: 160, transform: `translateY(${(1 - e) * 40}px)`, opacity: e }}>
        <div style={{ fontFamily: F.titulo, fontStyle: m.codigo.fontes.tituloEstilo, fontSize: 120, lineHeight: 0.95, color: cor, letterSpacing: "-0.02em", ...contornoCss(m.codigo.legenda.contorno ? 6 : 0, m.cores[0].hex) }}>
          {texto}
        </div>
        {sub ? (
          <div style={{ marginTop: 18, display: "inline-block", fontFamily: F.apoio, fontSize: 38, padding: "6px 16px", borderRadius: 10, background: m.cores[1].hex, color: textoSobre(m.cores[1].hex) }}>{sub}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

/** Transição da marca, sobreposta no ponto de corte. Coloque numa <Sequence> de ~12 frames centrada no corte. */
export const TransicaoMarca: React.FC<{ marca: string }> = ({ marca }) => {
  const m = getMarca(marca);
  const frame = useCurrentFrame();
  const { durationInFrames: d, width } = useVideoConfig();
  const p = frame / Math.max(1, d - 1);
  const tri = 1 - Math.abs(p * 2 - 1); // 0 → 1 → 0
  const acc = m.cores[1].hex;
  switch (m.codigo.transicao) {
    case "flash":
      return <AbsoluteFill style={{ background: "#fff", opacity: frame < 2 ? 1 : 0 }} />;
    case "luz":
      return <AbsoluteFill style={{ background: `radial-gradient(60% 50% at ${20 + p * 60}% 40%, ${m.cores[3].hex}, transparent 70%)`, mixBlendMode: "screen", opacity: tri }} />;
    case "dissolve":
      return <AbsoluteFill style={{ background: m.cores[0].hex, opacity: tri }} />;
    case "whip":
      return <AbsoluteFill style={{ backdropFilter: `blur(${tri * 30}px)`, background: `linear-gradient(90deg, transparent, ${acc}55, transparent)`, transform: `translateX(${(p - 0.5) * width}px)` }} />;
    case "slide":
      return <AbsoluteFill style={{ background: m.cores[0].hex, transform: `translateX(${(p < 0.5 ? -1 + p * 2 : (p - 0.5) * 2) * 100}%)` }} />;
    case "mascara":
      return (
        <AbsoluteFill>
          <div style={{ position: "absolute", top: 0, bottom: 0, left: `${p * 100}%`, width: 4, background: m.cores[1].hex, boxShadow: `0 0 30px ${m.cores[1].hex}` }} />
        </AbsoluteFill>
      );
    default:
      return null;
  }
};
