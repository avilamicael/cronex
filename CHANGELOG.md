# 📦 Changelog - Cronex


## [0.0.1] - 2025-05-15
### Alterado
- Ajustado um pouco a cor, deixado mais fraco

# 📦 Changelog - Cronex


## [0.0.1] - 2025-05-15
### Alterado
- Alterado a cor das linhas na listagem de contas a pagar

# 📦 Changelog - Cronex


## [0.0.1] - 2025-05-15
### Corrigido
- Ajustado campo fornecedor que estava buscando o primeiro fornecedor após um erro no formulario
- Ajustado campo transacao que estava ficando vazio apósum erro no formulario

# Changelog - Cronex

Todas as mudanças relevantes neste projeto serão documentadas aqui.

## [1.0.0] - 2025-05-15

### Adicionado
- Tela de **lançamento de contas a pagar**, com formulário completo (filial, transação, fornecedor, tipo de pagamento, datas, valores, descrição, código de barras e notas fiscais).
- Funcionalidade de **importação de contas** via arquivos `.csv` e `.xml`.
- Página de **listagem de contas a pagar** com múltiplos filtros (filial, transação, fornecedor, tipo pagamento, status, documento, notas, movimentação, vencimento).
- Tela de **baixa em lote de contas**, com aplicação de data global e cálculo automático de valor de pagamento (juros, multa, desconto, acréscimos).
- Máscaras e validações de campos numéricos, datas e selects com Select2 e Ajax.
- Componente de **alertas visuais customizados** com cores e ícones, adaptados via `base.css`.
- Select de **filial padrão** no topo do layout para filtragem global de ações por filial.

### Alterado
- Layout e estilo da tabela de contas para melhor leitura: truncamento de campos longos e colunas com largura mínima.
- Inclusão de filtros colapsáveis para melhorar a experiência em dispositivos menores.

### Corrigido
- Comportamento de selects (`filial`, `transação`, `tipo de pagamento`, `fornecedor`) para manter o valor selecionado após erro no formulário.
- Ajuste do campo `valor_bruto` para aplicar máscara de valor monetário e converter corretamente ao submeter.
- Correção do campo de transação que estava buscando o valor com variável incorreta (`tipo` ao invés de `transacao`).

---
