param (
    [string]$BuildId = "ea2a29db-d3d2-41ca-960f-f7e2e56f31c6"
)

$rootDir = Split-Path -Parent $PSScriptRoot
Write-Host "Esperando compilación de Android en EAS ($BuildId)..."

while ($true) {
    try {
        Push-Location "$rootDir\apps\conductor-tablet"
        $output = npx eas-cli build:view $BuildId --json 2>$null
        Pop-Location
        
        $jsonStart = $output.IndexOf('{')
        if ($jsonStart -ge 0) {
            $jsonStr = $output.Substring($jsonStart)
            $build = $jsonStr | ConvertFrom-Json
            $status = $build.status
            Write-Host "Estado actual: $status ($(Get-Date -Format 'HH:mm:ss'))"
            
            if ($status -eq "FINISHED") {
                $url = $build.artifacts.buildUrl
                if (-not $url) {
                    $url = $build.artifacts.applicationArchiveUrl
                }
                Write-Host "Descargando APK desde $url..."
                curl.exe -L -o "$rootDir\dist-mobile\conductor-tablet.apk" $url
                Write-Host "APK descargado con éxito en dist-mobile\conductor-tablet.apk"
                break
            }
            elseif ($status -eq "ERRORED" -or $status -eq "CANCELED") {
                Write-Host "La compilación terminó con error: $status"
                break
            }
        }
    }
    catch {
        Write-Host "Error consultando EAS: $_"
    }
    Start-Sleep -Seconds 45
}
