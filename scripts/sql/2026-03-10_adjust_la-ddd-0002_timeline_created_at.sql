-- Ajuste de fechas historicas para conservar linea de tiempo real
-- Proyecto: LA-DDD-0002
-- Fecha de registro del ajuste: 2026-03-10

UPDATE project_notes
SET created_at = '2026-01-30 20:58:15'
WHERE entry_group_id = '26736f785cee4a149f6ff56cf645d411'
  AND project_id = 'LA-DDD-0002';

UPDATE project_notes
SET created_at = '2026-02-07 20:59:31'
WHERE entry_group_id = 'd52ea0171432445e83a4645db40488c2'
  AND project_id = 'LA-DDD-0002';

UPDATE project_notes
SET created_at = '2026-02-17 21:01:08'
WHERE entry_group_id = '809ddba728934aa6b9f3ea7e5b592e25'
  AND project_id = 'LA-DDD-0002';

UPDATE project_notes
SET created_at = '2026-02-23 21:01:44'
WHERE entry_group_id = 'c6f86fc312e34d3386d5544406e98fcc'
  AND project_id = 'LA-DDD-0002';
