"""Recorte determinístico e relacionamentos TPC-H usados na extração."""


def sampled_lineitems(limit):
    sql = "SELECT * FROM lineitem ORDER BY l_orderkey, l_linenumber"
    return (sql + " LIMIT %s", (limit,)) if limit else (sql, ())


def extraction_sql(limit):
    sample, params = sampled_lineitems(limit)
    # LEFT JOIN mantém itens órfãos visíveis para a checagem de qualidade.
    return f"""
SELECT l.l_orderkey, l.l_linenumber, l.l_shipdate, l.l_commitdate,
       l.l_receiptdate, l.l_shipmode, l.l_quantity, l.l_suppkey, l.l_partkey,
       s.s_name AS fornecedor_nome, sn.n_name AS fornecedor_nacao,
       sr.r_name AS fornecedor_regiao, p.p_brand, p.p_type,
       o.o_custkey, c.c_custkey AS cliente_encontrado, c.c_mktsegment,
       cn.n_name AS cliente_nacao, cr.r_name AS cliente_regiao
FROM ({sample}) AS l
LEFT JOIN orders o ON o.o_orderkey = l.l_orderkey
LEFT JOIN customer c ON c.c_custkey = o.o_custkey
LEFT JOIN nation cn ON cn.n_nationkey = c.c_nationkey
LEFT JOIN region cr ON cr.r_regionkey = cn.n_regionkey
LEFT JOIN supplier s ON s.s_suppkey = l.l_suppkey
LEFT JOIN nation sn ON sn.n_nationkey = s.s_nationkey
LEFT JOIN region sr ON sr.r_regionkey = sn.n_regionkey
LEFT JOIN part p ON p.p_partkey = l.l_partkey
ORDER BY l.l_orderkey, l.l_linenumber
""", params


def reference_sql(limit):
    """Cálculos independentes em SQL para validar a transformação Python."""
    extraction, params = extraction_sql(limit)
    return f"""
SELECT origem.*,
       (l_receiptdate > l_commitdate) AS esperado_atrasada,
       GREATEST(DATEDIFF(l_receiptdate, l_commitdate), 0) AS esperado_dias,
       DATE_FORMAT(l_commitdate, '%%Y-%%m') AS esperado_mes
FROM ({extraction}) AS origem
ORDER BY l_orderkey, l_linenumber
""", params
