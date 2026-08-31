import { useEffect, useState } from 'react';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import ContextoTela from './ContextoTela.jsx';
import MapaMunicipal from './MapaMunicipal.jsx';
import { useTema } from '../theme.js';
import { formatarNomeProprio } from '../utils/formatarTexto.js';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const moeda = (valor) => new Intl.NumberFormat('pt-BR', {
  style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 2,
}).format(Number(valor) || 0);
const habitantes = (valor) => new Intl.NumberFormat('pt-BR').format(Number(valor) || 0);

export default function RepassesMunicipais({ temaClaro }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');
  const [modo, setModo] = useState('absoluto');
  const [geojson, setGeojson] = useState(null);
  const tema = useTema(temaClaro);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/repasses/resumo?ano=2025`),
      fetch('/dados/goias_municipios_2025.geojson'),
    ])
      .then(async ([respostaDados, respostaMapa]) => {
        if (!respostaDados.ok || !respostaMapa.ok) throw Error();
        return [await respostaDados.json(), await respostaMapa.json()];
      })
      .then(([resumo, mapa]) => {
        setDados(resumo);
        setGeojson(mapa);
      })
      .catch(() => setErro('Não foi possível carregar os repasses.'));
  }, []);

  const perCapita = modo === 'per_capita';
  const ranking = dados
    ? (perCapita ? dados.ranking_per_capita : dados.ranking).map((item) => ({
        ...item,
        nome: formatarNomeProprio(item.nome),
      }))
    : [];
  const campoValor = perCapita ? 'valor_per_capita' : 'valor';

  return <div>
    <ContextoTela
      temaClaro={temaClaro}
      etiqueta="O recurso chega ao território"
      titulo="Repasses aos Municípios"
      descricao="Acompanhe os valores de ICMS, IPI e IPVA efetivamente creditados aos municípios goianos."
      pergunta="Quais municípios receberam os maiores repasses e como o resultado muda quando consideramos a população?"
      ressalva="O valor absoluto mostra a dimensão financeira; o valor per capita divide o total pela população estimada e não representa quanto cada morador recebeu. A cobertura financeira vai de janeiro a julho de 2025."
    />
    {erro && <div role="alert">{erro}</div>}
    {dados && <>
      <div className="mb-6 grid gap-4 sm:grid-cols-4">
        {[
          ['Total creditado', dados.kpis.total],
          ['ICMS', dados.kpis.icms],
          ['IPVA', dados.kpis.ipva],
          ['Dedução Fundeb', dados.kpis.fundeb],
        ].map(([nome, valor]) => <div key={nome} className={`rounded-xl border p-5 ${tema.card}`}>
          <p className={tema.secundario}>{nome}</p>
          <p className={`mt-2 text-xl font-black ${tema.titulo}`}>{moeda(valor)}</p>
        </div>)}
      </div>

      <section className={`rounded-xl border p-5 ${tema.card}`}>
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h3 className={`font-black ${tema.titulo}`}>Compare os municípios no mapa e no ranking</h3>
            <p className={`mt-1 text-sm ${tema.secundario}`}>
              {dados.kpis.municipios} municípios conciliados pelo código IBGE · {dados.cobertura}
            </p>
            <p className={`mt-1 text-xs ${tema.secundario}`}>
              {dados.populacao_referencia} · registros sem município permanecem fora do ranking
            </p>
          </div>
          <div className={`flex rounded-lg border p-1 ${tema.campo}`} aria-label="Modo do ranking">
            {[['absoluto', 'Valor total'], ['per_capita', 'Por habitante']].map(([valor, rotulo]) =>
              <button
                key={valor}
                type="button"
                onClick={() => setModo(valor)}
                className={`rounded-md px-3 py-2 text-sm font-bold ${modo === valor ? 'bg-goiasGreen text-white' : ''}`}
              >{rotulo}</button>)}
          </div>
        </div>

        {geojson && <div className="mt-6 border-t pt-5">
          <h3 className={`mb-1 font-black ${tema.titulo}`}>Distribuição territorial dos repasses</h3>
          <p className={`mb-4 text-sm ${tema.secundario}`}>
            Cada cor compara o município com os demais no modo selecionado; não representa qualidade da gestão.
          </p>
          <MapaMunicipal geojson={geojson} dados={dados.mapa} modo={modo} tema={tema} />
        </div>}

        <div className="mt-6 border-t pt-5">
          <h3 className={`font-black ${tema.titulo}`}>
            {perCapita ? 'Maior valor creditado por habitante' : 'Maior valor total creditado'}
          </h3>
          <p className={`mb-4 mt-1 text-sm ${tema.secundario}`}>Os 15 maiores valores no modo selecionado.</p>
        </div>
        <div className="h-[440px]">
          <ResponsiveContainer>
            <BarChart data={ranking} layout="vertical" margin={{ left: 10 }}>
              <XAxis type="number" tickFormatter={moeda} />
              <YAxis type="category" dataKey="nome" width={130} fontSize={10} />
              <Tooltip
                formatter={(valor) => [moeda(valor), perCapita ? 'Por habitante' : 'Total creditado']}
                labelFormatter={(nome) => {
                  const item = ranking.find((linha) => linha.nome === nome);
                  return item ? `${nome} · ${habitantes(item.populacao)} habitantes` : nome;
                }}
              />
              <Bar dataKey={campoValor} fill={perCapita ? '#003087' : '#00813A'} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </>}
  </div>;
}
