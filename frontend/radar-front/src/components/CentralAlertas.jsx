import { useEffect, useState } from 'react';
import { AlertTriangle, BarChart3, Copy, Loader2, ShieldAlert, TrendingUp } from 'lucide-react';
import { formatarNomeProprio } from '../utils/formatarTexto.js';
import { useTema } from '../theme.js';
import ContextoTela from './ContextoTela.jsx';


const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const TIPOS = ['duplicidade', 'concentracao', 'variacao_mensal', 'atipico_iqr'];
const ICONES = { duplicidade: Copy, concentracao: BarChart3, variacao_mensal: TrendingUp, atipico_iqr: AlertTriangle };
const moeda = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(valor || 0));
const percentual = (valor) => `${Number(valor || 0).toFixed(1)}%`;


function Evidencia({ tipo, item, titulo, secundario }) {
  if (tipo === 'duplicidade') return <><p className={`font-semibold ${titulo}`}>{formatarNomeProprio(item.favorecido)}</p><p className={`text-xs ${secundario}`}>{formatarNomeProprio(item.orgao)} · Empenho {item.numero_empenho || 'não informado'}</p><p className="mt-2 text-sm text-amber-500">{item.repeticoes} registros de {moeda(item.valor_pago)} · agregado {moeda(item.valor_agregado)}</p></>;
  if (tipo === 'concentracao') return <><p className={`font-semibold ${titulo}`}>{formatarNomeProprio(item.favorecido)}</p><p className={`text-xs ${secundario}`}>{formatarNomeProprio(item.orgao)}</p><p className="mt-2 text-sm text-amber-500">{percentual(item.concentracao_percentual)} do órgão · {moeda(item.valor)}</p></>;
  if (tipo === 'variacao_mensal') return <><p className={`font-semibold ${titulo}`}>{formatarNomeProprio(item.orgao)}</p><p className={`text-xs ${secundario}`}>Mês {item.mes_anterior} para mês {item.mes}</p><p className="mt-2 text-sm text-amber-500">+{percentual(item.variacao_percentual)} · {moeda(item.valor_anterior)} para {moeda(item.valor_atual)}</p></>;
  return <><p className={`font-semibold ${titulo}`}>{formatarNomeProprio(item.favorecido)}</p><p className={`text-xs ${secundario}`}>{formatarNomeProprio(item.orgao)} · Empenho {item.numero_empenho || 'não informado'}</p><p className="mt-2 text-sm text-amber-500">{moeda(item.valor_pago)} · limite estatístico {moeda(item.limite_superior)}</p></>;
}


