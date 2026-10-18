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
  $initialVisibility = Invoke-RestMethod 'http://127.0.0.1:19000/api/admin/standard/visibility' -WebSession $admin
  if (@($initialVisibility).Count -ne 0) { throw 'Expected empty published exams on fresh database' }
  $student = @{username='standard_test_student';password='StudentPassword123';student_code='ST-TEST-001';full_name='Test Student';grade='Primary 3'} | ConvertTo-Json
  Invoke-RestMethod 'http://127.0.0.1:19000/api/students' -Method Post -ContentType 'application/json' -Body $student -WebSession $admin | Out-Null
  $publicSignup = @{username='public_signup_student';password='StudentPassword456';full_name='Public Signup Student';grade='Primary 4';role='admin'} | ConvertTo-Json
  $registered = Invoke-RestMethod 'http://127.0.0.1:19000/api/standard/register' -Method Post -Body $publicSignup -ContentType 'application/json'
  if ($registered.role -ne 'student' -or -not $registered.student_code) { throw 'Public signup must create student role only' }
  $publicSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
  $publicLogin = @{username='public_signup_student';password='StudentPassword456'} | ConvertTo-Json
  $publicIdentity = Invoke-RestMethod 'http://127.0.0.1:19000/api/login' -Method Post -Body $publicLogin -ContentType 'application/json' -WebSession $publicSession
  if ($publicIdentity.role -ne 'student') { throw 'Public student login failed or role escalation detected' }
  $denied = $false
  try { Invoke-RestMethod 'http://127.0.0.1:19000/api/students' -WebSession $publicSession | Out-Null } catch { if ([int]$_.Exception.Response.StatusCode -eq 403) { $denied=$true } }
  if (-not $denied) { throw 'Public student gained admin privileges' }
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
  Invoke-RestMethod ('http://127.0.0.1:19000/api/admin/standard/visibility/'+$published.id+'/show') -Method Post -WebSession $admin | Out-Null
  $studentSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
  $studentLogin = @{username='standard_test_student';password='StudentPassword123'} | ConvertTo-Json
  Invoke-RestMethod 'http://127.0.0.1:19000/api/login' -Method Post -Body $studentLogin -ContentType 'application/json' -WebSession $studentSession | Out-Null
  $studentDeniedAdmin = $false
  try {
    Invoke-RestMethod 'http://127.0.0.1:19000/api/admin/standard/visibility' -WebSession $studentSession | Out-Null
  } catch {
    if ([int]$_.Exception.Response.StatusCode -eq 403) { $studentDeniedAdmin = $true }
  }
  if (-not $studentDeniedAdmin) { throw 'Student was not blocked from admin exam controls' }
  $studentDeniedScores = $false
  try { Invoke-RestMethod 'http://127.0.0.1:19000/api/admin/standard/results' -WebSession $studentSession | Out-Null } catch { if ([int]$_.Exception.Response.StatusCode -eq 403) { $studentDeniedScores = $true } }
  if (-not $studentDeniedScores) { throw 'Student was not blocked from admin results' }
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
  Invoke-RestMethod ('http://127.0.0.1:19000/api/admin/standard/visibility/'+$published.id+'/hide') -Method Post -WebSession $admin | Out-Null
  $hidden = @(Invoke-RestMethod 'http://127.0.0.1:19000/api/standard/exams' -WebSession $studentSession)
  if ($hidden.Count -ne 0) { throw 'Hidden teacher exam was still listed' }
  Invoke-RestMethod ('http://127.0.0.1:19000/api/admin/standard/visibility/'+$published.id+'/show') -Method Post -WebSession $admin | Out-Null
  $builderBody = @{title='Filtered Unit Exam';grade='Primary 3';units=@('Unit 1');kinds=@('choose');count=20} | ConvertTo-Json
  $filteredDraft = Invoke-RestMethod 'http://127.0.0.1:19000/api/admin/standard/build' -Method Post -ContentType 'application/json' -Body $builderBody -WebSession $admin
  if ($filteredDraft.question_count -ne 20) { throw 'Filtered exam builder failed' }
  $studentFilters = Invoke-RestMethod 'http://127.0.0.1:19000/api/standard/practice-filters' -WebSession $studentSession
  if ($studentFilters.grade -ne 'Primary 3') { throw 'Student grade filter failed' }
  $practiceBody = @{units=@('Unit 1');kinds=@('choose');count=20} | ConvertTo-Json
  $practice = Invoke-RestMethod 'http://127.0.0.1:19000/api/standard/practice-create' -Method Post -ContentType 'application/json' -Body $practiceBody -WebSession $studentSession
  $practiceExam = Invoke-RestMethod ('http://127.0.0.1:19000/api/standard/practice/'+$practice.id) -WebSession $studentSession
  if ($practiceExam.questions.Count -ne 20) { throw 'Custom practice question count incorrect' }
  if ($practiceExam.questions[0].PSObject.Properties.Name -contains 'answer') { throw 'Practice answer leaked' }
  $practiceSubmission = @{attempt_id='practice-test-attempt-0001';answers=$answers} | ConvertTo-Json -Depth 6
  $practiceResult = Invoke-RestMethod ('http://127.0.0.1:19000/api/standard/practice/'+$practice.id+'/submit') -Method Post -ContentType 'application/json' -Body $practiceSubmission -WebSession $studentSession
  if ($practiceResult.score -ne 20) { throw 'Custom practice scoring incorrect' }
  $overview = Invoke-RestMethod 'http://127.0.0.1:19000/api/admin/standard/results' -WebSession $admin
  if ($overview.total -ne 2) { throw 'Admin dashboard should show both teacher and practice attempts' }
  $filtered = Invoke-RestMethod 'http://127.0.0.1:19000/api/admin/standard/results?grade=Primary%203' -WebSession $admin
  if ($filtered.total -ne 2 -or $filtered.students -ne 1) { throw 'Admin grade filtering failed' }
  if ($filtered.teacher_attempts -ne 1 -or $filtered.practice_attempts -ne 1) { throw 'Filtered teacher/practice counters incorrect' }
  $emptyGrade = Invoke-RestMethod 'http://127.0.0.1:19000/api/admin/standard/results?grade=Primary%204' -WebSession $admin
  if ($emptyGrade.total -ne 0 -or $emptyGrade.teacher_attempts -ne 0 -or $emptyGrade.practice_attempts -ne 0) { throw 'Other grade results leaked into filtered counters' }
  foreach ($path in @('export.xlsx','export.pdf','print')) {
    $blocked = $false
    try { Invoke-WebRequest ('http://127.0.0.1:19000/api/admin/standard/'+$path) -WebSession $studentSession | Out-Null } catch { if ([int]$_.Exception.Response.StatusCode -eq 403) { $blocked = $true } }
    if (-not $blocked) { throw ('Student was able to access '+$path) }
  }
  $xlsxPath = Join-Path $env:RUNNER_TEMP 'tso-results-test.xlsx'
  $pdfPath = Join-Path $env:RUNNER_TEMP 'tso-results-test.pdf'
  Invoke-WebRequest 'http://127.0.0.1:19000/api/admin/standard/export.xlsx?grade=Primary%203' -WebSession $admin -OutFile $xlsxPath
  Invoke-WebRequest 'http://127.0.0.1:19000/api/admin/standard/export.pdf?grade=Primary%203' -WebSession $admin -OutFile $pdfPath
  $xlsxBytes = [System.IO.File]::ReadAllBytes($xlsxPath)
  $pdfBytes = [System.IO.File]::ReadAllBytes($pdfPath)
  if ($xlsxBytes.Length -lt 1000 -or $xlsxBytes[0] -ne 80 -or $xlsxBytes[1] -ne 75) { throw 'Excel report is not a valid XLSX archive' }
  if ($pdfBytes.Length -lt 1000 -or [System.Text.Encoding]::ASCII.GetString($pdfBytes,0,4) -ne '%PDF') { throw 'PDF report is not valid' }
  & ./runtime/python.exe -c 'from openpyxl import load_workbook; from pypdf import PdfReader; import os; from pathlib import Path; d=Path(os.environ["RUNNER_TEMP"]); w=load_workbook(d/"tso-results-test.xlsx",read_only=True); assert w.active.max_row>=7; p=PdfReader(str(d/"tso-results-test.pdf")); assert len(p.pages)>0; print("PDF and Excel parsed successfully")'
  if ($LASTEXITCODE -ne 0) { throw 'Report document parsing failed' }
  & ./runtime/python.exe -c 'from openpyxl import load_workbook; import os; from pathlib import Path; w=load_workbook(Path(os.environ["RUNNER_TEMP"])/"tso-results-test.xlsx",read_only=True); assert w.active["A6"].value=="Test Student"; print("Excel student data verified")'
  if ($LASTEXITCODE -ne 0) { throw 'Exported Excel did not contain expected student' }
  $printPage = Invoke-WebRequest 'http://127.0.0.1:19000/api/admin/standard/print?grade=Primary%203' -WebSession $admin
  if ($printPage.Content -notmatch 'THE SPECIAL ONE') { throw 'Print view failed' }
  Write-Host 'PASS: login, import, publish, activation, student exam, practice, grading, results'
} finally {
  Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
  Remove-Item Env:TSO_ADMIN_INITIAL_PASSWORD -ErrorAction SilentlyContinue
}
