import React from 'react';
import {Composition} from 'remotion';
import {fontesProntas} from './fontes';
import {calcularLayout} from './layout';
import type {Props} from './tipos';
import {Video} from './Video';
import exemplo from './exemplo.json';

const FPS = 30;

export const Root: React.FC = () => (
	<Composition
		id="Carrossel"
		component={Video}
		width={1080}
		height={1920}
		fps={FPS}
		durationInFrames={FPS * 10}
		defaultProps={exemplo as unknown as Props}
		calculateMetadata={async ({props}) => {
			await fontesProntas();
			const {layout, erros} = calcularLayout(props);
			return {
				durationInFrames: Math.max(1, Math.round(props.duracao * FPS)),
				props: {...props, layout, erros},
			};
		}}
	/>
);
