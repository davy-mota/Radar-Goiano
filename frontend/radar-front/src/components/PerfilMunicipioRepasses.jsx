import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatarNomeProprio } from '../utils/formatarTexto.js';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const moeda = (valor, compacto = false) => new Intl.NumberFormat('pt-BR', {
  style: 'currency', currency: 'BRL', notation: compacto ? 'compact' : 'standard', maximumFractionDigits: 2,
}).format(Number(valor) || 0);
const numero = (valor) => new Intl.NumberFormat('pt-BR').format(Number(valor) || 0);
const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

export default function PerfilMunicipioRepasses({ codigoIbge, tema, ano = 2025 }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    fetch(`${API}/api/repasses/municipio/${codigoIbge}?ano=${ano}`)
      .then((resposta) => {
        if (!resposta.ok) throw Error();
        return resposta.json();
      })
      .then(setDados)
      .catch(() => setErro('Não foi possível carregar o detalhamento deste município.'));
  }, [codigoIbge, ano]);

  if (erro) return <div role="alert" className="mt-5 rounded-xl border border-red-400 p-4">{erro}</div>;
  if (!dados) return <p className={`mt-5 ${tema.secundario}`}>Carregando perfil municipal…</p>;

  const municipio = dados.municipio;
  const serie = dados.serie_mensal.map((item) => ({ ...item, mes_nome: MESES[item.mes - 1] }));
  const composicao = [
    ['ICMS', municipio.icms, '#00813A'],
    ['IPVA', municipio.ipva, '#003087'],
    ['IPI', municipio.ipi, '#FACC15'],
  ];

  return <article className={`mt-6 rounded-xl border p-5 ${tema.card}`} aria-label="Perfil municipal de repasses">
    <header>
      <p className="text-xs font-black uppercase tracking-widest text-goiasGreen">Município selecionado</p>
      <h3 className={`mt-1 text-2xl font-black ${tema.titulo}`}>{formatarNomeProprio(municipio.nome)}</h3>
      <p className={`mt-1 text-sm ${tema.secundario}`}>
        {municipio.regiao_imediata} · código IBGE {municipio.codigo_ibge} · {dados.cobertura}
      </p>
    </header>

    <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {[
        ['Total creditado', moeda(municipio.total)],
        ['Por habitante', moeda(municipio.valor_per_capita)],
        ['Posição no total', `${municipio.posicao_total}º de 246`],
        ['Posição per capita', `${municipio.posicao_per_capita}º de 246`],
      ].map(([rotulo, valor]) => <div key={rotulo} className={`rounded-lg border p-4 ${tema.campo}`}>
        <p className={`text-xs ${tema.secundario}`}>{rotulo}</p>
        <p className={`mt-1 font-black ${tema.titulo}`}>{valor}</p>
      </div>)}
    </div>

    <section className="mt-6 border-t pt-5">
      <h4 className={`font-black ${tema.titulo}`}>1. De quais tributos veio o valor?</h4>
      <p className={`mt-1 text-sm ${tema.secundario}`}>Composição dos créditos estaduais no período publicado.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {composicao.map(([nome, valor, cor]) => <div key={nome} className={`rounded-lg border-l-4 p-4 ${tema.campo}`} style={{ borderLeftColor: cor }}>
          <p className={`text-sm ${tema.secundario}`}>{nome}</p>
          <p className={`mt-1 text-lg font-black ${tema.titulo}`}>{moeda(valor)}</p>
          <p className={`text-xs ${tema.secundario}`}>{((Number(valor) / Number(municipio.total)) * 100).toFixed(1).replace('.', ',')}% do total</p>
        </div>)}
      </div>
    </section>

    <section className="mt-6 border-t pt-5">
      <h4 className={`font-black ${tema.titulo}`}>2. Como os créditos evoluíram mês a mês?</h4>
      <p className={`mt-1 text-sm ${tema.secundario}`}>A altura total da coluna é a soma de ICMS, IPVA e IPI no mês.</p>
      <div className="mt-4 h-72">
        <ResponsiveContainer>
          <BarChart data={serie}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
            <XAxis dataKey="mes_nome" />
            <YAxis tickFormatter={(valor) => moeda(valor, true)} width={75} />
            <Tooltip formatter={(valor, nome) => [moeda(valor), nome.toUpperCase()]} />
            <Legend />
            <Bar dataKey="icms" name="ICMS" stackId="total" fill="#00813A" />
            <Bar dataKey="ipva" name="IPVA" stackId="total" fill="#003087" />
            <Bar dataKey="ipi" name="IPI" stackId="total" fill="#FACC15" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>

    <section className="mt-6 border-t pt-5">
      <h4 className={`font-black ${tema.titulo}`}>3. Como se compara a municípios de porte semelhante?</h4>
      <p className={`mt-1 text-sm leading-6 ${tema.secundario}`}>
        Os cinco municípios com população numericamente mais próxima dos {numero(municipio.populacao)} habitantes estimados.
        Proximidade populacional não significa a mesma atividade econômica ou arrecadação.
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className={tema.secundario}><tr><th className="py-2">Município</th><th>População</th><th>Diferença</th><th>Total</th><th>Por habitante</th></tr></thead>
          <tbody>
            {dados.municipios_semelhantes.map((item) => <tr key={item.codigo_ibge} className="border-t border-current/10">
              <td className={`py-3 font-bold ${tema.titulo}`}>{formatarNomeProprio(item.nome)}</td>
              <td>{numero(item.populacao)}</td>
              <td>{Number(item.diferenca_populacao_percentual) >= 0 ? '+' : ''}{Number(item.diferenca_populacao_percentual).toFixed(1).replace('.', ',')}%</td>
              <td>{moeda(item.total)}</td><td>{moeda(item.valor_per_capita)}</td>
            </tr>)}
          </tbody>
        </table>
      </div>
    </section>
  </article>;
}
