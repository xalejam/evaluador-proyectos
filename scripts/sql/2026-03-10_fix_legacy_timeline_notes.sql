-- Ajustes de linea de tiempo para entradas historicas (legacy)
-- Fecha: 2026-03-10

-- LA-DDD-0002
UPDATE project_notes
SET progress_percent = 50
WHERE entry_group_id = 'c6f86fc312e34d3386d5544406e98fcc'
  AND project_id = 'LA-DDD-0002';

UPDATE project_notes
SET estimated_end_date = '2026-01-30'
WHERE entry_group_id = '26736f785cee4a149f6ff56cf645d411'
  AND project_id = 'LA-DDD-0002';

UPDATE project_notes
SET estimated_end_date = '2026-02-07'
WHERE entry_group_id = 'd52ea0171432445e83a4645db40488c2'
  AND project_id = 'LA-DDD-0002';

UPDATE project_notes
SET estimated_end_date = '2026-02-17'
WHERE entry_group_id = '809ddba728934aa6b9f3ea7e5b592e25'
  AND project_id = 'LA-DDD-0002';

UPDATE project_notes
SET estimated_end_date = '2026-02-23'
WHERE entry_group_id = 'c6f86fc312e34d3386d5544406e98fcc'
  AND project_id = 'LA-DDD-0002';

-- MX-DDD-0003
DELETE FROM project_notes
WHERE entry_group_id = '601f277995d743b4aa6d98a93733a6bd'
  AND project_id = 'MX-DDD-0003';
