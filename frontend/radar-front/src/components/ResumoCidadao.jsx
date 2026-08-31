import { createElement } from 'react';
import { AlertCircle, ArrowRight, Building2, FileText, HelpCircle, Plane, Search, ShieldCheck, Users } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useTema } from '../theme.js';
import { formatarNomeProprio } from '../utils/formatarTexto.js';

const moeda = (valor) => new Intl.NumberFormat('pt-BR', {
  style: 'currency', currency: 'BRL', maximumFractionDigits: 0,
}).format(Number(valor) || 0);

const periodo = (ano) => ano === 'todos' ? 'todos os exercícios disponíveis' : `o exercício de ${ano}`;

function NumeroEtapa({ children, temaClaro }) {
  return <span className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-black ${temaClaro ? 'bg-green-100 text-green-800' : 'bg-goiasGreen/20 text-goiasGreen'}`}>{children}</span>;
}

function CartaoEscopo({ icone, titulo, valor, explicacao, cor, tema }) {
  return (
    <article className={`relative overflow-hidden rounded-2xl border p-5 md:p-6 ${tema.card}`}>
      <div className={`absolute inset-x-0 top-0 h-1 ${cor}`} />
      {createElement(icone, { size: 22, className: 'mb-5 text-goiasGreen', 'aria-hidden': true })}
      <p className={`text-xs font-bold uppercase tracking-[0.16em] ${tema.subtitulo}`}>{titulo}</p>
      <p className={`mt-2 text-2xl font-black tracking-tight md:text-3xl ${tema.titulo}`}>{moeda(valor)}</p>
      <p className={`mt-3 text-sm leading-6 ${tema.subtitulo}`}>{explicacao}</p>
    </article>
  );
}

export default function ResumoCidadao({ dados, ano, temaClaro, navegar }) {
  const tema = useTema(temaClaro);
  const categorias = Object.fromEntries((dados.raio_x || []).map((item) => [item.name.toLowerCase(), item.value]));
  const topOrgaos = (dados.top_orgaos || []).map((item) => ({ ...item, nome: formatarNomeProprio(item.nome) }));
  const alertas = dados.radar_ia_geral || [];

  return (
    <div className="animate-fade-in space-y-8 md:space-y-12">
      <section className={`relative overflow-hidden rounded-3xl border px-6 py-9 md:px-10 md:py-12 ${tema.card}`}>
        <div className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-goiasGreen/10 blur-3xl" />
        <div className="relative max-w-4xl">
          <p className="mb-3 text-xs font-black uppercase tracking-[0.22em] text-goiasGreen">Resumo cidadão · {ano === 'todos' ? 'série histórica' : ano}</p>
          <h2 className={`max-w-3xl text-3xl font-black leading-tight tracking-tight md:text-5xl ${tema.titulo}`}>Entenda o que os dados públicos mostram — e o que eles não mostram</h2>
          <p className={`mt-5 max-w-3xl text-base leading-7 md:text-lg ${tema.subtitulo}`}>Uma leitura guiada de {periodo(ano)}, em linguagem direta. Primeiro apresentamos o alcance dos dados; depois mostramos onde estão os maiores valores e quais registros merecem uma análise mais cuidadosa.</p>
          <div className={`mt-7 flex items-start gap-3 rounded-xl border p-4 text-sm leading-6 ${temaClaro ? 'border-blue-200 bg-blue-50 text-blue-950' : 'border-blue-400/25 bg-blue-400/10 text-blue-100'}`}>
            <ShieldCheck className="mt-0.5 shrink-0" size={20} />
            <p><strong>Importante:</strong> contratos, folha e diárias têm significados diferentes. Por isso, não os somamos como se fossem o “gasto total do governo”. Valor contratado não significa, necessariamente, valor pago no mesmo período.</p>
          </div>
        </div>
      </section>

      <section aria-labelledby="escopo-dados">
        <div className="mb-5 flex items-start gap-3">
          <NumeroEtapa temaClaro={temaClaro}>1</NumeroEtapa>
          <div><h3 id="escopo-dados" className={`text-xl font-black md:text-2xl ${tema.titulo}`}>Três perspectivas, três significados</h3><p className={`mt-1 text-sm ${tema.subtitulo}`}>Leia cada número de forma independente.</p></div>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <CartaoEscopo icone={Users} titulo="Folha de pagamento" valor={categorias.folha} cor="bg-cyan-500" tema={tema} explicacao="Soma das remunerações brutas registradas. Não representa a quantidade de pessoas distintas nem o valor líquido recebido." />
          <CartaoEscopo icone={FileText} titulo="Contratos formalizados" valor={categorias.contratos} cor="bg-purple-500" tema={tema} explicacao="Valor registrado nos contratos. Pode abranger mais de um exercício e não comprova que todo o montante já foi pago." />
          <CartaoEscopo icone={Plane} titulo="Diárias e passagens" valor={categorias['diárias'] || categorias.diarias} cor="bg-amber-500" tema={tema} explicacao="Soma dos registros de deslocamento disponíveis na base para o período selecionado." />
        </div>
      </section>

      <section className={`rounded-3xl border p-5 md:p-8 ${tema.card}`} aria-labelledby="concentracao-orgaos">
        <div className="mb-6 flex items-start gap-3">
          <NumeroEtapa temaClaro={temaClaro}>2</NumeroEtapa>
          <div><h3 id="concentracao-orgaos" className={`text-xl font-black md:text-2xl ${tema.titulo}`}>Onde folha e diárias se concentram?</h3><p className={`mt-1 text-sm leading-6 ${tema.subtitulo}`}>O ranking combina somente folha e diárias por órgão. Órgãos maiores ou responsáveis por aposentadorias tendem naturalmente a aparecer no topo.</p></div>
        </div>
        <div className="h-80 min-h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={topOrgaos} layout="vertical" margin={{ left: 5, right: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={tema.graficoGrid} horizontal={false} />
              <XAxis type="number" stroke={tema.graficoTexto} tickFormatter={(valor) => `R$ ${(valor / 1e9).toFixed(1)} bi`} />
              <YAxis dataKey="nome" type="category" width={125} stroke={tema.graficoTexto} fontSize={10} tickFormatter={(nome) => nome.length > 20 ? `${nome.slice(0, 20)}…` : nome} />
              <Tooltip cursor={{ fill: tema.graficoGrid }} contentStyle={tema.tooltip} formatter={(valor) => moeda(valor)} />
              <Bar dataKey="total" fill="#00813A" radius={[0, 5, 5, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <button type="button" onClick={() => navegar('Folha')} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-goiasGreen px-4 py-3 text-sm font-bold text-white hover:opacity-90">Entender a folha por órgão <ArrowRight size={17} /></button>
      </section>

      <section aria-labelledby="pontos-atencao">
        <div className="mb-5 flex items-start gap-3">
          <NumeroEtapa temaClaro={temaClaro}>3</NumeroEtapa>
          <div><h3 id="pontos-atencao" className={`text-xl font-black md:text-2xl ${tema.titulo}`}>Pontos que merecem contexto</h3><p className={`mt-1 text-sm leading-6 ${tema.subtitulo}`}>São maiores valores encontrados por regras reproduzíveis. Não são acusações nem prova de irregularidade.</p></div>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {alertas.map((alerta) => (
            <article key={`${alerta.tipo}-${alerta.nome}`} className={`rounded-2xl border p-5 ${tema.card}`}>
              <div className="flex items-center justify-between gap-3"><span className={`rounded-full px-3 py-1 text-xs font-bold ${temaClaro ? 'bg-amber-100 text-amber-900' : 'bg-amber-400/15 text-amber-300'}`}>{alerta.tipo}</span><Search size={18} className={tema.subtitulo} /></div>
              <p className={`mt-5 text-lg font-black ${tema.titulo}`}>{formatarNomeProprio(alerta.nome)}</p>
              <p className={`mt-1 text-sm ${tema.subtitulo}`}>{formatarNomeProprio(alerta.orgao)}</p>
              <p className="mt-4 text-xl font-black text-goiasGreen">{moeda(alerta.valor)}</p>
              <p className={`mt-3 text-xs leading-5 ${tema.subtitulo}`}>{alerta.motivo}</p>
            </article>
          ))}
        </div>
        <button type="button" onClick={() => navegar('Alertas')} className={`mt-5 inline-flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-bold ${temaClaro ? 'border-gray-300 bg-white text-gray-800' : 'border-white/15 bg-white/5 text-white'}`}>Ver metodologia e evidências <ArrowRight size={17} /></button>
      </section>

      <section className={`grid grid-cols-1 gap-5 rounded-3xl border p-6 md:grid-cols-[1fr_auto] md:items-center md:p-8 ${temaClaro ? 'border-green-200 bg-green-50' : 'border-goiasGreen/25 bg-goiasGreen/10'}`}>
        <div className="flex items-start gap-4"><Building2 className="mt-1 shrink-0 text-goiasGreen" /><div><h3 className={`text-xl font-black ${tema.titulo}`}>Quer conferir um valor até o registro de origem?</h3><p className={`mt-2 max-w-2xl text-sm leading-6 ${tema.subtitulo}`}>Use o Explorador de Despesas para filtrar pagamentos por período, órgão ou fornecedor. Os resultados são paginados e podem ser exportados para conferência.</p></div></div>
        <button type="button" onClick={() => navegar('Despesas')} className="inline-flex items-center justify-center gap-2 rounded-lg bg-goiasGreen px-5 py-3 text-sm font-bold text-white hover:opacity-90">Investigar registros <ArrowRight size={17} /></button>
      </section>

      <details className={`rounded-2xl border p-5 ${tema.card}`}>
        <summary className={`flex cursor-pointer list-none items-center gap-3 font-bold ${tema.titulo}`}><HelpCircle size={20} className="text-goiasGreen" />Glossário: o que cada termo significa?</summary>
        <dl className={`mt-5 grid grid-cols-1 gap-5 text-sm leading-6 md:grid-cols-2 ${tema.subtitulo}`}>
          <div><dt className={`font-bold ${tema.titulo}`}>Empenhado</dt><dd>Reserva do orçamento para uma despesa planejada. Ainda não significa pagamento.</dd></div>
          <div><dt className={`font-bold ${tema.titulo}`}>Liquidado</dt><dd>Etapa em que a administração reconhece que o bem ou serviço foi entregue.</dd></div>
          <div><dt className={`font-bold ${tema.titulo}`}>Pago</dt><dd>Valor efetivamente desembolsado ao credor na etapa financeira.</dd></div>
          <div><dt className={`font-bold ${tema.titulo}`}>Alerta</dt><dd>Registro selecionado por uma regra analítica para revisão humana, sem conclusão de irregularidade.</dd></div>
        </dl>
      </details>

      <p className={`flex items-start gap-2 text-xs leading-5 ${tema.subtitulo}`}><AlertCircle size={16} className="mt-0.5 shrink-0" />Fonte primária: Portal de Dados Abertos do Estado de Goiás. Os números refletem a cobertura disponível e podem ser atualizados ou retificados pelo órgão publicador.</p>
    </div>
  );
}
