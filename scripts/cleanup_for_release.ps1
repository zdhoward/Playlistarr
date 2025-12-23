# PowerShell script to clean up project before public release
# Run this before your first git commit
# This script can be run from anywhere but operates on the project root

# Change to project root (parent of scripts directory)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "Playlistarr - Release Cleanup Script" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host "Working directory: $projectRoot"
Write-Host ""

$errors = 0
$warnings = 0
$pattern = 'AIzaSy[A-Za-z0-9_-]{33}'

# Function to check file exists
function Test-FileExists {
    param($Path, $Description)
    if (Test-Path $Path) {
        Write-Host "Pass: $Description exists" -ForegroundColor Green
        return $true
    }
    else {
        Write-Host "FAIL: $Description missing!" -ForegroundColor Red
        $script:errors++
        return $false
    }
}

# Function to check file doesn't exist
function Test-FileNotExists {
    param($Path, $Description)
    if (-not (Test-Path $Path)) {
        Write-Host "Pass: $Description not present (good)" -ForegroundColor Green
        return $true
    }
    else {
        Write-Host "WARN: $Description exists - should be in .gitignore!" -ForegroundColor Yellow
        $script:warnings++
        return $false
    }
}

# Function to search for secrets in files
function Test-NoSecrets {
    param($Pattern, $Description, $ExcludeFiles = @())

    try {
        $found = Get-ChildItem -Path . -Filter "*.py" -File -ErrorAction SilentlyContinue |
                 Where-Object { $ExcludeFiles -notcontains $_.Name } |
                 Select-String -Pattern $Pattern -ErrorAction SilentlyContinue |
                 Select-Object -First 5

        if ($found) {
            Write-Host "FAIL: SECURITY - Found $Description in files!" -ForegroundColor Red
            $found | ForEach-Object { Write-Host "  $($_.Filename):$($_.LineNumber)" -ForegroundColor Red }
            $script:errors++
            return $false
        }
        else {
            Write-Host "Pass: No $Description found" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "WARN: Could not check for $Description" -ForegroundColor Yellow
        $script:warnings++
        return $false
    }
}

Write-Host "1. Checking Required Files..." -ForegroundColor Yellow
Write-Host "------------------------------------------------------------"

Test-FileExists "README.md" "README"
Test-FileExists "LICENSE" "License"
Test-FileExists "CONTRIBUTING.md" "Contributing guide"
Test-FileExists "CHANGELOG.md" "Changelog"
Test-FileExists ".gitignore" ".gitignore"
Test-FileExists "requirements.txt" "Requirements"
Test-FileExists ".env.example" ".env example"
Test-FileExists "config.sample.py" "Config sample"

Write-Host ""
Write-Host "2. Checking Core Scripts..." -ForegroundColor Yellow
Write-Host "------------------------------------------------------------"

Test-FileExists "config.py" "Config"
Test-FileExists "filters.py" "Filters"
Test-FileExists "utils.py" "Utils"
Test-FileExists "api_manager.py" "API Manager"
Test-FileExists "client.py" "Client"
Test-FileExists "discover_music_videos.py" "Discovery script"
Test-FileExists "youtube_playlist_sync.py" "Sync script"
Test-FileExists "playlist_invalidate.py" "Invalidation plan script"
Test-FileExists "playlist_apply_invalidation.py" "Invalidation apply script"

Write-Host ""
Write-Host "3. Security Check - Sensitive Files..." -ForegroundColor Yellow
Write-Host "------------------------------------------------------------"

Test-FileNotExists "auth/client_secrets.json" "OAuth secrets"
Test-FileNotExists "auth/oauth_token.json" "OAuth token"
Test-FileNotExists ".env" ".env file"
Test-FileNotExists "config_local.py" "Local config"

Write-Host ""
Write-Host "4. Security Check - API Keys in Code..." -ForegroundColor Yellow
Write-Host "------------------------------------------------------------"

# Exclude sample files and scripts from security checks
$excludeFiles = @('config.sample.py', 'verify_release.py', 'cleanup_for_release.ps1')

Test-NoSecrets "AIzaSy[A-Za-z0-9_-]{33}" "exposed API keys" $excludeFiles
Test-NoSecrets "YOUR_API_KEY" "placeholder API keys" $excludeFiles

Write-Host ""
Write-Host "5. Checking .gitignore..." -ForegroundColor Yellow
Write-Host "------------------------------------------------------------"

$gitignoreFile = ".gitignore"
if (Test-Path $gitignoreFile) {
    $gitignoreContent = Get-Content $gitignoreFile -Raw
    $requiredPatterns = @("auth/", "cache/", "out/", ".env", "*.pyc", "__pycache__")

    foreach ($pattern in $requiredPatterns) {
        $escaped = [regex]::Escape($pattern)
        $matches = $gitignoreContent -match $escaped
        if ($matches) {
            Write-Host "Pass: .gitignore contains '$pattern'" -ForegroundColor Green
        }
        else {
            Write-Host "FAIL: .gitignore missing '$pattern'!" -ForegroundColor Red
            $errors++
        }
    }
}
else {
    Write-Host "FAIL: .gitignore file not found!" -ForegroundColor Red
    $errors++
}

Write-Host ""
Write-Host "6. Checking Python Syntax..." -ForegroundColor Yellow
Write-Host "------------------------------------------------------------"

$pythonFiles = Get-ChildItem -Path . -Filter "*.py" -File
foreach ($pyFile in $pythonFiles) {
    $compileResult = python -m py_compile $pyFile.Name 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Pass: $($pyFile.Name) syntax OK" -ForegroundColor Green
    }
    else {
        Write-Host "FAIL: $($pyFile.Name) has syntax errors!" -ForegroundColor Red
        Write-Host "  $compileResult" -ForegroundColor Red
        $errors++
    }
}

