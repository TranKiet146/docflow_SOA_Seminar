param(
    [string]$BaseUrl = "http://localhost:8080",
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"

$temporaryFile = Join-Path `
    $env:TEMP `
    "docflow-recovery-test.md"

$workerStopped = $false


function Get-JobStatus {
    param([string]$JobId)

    return Invoke-RestMethod `
        "$BaseUrl/api/jobs/$JobId"
}


function Wait-ForFinishedJob {
    param([string]$JobId)

    $deadline = (Get-Date).AddSeconds(
        $TimeoutSeconds
    )

    $lastStatus = $null

    while ((Get-Date) -lt $deadline) {
        $job = Get-JobStatus -JobId $JobId

        if ($job.status -ne $lastStatus) {
            Write-Host `
                "Job status: $($job.status)"

            $lastStatus = $job.status
        }

        if ($job.status -eq "finished") {
            return $job
        }

        if ($job.status -eq "failed") {
            throw "Recovery job failed"
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
# Worker recovery test

This job must remain queued while the Worker is stopped.
It must finish after the Worker is started again.
"@ | Set-Content `
        -Encoding utf8 `
        $temporaryFile

    Write-Host "[1/5] Stopping Worker..."

    docker compose stop worker |
    Out-Host

    if ($LASTEXITCODE -ne 0) {
        throw "Could not stop Worker"
    }

    $workerStopped = $true

    Write-Host (
        "[2/5] Uploading document while " +
        "Worker is stopped..."
    )

    $rawResponse = & curl.exe `
        -sS `
        -X POST `
        "$BaseUrl/api/jobs" `
        -F "file=@$temporaryFile"

    if ($LASTEXITCODE -ne 0) {
        throw "Upload request failed"
    }

    $response = (
        $rawResponse |
        ConvertFrom-Json
    )

    $jobId = $response.job_id

    if (
        [string]::IsNullOrWhiteSpace(
            $jobId
        )
    ) {
        throw (
            "Upload did not return " +
            "a job_id: $rawResponse"
        )
    }

    Write-Host "Created job: $jobId"

    Write-Host (
        "[3/5] Confirming the job " +
        "remains queued..."
    )

    Start-Sleep -Seconds 2

    $waitingJob = Get-JobStatus `
        -JobId $jobId

    if ($waitingJob.status -ne "queued") {
        throw (
            "Expected queued status, " +
            "received: $($waitingJob.status)"
        )
    }

    Write-Host "PASS: job remained queued"

    Write-Host "[4/5] Starting Worker..."

    docker compose start worker |
    Out-Host

    if ($LASTEXITCODE -ne 0) {
        throw "Could not start Worker"
    }

    $workerStopped = $false

    Write-Host (
        "[5/5] Waiting for the queued " +
        "job to finish..."
    )

    Wait-ForFinishedJob `
        -JobId $jobId |
    Out-Null

    Write-Host (
        "PASS: queued job finished " +
        "after Worker recovery"
    )

    Write-Host (
        "ALL WORKER RECOVERY TESTS PASSED"
    )
}
finally {
    if ($workerStopped) {
        Write-Host (
            "Restoring Worker after test..."
        )

        docker compose start worker |
        Out-Null
    }

    Remove-Item `
        $temporaryFile `
        -ErrorAction SilentlyContinue
}