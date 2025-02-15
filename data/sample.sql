SELECT distinct *,
CASE ADR6.ADDRNUMBER WHEN 'DE' THEN 'YES' ELSE 'NO' END as IN_DE
FROM LFA1
LEFT JOIN LFB1 ON LFA1.MANDT = LFB1.MANDT AND LFA1.LIFNR = LFB1.LIFNR
LEFT JOIN ADR6 ON LFA1.ADRNR = ADR6.ADDRNUMBER AND LFA1.MANDT = ADR6.CLIENT
LEFT JOIN T001 ON  LFB1.MANDT = T001.MANDT AND LFB1.BUKRS = T001.BUKRS
WHERE ADR6.CLIENT = 800
ORDER BY LFA1.MANDT ASC