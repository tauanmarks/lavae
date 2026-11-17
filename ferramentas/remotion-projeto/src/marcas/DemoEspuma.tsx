// Demonstração da marca Espuma (sem vídeo): abertura, passos com selo/barra/legenda, check, espera e encerramento.
import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame } from "remotion";
import { LegendaMarca, Palavra, TransicaoMarca, ZoomMarca } from "./componentes";
import { AZUL, Barra, Bolhas, CartaoEspera, CartaoFinal, Check, CEU, Etiqueta, Selo, TituloAbertura, volumeTrilha } from "./espuma";

const FPS = 30;
const f = (s: number) => Math.round(s * FPS);
export const DEMO_ESPUMA_DUR = f(16);

const PASSOS = ["Acesse com seu CPF", "Escolha a máquina", "Pagamento"];
const LEGENDA: Palavra[] = [
  { w: "digite", a: 3.2, b: 3.5, kw: true }, { w: "seu", a: 3.5, b: 3.7 }, { w: "CPF", a: 3.7, b: 4.2 }, { w: "no", a: 4.2, b: 4.35 }, { w: "totem", a: 4.35, b: 4.9 },
  { w: "escolha", a: 6.2, b: 6.6, kw: true }, { w: "a", a: 6.6, b: 6.7 }, { w: "máquina", a: 6.7, b: 7.3 }, { w: "livre", a: 7.3, b: 7.8 },
  { w: "e", a: 9.2, b: 9.3 }, { w: "pague", a: 9.3, b: 9.7, kw: true }, { w: "no", a: 9.7, b: 9.85 }, { w: "Pix", a: 9.85, b: 10.4, kw: true },
];
const FALAS: [number, number][] = [[3.2, 4.9], [6.2, 7.8], [9.2, 10.4]];

const Fundo: React.FC = () => (
  <ZoomMarca marca="espuma">
    <AbsoluteFill style={{ background: `radial-gradient(120% 80% at 30% 20%, ${CEU}, ${AZUL})` }} />
  </ZoomMarca>
);

export const DemoEspuma: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const passo = t < 3 ? 0 : t < 6 ? 1 : t < 9 ? 2 : 3;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Fundo />
      <Sequence durationInFrames={f(3)}><TituloAbertura linha1="lavar e secar" linha2="na" destaque="lavaê" pilula="em poucos passos" /></Sequence>
      {t >= 2.7 && t < 12 ? <Barra total={PASSOS.length} atual={passo} tudo={t >= 11} /> : null}
      {PASSOS.map((p, k) => (
        <Sequence key={p} from={f(3 + k * 3)} durationInFrames={f(3)}>
          <Selo n={k + 1} texto={p} />
          <Sequence durationInFrames={f(1.2)}><Bolhas qtd={10} dur={36} seed={k + 2} /></Sequence>
        </Sequence>
      ))}
      <Sequence from={f(7)} durationInFrames={f(2)}><Etiqueta texto="NORMAL · DELICADAS → INICIAR" /></Sequence>
      <Sequence from={f(10.5)} durationInFrames={f(1.5)}><Check /></Sequence>
      <LegendaMarca marca="espuma" palavras={LEGENDA} />
      <Sequence from={f(12)} durationInFrames={f(2)}><CartaoEspera /></Sequence>
      <Sequence from={f(14)}><CartaoFinal /></Sequence>
      {[3, 6, 9, 12, 14].map((s) => (
        <Sequence key={`tr${s}`} from={f(s) - 5} durationInFrames={10}><TransicaoMarca marca="espuma" /></Sequence>
      ))}
      <Audio src={staticFile("sons/espuma/trilha.wav")} volume={(fr) => volumeTrilha(fr, FPS, DEMO_ESPUMA_DUR, (x) => FALAS.some(([a, b]) => x >= a - 0.25 && x <= b + 0.25))} />
      {[3, 6, 9].map((s) => (
        <Sequence key={`b${s}`} from={f(s) + 2} durationInFrames={f(2)}><Audio src={staticFile("sons/espuma/bolha.wav")} volume={0.45} /></Sequence>
      ))}
      <Sequence from={f(10.5)} durationInFrames={f(2)}><Audio src={staticFile("sons/espuma/ding_suave.wav")} volume={0.55} /></Sequence>
      <Sequence from={f(12)} durationInFrames={f(2)}><Audio src={staticFile("sons/espuma/swoosh_macio.wav")} volume={0.4} /></Sequence>
      <Sequence from={f(14.1)} durationInFrames={f(2)}><Audio src={staticFile("sons/espuma/ding_suave.wav")} volume={0.5} /></Sequence>
    </AbsoluteFill>
  );
};
