import { Composition, Folder } from "remotion";
import { DEMO_ESPUMA_DUR, DemoEspuma } from "./marcas/DemoEspuma";
import { CARROSSEL_EXEMPLO, CARROSSEL_H, CARROSSEL_W, CarrosselEspuma, PropsCarrossel } from "./carrossel/CarrosselEspuma";

// Cada vídeo novo: src/<projeto>/<Projeto>.tsx (use referencias/exemplo-lavae/Lavae.tsx como modelo) e registre aqui em "Videos".
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Folder name="Marca-Espuma">
        <Composition id="DemoEspuma" component={DemoEspuma} durationInFrames={DEMO_ESPUMA_DUR} fps={30} width={1080} height={1920} />
      </Folder>
      <Folder name="Instagram">
        {/* Carrossel de feed: um quadro por slide. Props vêm do post.json do ciclo (automacao-instagram/criar_post.py). */}
        <Composition
          id="CarrosselEspuma"
          component={CarrosselEspuma}
          durationInFrames={CARROSSEL_EXEMPLO.slides.length}
          fps={1}
          width={CARROSSEL_W}
          height={CARROSSEL_H}
          defaultProps={CARROSSEL_EXEMPLO}
          calculateMetadata={({ props }: { props: PropsCarrossel }) => ({ durationInFrames: Math.max(1, props.slides.length) })}
        />
      </Folder>
    </>
  );
};
