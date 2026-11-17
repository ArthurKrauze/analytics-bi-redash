-- Conferência manual no MySQL para ETL_LIMIT=0 (base inteira).
-- Para um limite positivo use o script etl.validate, que aplica o recorte exato.
SELECT COUNT(*) AS total_itens,
       SUM(l_receiptdate > l_commitdate) AS itens_atrasados,
       SUM(GREATEST(DATEDIFF(l_receiptdate,l_commitdate),0)) AS dias_atraso_total,
       ROUND(100.0 * SUM(l_receiptdate > l_commitdate) / NULLIF(COUNT(*),0),2) AS taxa_atraso_percentual,
       ROUND(SUM(GREATEST(DATEDIFF(l_receiptdate,l_commitdate),0)) /
             NULLIF(SUM(l_receiptdate > l_commitdate),0),2) AS media_dias_atraso
FROM lineitem;

SELECT l_shipmode AS modalidade, COUNT(*) AS total_itens,
       SUM(l_receiptdate > l_commitdate) AS itens_atrasados,
       ROUND(100.0 * SUM(l_receiptdate > l_commitdate) / COUNT(*),2) AS taxa_atraso_percentual
FROM lineitem GROUP BY l_shipmode ORDER BY taxa_atraso_percentual DESC, modalidade;

SELECT DATE_FORMAT(l_commitdate,'%Y-%m') AS mes_compromisso,
       COUNT(*) AS total_itens, SUM(l_receiptdate > l_commitdate) AS itens_atrasados,
       ROUND(100.0 * SUM(l_receiptdate > l_commitdate) / COUNT(*),2) AS taxa_atraso_percentual
FROM lineitem GROUP BY mes_compromisso ORDER BY mes_compromisso;
