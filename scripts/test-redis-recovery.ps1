param(
    [string]$BaseUrl = "http://localhost:8080",
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"

$documentPath = Join-Path `
    $env:TEMP `
    "docflow-redis-recovery.md"

$responsePath = Join-Path `
    $env:TEMP `
    "docflow-redis-response.json"

$redisStopped = $false


function Upload-Document {
    $statusCode = & curl.exe `
        -sS `
        -o $responsePath `
        -w "%{http_code}" `
        -X POST `
        "$BaseUrl/api/jobs" `
        -F "file=@$documentPath"

    if ($LASTEXITCODE -ne 0) {
        throw (
            "Upload request could not " +
            "reach the Gateway"
        )
    }

    $body = Get-Content `
        -Raw `
        $responsePath

    return [PSCustomObject]@{
        StatusCode = [int]$statusCode
        Body = $body
    }
}


function Wait-ForRedisReadiness {
    $deadline = (Get-Date).AddSeconds(
        $TimeoutSeconds
    )

    while ((Get-Date) -lt $deadline) {
        docker compose exec `
            -T api `
            python -c `
            "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')" `
            2>$null |
            Out-Null

        if ($LASTEXITCODE -eq 0) {
            return
        }

        Start-Sleep -Seconds 1
    }

    throw (
        "API readiness did not recover " +
        "within $TimeoutSeconds seconds"
    )
}


function Wait-ForFinishedJob {
    param([string]$JobId)

    $deadline = (Get-Date).AddSeconds(
        $TimeoutSeconds
    )

    while ((Get-Date) -lt $deadline) {
        $job = Invoke-RestMethod `
            "$BaseUrl/api/jobs/$JobId"

        Write-Host `
            "Job status: $($job.status)"

        if ($job.status -eq "finished") {
            return
        }

        if ($job.status -eq "failed") {
            throw (
                "Job failed after " +
                "Redis recovery"
            )
        }

        Start-Sleep -Seconds 1
    }

    throw (
        "Job did not finish within " +
        "$TimeoutSeconds seconds"
    )
}


try {
    @"
# Redis recovery test

The first upload must fail while Redis is unavailable.
The second upload must finish after Redis recovers.
"@ | Set-Content `
        -Encoding utf8 `
        $documentPath

    Write-Host "[1/6] Stopping Redis..."

    docker compose stop redis |
        Out-Host

    if ($LASTEXITCODE -ne 0) {
        throw "Could not stop Redis"
    }

    $redisStopped = $true

    Start-Sleep -Seconds 2

    Write-Host (
        "[2/6] Confirming uploads " +
        "fail safely..."
    )

    $unavailableResponse = Upload-Document

    if ($unavailableResponse.StatusCode -ne 503) {
        throw (
            "Expected HTTP 503 while Redis " +
            "was stopped; received " +
            "$($unavailableResponse.StatusCode): " +
            $unavailableResponse.Body
        )
    }

    Write-Host (
        "PASS: API returned 503 while " +
        "Redis was unavailable"
    )

    Write-Host "[3/6] Starting Redis..."

    docker compose start redis |
        Out-Host

    if ($LASTEXITCODE -ne 0) {
        throw "Could not start Redis"
    }

    $redisStopped = $false

    Write-Host (
        "[4/6] Waiting for API readiness..."
    )

    Wait-ForRedisReadiness

    Write-Host (
        "PASS: API readiness recovered"
    )

    docker compose up -d worker |
        Out-Host

    Write-Host (
        "[5/6] Uploading after " +
        "Redis recovery..."
    )

    $recoveredResponse = Upload-Document

    if ($recoveredResponse.StatusCode -ne 202) {
        throw (
            "Expected HTTP 202 after " +
            "recovery; received " +
            "$($recoveredResponse.StatusCode): " +
            $recoveredResponse.Body
        )
    }

    $job = (
        $recoveredResponse.Body |
        ConvertFrom-Json
    )

    if (
        [string]::IsNullOrWhiteSpace(
            $job.job_id
        )
    ) {
        throw (
            "Recovered upload did not " +
            "return a job_id"
        )
    }

    Write-Host (
        "[6/6] Waiting for the recovered " +
        "job to finish..."
    )

    Wait-ForFinishedJob `
        -JobId $job.job_id

    Write-Host (
        "PASS: new jobs completed after " +
        "Redis recovery"
    )

    Write-Host (
        "ALL REDIS RECOVERY TESTS PASSED"
    )
}
finally {
    if ($redisStopped) {
        Write-Host (
            "Restoring Redis after test..."
        )

        docker compose start redis |
            Out-Null
    }

    docker compose up -d api worker |
        Out-Null

    Remove-Item `
        $documentPath `
        -ErrorAction SilentlyContinue

    Remove-Item `
        $responsePath `
        -ErrorAction SilentlyContinue
}