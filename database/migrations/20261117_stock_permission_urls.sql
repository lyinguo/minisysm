-- Normalize only known static warehouse function paths with accidental whitespace.
-- Keep function IDs, enabled flags and all role selections unchanged.
UPDATE func_perm SET url='/j2-store/otherin'
WHERE id='182' AND REPLACE(REPLACE(REPLACE(REPLACE(url,CHAR(13),''),CHAR(10),''),CHAR(9),''),' ','')='/j2-store/otherin';
UPDATE func_perm SET url='/j2-store/otherout/add'
WHERE id='194' AND REPLACE(REPLACE(REPLACE(REPLACE(url,CHAR(13),''),CHAR(10),''),CHAR(9),''),' ','')='/j2-store/otherout/add';
UPDATE func_perm SET url='/j2-store/transfer/query-transferList'
WHERE id='202' AND REPLACE(REPLACE(REPLACE(REPLACE(url,CHAR(13),''),CHAR(10),''),CHAR(9),''),' ','')='/j2-store/transfer/query-transferList';