function CentralAlertas({ anoInicial, temaClaro }) {
  const anoPadrao = anoInicial === 'todos' || Number(anoInicial) > 2025 ? '2025' : anoInicial;
  const [ano, setAno] = useState(anoPadrao);
  const [grupos, setGrupos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    Promise.all(TIPOS.map(async (tipo) => {
      const resposta = await fetch(`${API_URL}/api/alertas?ano=${ano}&tipo=${tipo}`, { signal: controller.signal });
      if (!resposta.ok) throw new Error('Não foi possível calcular os alertas.');
      const resultado = await resposta.json();
      return resultado.grupos[0];
    })).then(setGrupos).catch((falha) => {
      if (falha.name !== 'AbortError') setErro(falha.message);
    }).finally(() => {
      if (!controller.signal.aborted) setCarregando(false);
    });
    return () => controller.abort();
  }, [ano]);

  const alterarAno = (evento) => {
    setCarregando(true);
    setErro('');
    setGrupos([]);
    setAno(evento.target.value);
  };

  const { card, titulo, secundario, campo } = useTema(temaClaro);
  const total = grupos.reduce((soma, grupo) => soma + Number(grupo.total), 0);

  return (
    <div className="animate-fade-in">
      <ContextoTela temaClaro={temaClaro} etiqueta="Priorizar não é acusar" titulo="Central de Alertas Explicáveis" descricao="Quatro regras reproduzíveis reduzem milhões de registros a uma lista menor para conferência humana." pergunta="Quais padrões merecem abrir o documento original e buscar uma explicação administrativa?" ressalva="O total representa ocorrências de regras, não casos comprovados. Um mesmo registro pode aparecer em mais de uma regra e possuir justificativa legítima.">
        <select aria-label="Ano dos alertas" value={ano} onChange={alterarAno} className={`border rounded-lg p-3 text-sm ${campo}`}>{Array.from({ length: 2025 - 2003 + 1 }, (_, indice) => 2025 - indice).map((item) => <option key={item} value={item}>{item}</option>)}</select>
      </ContextoTela>

      <div className="mb-6 flex gap-3 p-4 rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-600"><ShieldAlert className="shrink-0" /><p className="text-sm"><strong>Alerta não é acusação.</strong> Os resultados indicam padrões nos dados publicados e precisam de contexto documental e análise humana.</p></div>
      {erro && <div role="alert" className="mb-6 p-4 rounded-lg border border-red-500/40 bg-red-500/10 text-red-500">{erro}</div>}
      {carregando && <div className="h-56 flex flex-col items-center justify-center gap-3"><Loader2 className="animate-spin text-goiasGreen" size={42} /><p className={secundario}>Aplicando quatro regras aos dados de {ano}...</p></div>}

      {!carregando && grupos.length > 0 && <>
        <div className="grid grid-cols-2 xl:grid-cols-5 gap-4 mb-6">
          <div className={`border rounded-xl p-5 ${card}`}><p className={`text-xs uppercase font-semibold ${secundario}`}>Total de indícios</p><p className="text-2xl font-bold text-amber-500 mt-1">{total.toLocaleString('pt-BR')}</p></div>
          {grupos.map((grupo) => { const Icone = ICONES[grupo.tipo]; return <div key={grupo.tipo} className={`border rounded-xl p-5 ${card}`}><div className="flex items-center gap-2"><Icone size={18} className="text-amber-500" /><p className={`text-xs uppercase font-semibold ${secundario}`}>{grupo.titulo}</p></div><p className={`text-2xl font-bold mt-2 ${titulo}`}>{Number(grupo.total).toLocaleString('pt-BR')}</p></div>; })}
        </div>

        <div className="space-y-5">
          {grupos.map((grupo) => { const Icone = ICONES[grupo.tipo]; return <details key={grupo.tipo} className={`border rounded-xl overflow-hidden ${card}`}>
            <summary className="p-5 cursor-pointer list-none flex items-center justify-between gap-4"><div className="flex items-center gap-3"><Icone className="text-amber-500" /><div><h3 className={`font-bold ${titulo}`}>{grupo.titulo}</h3><p className={`text-xs mt-1 ${secundario}`}>{Number(grupo.total).toLocaleString('pt-BR')} ocorrências · exibindo até {grupo.itens.length}</p></div></div><span className={`text-sm ${secundario}`}>Ver evidências</span></summary>
            <div className="border-t border-gray-500/20 p-5"><div className="grid lg:grid-cols-2 gap-4 mb-5"><div className={`p-4 rounded-lg ${temaClaro ? 'bg-gray-50' : 'bg-black/20'}`}><p className={`text-xs uppercase font-semibold mb-1 ${secundario}`}>Regra</p><p className={`text-sm ${titulo}`}>{grupo.regra}</p></div><div className="p-4 rounded-lg bg-amber-500/10"><p className="text-xs uppercase font-semibold mb-1 text-amber-600">Limitação</p><p className="text-sm text-amber-600">{grupo.ressalva}</p></div></div>
              <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">{grupo.itens.map((item, indice) => <div key={`${grupo.tipo}-${indice}`} className={`border rounded-lg p-4 ${temaClaro ? 'border-gray-200' : 'border-darkBorder'}`}><Evidencia tipo={grupo.tipo} item={item} titulo={titulo} secundario={secundario} /></div>)}</div>
            </div>
          </details>; })}
        </div>
      </>}
    </div>
  );
}

export default CentralAlertas;
