import { BookOpen, Info } from 'lucide-react';
import { useTema } from '../theme.js';

export default function ContextoTela({ temaClaro, etiqueta, titulo, descricao, pergunta, ressalva, children }) {
  const tema = useTema(temaClaro);
  return (
    <header className={`mb-6 rounded-2xl border p-5 md:p-7 ${tema.card}`}>
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <p className="mb-2 text-xs font-black uppercase tracking-[0.18em] text-goiasGreen">{etiqueta}</p>
          <h2 className={`text-2xl font-black tracking-tight md:text-3xl ${tema.titulo}`}>{titulo}</h2>
          <p className={`mt-3 text-sm leading-6 md:text-base ${tema.subtitulo}`}>{descricao}</p>
        </div>
        {children && <div className="shrink-0">{children}</div>}
      </div>
      {(pergunta || ressalva) && <div className="mt-5 grid gap-3 md:grid-cols-2">
        {pergunta && <div className={`flex items-start gap-3 rounded-xl p-4 text-sm leading-6 ${temaClaro ? 'bg-green-50 text-green-950' : 'bg-goiasGreen/10 text-green-100'}`}><BookOpen size={19} className="mt-0.5 shrink-0 text-goiasGreen" /><p><strong>Pergunta que esta tela responde:</strong> {pergunta}</p></div>}
        {ressalva && <div className={`flex items-start gap-3 rounded-xl p-4 text-sm leading-6 ${temaClaro ? 'bg-blue-50 text-blue-950' : 'bg-blue-400/10 text-blue-100'}`}><Info size={19} className="mt-0.5 shrink-0" /><p><strong>Como interpretar:</strong> {ressalva}</p></div>}
      </div>}
    </header>
  );
}
