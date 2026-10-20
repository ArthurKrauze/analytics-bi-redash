# Modelo conceitual e implementação do protótipo

```text
                  DIM_TEMPO
                      |
DIM_CLIENTE --- FATO_VENDAS --- DIM_PRODUTO
                      |
                DIM_FORNECEDOR
```

**Grão:** um item do pedido TPC-H (`l_orderkey`, `l_linenumber`).

| Origem | Destino MongoDB | Observação |
|---|---|---|
| `orders.o_orderdate` | `dataPedido` | Data do pedido, não expedição |
| `orders.o_orderkey` | `pedidoId` | Contagem de pedidos exige `distinct` |
| `lineitem.l_linenumber` | `numeroItem` | Chave com pedido |
| `customer` + `nation` + `region` | `cliente` | Região do cliente |
| `part` | `produto` | Marca e tipo |
| `supplier` + `nation` + `region` | `fornecedor` | Região do fornecedor |
| `lineitem.l_quantity` | `quantidade` | Medida aditiva |
| `lineitem.l_extendedprice` | `precoBase` | Valor antes do desconto |
| `lineitem.l_discount` | `desconto` | Fração (0 a 1) |
| preço × (1 − desconto) | `receitaLiquida` | Arredondada a centavos por item |

A implementação usa **embedding** das dimensões na coleção `fato_vendas`:
é um *modelo dimensional conceitual*, **não** quatro coleções de dimensão físicas.
A escolha reduz `$lookup` nas consultas demonstrativas e duplica descrições
dimensionais em cada item. O TDE deve discutir essa troca e alternativas
com `referencing` ou modelagem híbrida.

**Não** some `orders.o_totalprice` por item: isso multiplica o total do pedido.
O preço líquido não inclui impostos (`l_tax`); não é lucro nem margem.
Valores monetários em `float` são apenas uma simplificação didática; em
produção use Decimal128 ou inteiros de centavos.

**Amostragem:** `ORDER BY l_orderkey, l_linenumber LIMIT 10000` não é amostra
aleatória nem estratificada. Evite inferências sobre o universo TPC-H.
