$ErrorActionPreference = 'Stop'
$env:TSO_DB_PATH = Join-Path $env:RUNNER_TEMP 'standard-release-smoke.sqlite3'
$env:TSO_ADMIN_INITIAL_PASSWORD = 'TemporaryTestPassword2026'
$env:TSO_ADMIN_USERNAME = 'Mrsameh'
$env:TSO_EDITION = 'standard'
$server = Start-Process -FilePath (Join-Path (Get-Location) 'runtime/python.exe') -ArgumentList '-m','uvicorn','backend.standard_app:app','--host','127.0.0.1','--port','19000' -PassThru -WindowStyle Hidden
try {
  $ready = $false
  for ($i = 0; $i -lt 30; $i++) {
    try {
      $health = Invoke-RestMethod 'http://127.0.0.1:19000/api/standard/health' -TimeoutSec 2
      if ($health.edition -eq 'standard') { $ready = $true; break }
    } catch { Start-Sleep -Seconds 2 }
  }
  if (-not $ready) { throw 'Standard HTTP server did not start' }
  $admin = New-Object Microsoft.PowerShell.Commands.WebRequestSession
  $body = @{username='Mrsameh';password=$env:TSO_ADMIN_INITIAL_PASSWORD} | ConvertTo-Json
  $login = Invoke-RestMethod 'http://127.0.0.1:19000/api/login' -Method Post -ContentType 'application/json' -Body $body -WebSession $admin
  if ($login.role -ne 'admin') { throw 'Admin login failed' }
  $student = @{username='standard_test_student';password='StudentPassword123';student_code='ST-TEST-001';full_name='Test Student';grade='Primary 3'} | ConvertTo-Json
  Invoke-RestMethod 'http://127.0.0.1:19000/api/students' -Method Post -ContentType 'application/json' -Body $student -WebSession $admin | Out-Null
  $questions = @()
  for ($i=1; $i -le 20; $i++) {
    $questions += @{grade='Primary 3';unit='Unit 1';lesson='Lesson 1';difficulty='easy';kind='choose';prompt="Test question $i";answer='A';options=@('A','B','C')}
  }
  $bank = @{format='the-special-one-question-bank';version=1;questions=$questions} | ConvertTo-Json -Depth 8
  $bankPath = Join-Path $env:RUNNER_TEMP 'standard-test-bank.json'
  [System.IO.File]::WriteAllText($bankPath,$bank,[System.Text.Encoding]::UTF8)
  $import = Invoke-RestMethod 'http://127.0.0.1:19000/api/admin/question-bank/import' -Method Post -Form @{file=Get-Item $bankPath} -WebSession $admin
  if ($import.imported -ne 20) { throw 'Question import failed' }
  $draftBody = @{title='Standard Release Smoke Test';grade='Primary 3';count=20} | ConvertTo-Json
  $draft = Invoke-RestMethod 'http://127.0.0.1:19000/api/admin/exam-drafts' -Method Post -Body $draftBody -ContentType 'application/json' -WebSession $admin
  $published = Invoke-RestMethod ("http://127.0.0.1:19000/api/standard/publish/"+$draft.id) -Method Post -WebSession $admin
  $studentSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
  $studentLogin = @{username='standard_test_student';password='StudentPassword123'} | ConvertTo-Json
  Invoke-RestMethod 'http://127.0.0.1:19000/api/login' -Method Post -Body $studentLogin -ContentType 'application/json' -WebSession $studentSession | Out-Null
  $exams = Invoke-RestMethod 'http://127.0.0.1:19000/api/standard/exams' -WebSession $studentSession
  if (@($exams).Count -ne 1) { throw 'Published exam not visible to student' }
  $exam = Invoke-RestMethod ("http://127.0.0.1:19000/api/standard/exams/"+$published.id) -WebSession $studentSession
  if ($exam.questions.Count -ne 20) { throw 'Wrong question count' }
  if ($exam.questions[0].PSObject.Properties.Name -contains 'answer') { throw 'Answer key leaked' }
  $answers = @{}
  foreach ($q in $exam.questions) { $answers[$q.id] = 'A' }
  $submission = @{attempt_id='standard-smoke-attempt-0001';answers=$answers} | ConvertTo-Json -Depth 6
  $result = Invoke-RestMethod ("http://127.0.0.1:19000/api/standard/exams/"+$published.id+"/submit") -Method Post -Body $submission -ContentType 'application/json' -WebSession $studentSession
  if ($result.score -ne 20) { throw 'Exam scoring failed' }
  $history = Invoke-RestMethod 'http://127.0.0.1:19000/api/standard/my-attempts' -WebSession $studentSession
  if (@($history).Count -ne 1) { throw 'Student result not persisted' }
  Write-Host 'PASS: Standard login, import, publish, student access, grading, results'
} finally {
  Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
  Remove-Item Env:TSO_ADMIN_INITIAL_PASSWORD -ErrorAction SilentlyContinue
}
