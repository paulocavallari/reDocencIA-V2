$ErrorActionPreference = "Stop"
$dep = "https://redocencia-e5u0s5kx1-paulocavallaris-projects.vercel.app"

function Enc([string]$v) { [uri]::EscapeDataString($v) }

$nivel = "Ensino Fundamental: Anos Finais"
$bimestre = 1

$anos = vercel curl "/api/curriculum/anos?nivel=$(Enc $nivel)" --deployment $dep | ConvertFrom-Json
$ano = $anos[0]

$disciplinas = vercel curl "/api/curriculum/disciplinas?nivel=$(Enc $nivel)&ano=$(Enc $ano)" --deployment $dep | ConvertFrom-Json
$disciplina = $disciplinas[0]

$aes = vercel curl "/api/curriculum/aes?nivel=$(Enc $nivel)&bimestre=$bimestre&ano=$(Enc $ano)&disciplina=$(Enc $disciplina)" --deployment $dep | ConvertFrom-Json
$ae = $aes[0]

$conteudos = vercel curl "/api/curriculum/conteudos?nivel=$(Enc $nivel)&ano=$(Enc $ano)&disciplina=$(Enc $disciplina)&ae_id=$($ae.id)" --deployment $dep | ConvertFrom-Json
$conteudo = $conteudos[0]

$habilidades = vercel curl "/api/curriculum/habilidades?nivel=$(Enc $nivel)&ano=$(Enc $ano)&disciplina=$(Enc $disciplina)&ae_id=$($ae.id)" --deployment $dep | ConvertFrom-Json
$ids = @($habilidades | Where-Object { $_.skill_category -in @('habilidade_priorizada','conhecimento_previo','habilidade_relacionada') } | Select-Object -First 2 | ForEach-Object { $_.id })

$payload = [ordered]@{
  nivel_ensino = $nivel
  bimestre = $bimestre
  ano_serie = $ano
  disciplina = $disciplina
  ae_id = $ae.id
  conteudos = @($conteudo.objetos_conhecimento)
  habilidades_ids = $ids
  objetivos = "Desenvolver compreensão prática do conteúdo e verificar aprendizagem com avaliação formativa."
  duracao = "50 minutos"
  orientacoes = "Priorizar exemplos próximos da realidade da turma e linguagem clara."
  material_context = $null
} | ConvertTo-Json -Depth 10 -Compress

$result = vercel curl "/api/ai/generate" --deployment $dep -- --request POST --header "Content-Type: application/json" --data "$payload" | ConvertFrom-Json

Write-Output "=== Requisição simulada OK ==="
Write-Output ("Disciplina: " + $disciplina)
Write-Output ("Turma: " + $ano)
Write-Output ("AE: " + $ae.ae_codigo)
Write-Output ("Skill IDs: " + ($ids -join ', '))
Write-Output ("Conteúdo: " + $conteudo.objetos_conhecimento)
Write-Output ""
Write-Output ("Prompt length: " + $result.prompt.Length)
Write-Output ("HTML length: " + $result.html.Length)
Write-Output ""
Write-Output "Prompt (primeiros 1000 chars):"
Write-Output ($result.prompt.Substring(0, [Math]::Min(1000, $result.prompt.Length)))
Write-Output ""
Write-Output "HTML (primeiros 1000 chars):"
Write-Output ($result.html.Substring(0, [Math]::Min(1000, $result.html.Length)))
