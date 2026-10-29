-- Report Comercial (enviado aos clientes): "Aderência"
-- Dono: time Comercial | Última alteração: jun/2026
-- Obs.: vagas canceladas pelo cliente não entram na conta.
WITH vagas_validas AS (
    SELECT *
    FROM vagas
    WHERE cancelada_cliente_em IS NULL
)
SELECT
    v.cliente_id,
    DATE_TRUNC('week', CAST(v.criada_em AS TIMESTAMP))               AS semana,
    COUNT(DISTINCT v.vaga_id)                                         AS vagas,
    COUNT(a.atendimento_id)                                           AS atendimentos_realizados,
    ROUND(100.0 * COUNT(a.atendimento_id) / COUNT(DISTINCT v.vaga_id), 1) AS aderencia_pct
FROM vagas_validas v
LEFT JOIN atendimentos a
       ON a.vaga_id = v.vaga_id
      AND LOWER(TRIM(a.status)) = 'realizado'
GROUP BY 1, 2
ORDER BY 1, 2;