Write-Host ""
Write-Host "7. Checking for Debug Code..." -ForegroundColor Yellow
Write-Host "------------------------------------------------------------"

$debugChecks = @{
    'print('            = "debug print statements"
    'pdb.set_trace()'   = "debugger breakpoints"
    'import pdb'        = "pdb imports"
    '# TODO'            = "TODO comments"
    '# FIXME'           = "FIXME comments"
}

foreach ($key in $debugChecks.Keys) {
    $searchResult = Get-ChildItem -Path . -Recurse -Filter "*.py" | Select-String -Pattern $key -SimpleMatch 2>$null

    if ($searchResult) {
        Write-Host "WARN: Found $($debugChecks[$key])" -ForegroundColor Yellow
        $warnings++
    }
    else {
        Write-Host "Pass: No $($debugChecks[$key])" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "8. Checking Directory Structure..." -ForegroundColor Yellow
Write-Host "------------------------------------------------------------"

$directories = @("auth", "cache", "out")
foreach ($directory in $directories) {
    if (Test-Path $directory) {
        Write-Host "Pass: $directory/ directory exists" -ForegroundColor Green
        $readmePath = Join-Path $directory "README.md"
        if (Test-Path $readmePath) {
            Write-Host "  Pass: $directory/README.md exists" -ForegroundColor Green
        }
        else {
            Write-Host "  WARN: $directory/README.md missing (optional)" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "WARN: $directory/ directory missing (will be created on first run)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "9. Checking GitHub Configuration..." -ForegroundColor Yellow
Write-Host "------------------------------------------------------------"

Test-FileExists ".github/workflows/ci.yml" "GitHub Actions CI"
Test-FileExists ".github/ISSUE_TEMPLATE/bug_report.md" "Bug report template"
Test-FileExists ".github/ISSUE_TEMPLATE/feature_request.md" "Feature request template"

Write-Host ""
Write-Host "============================================================"
Write-Host ""

if ($errors -eq 0 -and $warnings -eq 0) {
    Write-Host "SUCCESS! Project is ready for public release!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Review all files one more time"
    Write-Host "  2. Create GitHub repository"
    Write-Host "  3. git init"
    Write-Host "  4. git add ."
    Write-Host "  5. git commit -m 'Initial commit - v1.0.0'"
    Write-Host "  6. git push"
    Write-Host ""
}
elseif ($errors -eq 0) {
    Write-Host "Project has $warnings warnings but is OK to release" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Review warnings above and fix if needed." -ForegroundColor Yellow
    Write-Host ""
}
else {
    Write-Host "Project has $errors errors and $warnings warnings!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Fix all errors before releasing!" -ForegroundColor Red
    Write-Host ""
    exit 1
}