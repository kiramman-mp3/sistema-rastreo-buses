param (
    [string]$AndroidBuildId = "25d09c94-6af6-453d-acdf-9076630de5e9",
    [string]$IosBuildId = "86f05305-a049-494b-bb29-9328136e4da6"
)

$rootDir = Split-Path -Parent $PSScriptRoot
$distDir = Join-Path $rootDir "dist-mobile"

if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir -Force | Out-Null
}

$androidDone = [string]::IsNullOrEmpty($AndroidBuildId)
$iosDone = [string]::IsNullOrEmpty($IosBuildId)

Write-Host "Iniciando monitoreo de builds EAS..."
Write-Host "Android Build ID: $AndroidBuildId"
Write-Host "iOS Build ID:     $IosBuildId"

function Get-BuildInfo([string]$buildId) {
    Push-Location "$rootDir\apps\conductor-tablet"
    try {
        $output = npx --no-install eas-cli build:view $buildId --json 2>$null
    }
    finally {
        Pop-Location
    }

    if (-not $output) { return $null }

    $jsonStart = $output.IndexOf('{')
    if ($jsonStart -ge 0) {
        $jsonStr = $output.Substring($jsonStart)
        try {
            return ($jsonStr | ConvertFrom-Json)
        }
        catch {
            return $null
        }
    }
    return $null
}

function Extract-ArtifactUrl($build) {
    if (-not $build.artifacts) { return $null }
    
    if ($build.artifacts.buildUrl) {
        return $build.artifacts.buildUrl
    }
    if ($build.artifacts.applicationArchiveUrl) {
        return $build.artifacts.applicationArchiveUrl
    }
    
    # Check all properties of artifacts object
    foreach ($prop in $build.artifacts.PSObject.Properties) {
        if ($prop.Value -and ($prop.Value -like "http*")) {
            return $prop.Value
        }
    }
    return $null
}

while (-not ($androidDone -and $iosDone)) {
    $time = Get-Date -Format "HH:mm:ss"
    
    # Check Android
    if (-not $androidDone) {
        $buildA = Get-BuildInfo $AndroidBuildId
        if ($buildA) {
            $statusA = $buildA.status
            Write-Host "[$time] Android ($AndroidBuildId): $statusA"
            if ($statusA -eq "FINISHED") {
                $urlA = Extract-ArtifactUrl $buildA
                if ($urlA) {
                    $targetA = Join-Path $distDir "conductor-tablet.apk"
                    Write-Host "Descargando Android APK desde $urlA..."
                    curl.exe -L -o "$targetA" "$urlA"
                    Write-Host "APK guardado exitosamente en: $targetA"
                    $androidDone = $true
                } else {
                    Write-Host "Android terminado pero no se encontró URL de artefacto!"
                    $androidDone = $true
                }
            } elseif ($statusA -eq "ERRORED" -or $statusA -eq "CANCELED") {
                Write-Host "Android falló o fue cancelado: $statusA"
                $androidDone = $true
            }
        }
    }

    # Check iOS
    if (-not $iosDone) {
        $buildI = Get-BuildInfo $IosBuildId
        if ($buildI) {
            $statusI = $buildI.status
            Write-Host "[$time] iOS ($IosBuildId): $statusI"
            if ($statusI -eq "FINISHED") {
                $urlI = Extract-ArtifactUrl $buildI
                if ($urlI) {
                    $targetI = Join-Path $distDir "conductor-tablet.ipa"
                    Write-Host "Descargando iOS IPA desde $urlI..."
                    curl.exe -L -o "$targetI" "$urlI"
                    Write-Host "IPA guardado exitosamente en: $targetI"
                    $iosDone = $true
                } else {
                    Write-Host "iOS terminado pero no se encontró URL de artefacto!"
                    $iosDone = $true
                }
            } elseif ($statusI -eq "ERRORED" -or $statusI -eq "CANCELED") {
                Write-Host "iOS falló o fue cancelado: $statusI"
                $iosDone = $true
            }
        }
    }

    if (-not ($androidDone -and $iosDone)) {
        Start-Sleep -Seconds 30
    }
}

Write-Host "Proceso de monitoreo y descarga completado."
