// Mede o layout (com as fontes de verdade, no navegador do Remotion) e renderiza o vídeo.
//   node render.mjs <props.json> <saida.mp4>          mede; se tudo couber, renderiza
//   node render.mjs <props.json> --so-medir           só mede (sai 2 se algum texto não couber)
//   node render.mjs <props.json> --quadros <pasta> t1 t2 ...   PNGs de conferência nesses segundos
// Saída 0 = ok; 2 = erro de layout (texto não cabe); 1 = falha técnica.
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import {readFileSync, mkdirSync, writeFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const [arqProps, alvo, ...resto] = process.argv.slice(2);
if (!arqProps || !alvo) {
	console.error('uso: node render.mjs <props.json> <saida.mp4> | --so-medir | --quadros <pasta> t...');
	process.exit(1);
}
const inputProps = JSON.parse(readFileSync(arqProps, 'utf8'));

const serveUrl = await bundle({entryPoint: path.join(aqui, 'src', 'index.ts'), publicDir: path.join(aqui, 'public')});
const comp = await selectComposition({serveUrl, id: 'Carrossel', inputProps});
const erros = comp.props.erros ?? [];
writeFileSync(arqProps.replace(/\.json$/, '') + '.layout.json', JSON.stringify({erros, layout: comp.props.layout}, null, 1));
if (erros.length) {
	console.error('ERRO DE LAYOUT:');
	for (const e of erros) console.error('  - ' + e);
	process.exit(2);
}
console.log(`layout ok: ${comp.durationInFrames} quadros (${(comp.durationInFrames / comp.fps).toFixed(2)} s)`);
if (alvo === '--so-medir') process.exit(0);

if (alvo === '--quadros') {
	const [pasta, ...tempos] = resto;
	mkdirSync(pasta, {recursive: true});
	for (const t of tempos) {
		const frame = Math.min(comp.durationInFrames - 1, Math.round(Number(t) * comp.fps));
		const output = path.join(pasta, `t${Number(t).toFixed(2)}.png`);
		await renderStill({composition: comp, serveUrl, inputProps, frame, output, imageFormat: 'png'});
		console.log('quadro ' + output);
	}
	process.exit(0);
}

let ultimo = -1;
await renderMedia({
	composition: comp,
	serveUrl,
	inputProps,
	codec: 'h264',
	crf: 20,
	pixelFormat: 'yuv420p',
	audioCodec: 'aac',
	audioBitrate: '192k',
	outputLocation: alvo,
	onProgress: ({progress}) => {
		const p = Math.floor(progress * 10);
		if (p !== ultimo) {
			ultimo = p;
			console.log(`render ${p * 10}%`);
		}
	},
});
console.log('vídeo ' + alvo);
