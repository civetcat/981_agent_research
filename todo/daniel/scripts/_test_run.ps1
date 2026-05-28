$ErrorActionPreference = "Continue"
$out = "C:\dev\stock-simulator\scripts\_test_out.log"
"=== RUN: $($args -join ' ') @ $(Get-Date -Format o) ===" | Out-File -FilePath $out -Append -Encoding utf8
& $args[0] 2>&1 | Tee-Object -FilePath $out -Append
"=== END exit=$LASTEXITCODE ===" | Out-File -FilePath $out -Append -Encoding utf8
