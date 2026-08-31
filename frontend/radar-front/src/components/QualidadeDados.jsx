import { useEffect, useState } from 'react';
import { CheckCircle2, ExternalLink, History, Loader2, XCircle } from 'lucide-react';
import { useTema } from '../theme.js';
import ContextoTela from './ContextoTela.jsx';


const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const rotuloMetrica = (nome) => ({
  empenho_preenchido_pct: 'Empenho preenchido', orgao_preenchido_pct: 'Órgão preenchido',
  credor_preenchido_pct: 'Credor preenchido', previsao_positiva_pct: 'Previsão positiva',
  categoria_preenchida_pct: 'Categoria econômica preenchida',
  documento_preenchido_pct: 'Documento preenchido', objeto_preenchido_pct: 'Objeto preenchido',
  cargo_preenchido_pct: 'Cargo preenchido', destino_preenchido_pct: 'Destino preenchido',
  motivo_preenchido_pct: 'Motivo preenchido',
}[nome] || nome);


function QualidadeDados({ temaClaro }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetch(`${API_URL}/api/metadados`, { signal: controller.signal }),
      fetch(`${API_URL}/api/cargas?limite=20`, { signal: controller.signal }),
    ])
      .then(async ([respostaMetadados, respostaCargas]) => {
        if (!respostaMetadados.ok || !respostaCargas.ok) throw new Error('Não foi possível consultar a qualidade dos dados.');
        const [metadados, historico] = await Promise.all([respostaMetadados.json(), respostaCargas.json()]);
        return { ...metadados, cargas: historico.cargas };
      })
      .then(setDados).catch((falha) => { if (falha.name !== 'AbortError') setErro(falha.message); });
    return () => controller.abort();
  }, []);

  const { card, titulo, secundario } = useTema(temaClaro);

  if (erro) return <div role="alert" className="p-5 rounded-xl border border-red-500/40 bg-red-500/10 text-red-500">{erro}</div>;
  if (!dados) return <div className="h-64 flex items-center justify-center"><Loader2 className="animate-spin text-goiasGreen" size={42} /></div>;

  return (
    <div className="animate-fade-in">
      <ContextoTela temaClaro={temaClaro} etiqueta="Antes de interpretar, verifique a base" titulo="Qualidade e Proveniência dos Dados" descricao="Veja cobertura temporal, preenchimento, fonte e histórico das cargas que sustentam os indicadores." pergunta="Até onde os dados permitem chegar e quais limitações precisam acompanhar qualquer conclusão?" ressalva="Campo preenchido não significa campo correto. Os percentuais medem completude estrutural; exatidão e coerência exigem validações adicionais contra a fonte." />
      <div className={`mb-6 p-4 rounded-xl border ${temaClaro ? 'bg-blue-50 border-blue-200 text-blue-800' : 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300'}`}>{dados.observacao}</div>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {dados.conjuntos.map((conjunto) => <section key={conjunto.id} className={`border rounded-xl p-5 ${card}`}>
          <div className="flex items-start justify-between gap-4 mb-5"><div><h3 className={`text-lg font-bold ${titulo}`}>{conjunto.nome}</h3><p className={`text-sm ${secundario}`}>{Number(conjunto.registros).toLocaleString('pt-BR')} registros · {conjunto.ano_min || '—'} a {conjunto.ano_max || '—'}</p></div><a href={conjunto.fonte} target="_blank" rel="noreferrer" aria-label={`Abrir fonte de ${conjunto.nome}`} className="text-goiasGreen"><ExternalLink size={19} /></a></div>
          {conjunto.maior_data_referencia && <p className={`text-xs mb-4 ${secundario}`}>Maior data de referência: {new Date(`${conjunto.maior_data_referencia}T00:00:00`).toLocaleDateString('pt-BR')}</p>}
          <p className={`text-xs mb-4 ${secundario}`}>Métricas calculadas em: {new Date(conjunto.calculado_em).toLocaleString('pt-BR')}</p>
          <div className="space-y-4">{Object.entries(conjunto.qualidade).map(([nome, valor]) => <div key={nome}><div className="flex justify-between text-sm"><span className={titulo}>{rotuloMetrica(nome)}</span><strong className={Number(valor) < 70 ? 'text-amber-500' : 'text-green-500'}>{Number(valor).toFixed(2)}%</strong></div><div className="h-2 mt-2 rounded bg-gray-500/20"><div className={`h-full rounded ${Number(valor) < 70 ? 'bg-amber-500' : 'bg-goiasGreen'}`} style={{ width: `${Math.min(100, Number(valor))}%` }} /></div></div>)}</div>
        </section>)}
      </div>
      <section className={`border rounded-xl p-5 mt-6 ${card}`}>
        <div className="flex items-center gap-3 mb-4"><History className="text-goiasGreen" size={21} /><div><h3 className={`text-lg font-bold ${titulo}`}>Histórico de cargas</h3><p className={`text-xs ${secundario}`}>Execuções registradas prospectivamente pelo processo de importação</p></div></div>
        {dados.cargas.length === 0 ? <p className={`text-sm py-5 ${secundario}`}>Nenhuma carga auditada ainda. As execuções anteriores à implantação deste recurso não podem ser reconstruídas.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-sm"><thead><tr className={`text-left border-b ${temaClaro ? 'border-gray-200' : 'border-darkBorder'} ${secundario}`}><th className="py-3 pr-4">Conjunto</th><th className="py-3 pr-4">Status</th><th className="py-3 pr-4">Início</th><th className="py-3 pr-4">Duração</th><th className="py-3 pr-4 text-right">Registros</th><th className="py-3">Fonte</th></tr></thead><tbody>{dados.cargas.map((carga) => <tr key={carga.id} className={`border-b last:border-0 ${temaClaro ? 'border-gray-100' : 'border-darkBorder'}`}><td className={`py-3 pr-4 font-medium capitalize ${titulo}`}>{carga.conjunto.replace(/_/g, ' ')}</td><td className="py-3 pr-4">{carga.status === 'sucesso' ? <span className="inline-flex items-center gap-1 text-green-500"><CheckCircle2 size={15} /> Sucesso</span> : carga.status === 'falha' ? <span className="inline-flex items-center gap-1 text-red-500" title={carga.mensagem_erro || ''}><XCircle size={15} /> Falha</span> : <span className="inline-flex items-center gap-1 text-amber-500"><Loader2 className="animate-spin" size={15} /> Em execução</span>}</td><td className={`py-3 pr-4 ${secundario}`}>{new Date(carga.iniciado_em).toLocaleString('pt-BR')}</td><td className={`py-3 pr-4 ${secundario}`}>{carga.duracao_segundos == null ? '—' : `${Number(carga.duracao_segundos).toFixed(1)} s`}</td><td className={`py-3 pr-4 text-right ${secundario}`}>{carga.registros_processados == null ? '—' : Number(carga.registros_processados).toLocaleString('pt-BR')}</td><td className={`py-3 ${secundario}`}>{carga.fonte?.startsWith('http') ? <a href={carga.fonte} target="_blank" rel="noreferrer" className="text-goiasGreen inline-flex items-center gap-1">Abrir <ExternalLink size={14} /></a> : carga.fonte}</td></tr>)}</tbody></table></div>}
      </section>
      <p className={`text-xs mt-6 ${secundario}`}>Percentual de preenchimento mede presença do campo, não exatidão semântica. Valores completos ainda podem conter erros da fonte.</p>
    </div>
  );
}

export default QualidadeDados;
