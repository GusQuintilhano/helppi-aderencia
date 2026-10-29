-- Fechamento Financeiro: "Aderência em horas e GBV"
-- Dono: time Financeiro | Última alteração: ago/2026
SELECT
    v.cliente_id,
    DATE_TRUNC('week', CAST(v.data_servico AS DATE))                 AS semana,
    SUM(v.horas_previstas)                                            AS horas_previstas,
    SUM(CASE WHEN LOWER(TRIM(a.status)) = 'realizado'
             THEN CAST(a.horas_realizadas AS NUMERIC) END)            AS horas_realizadas,
    ROUND(100.0 * SUM(CASE WHEN LOWER(TRIM(a.status)) = 'realizado'
                           THEN CAST(a.horas_realizadas AS NUMERIC) END)
          / SUM(v.horas_previstas), 1)                                AS aderencia_horas_pct,
    SUM(CASE WHEN LOWER(TRIM(a.status)) = 'realizado'
             THEN CAST(a.horas_realizadas AS NUMERIC) * p.preco_hora END) AS gbv
FROM vagas v
LEFT JOIN atendimentos a ON a.vaga_id = v.vaga_id
LEFT JOIN precos p
       ON p.cliente_id = v.cliente_id
      AND p.tipo_servico = v.tipo_servico
GROUP BY 1, 2
ORDER BY 1, 2;
