-- Reset sequences
SELECT setval('aprendizagens_essenciais_id_seq', (SELECT COALESCE(MAX(id), 1) FROM aprendizagens_essenciais));
SELECT setval('curriculum_skills_id_seq', (SELECT COALESCE(MAX(id), 1) FROM curriculum_skills));
SELECT setval('curriculum_contents_id_seq', (SELECT COALESCE(MAX(id), 1) FROM curriculum_contents));
