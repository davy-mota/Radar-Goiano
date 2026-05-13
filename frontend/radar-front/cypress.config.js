import { defineConfig } from "cypress";

export default defineConfig({
  e2e: {
    // Isso diz ao Cypress qual é o link padrão do seu site rodando no Vite
    baseUrl: 'http://localhost:5173', 
    setupNodeEvents(on, config) {
      // Aqui você pode adicionar plugins no futuro, se precisar
    },
  },
});