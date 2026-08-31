import { useMemo, useState } from 'react';
import { formatarNomeProprio } from '../utils/formatarTexto.js';
import PerfilMunicipioRepasses from './PerfilMunicipioRepasses.jsx';

const CORES = ['#dcfce7', '#86efac', '#22c55e', '#00813a', '#14532d'];
const moeda = (valor) => new Intl.NumberFormat('pt-BR', {
  style: 'currency', currency: 'BRL', maximumFractionDigits: 2,
}).format(Number(valor) || 0);
const numero = (valor) => new Intl.NumberFormat('pt-BR').format(Number(valor) || 0);

function percorrerCoordenadas(coordenadas, callback) {
  if (typeof coordenadas?.[0] === 'number') callback(coordenadas);
  else coordenadas?.forEach((item) => percorrerCoordenadas(item, callback));
}

function criarProjetor(features, largura, altura, margem = 12) {
  const limites = { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity };
  features.forEach((feature) => percorrerCoordenadas(feature.geometry.coordinates, ([x, y]) => {
    limites.minX = Math.min(limites.minX, x);
    limites.maxX = Math.max(limites.maxX, x);
    limites.minY = Math.min(limites.minY, y);
    limites.maxY = Math.max(limites.maxY, y);
  }));
  const escala = Math.min(
    (largura - 2 * margem) / (limites.maxX - limites.minX),
    (altura - 2 * margem) / (limites.maxY - limites.minY),
  );
  const deslocamentoX = (largura - (limites.maxX - limites.minX) * escala) / 2;
  const deslocamentoY = (altura - (limites.maxY - limites.minY) * escala) / 2;
  return ([x, y]) => [
    deslocamentoX + (x - limites.minX) * escala,
    altura - deslocamentoY - (y - limites.minY) * escala,
  ];
}

function caminhoAnel(anel, projetar) {
  return anel.map((ponto, indice) => {
    const [x, y] = projetar(ponto);
    return `${indice ? 'L' : 'M'}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(' ') + ' Z';
}

function caminhoGeometria(geometria, projetar) {
  const poligonos = geometria.type === 'Polygon' ? [geometria.coordinates] : geometria.coordinates;
  return poligonos.flatMap((poligono) => poligono.map((anel) => caminhoAnel(anel, projetar))).join(' ');
}

function quantis(valores) {
  const ordenados = valores.filter((valor) => Number.isFinite(valor)).sort((a, b) => a - b);
  return [0.2, 0.4, 0.6, 0.8].map((parte) => ordenados[Math.floor((ordenados.length - 1) * parte)] || 0);
}

export default function MapaMunicipal({ geojson, dados, modo, tema }) {
  const [selecionado, setSelecionado] = useState(null);
  const largura = 720;
  const altura = 570;
  const campo = modo === 'per_capita' ? 'valor_per_capita' : 'valor';
  const indice = useMemo(() => new Map(dados.map((item) => [String(item.codigo_ibge), item])), [dados]);
  const projetar = useMemo(() => criarProjetor(geojson.features, largura, altura), [geojson]);
  const limites = useMemo(() => quantis(dados.map((item) => Number(item[campo]))), [dados, campo]);
  const cor = (valor) => CORES[limites.findIndex((limite) => valor <= limite) === -1
    ? CORES.length - 1
    : limites.findIndex((limite) => valor <= limite)];
  const detalhe = selecionado ? indice.get(selecionado) : null;

  return <div><div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_260px]">
    <div className="overflow-hidden rounded-xl border border-black/10 bg-slate-50">
      <svg
        viewBox={`0 0 ${largura} ${altura}`}
        className="h-auto w-full"
        role="img"
        aria-label={`Mapa de repasses municipais por ${modo === 'per_capita' ? 'habitante' : 'valor total'}`}
      >
        {geojson.features.map((feature) => {
          const codigo = String(feature.properties.codarea);
          const item = indice.get(codigo);
          const nome = item?.nome || `Código IBGE ${codigo}`;
          const valor = Number(item?.[campo]) || 0;
          return <path
            key={codigo}
            d={caminhoGeometria(feature.geometry, projetar)}
            fill={item ? cor(valor) : '#e5e7eb'}
            stroke={selecionado === codigo ? '#facc15' : '#ffffff'}
            strokeWidth={selecionado === codigo ? 2.5 : 0.7}
            className="cursor-pointer transition-opacity hover:opacity-70 focus:outline-none"
            tabIndex="0"
            role="button"
            aria-label={`${nome}: ${moeda(valor)}${modo === 'per_capita' ? ' por habitante' : ''}`}
            onClick={() => setSelecionado(codigo)}
            onKeyDown={(evento) => {
              if (evento.key === 'Enter' || evento.key === ' ') setSelecionado(codigo);
            }}
          ><title>{`${nome}: ${moeda(valor)}${modo === 'per_capita' ? ' por habitante' : ''}`}</title></path>;
        })}
      </svg>
    </div>

    <aside className={`rounded-xl border p-4 ${tema.card}`} aria-live="polite">
      <h4 className={`font-black ${tema.titulo}`}>Leitura do mapa</h4>
      <p className={`mt-2 text-sm leading-6 ${tema.secundario}`}>
        Tons mais escuros representam os 20% de municípios com maiores valores nesta leitura.
        Clique em um território para ver os detalhes.
      </p>
      <div className="mt-4 flex" aria-label="Escala de cores">
        {CORES.map((item) => <span key={item} className="h-3 flex-1" style={{ backgroundColor: item }} />)}
      </div>
      <div className={`mt-1 flex justify-between text-xs ${tema.secundario}`}><span>Menor</span><span>Maior</span></div>
      {detalhe
        ? <div className="mt-6 border-t pt-4">
            <p className={`text-lg font-black ${tema.titulo}`}>{formatarNomeProprio(detalhe.nome)}</p>
            <dl className={`mt-3 space-y-2 text-sm ${tema.secundario}`}>
              <div><dt>Valor total</dt><dd className={`font-bold ${tema.titulo}`}>{moeda(detalhe.valor)}</dd></div>
              <div><dt>Por habitante</dt><dd className={`font-bold ${tema.titulo}`}>{moeda(detalhe.valor_per_capita)}</dd></div>
              <div><dt>População estimada</dt><dd className={`font-bold ${tema.titulo}`}>{numero(detalhe.populacao)}</dd></div>
              <div><dt>Código IBGE</dt><dd className={`font-bold ${tema.titulo}`}>{detalhe.codigo_ibge}</dd></div>
            </dl>
          </div>
        : <p className={`mt-6 text-sm ${tema.secundario}`}>Nenhum município selecionado.</p>}
    </aside>
  </div>
  {selecionado && <PerfilMunicipioRepasses key={selecionado} codigoIbge={selecionado} tema={tema} />}
  </div>;
}
