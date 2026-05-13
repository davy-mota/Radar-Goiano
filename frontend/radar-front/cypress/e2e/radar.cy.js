describe('Radar Goiano - Testes de Interface e Integração', () => {
  
  beforeEach(() => {
    // O Cypress sempre vai acessar a página inicial antes de cada teste
    cy.visit('/');
  });

  it('Deve carregar a página inicial e exibir o título do sistema', () => {
    // Verifica se o nome do projeto está na tela
    cy.contains('h1', 'Radar Goiano').should('be.visible');
    
    // Verifica se o menu carregou
    cy.contains('button', 'Visão Geral').should('be.visible');
  });

  it('Deve alternar para o Tema Claro com sucesso', () => {
    // O padrão inicial do App.jsx é o tema escuro. Vamos testar o botão!
    cy.contains('button', 'Modo Claro').click();
    
    // O texto do botão deve mudar para "Modo Escuro"
    cy.contains('button', 'Modo Escuro').should('be.visible');
    
    // CORREÇÃO: Procura a div principal do seu layout em vez da div do React
    cy.get('.flex.h-screen').should('have.class', 'bg-gray-50');
  });

  it('Deve navegar para a aba Folha de Pagamento e renderizar os KPIs', () => {
    cy.contains('button', 'Folha de Pagamento').click();
    
    cy.contains('h2', 'Folha de Pagamento (todos)').should('be.visible');
    
    cy.contains('TOTAL DA FOLHA').should('be.visible');
    cy.contains('QTD. SERVIDORES').should('be.visible');
    cy.contains('MÉDIA SALARIAL').should('be.visible');
  });

  it('CRÍTICO: Deve exibir o Alerta da Inteligência Artificial na Folha', () => {
    cy.contains('button', 'Folha de Pagamento').click();
    
    // CORREÇÃO: Manda o Cypress "rolar a tela" até o alerta da IA aparecer
    cy.contains('h3', 'Malha Fina da Inteligência Artificial')
      .scrollIntoView()
      .should('be.visible');
      
    cy.contains('O algoritmo Isolation Forest').should('be.visible');
    
    // Garante que pelo menos um alerta foi desenhado na tela
    cy.contains('Salário com desvio estatístico').should('exist');
  });

  // --- TESTE 1: ABA PADRÃO (VISÃO GERAL) ---
  it('Deve renderizar os KPIs principais na aba inicial (Visão Geral)', () => {
    // Como é a aba padrão, não precisa clicar no menu
    cy.contains('h2', 'Raio-X (todos)').should('be.visible');
    
    // Verifica se os cards de indicadores carregaram
    cy.contains('CUSTO TOTAL AUDITADO').should('be.visible');
    cy.contains('ÓRGÃO MAIS CUSTOSO').should('be.visible');
    cy.contains('MAIOR DESPESA ÚNICA').should('be.visible');
    cy.contains('ALERTA TETO SALARIAL').should('be.visible');
  });

  // --- TESTE 2: RADAR DE DESTAQUES (SCROLL) ---
  it('Deve exibir o Radar de Destaques na Visão Geral', () => {
    // Rola a página para baixo para ver os destaques especiais
    cy.contains('h3', 'Radar de Destaques').scrollIntoView().should('be.visible');
    
    // Verifica se os blocos roxos e azuis da interface apareceram
    cy.contains('O MAIOR VIAJANTE').should('be.visible');
    cy.contains('A EMPRESA FAVORITA').should('be.visible');
  });

  // --- TESTE 3: ABA DE CONTRATOS ---
  it('Deve navegar para a aba Contratos e exibir seus indicadores', () => {
    cy.contains('button', 'Contratos').click();
    
    cy.contains('h2', 'Auditoria de Contratos (todos)').should('be.visible');
    
    // Confirma se os KPIs específicos de licitações estão na tela
    cy.contains('TOTAL CONTRATADO').should('be.visible');
    cy.contains('QTD. CONTRATOS').should('be.visible');
    cy.contains('TICKET MÉDIO').should('be.visible');
    
    // Rola a tela e verifica se o título do gráfico carregou
    cy.contains('h3', 'Maiores Fornecedores').scrollIntoView().should('be.visible');
  });

  // --- TESTE 4: ABA DE DIÁRIAS ---
  it('Deve navegar para a aba Diárias e Viagens e exibir seus painéis', () => {
    cy.contains('button', 'Diárias e Viagens').click();
    
    cy.contains('h2', 'Diárias e Passagens (todos)').should('be.visible');
    
    // Confirma se os KPIs de logística carregaram
    cy.contains('TOTAL GASTO').should('be.visible');
    cy.contains('MAIOR DIÁRIA').should('be.visible');
    
    // Confirma se os títulos dos gráficos de viagens estão visíveis
    cy.contains('h3', 'Top Viajantes').scrollIntoView().should('be.visible');
    cy.contains('h3', 'Top Destinos').should('be.visible');
  });

  // --- TESTE 5: INTERAÇÃO COM O FILTRO DE ANO ---
  it('Deve alterar o ano de exercício no menu e atualizar os dados da tela', () => {
    // O Cypress busca o elemento <select> na tela e escolhe a opção "2026"
    cy.get('select').select('2026');
    
    // Verifica se o título principal da página atualizou dinamicamente para o ano selecionado
    cy.contains('h2', 'Raio-X (2026)').should('be.visible');
    
    // Testa voltar para "Todos os Anos" ("todos" é o valor da tag <option>)
    cy.get('select').select('todos');
    cy.contains('h2', 'Raio-X (todos)').should('be.visible');
  });
});