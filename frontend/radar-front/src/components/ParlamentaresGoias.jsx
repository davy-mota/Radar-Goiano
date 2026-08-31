import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import ContextoTela from './ContextoTela.jsx';
import { useTema } from '../theme.js';
import { formatarNomeProprio } from '../utils/formatarTexto.js';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const moeda = (valor, compacto = false) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', notation: compacto ? 'compact' : 'standard', maximumFractionDigits: 2 }).format(Number(valor) || 0);
const numero = (valor) => new Intl.NumberFormat('pt-BR').format(Number(valor) || 0);
const pct = (valor) => `${(Number(valor || 0) * 100).toFixed(0)}%`;

function sinal(item) {
  if (Number(item.tamanho_coorte) < 10) return ['Amostra pequena', 'bg-amber-500/15 text-amber-700'];
  if (Number(item.razao_mediana) >= 1.25) return ['Acima da mediana', 'bg-blue-500/15 text-blue-700'];
  if (Number(item.razao_mediana) <= 0.75) return ['Abaixo da mediana', 'bg-green-500/15 text-green-700'];
  return ['Próximo da mediana', 'bg-slate-500/15 text-slate-600'];
}

export default function ParlamentaresGoias({ temaClaro }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');
  const [cargo, setCargo] = useState('deputado_federal');
  const tema = useTema(temaClaro);

  useEffect(() => {
    fetch(`${API}/api/parlamentares/resumo?ano=2025`).then((resposta) => {
      if (!resposta.ok) throw Error();
      return resposta.json();
    }).then(setDados).catch(() => setErro('Não foi possível carregar as despesas parlamentares.'));
  }, []);

  const lista = dados?.parlamentares.filter((item) => item.cargo === cargo) || [];
  const cobertura = dados?.cobertura.find((item) => item.cargo === cargo);
  const total = dados?.totais.find((item) => item.cargo === cargo);
  const titulos = { deputado_federal: 'Deputados federais de Goiás', deputado_estadual: 'Deputados estaduais de Goiás', senador: 'Senadores de Goiás' };
  const tituloCargo = titulos[cargo];

  return <div className="animate-fade-in">
    <ContextoTela temaClaro={temaClaro} etiqueta="Comparação responsável entre pares" titulo="Despesas de Parlamentares" descricao="Compare reembolsos da atividade parlamentar entre representantes do mesmo cargo e no mesmo período." pergunta="Quais gabinetes apresentam valores, picos ou concentrações que merecem consulta aos documentos?" ressalva="Estar acima da mediana não prova gasto excessivo, desperdício ou irregularidade. Mandato parcial, funções, território, glosas e datas de reembolso podem alterar a comparação." />
    {erro && <div role="alert">{erro}</div>}
    {dados && <>
      <section className="grid gap-3 md:grid-cols-4" aria-label="Cobertura dos cargos eletivos">
        {[
          ['Deputados federais', 'CEAP oficial', true], ['Senadores', 'CEAPS oficial', true],
          ['Deputados estaduais', 'Verba Indenizatória da Alego', true], ['Vereadores', 'Sem fonte centralizada', false],
        ].map(([nome, descricao, disponivel]) => <div key={nome} className={`rounded-xl border p-4 ${tema.card}`}>
          <span className={`rounded-full px-2 py-1 text-xs font-bold ${disponivel ? 'bg-green-500/15 text-green-700' : 'bg-amber-500/15 text-amber-700'}`}>{disponivel ? 'Disponível' : 'Cobertura pendente'}</span>
          <h3 className={`mt-3 font-black ${tema.titulo}`}>{nome}</h3><p className={`mt-1 text-xs ${tema.secundario}`}>{descricao}</p>
        </div>)}
      </section>

      <div className={`mt-6 inline-flex rounded-lg border p-1 ${tema.campo}`} aria-label="Cargo parlamentar">
        {[['deputado_federal', 'Deputados federais'], ['deputado_estadual', 'Deputados estaduais'], ['senador', 'Senadores']].map(([valor, nome]) => <button key={valor} type="button" onClick={() => setCargo(valor)} className={`rounded-md px-4 py-2 text-sm font-bold ${cargo === valor ? 'bg-goiasGreen text-white' : ''}`}>{nome}</button>)}
      </div>

      <section className={`mt-4 rounded-xl border p-5 ${tema.card}`}>
        <h3 className={`text-xl font-black ${tema.titulo}`}>{tituloCargo}</h3><p className={`mt-1 text-sm ${tema.secundario}`}>{dados.fontes[cargo]} · exercício de 2025</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          {[
            ['Cadastrados', cobertura?.cadastrados], ['Com registros', cobertura?.com_registros],
            [cargo === 'deputado_estadual' ? 'Prestações mensais' : 'Documentos', numero(total?.documentos)], ['Reembolsado', moeda(total?.reembolsado, true)],
          ].map(([nome, valor]) => <div key={nome} className={`rounded-lg border p-4 ${tema.campo}`}><p className={`text-xs ${tema.secundario}`}>{nome}</p><p className={`mt-1 font-black ${tema.titulo}`}>{valor}</p></div>)}
        </div>
        {cargo === 'senador' && cobertura?.sem_registros > 0 && <p className={`mt-4 rounded-lg bg-amber-500/10 p-3 text-sm ${tema.secundario}`}>{dados.sem_registros.filter((item) => item.cargo === 'senador').map((item) => formatarNomeProprio(item.parlamentar_nome)).join(', ')} não possui registro na CEAPS de 2025. Isso significa ausência de documentos nessa fonte, não gasto comprovadamente igual a zero.</p>}
        <h4 className={`mt-6 font-black ${tema.titulo}`}>Média por mês com registro</h4>
        <p className={`mt-1 text-sm ${tema.secundario}`}>Essa medida reduz parte da distorção de mandatos ou reembolsos que não cobrem os doze meses.</p>
        <div className="mt-4 h-[440px]"><ResponsiveContainer><BarChart data={lista.map((item) => ({ ...item, nome: formatarNomeProprio(item.parlamentar_nome) }))} layout="vertical"><CartesianGrid strokeDasharray="3 3" opacity={0.15} /><XAxis type="number" tickFormatter={(valor) => moeda(valor, true)} /><YAxis type="category" dataKey="nome" width={135} fontSize={10} /><Tooltip formatter={(valor) => moeda(valor)} /><Bar dataKey="media_mensal" name="Média mensal" fill="#00813A" /></BarChart></ResponsiveContainer></div>
      </section>

      <section className={`mt-6 rounded-xl border p-5 ${tema.card}`}>
        <h3 className={`font-black ${tema.titulo}`}>Sinais para aprofundar a análise documental</h3>
        <p className={`mt-1 text-sm leading-6 ${tema.secundario}`}>Média mensal, pico e concentração ajudam a encontrar casos que merecem contexto. Nenhum indicador isolado classifica mau uso.</p>
        {cargo === 'deputado_estadual' && <p className={`mt-2 rounded-lg bg-blue-500/10 p-3 text-sm ${tema.secundario}`}>A Alego foi integrada pelo resumo mensal oficial. “Prestações” representa um total mensal por gabinete, não a quantidade de notas fiscais. Consulte o link de origem para o detalhamento documental.</p>}
        <div className="mt-4 overflow-x-auto"><table className="min-w-[1120px] w-full text-left text-sm"><thead className={tema.secundario}><tr><th className="py-2">Parlamentar</th><th>Sinal</th><th>Total</th><th>Média mensal</th><th>Mediana</th><th>Pico/média</th><th>Principal categoria</th><th>Concentração</th><th>Documentos</th><th>Glosas</th></tr></thead><tbody>
          {lista.map((item) => { const [rotulo, estilo] = sinal(item); return <tr key={`${item.cargo}-${item.parlamentar_codigo}`} className="border-t border-current/10"><td className={`py-3 pr-4 font-bold ${tema.titulo}`}>{formatarNomeProprio(item.parlamentar_nome)} {item.partido && <span className={`font-normal ${tema.secundario}`}>({item.partido})</span>}</td><td className="pr-4"><span className={`rounded-full px-2 py-1 text-xs font-bold ${estilo}`}>{rotulo}</span></td><td className="pr-4">{moeda(item.reembolsado)}</td><td className="pr-4">{moeda(item.media_mensal)}</td><td className="pr-4">{moeda(item.mediana_coorte)}</td><td className="pr-4">{Number(item.razao_pico_mensal).toFixed(1).replace('.', ',')}×</td><td className="max-w-xs pr-4">{cargo === 'deputado_estadual' ? 'Resumo mensal' : item.categoria_principal}</td><td className="pr-4">{cargo === 'deputado_estadual' ? '—' : pct(item.concentracao_categoria)}</td><td className="pr-4">{numero(item.documentos)}</td><td>{moeda(item.glosas)}</td></tr>; })}
        </tbody></table></div>
      </section>

      <section className={`mt-6 rounded-xl border p-5 ${tema.card}`}><h3 className={`font-black ${tema.titulo}`}>Como ler “acima da mediana”</h3><p className={`mt-2 text-sm leading-6 ${tema.secundario}`}>O sinal aparece quando a média mensal supera a mediana do cargo em pelo menos 25% e o grupo possui dez ou mais parlamentares. Para senadores, a amostra é pequena e o sistema não produz esse sinal.</p></section>
    </>}
  </div>;
}
