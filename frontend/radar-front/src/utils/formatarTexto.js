const CONECTIVOS = new Set(['de', 'da', 'do', 'das', 'dos', 'e', 'em', 'a', 'o', 'com', 'para']);
const SUFIXOS_SOCIETARIOS = new Set(['ltda', 'me', 'epp', 'eireli', 'sa', 's.a']);

// A fonte publica nomes de órgão/credor ora em CAIXA ALTA, ora em minúsculas,
// nunca em Title Case. Só reformata texto que está inteiramente em um dos dois
// casos — texto já misto passa intacto, para não estragar algo já correto.
// eslint-disable-next-line no-control-regex
const TEM_CARACTERE_DE_CONTROLE = /[\x00-\x1f\x7f-\x9f]/;

export function formatarNomeProprio(texto) {
  if (!texto) return texto;
  const normalizado = texto.trim();
  if (!normalizado) return normalizado;
  // texto com caractere de controle indica bytes UTF-8 decodificados como Latin-1
  // na origem (fora deste utilitário); mexer na capitalização só disfarçaria a
  // corrupção em vez de expor que o dado está errado.
  if (TEM_CARACTERE_DE_CONTROLE.test(normalizado)) return normalizado;

  const tudoMaiusculo = normalizado === normalizado.toUpperCase() && normalizado !== normalizado.toLowerCase();
  const tudoMinusculo = normalizado === normalizado.toLowerCase();
  if (!tudoMaiusculo && !tudoMinusculo) return normalizado;

  const formatado = normalizado.toLowerCase().split(' ').map((palavra, indice) => {
    if (!palavra) return palavra;
    const semPontuacao = palavra.replace(/[.,]/g, '');
    if (SUFIXOS_SOCIETARIOS.has(semPontuacao)) return palavra.toUpperCase();
    if (indice > 0 && CONECTIVOS.has(palavra)) return palavra;
    return palavra.charAt(0).toUpperCase() + palavra.slice(1);
  }).join(' ')
    // "s a" ao final (variação sem pontuação de "S.A.") vira "S.A"
    .replace(/\bS a$/, 'S.A');

  // padrão frequente em nomes de órgão: "Nome Completo - SIGLA"
  const partes = formatado.split(' - ');
  const ultima = partes[partes.length - 1];
  if (partes.length > 1 && ultima.length <= 15 && !ultima.includes(' ')) {
    partes[partes.length - 1] = ultima.toUpperCase();
  }
  return partes.join(' - ');
}
