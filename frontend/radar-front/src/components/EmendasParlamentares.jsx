import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import ContextoTela from './ContextoTela.jsx';
import { useTema } from '../theme.js';
import { formatarNomeProprio } from '../utils/formatarTexto.js';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const moeda = (valor, compacto = false) => new Intl.NumberFormat('pt-BR', {
  style: 'currency', currency: 'BRL', notation: compacto ? 'compact' : 'standard', maximumFractionDigits: 2,
}).format(Number(valor) || 0);
const percentual = (parte, total) => total ? `${((Number(parte) / Number(total)) * 100).toFixed(1).replace('.', ',')}%` : '—';

export default function EmendasParlamentares({ temaClaro }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');
  const tema = useTema(temaClaro);

  useEffect(() => {
    fetch(`${API}/api/emendas/resumo?ano=2025`)
      .then((resposta) => {
        if (!resposta.ok) throw Error();
        return resposta.json();
      })
      .then(setDados)
      .catch(() => setErro('Não foi possível carregar as emendas parlamentares.'));
  }, []);

  const etapas = dados ? [
    ['Indicado', dados.kpis.indicado, 'Valor informado na parcela da emenda'],
    ['Empenhado', dados.kpis.empenhado, 'Compromisso orçamentário registrado'],
    ['Liquidado', dados.kpis.liquidado, 'Despesa reconhecida após verificação'],
    ['Pago', dados.kpis.pago, 'Ordem de pagamento registrada'],
  ] : [];

  return <div>
    <ContextoTela
      temaClaro={temaClaro}
      etiqueta="Da indicação até o pagamento"
      titulo="Emendas Parlamentares Estaduais"
      descricao="Acompanhe autores, áreas, beneficiários e as etapas financeiras das emendas destinadas pela Assembleia Legislativa de Goiás."
      pergunta="Quanto foi indicado, empenhado, liquidado e pago, e para quais áreas e localidades o recurso foi destinado?"
      ressalva="Emenda indicada não é pagamento realizado. Os valores representam etapas diferentes e não devem ser somados. A presença de um autor ou beneficiário não indica favorecimento ou irregularidade."
    />
    {erro && <div role="alert">{erro}</div>}
    {dados && <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Etapas financeiras das emendas">
        {etapas.map(([nome, valor, explicacao], indice) => <div key={nome} className={`rounded-xl border p-5 ${tema.card}`}>
          <p className="text-xs font-black uppercase tracking-wider text-goiasGreen">Etapa {indice + 1}</p>
          <h3 className={`mt-1 font-black ${tema.titulo}`}>{nome}</h3>
          <p className={`mt-2 text-xl font-black ${tema.titulo}`}>{moeda(valor, true)}</p>
          <p className={`mt-2 text-xs leading-5 ${tema.secundario}`}>{explicacao}</p>
          {indice > 0 && <p className={`mt-2 text-xs ${tema.secundario}`}>{percentual(valor, dados.kpis.indicado)} do valor indicado</p>}
        </div>)}
      </section>

      <section className={`mt-6 rounded-xl border p-5 ${tema.card}`}>
        <h3 className={`font-black ${tema.titulo}`}>O que a base de 2025 permite enxergar?</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {[
            ['Registros', dados.kpis.registros], ['Autores', dados.kpis.autores],
            ['Áreas', dados.kpis.funcoes], ['Beneficiários', dados.kpis.beneficiarios],
            ['Municípios conciliados', dados.kpis.municipios],
          ].map(([nome, valor]) => <div key={nome} className={`rounded-lg border p-4 ${tema.campo}`}>
            <p className={`text-xs ${tema.secundario}`}>{nome}</p><p className={`mt-1 text-lg font-black ${tema.titulo}`}>{valor}</p>
          </div>)}
        </div>
        <p className={`mt-4 text-xs leading-5 ${tema.secundario}`}>
          A fonte contém {dados.qualidade.metricas.registros_fonte} linhas de 2020 a 2025; {dados.qualidade.metricas.registros_descartados_outros_exercicios} linhas de outros exercícios foram excluídas deste recorte. Há {dados.qualidade.metricas.valores_monetarios_invalidos} valores monetários “#N/D”, tratados como ausentes nas somas.
        </p>
      </section>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <section className={`rounded-xl border p-5 ${tema.card}`}>
          <h3 className={`font-black ${tema.titulo}`}>Autores com maior valor empenhado</h3>
          <p className={`mb-4 mt-1 text-sm ${tema.secundario}`}>O gráfico descreve destinação orçamentária; não avalia mérito parlamentar.</p>
          <div className="h-96"><ResponsiveContainer><BarChart data={dados.autores.map((item) => ({ ...item, nome: formatarNomeProprio(item.nome) }))} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} /><XAxis type="number" tickFormatter={(valor) => moeda(valor, true)} />
            <YAxis type="category" dataKey="nome" width={125} fontSize={10} /><Tooltip formatter={(valor) => moeda(valor)} />
            <Bar dataKey="empenhado" name="Empenhado" fill="#00813A" /><Bar dataKey="pago" name="Pago" fill="#003087" />
          </BarChart></ResponsiveContainer></div>
        </section>
        <section className={`rounded-xl border p-5 ${tema.card}`}>
          <h3 className={`font-black ${tema.titulo}`}>Áreas com maior valor empenhado</h3>
          <p className={`mb-4 mt-1 text-sm ${tema.secundario}`}>Função orçamentária informada pela fonte.</p>
          <div className="h-96"><ResponsiveContainer><BarChart data={dados.funcoes}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} /><XAxis dataKey="nome" fontSize={9} angle={-20} height={70} />
            <YAxis tickFormatter={(valor) => moeda(valor, true)} width={75} /><Tooltip formatter={(valor) => moeda(valor)} /><Legend />
            <Bar dataKey="empenhado" name="Empenhado" fill="#00813A" /><Bar dataKey="pago" name="Pago" fill="#003087" />
          </BarChart></ResponsiveContainer></div>
        </section>
      </div>

      <section className={`mt-6 rounded-xl border p-5 ${tema.card}`}>
        <h3 className={`font-black ${tema.titulo}`}>Maiores registros empenhados</h3>
        <p className={`mb-4 mt-1 text-sm ${tema.secundario}`}>Use objeto e beneficiário para contextualizar o valor; uma linha não representa necessariamente uma emenda completa.</p>
        <div className="overflow-x-auto"><table className="min-w-[980px] w-full text-left text-sm">
          <thead className={tema.secundario}><tr><th className="py-2">Autor</th><th>Objeto</th><th>Beneficiário / município</th><th>Área</th><th>Empenhado</th><th>Pago</th></tr></thead>
          <tbody>{dados.registros.map((item, indice) => <tr key={`${item.autor}-${indice}`} className="border-t border-current/10 align-top">
            <td className={`py-3 pr-4 font-bold ${tema.titulo}`}>{formatarNomeProprio(item.autor)}</td>
            <td className="max-w-xs py-3 pr-4">{item.objeto || 'Não informado'}</td>
            <td className="max-w-xs py-3 pr-4">{item.beneficiario || item.municipio_origem || 'Não informado'}</td>
            <td className="py-3 pr-4">{item.funcao}</td><td className="py-3 pr-4">{moeda(item.valor_empenhado)}</td><td className="py-3">{moeda(item.valor_pago)}</td>
          </tr>)}</tbody>
        </table></div>
      </section>
    </>}
  </div>;
}
