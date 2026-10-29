-- Dashboard de Operação: "Taxa de aderência semanal por cliente"
-- Dono: time de Operações | Última alteração: mar/2026
SELECT
    v.cliente_id,
    DATE_TRUNC('week', CAST(v.data_servico AS DATE))                 AS semana,
    COUNT(*)                                                          AS vagas_abertas,
    COUNT(DISTINCT CASE WHEN a.status = 'realizado' THEN v.vaga_id END) AS vagas_preenchidas,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN a.status = 'realizado' THEN v.vaga_id END)
          / COUNT(DISTINCT v.vaga_id), 1)                             AS taxa_aderencia_pct
FROM vagas v
LEFT JOIN atendimentos a ON a.vaga_id = v.vaga_id
GROUP BY 1, 2
ORDER BY 1, 2;
